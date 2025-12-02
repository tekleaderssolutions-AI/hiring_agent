import json
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render

import pdfplumber
from io import BytesIO

from jd_agent import analyze_job_description
from ranker_agent import get_top_matches_for_role
from resume_agent import process_resume_text


def index(request):
    # Serve the pre-built static index.html
    print("Index view accessed")
    return FileResponse(open("static/index.html", "rb"))


@csrf_exempt
@require_POST
def init_db(request):
    try:
        # Run migrations using the project's DB initializer
        from django.core.management import call_command
        call_command('init_db')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'status': 'ok', 'message': 'migrations run'})


def _extract_pdf_text(contents: bytes) -> str:
    with pdfplumber.open(BytesIO(contents)) as pdf:
        return "\n".join([page.extract_text() or "" for page in pdf.pages])


@csrf_exempt
@require_POST
def analyze_jd_pdf(request):
    file = request.FILES.get('file')
    job_id = request.POST.get('job_id')
    source_url = request.POST.get('source_url')
    if not file:
        return JsonResponse({'error': 'file required'}, status=400)

    if not file.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'Only PDF supported'}, status=400)

    contents = file.read()
    raw_jd_text = _extract_pdf_text(contents)
    if not raw_jd_text.strip():
        return JsonResponse({'error': 'no text extracted'}, status=400)

    try:
        memory_json = analyze_job_description(
            raw_jd_text=raw_jd_text,
            job_id=job_id,
            source_url=source_url,
            created_by='jd_analyzer_agent_pdf',
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse(memory_json)


@csrf_exempt
@require_POST
def upload_resumes(request):
    files = request.FILES.getlist('files')
    source_url = request.POST.get('source_url')
    if not files:
        return JsonResponse({'error': 'no files uploaded'}, status=400)

    results = []
    for file in files:
        filename = file.name
        if not filename.lower().endswith('.pdf'):
            results.append({'file_name': filename, 'status': 'skipped', 'reason': 'not a PDF'})
            continue
        try:
            contents = file.read()
            raw_text = _extract_pdf_text(contents).strip()
            if not raw_text:
                results.append({'file_name': filename, 'status': 'error', 'reason': 'no text extracted'})
                continue
            processed = process_resume_text(raw_text=raw_text, source_url=source_url, file_name=filename)
            resume_id = processed.get('resume_id')
            parsed = processed.get('parsed', {})
            results.append({
                'file_name': filename,
                'status': 'ok',
                'resume_id': resume_id,
                'candidate_name': parsed.get('candidate_name'),
                'current_title': parsed.get('current_title'),
            })
        except Exception as e:
            results.append({'file_name': filename, 'status': 'error', 'reason': str(e)})

    return JsonResponse({'count': len(results), 'items': results})


@csrf_exempt
@require_POST
def get_top_matches_by_role(request):
    role_name = request.POST.get('role_name')
    top_k = int(request.POST.get('top_k', 3))
    if not role_name:
        return JsonResponse({'error': 'role_name required'}, status=400)
    try:
        matches = get_top_matches_for_role(role_name=role_name, top_k=top_k)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'role_name': role_name, 'top_k': top_k, 'matches': matches})


@csrf_exempt
@require_POST
def get_top_matches_by_jd_id(request):
    jd_id = request.POST.get('jd_id')
    top_k = int(request.POST.get('top_k', 3))
    
    if not jd_id:
        return JsonResponse({'error': 'jd_id required'}, status=400)
        
    try:
        from ranking import get_top_k_resumes_for_jd_memory
        matches = get_top_k_resumes_for_jd_memory(jd_memory_id=jd_id, top_k=top_k)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
        
    return JsonResponse({
        "jd_id": jd_id,
        "top_k": top_k,
        "matches": matches,
    })


