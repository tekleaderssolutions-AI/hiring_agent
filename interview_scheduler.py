# interview_scheduler.py
"""
Interview scheduling agent that coordinates calendar availability and candidate outreach.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid
import json

from db import get_connection
from google_calendar import get_available_slots
from interview_email_template import generate_interview_slots_email
from email_sender import send_email
from config import BASE_URL, COMPANY_NAME, INTERVIEWER_EMAIL


def find_first_available_date(num_slots=3, max_days_ahead=30, excluded_dates=None):
    """
    Find the first date with available interview slots, skipping excluded dates.
    
    Args:
        num_slots: Number of slots needed (default: 3)
        max_days_ahead: Maximum days to search ahead (default: 30)
        excluded_dates: List of dates to skip (optional)
    
    Returns:
        datetime object of first available date, or None if no date found
    """
    if excluded_dates is None:
        excluded_dates = []
        
    current_date = datetime.now() + timedelta(days=1)  # Start from tomorrow
    end_date = datetime.now() + timedelta(days=max_days_ahead)
    
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            current_date += timedelta(days=1)
            continue
            
        # Skip excluded dates
        if current_date.date() in excluded_dates:
            print(f"Skipping {current_date.date()} (already scheduled)")
            current_date += timedelta(days=1)
            continue
        
        try:
            slots = get_available_slots(current_date, num_slots)
            if len(slots) >= num_slots:
                return current_date
        except Exception as e:
            print(f"Error checking {current_date.date()}: {e}")
        
        current_date += timedelta(days=1)
    
    return None


def schedule_interview_for_single_candidate(
    outreach_id: str,
    num_slots: int = 3
) -> Dict[str, Any]:
    """
    Schedule interview for a single candidate (used for automatic scheduling).
    Finds the first available date automatically.
    
    Args:
        outreach_id: Outreach ID of the candidate
        num_slots: Number of time slots to offer (default: 3)
    
    Returns:
        Dictionary with scheduling result
    """
    conn = get_connection()
    
    try:
        cur = conn.cursor()
        
        # Fetch candidate and JD details
        cur.execute(
            """
            SELECT 
                co.id as outreach_id,
                co.resume_id,
                co.candidate_email,
                co.candidate_name,
                co.jd_id,
                r.canonical_json,
                m.title,
                m.canonical_json as jd_json
            FROM candidate_outreach co
            JOIN resumes r ON r.id = co.resume_id
            JOIN memories m ON m.id = co.jd_id
            WHERE co.id = %s
            """,
            [outreach_id]
        )
        
        row = cur.fetchone()
        
        if not row:
            return {"error": "Outreach record not found"}
        
        outreach_id, resume_id, email, name, jd_id, resume_json, jd_title, jd_json = row
        
        # Check if already scheduled
        cur.execute(
            """
            SELECT id FROM interview_schedules
            WHERE outreach_id = %s AND status NOT IN ('cancelled', 'declined')
            """,
            [outreach_id]
        )
        
        if cur.fetchone():
            return {"message": "Interview already scheduled for this candidate"}
            
        # Fetch dates that are already taken by other candidates
        cur.execute(
            """
            SELECT DISTINCT interview_date 
            FROM interview_schedules 
            WHERE status NOT IN ('cancelled', 'declined')
            """
        )
        busy_dates = [row[0] for row in cur.fetchall()]
        
        # Find first available date (excluding busy dates)
        interview_date = find_first_available_date(num_slots, excluded_dates=busy_dates)
        
        if not interview_date:
            return {"error": "No available dates found in the next 30 days"}
        
        # Fetch available time slots
        try:
            time_slots = get_available_slots(interview_date, num_slots)
            
            if not time_slots:
                return {"error": "No available time slots found"}
        except Exception as e:
            return {"error": f"Failed to fetch calendar availability: {str(e)}"}
        
        # Prepare data
        interview_id = str(uuid.uuid4())
        
        candidate_data = {
            "candidate_name": name,
            "email": email,
            "canonical_json": resume_json
        }
        
        jd_data = {
            "id": jd_id,
            "title": jd_title,
            "canonical_json": jd_json,
            "role": jd_json.get("role") if jd_json else "Position"
        }
        
        # Generate email with time slots
        email_content = generate_interview_slots_email(
            candidate_data=candidate_data,
            jd_data=jd_data,
            interview_id=interview_id,
            outreach_id=outreach_id,
            date=interview_date,
            time_slots=time_slots,
            base_url=BASE_URL,
            company_name=COMPANY_NAME
        )
        
        # Send email with interviewer CC'd
        send_result = send_email(
            to_email=email,
            subject=email_content["subject"],
            html_body=email_content["body"],
            cc_email=INTERVIEWER_EMAIL  # CC the interviewer
        )
        
        if send_result["success"]:
            # Store interview schedule in database
            proposed_slots_data = {
                "slot1": {
                    "start": time_slots[0]['start_time'].isoformat(),
                    "end": time_slots[0]['end_time'].isoformat()
                },
                "slot2": {
                    "start": time_slots[1]['start_time'].isoformat(),
                    "end": time_slots[1]['end_time'].isoformat()
                } if len(time_slots) > 1 else None,
                "slot3": {
                    "start": time_slots[2]['start_time'].isoformat(),
                    "end": time_slots[2]['end_time'].isoformat()
                } if len(time_slots) > 2 else None
            }
            
            cur.execute(
                """
                INSERT INTO interview_schedules 
                (id, resume_id, jd_id, outreach_id, interview_date, 
                 proposed_slots, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, NOW())
                """,
                [
                    interview_id,
                    resume_id,
                    jd_id,
                    outreach_id,
                    interview_date.date(),
                    json.dumps(proposed_slots_data),
                    'pending'
                ]
            )
            conn.commit()
            
            return {
                "success": True,
                "interview_id": interview_id,
                "interview_date": interview_date.strftime('%Y-%m-%d'),
                "candidate_name": name,
                "email": email
            }
        else:
            return {"error": send_result["message"]}
            
    except Exception as e:
        return {"error": f"Error scheduling interview: {str(e)}"}
    finally:
        conn.close()


def schedule_interviews_for_interested_candidates(
    jd_id: str,
    interview_date: datetime,
    num_slots: int = 3
) -> Dict[str, Any]:
    """
    Schedule interviews for all interested candidates for a given JD.
    
    Args:
        jd_id: Job description ID
        interview_date: Date for the interviews
        num_slots: Number of time slots to offer (default: 3)
    
    Returns:
        Dictionary with scheduling results
    """
    conn = get_connection()
    results = []
    
    try:
        cur = conn.cursor()
        
        # Fetch JD details
        cur.execute(
            "SELECT id, title, canonical_json FROM memories WHERE id = %s",
            [jd_id]
        )
        jd_row = cur.fetchone()
        
        if not jd_row:
            return {"error": f"JD not found: {jd_id}"}
        
        jd_data = {
            "id": jd_row[0],
            "title": jd_row[1],
            "canonical_json": jd_row[2],
            "role": jd_row[2].get("role") if jd_row[2] else "Position"
        }
        
        # Fetch available time slots from Google Calendar
        try:
            time_slots = get_available_slots(interview_date, num_slots)
            
            if not time_slots:
                return {"error": "No available time slots found for the specified date"}
        except Exception as e:
            return {"error": f"Failed to fetch calendar availability: {str(e)}"}
        
        # Fetch interested candidates
        cur.execute(
            """
            SELECT 
                co.id as outreach_id,
                co.resume_id,
                co.candidate_email,
                co.candidate_name,
                r.canonical_json
            FROM candidate_outreach co
            JOIN resumes r ON r.id = co.resume_id
            WHERE co.jd_id = %s 
              AND co.acknowledgement = 'interested'
              AND co.resume_id NOT IN (
                  SELECT resume_id FROM interview_schedules 
                  WHERE jd_id = %s AND status NOT IN ('cancelled', 'declined')
              )
            """,
            [jd_id, jd_id]
        )
        
        interested_candidates = cur.fetchall()
        
        if not interested_candidates:
            return {
                "message": "No interested candidates found or all have already been scheduled",
                "scheduled": 0
            }
        
        # Schedule interview for each interested candidate
        for outreach_id, resume_id, email, name, resume_json in interested_candidates:
            try:
                interview_id = str(uuid.uuid4())
                
                candidate_data = {
                    "candidate_name": name,
                    "email": email,
                    "canonical_json": resume_json
                }
                
                # Generate email with time slots
                email_content = generate_interview_slots_email(
                    candidate_data=candidate_data,
                    jd_data=jd_data,
                    interview_id=interview_id,
                    outreach_id=outreach_id,
                    date=interview_date,
                    time_slots=time_slots,
                    base_url=BASE_URL,
                    company_name=COMPANY_NAME
                )
                
                # Send email with interviewer CC'd
                send_result = send_email(
                    to_email=email,
                    subject=email_content["subject"],
                    html_body=email_content["body"],
                    cc_email=INTERVIEWER_EMAIL  # CC the interviewer
                )
                
                if send_result["success"]:
                    # Store interview schedule in database
                    
                    proposed_slots_data = {
                        "slot1": {
                            "start": time_slots[0]['start_time'].isoformat(),
                            "end": time_slots[0]['end_time'].isoformat()
                        },
                        "slot2": {
                            "start": time_slots[1]['start_time'].isoformat(),
                            "end": time_slots[1]['end_time'].isoformat()
                        } if len(time_slots) > 1 else None,
                        "slot3": {
                            "start": time_slots[2]['start_time'].isoformat(),
                            "end": time_slots[2]['end_time'].isoformat()
                        } if len(time_slots) > 2 else None
                    }
                    
                    cur.execute(
                        """
                        INSERT INTO interview_schedules 
                        (id, resume_id, jd_id, outreach_id, interview_date, 
                         proposed_slots, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, NOW())
                        """,
                        [
                            interview_id,
                            resume_id,
                            jd_id,
                            outreach_id,
                            interview_date.date(),
                            json.dumps(proposed_slots_data),
                            'pending'
                        ]
                    )
                    conn.commit()
                    
                    results.append({
                        "resume_id": resume_id,
                        "candidate_name": name,
                        "email": email,
                        "status": "success",
                        "interview_id": interview_id
                    })
                else:
                    results.append({
                        "resume_id": resume_id,
                        "candidate_name": name,
                        "email": email,
                        "status": "error",
                        "message": send_result["message"]
                    })
                    
            except Exception as e:
                results.append({
                    "resume_id": resume_id,
                    "candidate_name": name,
                    "status": "error",
                    "message": str(e)
                })
        
        cur.close()
        
        return {
            "total": len(interested_candidates),
            "scheduled": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"]),
            "results": results
        }
        
    except Exception as e:
        return {"error": f"Error scheduling interviews: {str(e)}"}
    finally:
        conn.close()


def confirm_interview_slot(interview_id: str, slot_id: str, outreach_id: str | None = None) -> Dict[str, Any]:
    """
    Confirm a candidate's selected interview time slot.
    Automatically creates a Google Calendar event and blocks both participants' calendars.
    Sends final confirmation emails to both candidate and interviewer.
    
    Args:
        interview_id: UUID of the interview
        slot_id: Selected slot ID (slot1, slot2, or slot3)
        outreach_id: Optional outreach token for authorization
    
    Returns:
        Dictionary with confirmation status, event link, and meet link
    """
    from google_calendar import create_calendar_event
    from email_sender import send_email
    from datetime import datetime
    
    conn = get_connection()
    
    try:
        cur = conn.cursor()
        
        # Fetch interview details (include outreach_id to validate requester)
        cur.execute(
            """
            SELECT id, resume_id, jd_id, proposed_slots, status, outreach_id, interview_date
            FROM interview_schedules
            WHERE id = %s
            """,
            [interview_id]
        )
        
        row = cur.fetchone()
        
        if not row:
            return {"error": "Interview not found"}
        
        interview_id_db, resume_id, jd_id, proposed_slots, status, outreach_id_db, interview_date = row
        
        if status == 'confirmed':
            return {"error": "Interview already confirmed"}
        
        # Ensure the requester is the candidate who received the outreach email
        if outreach_id is not None:
            if outreach_id != outreach_id_db:
                return {"error": "Unauthorized: outreach token mismatch"}

        if slot_id not in proposed_slots or proposed_slots[slot_id] is None:
            return {"error": "Invalid slot selection"}
        
        selected_slot = proposed_slots[slot_id]
        start_time_str = selected_slot['start']
        end_time_str = selected_slot['end']
        
        # Parse datetime strings and ensure they have timezone info
        try:
            start_dt = datetime.fromisoformat(start_time_str)
            end_dt = datetime.fromisoformat(end_time_str)
            
            # If datetimes are naive (no timezone), add UTC+5:30 (Asia/Kolkata) offset
            if start_dt.tzinfo is None:
                from datetime import timezone as dt_timezone
                kolkata_tz = dt_timezone(timedelta(hours=5, minutes=30))
                start_dt = start_dt.replace(tzinfo=kolkata_tz)
                end_dt = end_dt.replace(tzinfo=kolkata_tz)
        except ValueError as ve:
            return {"error": f"Invalid datetime format in selected slot: {str(ve)}"}
        
        # Fetch candidate and JD details
        cur.execute(
            "SELECT candidate_name, email FROM resumes WHERE id = %s",
            [resume_id]
        )
        cand_row = cur.fetchone()
        if not cand_row:
            return {"error": "Candidate not found"}
        candidate_name, candidate_email = cand_row
        
        cur.execute(
            "SELECT title, canonical_json FROM memories WHERE id = %s",
            [jd_id]
        )
        jd_row = cur.fetchone()
        if not jd_row:
            return {"error": "JD not found"}
        jd_title, jd_json = jd_row
        
        # Create Google Calendar event with Meet link
        try:
            event_summary = f"Interview: {candidate_name} - {jd_title}"
            event_description = f"Scheduled interview for {candidate_name} for the {jd_title} position."
            
            event = create_calendar_event(
                summary=event_summary,
                description=event_description,
                start_dt=start_dt,
                end_dt=end_dt,
                organizer_email=INTERVIEWER_EMAIL,
                attendees_emails=[candidate_email, INTERVIEWER_EMAIL],
                timezone="Asia/Kolkata",
                send_updates="all"  # Send calendar invitations
            )
            
            event_link = event.get('htmlLink')
            meet_link = event.get('hangoutLink')
            if not meet_link:
                conf = event.get('conferenceData', {})
                entry_points = conf.get('entryPoints', []) if conf else []
                if entry_points:
                    meet_link = entry_points[0].get('uri')
            
        except Exception as e:
            return {"error": f"Failed to create calendar event: {str(e)}"}
        
        # Update interview record with confirmed slot and event info
        cur.execute(
            """
            UPDATE interview_schedules
            SET selected_slot = %s,
                confirmed_slot_time = %s,
                status = 'scheduled',
                event_id = %s,
                event_link = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            [slot_id, start_time_str, event.get('id'), event_link, interview_id]
        )
        
        conn.commit()
        
        # Send final confirmation email to candidate with Meet link
        email_subject = f"Interview Confirmed - {jd_title}"
        email_body = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background-color: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px; }}
                .meet-link {{ background-color: #e8f5e9; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4caf50; }}
                .event-details {{ background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #4caf50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Interview Confirmed ✓</h1>
                </div>
                <div class="content">
                    <p>Hi {candidate_name},</p>
                    
                    <p>Great news! Your interview has been confirmed for the <strong>{jd_title}</strong> position at <strong>{COMPANY_NAME}</strong>.</p>
                    
                    <div class="event-details">
                        <h3 style="margin-top: 0;">Interview Details</h3>
                        <p><strong>Date & Time:</strong> {start_dt.strftime('%A, %B %d, %Y at %I:%M %p')}</p>
                        <p><strong>Duration:</strong> 60 minutes</p>
                        <p><strong>Interviewer:</strong> {INTERVIEWER_EMAIL}</p>
                    </div>
                    
                    <div class="meet-link">
                        <h3 style="margin-top: 0;">📹 Join the Interview</h3>
                        <p><a href="{meet_link}" class="button">Open Google Meet</a></p>
                        <p style="margin: 10px 0; font-size: 14px;">Or copy this link: <a href="{meet_link}">{meet_link}</a></p>
                    </div>
                    
                    <p><a href="{event_link}">View in Google Calendar</a></p>
                    
                    <p style="margin-top: 20px;">We look forward to speaking with you!</p>
                    
                    <div class="footer">
                        <p>Best regards,<br><strong>{COMPANY_NAME} Recruitment Team</strong></p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        send_email(
            to_email=candidate_email,
            subject=email_subject,
            html_body=email_body,
            cc_email=INTERVIEWER_EMAIL
        )
        
        cur.close()
        
        return {
            "success": True,
            "message": "Interview confirmed and calendars blocked successfully",
            "slot": selected_slot,
            "event_link": event_link,
            "meet_link": meet_link
        }
        
    except Exception as e:
        return {"error": f"Error confirming interview: {str(e)}"}
    finally:
        conn.close()
