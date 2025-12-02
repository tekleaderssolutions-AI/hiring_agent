# main.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional, List, Dict, Any
import pdfplumber
from io import BytesIO

from jd_agent import analyze_job_description
from ranker_agent import get_top_matches_for_role
from resume_agent import process_resume_text


 
app = FastAPI(title="JD Analyzer Agent")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Serve the minimal UI from ./static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_index():
    return FileResponse("static/index.html")


@app.post("/init-db")
def init_db_endpoint():
    """Run DB migrations (requires DB user to have extension creation rights).

    This endpoint is intentionally unprotected in this minimal example —
    in production protect it with auth.
    """
    try:
        import migrations

        migrations.init_db()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    return {"status": "ok", "message": "migrations run"}
 
@app.get("/debug")
def debug():
    import os
    return {
        "OPENROUTER_API_KEY_present": bool(os.environ.get("OPENROUTER_API_KEY")),
        "CHAT_MODEL": os.environ.get("CHAT_MODEL"),
        "EMBEDDING_MODEL": os.environ.get("EMBEDDING_MODEL"),
    }
 
def _extract_pdf_text(contents: bytes) -> str:
    with pdfplumber.open(BytesIO(contents)) as pdf:
        return "\n".join([page.extract_text() or "" for page in pdf.pages])


 
 
@app.post("/jd/analyze/pdf")
async def analyze_jd_pdf(
    job_id: Optional[str] = Form(default=None),
    source_url: Optional[str] = Form(default=None),
    file: UploadFile = File(...),   # required PDF
):
    """
    Analyze JD from uploaded PDF file.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
 
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
 
        raw_jd_text = _extract_pdf_text(contents)
 
        if not raw_jd_text.strip():
            raise HTTPException(status_code=400, detail="JD text is empty after PDF extraction")
 
        memory_json = analyze_job_description(
            raw_jd_text=raw_jd_text,
            job_id=job_id,
            source_url=source_url,
            created_by="jd_analyzer_agent_pdf",
        )
        
        # Add the database ID to the response for embedding-based matching
        # The memory_json already contains 'id' from jd_memory.create_memory
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error (pdf): {e}")
 
    return memory_json
 
 
@app.post("/resumes/upload")
async def upload_resumes(
    files: List[UploadFile] = File(...),
    source_url: Optional[str] = Form(default=None),
):
    """
    Upload MULTIPLE resume PDFs.
    For each:
      - Extract text
      - Parse with LLM
      - Store resume + vector
    Returns basic info for UI.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results: List[Dict[str, Any]] = []

    for file in files:
        filename = file.filename

        if not filename.lower().endswith(".pdf"):
            results.append({
                "file_name": filename,
                "status": "skipped",
                "reason": "not a PDF",
            })
            continue

        try:
            contents = await file.read()
            if not contents:
                results.append({
                    "file_name": filename,
                    "status": "error",
                    "reason": "empty file",
                })
                continue

            # Extract text from PDF
            raw_text = _extract_pdf_text(contents).strip()
            if not raw_text:
                results.append({
                    "file_name": filename,
                    "status": "error",
                    "reason": "no text extracted",
                })
                continue

            processed = process_resume_text(
                raw_text=raw_text,
                source_url=source_url,
                file_name=filename,
            )
            resume_id = processed["resume_id"]
            parsed = processed["parsed"]

            results.append({
                "file_name": filename,
                "status": "ok",
                "resume_id": resume_id,
                "candidate_name": parsed.get("candidate_name"),
                "current_title": parsed.get("current_title"),
            })

        except Exception as e:
            results.append({
                "file_name": filename,
                "status": "error",
                "reason": str(e),
            })

    return {
        "count": len(results),
        "items": results,
    }



    


