# interview_email_template.py
"""
Email templates for interview scheduling.
"""
from typing import Dict, Any, List
from datetime import datetime


def generate_interview_slots_email(
    candidate_data: Dict[str, Any],
    jd_data: Dict[str, Any],
    interview_id: str,
    outreach_id: str,
    date: datetime,
    time_slots: List[Dict[str, Any]],
    base_url: str,
    company_name: str
) -> Dict[str, str]:
    """
    Generate personalized interview scheduling email with time slots.
    
    Args:
        candidate_data: Dictionary with candidate information
        jd_data: Dictionary with job description information
        interview_id: UUID of the interview record
        date: Date of the interview
        time_slots: List of available time slots
        base_url: Base URL for confirmation links
        company_name: Company name
    
    Returns:
        Dictionary with 'subject' and 'body' keys
    """
    candidate_name = candidate_data.get('candidate_name', 'Candidate')
    role = jd_data.get('role', 'Position')
    
    # Format date
    date_str = date.strftime('%A, %B %d, %Y')
    
    # Generate slot options HTML
    slots_html = ""
    for idx, slot in enumerate(time_slots, 1):
        start_time = slot['start_time'].strftime('%I:%M %p').lstrip('0')
        end_time = slot['end_time'].strftime('%I:%M %p').lstrip('0')
        slot_id = f"slot{idx}"
        
        # Include outreach_id token in the confirmation URL so only the intended
        # candidate (recipient of the outreach email) can confirm the slot.
        confirm_url = f"{base_url}/confirm-interview/{interview_id}?slot={slot_id}&outreach_id={outreach_id}"
        
        slots_html += f"""
            <div class="slot-option">
                <strong>Option {idx}: {start_time} - {end_time}</strong><br>
                <a href="{confirm_url}" class="slot-button">Select This Time</a>
            </div>
        """
    
    subject = f"Interview Invitation - {role} at {company_name}"
    
    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                padding: 30px;
                border-radius: 8px;
            }}
            h2 {{
                color: #333;
                font-size: 18px;
                margin-top: 20px;
                margin-bottom: 10px;
            }}
            .slot-button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                margin-top: 10px;
            }}
            .slot-button:hover {{
                background-color: #45a049;
            }}
            .slot-option {{
                margin: 15px 0;
                padding: 15px;
                background-color: #f8f9fa;
                border-left: 4px solid #4CAF50;
                border-radius: 4px;
            }}
            .warning-box {{
                margin-top: 30px;
                padding: 15px;
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                border-radius: 4px;
                font-size: 14px;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
                font-size: 14px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <p>Dear {candidate_name},</p>
            
            <p>Congratulations! We were impressed with your profile and would like to invite you for an interview for the <strong>{role}</strong> position at <strong>{company_name}</strong>.</p>
            
            <h2>📅 Interview Date</h2>
            <p><strong>{date_str}</strong></p>
            
            <h2>⏰ Available Time Slots</h2>
            <p>Please select one of the following time slots that works best for you:</p>
            
            {slots_html}
            
            <div class="warning-box">
                <strong>⚠️ Important:</strong> Please confirm your preferred time slot by clicking one of the buttons above. Slots are available on a first-come, first-served basis.
            </div>
            
            <div class="footer">
                <p>If none of these times work for you, please reply to this email and we'll try to accommodate your schedule.</p>
                <p>We look forward to speaking with you!</p>
                <p style="margin-top: 20px; margin-bottom: 5px;">Best regards,</p>
                <p style="margin: 0;"><strong>{company_name} Recruitment Team</strong></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return {
        "subject": subject,
        "body": body
    }
