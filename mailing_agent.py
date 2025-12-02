# mailing_agent.py
"""
Mailing agent that generates personalized recruitment emails using LLM.
"""
import google.generativeai as genai
from typing import Dict, Any

from config import GEMINI_API_KEY, CHAT_MODEL, COMPANY_NAME, BASE_URL

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)


def generate_personalized_email(
    candidate_data: Dict[str, Any],
    jd_data: Dict[str, Any],
    outreach_id: str,
    rank: int,
    ats_score: int
) -> Dict[str, str]:
    """
    Generate a personalized recruitment email using LLM.
    
    Args:
        candidate_data: Resume data including name, skills, experience
        jd_data: Job description data including role, requirements
        outreach_id: UUID for acknowledgement tracking
        rank: Candidate's rank in the matching
        ats_score: ATS match score (0-100)
        
    Returns:
        Dict with 'subject' and 'body' (HTML)
    """
    candidate_name = candidate_data.get('candidate_name', 'Candidate')
    role = jd_data.get('role', 'Position')
    
    # Extract key skills from candidate
    canonical = candidate_data.get('canonical_json', {})
    skills = canonical.get('skills', [])[:5]  # Top 5 skills
    experience = canonical.get('experience', [])
    
    # Extract JD details
    jd_canonical = jd_data.get('canonical_json', {})
    primary_skills = jd_canonical.get('primary_skills', [])
    responsibilities = jd_canonical.get('responsibilities', [])[:3]
    
    # Create prompt for LLM
    prompt = f"""Generate a personalized recruitment email for a candidate.

Company: {COMPANY_NAME}
Role: {role}
Candidate Name: {candidate_name}
Candidate Skills: {', '.join(skills) if skills else 'Not specified'}
Candidate Experience: {len(experience)} positions
Required Skills: {', '.join(primary_skills) if primary_skills else 'Not specified'}
Match Score: {ats_score}%
Rank: #{rank}

Write a professional, warm, and personalized email that:
1. Congratulates them on being shortlisted
2. Mentions 2-3 specific skills or experiences that make them a great fit
3. Briefly describes the role
4. Sounds genuine and personalized (NOT generic)
5. Is concise (200-250 words)

IMPORTANT: Make each email unique. Do NOT use template phrases like "We are pleased to inform you" or "Your profile has been shortlisted". Be creative and conversational.

Return ONLY the email body text (no subject line). Use a friendly, professional tone."""

    try:
        # Use Gemini API to generate email
        model = genai.GenerativeModel(CHAT_MODEL)
        response = model.generate_content(prompt)
        
        email_body_text = response.text.strip()
        
        # Create HTML email with acknowledgement buttons
        interested_link = f"{BASE_URL}/acknowledge/{outreach_id}?response=interested"
        not_interested_link = f"{BASE_URL}/acknowledge/{outreach_id}?response=not_interested"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px 20px; background-color: #f9fafb; }}
        .buttons {{ text-align: center; margin: 30px 0; }}
        .btn {{ display: inline-block; padding: 12px 30px; margin: 0 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .btn-primary {{ background-color: #10b981; color: white; }}
        .btn-secondary {{ background-color: #6b7280; color: white; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>{COMPANY_NAME}</h2>
            <p>Recruitment Team</p>
        </div>
        <div class="content">
            <p>Dear {candidate_name},</p>
            {email_body_text.replace(chr(10), '<br>')}
            
            <div class="buttons">
                <a href="{interested_link}" class="btn btn-primary">✓ Yes, I'm Interested</a>
                <a href="{not_interested_link}" class="btn btn-secondary">✗ Not Interested</a>
            </div>
            
            <p>Best regards,<br>
            {COMPANY_NAME} Recruitment Team</p>
        </div>
        <div class="footer">
            <p>This is an automated email from {COMPANY_NAME}. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
"""
        
        subject = f"Opportunity at {COMPANY_NAME} - {role}"
        
        return {
            "subject": subject,
            "body": html_body
        }
        
    except Exception as e:
        # Fallback to a simple template if LLM fails
        interested_link = f"{BASE_URL}/acknowledge/{outreach_id}?response=interested"
        not_interested_link = f"{BASE_URL}/acknowledge/{outreach_id}?response=not_interested"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif;">
    <p>Dear {candidate_name},</p>
    <p>We are excited to inform you that your profile has been shortlisted for the <strong>{role}</strong> position at {COMPANY_NAME}.</p>
    <p>Your match score: <strong>{ats_score}%</strong></p>
    <p>Please let us know your interest:</p>
    <p>
        <a href="{interested_link}" style="background-color: #10b981; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Yes, I'm Interested</a>
        <a href="{not_interested_link}" style="background-color: #6b7280; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Not Interested</a>
    </p>
    <p>Best regards,<br>{COMPANY_NAME} Team</p>
</body>
</html>
"""
        
        return {
            "subject": f"Opportunity at {COMPANY_NAME} - {role}",
            "body": html_body
        }