@app.post("/match/top-by-role")
async def get_top_matches_by_role(
    role_name: str = Form(...),
    top_k: int = Form(3),
):
    """
    Input from UI:
      - role_name (e.g. 'Senior Data Scientist')
      - top_k (3 or 5)

    Backend:
      - finds latest JD with that role in memories (type='job')
      - computes vector similarity with all resumes
      - returns top-K resumes with ATS score + file_name + candidate_name.
    """
    # If top_k is very large (e.g. 1000), it effectively returns "all"
    try:
        matches = get_top_matches_for_role(role_name=role_name, top_k=top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error (match/top-by-role): {e}")

    return {
        "role_name": role_name,
        "top_k": top_k,
        "matches": matches,
    }


@app.post("/match/top-by-jd")
async def get_top_matches_by_jd_id(
    jd_id: str = Form(...),
    top_k: int = Form(3),
):
    """
    Input from UI:
      - jd_id: database UUID of the uploaded JD
      - top_k (3, 5, or 10)

    Backend:
      - uses the JD's embedding directly from the database
      - computes vector similarity with all resumes
      - returns top-K resumes with ATS score + file_name + candidate_name.
    """
    try:
        from ranking import get_top_k_resumes_for_jd_memory
        matches = get_top_k_resumes_for_jd_memory(jd_memory_id=jd_id, top_k=top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error (match/top-by-jd): {e}")

    return {
        "jd_id": jd_id,
        "top_k": top_k,
        "matches": matches,
    }


@app.post("/send-emails")
async def send_emails_to_candidates(
    jd_id: str = Form(...),
    candidate_ids: List[str] = Form(...),
):
    """
    Send personalized emails to selected candidates.
    
    Args:
        jd_id: Database UUID of the JD
        candidate_ids: List of resume IDs to send emails to
    
    Returns:
        Summary of sent emails with success/failure status
    """
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
            raise HTTPException(status_code=404, detail=f"JD not found: {jd_id}")
        
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
        raise HTTPException(status_code=500, detail=f"Error sending emails: {str(e)}")
    finally:
        conn.close()    
    return {
        "total": len(candidate_ids),
        "sent": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results
    }


@app.get("/acknowledge/{outreach_id}")
async def acknowledge_interest(outreach_id: str, response: str):
    """
    Record candidate's acknowledgement (interested/not_interested).
    
    Args:
        outreach_id: UUID of the outreach record
        response: 'interested' or 'not_interested'
    
    Returns:
        HTML confirmation page
    """
    from db import get_connection
    from fastapi.responses import HTMLResponse
    
    if response not in ['interested', 'not_interested']:
        raise HTTPException(status_code=400, detail="Invalid response")
    
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
            raise HTTPException(status_code=404, detail="Outreach record not found")
        
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
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording acknowledgement: {str(e)}")
    finally:
        conn.close()


@app.get("/confirm-interview/{interview_id}")
async def confirm_interview(interview_id: str, slot: str, outreach_id: str | None = None):
    """
    Confirm a candidate's selected interview time slot.
    Automatically creates a Google Calendar event and sends final emails.
    
    Args:
        interview_id: UUID of the interview
        slot: Selected slot ID (slot1, slot2, or slot3)
        outreach_id: Optional authorization token
    
    Returns:
        HTML confirmation page with Meet link and event details
    """
    from interview_scheduler import confirm_interview_slot
    from fastapi.responses import HTMLResponse
    
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
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error confirming interview: {str(e)}")


@app.post("/schedule-interviews")
async def schedule_interviews(
    jd_id: str = Form(...),
    interview_date: str = Form(...)  # Format: YYYY-MM-DD
):
    """
    Schedule interviews for all interested candidates for a given JD.
    
    Args:
        jd_id: Database UUID of the JD
        interview_date: Date for interviews (YYYY-MM-DD format)
    
    Returns:
        Summary of scheduled interviews
    """
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
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling interviews: {str(e)}")


@app.get("/confirm-interview/{interview_id}")
async def confirm_interview(interview_id: str, slot: str, outreach_id: str | None = None):
    """
    Confirm a candidate's selected interview time slot.
    
    Args:
        interview_id: UUID of the interview
        slot: Selected slot ID (slot1, slot2, or slot3)
    
    Returns:
        HTML confirmation page
    """
    from interview_scheduler import confirm_interview_slot
    from fastapi.responses import HTMLResponse
    
    try:
        result = confirm_interview_slot(interview_id, slot, outreach_id)
        
        if "error" in result:
            message = result["error"]
            color = "#dc3545"
            icon = "❌"
        else:
            slot_info = result.get("slot", {})
            start_time = slot_info.get("start", "")
            message = f"Your interview has been confirmed for {start_time}. We look forward to meeting you!"
            color = "#28a745"
            icon = "✅"
        
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
            color: #333;
            line-height: 1.6;
            font-size: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">{icon}</div>
        <h1>Interview Confirmation</h1>
        <p>{message}</p>
    </div>
</body>
</html>
"""
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error confirming interview: {str(e)}")


@app.get("/interviews/status")
async def get_interviews_status(jd_id: str = None):
    """
    Get status of all scheduled interviews, optionally filtered by JD.
    
    Args:
        jd_id: Optional JD ID to filter by
    
    Returns:
        List of scheduled interviews with their status
    """
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
                    m.title as jd_title
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
                    m.title as jd_title
                FROM interview_schedules i
                JOIN resumes r ON r.id = i.resume_id
                JOIN memories m ON m.id = i.jd_id
                ORDER BY i.interview_date DESC, i.created_at DESC
            """
            cur.execute(query)
        
        rows = cur.fetchall()
        cur.close()
        
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
                "jd_title": row[7]
            })
        
        return {
            "total": len(interviews),
            "interviews": interviews
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching interviews: {str(e)}")
    finally:
        conn.close()