@csrf_exempt
@require_POST
def send_emails_to_candidates(request):
    jd_id = request.POST.get('jd_id')
    # candidate_ids is expected to be a list of strings
    candidate_ids = request.POST.getlist('candidate_ids')
    
    # If sent as a single JSON string in one form field (common in some JS clients)
    if len(candidate_ids) == 1 and candidate_ids[0].startswith('['):
        try:
            candidate_ids = json.loads(candidate_ids[0])
        except:
            pass
            
    if not jd_id or not candidate_ids:
        return JsonResponse({'error': 'jd_id and candidate_ids required'}, status=400)
        
    from db import get_connection
    from mailing_agent import generate_personalized_email
    from email_sender import send_email
    import uuid
    
    results = []
    conn = get_connection()
    
    try:
        # Fetch JD details including embedding
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, canonical_json, embedding FROM memories WHERE id = %s",
            [jd_id]
        )
        jd_row = cur.fetchone()
        
        if not jd_row:
            return JsonResponse({'error': f"JD not found: {jd_id}"}, status=404)
        
        jd_data = {
            "id": jd_row[0],
            "title": jd_row[1],
            "canonical_json": jd_row[2],
            "role": jd_row[2].get("role") if jd_row[2] else "Position",
            "embedding": jd_row[3] # Get the JD embedding
        }
        
        # Process each candidate
        for idx, resume_id in enumerate(candidate_ids, start=1):
            try:
                # Fetch resume details AND calculate similarity on the fly
                # We use the JD embedding literal for the distance calculation
                jd_embedding_literal = jd_data["embedding"]
                
                cur.execute(
                    """
                    SELECT 
                        id, 
                        candidate_name, 
                        email, 
                        canonical_json, 
                        metadata, 
                        embedding,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM resumes 
                    WHERE id = %s
                    """,
                    [jd_embedding_literal, resume_id]
                )
                resume_row = cur.fetchone()
                
                if not resume_row:
                    results.append({
                        "resume_id": resume_id,
                        "status": "error",
                        "message": "Resume not found"
                    })
                    continue
                
                similarity = float(resume_row[6])
                ats_score = int(max(0.0, min(1.0, similarity)) * 100)
                
                candidate_data = {
                    "id": resume_row[0],
                    "candidate_name": resume_row[1],
                    "email": resume_row[2],
                    "canonical_json": resume_row[3],
                    "metadata": resume_row[4],
                    "embedding": resume_row[5]
                }
                
                candidate_email = candidate_data.get("email")
                if not candidate_email:
                    results.append({
                        "resume_id": resume_id,
                        "candidate_name": candidate_data.get("candidate_name"),
                        "status": "error",
                        "message": "No email address found"
                    })
                    continue
                
                # Create outreach record
                outreach_id = str(uuid.uuid4())
                
                # Generate personalized email
                email_content = generate_personalized_email(
                    candidate_data=candidate_data,
                    jd_data=jd_data,
                    outreach_id=outreach_id,
                    rank=idx,
                    ats_score=ats_score 
                )
                
                # Send email
                send_result = send_email(
                    to_email=candidate_email,
                    subject=email_content["subject"],
                    html_body=email_content["body"]
                )
                
                if send_result["success"]:
                    # Store in database with embedding and REAL ATS score
                    embedding_literal = candidate_data.get("embedding")
                    
                    cur.execute(
                        """
                        INSERT INTO candidate_outreach 
                        (id, resume_id, jd_id, candidate_email, candidate_name, 
                         email_subject, email_body, embedding, rank, ats_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s)
                        """,
                        [
                            outreach_id,
                            resume_id,
                            jd_id,
                            candidate_email,
                            candidate_data.get("candidate_name"),
                            email_content["subject"],
                            email_content["body"],
                            embedding_literal,
                            idx,
                            ats_score
                        ]
                    )
                    conn.commit()
                    
                    results.append({
                        "resume_id": resume_id,
                        "candidate_name": candidate_data.get("candidate_name"),
                        "email": candidate_email,
                        "status": "success",
                        "message": "Email sent successfully",
                        "ats_score": ats_score
                    })
                else:
                    results.append({
                        "resume_id": resume_id,
                        "candidate_name": candidate_data.get("candidate_name"),
                        "email": candidate_email,
                        "status": "error",
                        "message": send_result["message"]
                    })
                    
            except Exception as e:
                results.append({
                    "resume_id": resume_id,
                    "status": "error",
                    "message": str(e)
                })
        
        cur.close()
        
    except Exception as e:
        return JsonResponse({'error': f"Error sending emails: {str(e)}"}, status=500)
    finally:
        conn.close()    
        
    return JsonResponse({
        "total": len(candidate_ids),
        "sent": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results
    })


