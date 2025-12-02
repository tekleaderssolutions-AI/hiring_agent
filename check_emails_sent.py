#!/usr/bin/env python3
"""
Check which interview invitation emails were sent.
"""
from db import get_connection
from datetime import datetime, timedelta

conn = get_connection()
cur = conn.cursor()

print("=" * 80)
print("INTERVIEW INVITATION EMAILS SENT - DETAILED LOG")
print("=" * 80)

# Get all interview schedules with candidate info
cur.execute("""
    SELECT 
        i.id,
        i.created_at,
        i.interview_date,
        i.status,
        co.candidate_name,
        co.candidate_email,
        m.title as jd_title
    FROM interview_schedules i
    JOIN candidate_outreach co ON i.outreach_id = co.id
    JOIN memories m ON i.jd_id = m.id
    ORDER BY i.created_at DESC
""")

interviews = cur.fetchall()

if not interviews:
    print("\nNo interview schedules found in database.\n")
else:
    print(f"\nTotal interview emails sent: {len(interviews)}\n")
    
    for idx, (int_id, created_at, int_date, status, name, email, jd_title) in enumerate(interviews, 1):
        print(f"{idx}. {name} ({email})")
        print(f"   Position: {jd_title}")
        print(f"   Interview Date: {int_date}")
        print(f"   Email Sent: {created_at}")
        print(f"   Status: {status}")
        print()

# Check candidate outreach records to find "not interested" or "no response"
print("\n" + "=" * 80)
print("CANDIDATES MARKED 'INTERESTED' (should have received interview emails)")
print("=" * 80)

cur.execute("""
    SELECT 
        id,
        candidate_name,
        candidate_email,
        acknowledgement,
        acknowledged_at,
        sent_at
    FROM candidate_outreach
    WHERE acknowledgement = 'interested'
    ORDER BY acknowledged_at DESC
""")

interested = cur.fetchall()
print(f"\nTotal 'interested' candidates: {len(interested)}\n")

for out_id, name, email, ack, ack_at, sent_at in interested:
    # Check if there's an interview schedule for this outreach
    cur.execute("""
        SELECT COUNT(*) FROM interview_schedules WHERE outreach_id = %s
    """, [out_id])
    
    has_schedule = cur.fetchone()[0] > 0
    
    status_indicator = "[EMAILED]" if has_schedule else "[NOT EMAILED]"
    print(f"{status_indicator} {name} ({email})")
    print(f"   Marked interested: {ack_at}")
    print()

# Now test sending a fresh email
print("\n" + "=" * 80)
print("TEST: SENDING A TEST EMAIL NOW")
print("=" * 80)

from email_sender import send_email

test_email = "akshithach.30@gmail.com"
test_subject = "TEST: Interview Invitation - AI Engineer at Tek Leaders"
test_body = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 30px; }
        .slot-button { display: inline-block; padding: 12px 30px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <p>Dear Test Candidate,</p>
        <p>This is a TEST interview invitation email.</p>
        <h2>📅 Interview Date</h2>
        <p><strong>Wednesday, December 10, 2025</strong></p>
        <h2>⏰ Available Time Slots</h2>
        <p>Please select one of the following time slots that works best for you:</p>
        <div style="margin: 15px 0; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #4CAF50; border-radius: 4px;">
            <strong>Option 1: 09:00 AM - 10:00 AM</strong><br>
            <a href="http://localhost:8000/confirm-interview/test-id?slot=slot1" class="slot-button">Select This Time</a>
        </div>
        <p style="margin-top: 20px; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; font-size: 14px;">
            <strong>⚠️ Important:</strong> Please confirm your preferred time slot by clicking one of the buttons above. Slots are available on a first-come, first-served basis.
        </p>
        <p style="margin-top: 30px; font-size: 14px; color: #666;">If none of these times work for you, please reply to this email and we'll try to accommodate your schedule.</p>
        <p style="margin-top: 20px; border-top: 1px solid #e0e0e0; padding-top: 20px;">Best regards,<br><strong>Tek Leaders Recruitment Team</strong></p>
    </div>
</body>
</html>
"""

print(f"Sending test email to: {test_email}")
result = send_email(
    to_email=test_email,
    subject=test_subject,
    html_body=test_body,
    cc_email="akkireddy41473@gmail.com"
)

print(f"\nResult: {result['message']}")
print(f"Success: {result['success']}")

conn.close()

print("\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)
print("""
If emails are being sent but you're not receiving them:

1. Check Gmail SPAM/PROMOTIONS folder for emails from: srikanthtata8374@gmail.com
2. Check the email address in FROM_EMAIL config
3. Run: python test_email_simple.py (to verify SMTP works)
4. Check database for errors: SELECT * FROM interview_schedules;

If you see "[NOT EMAILED]" next to a candidate:
- They were marked 'interested' but no interview email was sent
- This indicates an error in the auto-scheduling process
- Check the server logs for errors during acknowledge_interest()
""")
