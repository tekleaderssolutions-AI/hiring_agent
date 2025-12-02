# email_sender.py
"""
SMTP email sending functionality using Gmail.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_body: str, cc_email: Optional[str] = None) -> Dict[str, Any]:
    """
    Send an email via Gmail SMTP.
    
    Args:
        to_email: Primary recipient email address
        subject: Email subject
        html_body: HTML content of the email
        cc_email: Optional additional recipient to include in TO field
        
    Returns:
        Dict with 'success' boolean and 'message' string
    """
    try:
        print(f"[EMAIL DEBUG] Attempting to send email to {to_email}")
        print(f"[EMAIL DEBUG] SMTP config: host={SMTP_HOST}, port={SMTP_PORT}, user={SMTP_USER}")
        print(f"[EMAIL DEBUG] Subject: {subject}")
        print(f"[EMAIL DEBUG] CC: {cc_email}")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = FROM_EMAIL
        
        # Build recipients list and proper headers: To (primary) and Cc (carbon copy)
        recipients = [to_email]
        msg['To'] = to_email
        if cc_email:
            recipients.append(cc_email)
            msg['Cc'] = cc_email
            
        msg['Subject'] = subject
        
        # Attach HTML body
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        print(f"[EMAIL DEBUG] Connecting to {SMTP_HOST}:{SMTP_PORT}")
        # Connect to Gmail SMTP server
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()  # Enable TLS encryption
        print(f"[EMAIL DEBUG] Logging in as {SMTP_USER}")
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        print(f"[EMAIL DEBUG] Sending to recipients: {recipients}")
        # Send email to all recipients (including CC)
        server.send_message(msg, to_addrs=recipients)
        server.quit()
        
        recipient_msg = f" and {cc_email}" if cc_email else ""
        print(f"[EMAIL DEBUG] Email sent successfully to {to_email}{recipient_msg}")
        return {
            "success": True,
            "message": f"Email sent successfully to {to_email}{recipient_msg}"
        }
        
    except Exception as e:
        print(f"[EMAIL DEBUG ERROR] Failed to send email to {to_email}: {str(e)}")
        logger.error(f"Email sending error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to send email to {to_email}: {str(e)}"
        }