@csrf_exempt
def acknowledge_interest(request, outreach_id):
    response = request.GET.get('response')
    
    if response not in ['interested', 'not_interested']:
        return HttpResponse("Invalid response", status=400)
    
    from db import get_connection
    
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # Update acknowledgement and get JD info
        cur.execute(
            """
            UPDATE candidate_outreach 
            SET acknowledgement = %s, acknowledged_at = NOW(), updated_at = NOW()
            WHERE id = %s
            RETURNING candidate_name, jd_id
            """,
            [response, outreach_id]
        )
        
        row = cur.fetchone()
        conn.commit()
        cur.close()
        
        if not row:
            return HttpResponse("Outreach record not found", status=404)
        
        candidate_name = row[0] or "Candidate"
        jd_id = row[1]
        
        # Automatically schedule interview if candidate is interested
        if response == 'interested':
            try:
                from interview_scheduler import schedule_interview_for_single_candidate
                
                # Schedule for the first available date (automatically finds it)
                schedule_result = schedule_interview_for_single_candidate(
                    outreach_id=outreach_id,
                    num_slots=3
                )
                
                # Check if scheduling was successful
                if schedule_result.get('success'):
                    interview_date = schedule_result.get('interview_date')
                    message = f"Thank you, {candidate_name}! We've sent you an interview invitation email for {interview_date}. Please check your inbox and select your preferred time slot."
                elif 'message' in schedule_result:
                    # Already scheduled
                    message = f"Thank you, {candidate_name}! {schedule_result['message']}"
                else:
                    message = f"Thank you, {candidate_name}! We've recorded your interest and our team will contact you soon."
                    
            except Exception as e:
                # If scheduling fails, still acknowledge but don't show error to candidate
                print(f"Auto-scheduling failed: {e}")
                message = f"Thank you, {candidate_name}! We've recorded your interest and our team will contact you soon."
            
            color = "#10b981"
        else:
            message = f"Thank you for your response, {candidate_name}. We appreciate your time."
            color = "#6b7280"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Response Recorded - Tek Leaders</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background-color: #f3f4f6;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 500px;
        }}
        .icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: {color};
            margin-bottom: 20px;
        }}
        p {{
            color: #6b7280;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">{'✓' if response == 'interested' else '✗'}</div>
        <h1>Response Recorded</h1>
        <p>{message}</p>
    </div>
</body>
</html>
"""
        
        return HttpResponse(html_content)
        
    except Exception as e:
        return HttpResponse(f"Error recording acknowledgement: {str(e)}", status=500)
    finally:
        conn.close()


@csrf_exempt
def confirm_interview(request, interview_id):
    slot = request.GET.get('slot')
    outreach_id = request.GET.get('outreach_id')
    
    from interview_scheduler import confirm_interview_slot
    
    try:
        result = confirm_interview_slot(interview_id, slot, outreach_id)
        
        if "error" in result:
            # Log error for debugging
            import sys
            print(f"[ERROR] Interview confirmation failed: {result['error']}", file=sys.stderr)
            message = result["error"]
            color = "#dc3545"
            icon = "❌"
            meet_link = None
            event_link = None
        else:
            meet_link = result.get("meet_link")
            event_link = result.get("event_link")
            message = f"Your interview has been confirmed! Check your email for the Google Meet link and calendar invitation."
            color = "#28a745"
            icon = "✅"
        
        meet_html = ""
        if meet_link:
            meet_html = f"""
            <div style="margin-top: 20px; padding: 20px; background-color: #e8f5e9; border-radius: 8px; border-left: 4px solid #4caf50;">
                <p style="color: #2e7d32; font-weight: bold;">📹 Google Meet Link:</p>
                <a href="{meet_link}" style="color: #4caf50; text-decoration: none; word-break: break-all;">{meet_link}</a>
            </div>
            """
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Interview Confirmation - Tek Leaders</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 600px;
        }}
        .icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: {color};
            margin-bottom: 20px;
            font-size: 28px;
        }}
        p {{
            color: #333;
            line-height: 1.6;
            font-size: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">{icon}</div>
        <h1>Interview Confirmed</h1>
        <p>{message}</p>
        {meet_html}
    </div>
</body>
</html>
"""
        
        return HttpResponse(html_content)
        
    except Exception as e:
        return HttpResponse(f"Error confirming interview: {str(e)}", status=500)


@csrf_exempt
@require_POST
def schedule_interviews(request):
    jd_id = request.POST.get('jd_id')
    interview_date = request.POST.get('interview_date') # Format: YYYY-MM-DD
    
    if not jd_id or not interview_date:
        return JsonResponse({'error': 'jd_id and interview_date required'}, status=400)

    from interview_scheduler import schedule_interviews_for_interested_candidates
    from datetime import datetime
    
    try:
        # Parse the date
        date_obj = datetime.strptime(interview_date, "%Y-%m-%d")
        
        # Schedule interviews
        result = schedule_interviews_for_interested_candidates(
            jd_id=jd_id,
            interview_date=date_obj,
            num_slots=3
        )
        
        return JsonResponse(result)
        
    except ValueError as e:
        return JsonResponse({'error': f"Invalid date format: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({'error': f"Error scheduling interviews: {str(e)}"}, status=500)


@csrf_exempt
def get_interviews_status(request):
    jd_id = request.GET.get('jd_id')
    
    from db import get_connection
    
    conn = get_connection()
    
    try:
        cur = conn.cursor()
        
        if jd_id:
            query = """
                SELECT 
                    i.id,
                    i.interview_date,
                    i.status,
                    i.selected_slot,
                    i.confirmed_slot_time,
                    r.candidate_name,
                    r.email,
                    m.title as jd_title,
                    i.event_link,
                    i.event_id
                FROM interview_schedules i
                JOIN resumes r ON r.id = i.resume_id
                JOIN memories m ON m.id = i.jd_id
                WHERE i.jd_id = %s
                ORDER BY i.interview_date DESC, i.created_at DESC
            """
            cur.execute(query, [jd_id])
        else:
            query = """
                SELECT 
                    i.id,
                    i.interview_date,
                    i.status,
                    i.selected_slot,
                    i.confirmed_slot_time,
                    r.candidate_name,
                    r.email,
                    m.title as jd_title,
                    i.event_link,
                    i.event_id
                FROM interview_schedules i
                JOIN resumes r ON r.id = i.resume_id
                JOIN memories m ON m.id = i.jd_id
                ORDER BY i.interview_date DESC, i.created_at DESC
            """
            cur.execute(query)
        
        rows = cur.fetchall()
        cur.close()
        
        from config import INTERVIEWER_EMAIL
        
        interviews = []
        for row in rows:
            interviews.append({
                "interview_id": row[0],
                "interview_date": str(row[1]),
                "status": row[2],
                "selected_slot": row[3],
                "confirmed_time": str(row[4]) if row[4] else None,
                "candidate_name": row[5],
                "candidate_email": row[6],
                "jd_title": row[7],
                "event_link": row[8],
                "event_id": row[9],
                "interviewer_email": INTERVIEWER_EMAIL
            })
        
        return JsonResponse({
            "total": len(interviews),
            "interviews": interviews
        })
        
    except Exception as e:
        return JsonResponse({'error': f"Error fetching interviews: {str(e)}"}, status=500)
    finally:
        conn.close()
