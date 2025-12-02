import builtins
from unittest.mock import patch, MagicMock

from email_sender import send_email
from config import SMTP_USER, SMTP_PASSWORD


def test_send_email_sets_cc_and_recipients():
    to = "candidate@example.com"
    cc = "interviewer@example.com"
    subject = "Test Subject"
    body = "<p>Hello</p>"

    # Patch smtplib.SMTP so no network calls are made
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        result = send_email(to_email=to, subject=subject, html_body=body, cc_email=cc)

        # Ensure SMTP was instantiated and used
        mock_smtp_cls.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(SMTP_USER, SMTP_PASSWORD)

        # Inspect send_message call
        assert mock_server.send_message.call_count == 1
        send_args, send_kwargs = mock_server.send_message.call_args
        # First positional arg is the message object
        msg = send_args[0]

        # Ensure headers: To should be the primary, Cc should be set
        assert msg["To"] == to
        assert msg["Cc"] == cc

        # Ensure recipients list includes both to and cc
        to_addrs = send_kwargs.get("to_addrs")
        assert to_addrs == [to, cc]

        # Function should report success
        assert result["success"] is True
        assert to in result["message"]
