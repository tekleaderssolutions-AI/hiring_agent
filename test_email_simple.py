#!/usr/bin/env python3
"""
Simple script to test email sending with debug output.
"""
from email_sender import send_email

# Test email sending
test_recipient = "akshithach.30@gmail.com"  # Replace with your test email
subject = "Test Interview Email - Debug"
body = """
<html>
<body>
<h2>Test Email</h2>
<p>This is a test email to verify SMTP configuration is working.</p>
<p>If you received this, the email system is functioning correctly.</p>
</body>
</html>
"""

print("=" * 60)
print("TESTING EMAIL SEND")
print("=" * 60)

result = send_email(
    to_email=test_recipient,
    subject=subject,
    html_body=body,
    cc_email="akkireddy41473@gmail.com"
)

print("\n" + "=" * 60)
print("RESULT:")
print(f"Success: {result['success']}")
print(f"Message: {result['message']}")
print("=" * 60)
