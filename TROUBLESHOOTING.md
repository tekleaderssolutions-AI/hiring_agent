# Interview Scheduling - Troubleshooting Summary

## Issue
Interview scheduling emails are not being sent.

## Root Cause
Google Calendar API is not enabled for your project `interview-agent-479906`.

## Solution

### Step 1: Enable Google Calendar API
1. Click this link: https://console.cloud.google.com/apis/library/calendar-json.googleapis.com?project=interview-agent-479906
2. Click the **"ENABLE"** button
3. Wait for it to be enabled (takes a few seconds)

### Step 2: Test the Integration
After enabling, run:
```bash
python test_calendar.py
```

You should see "SUCCESS! Google Calendar integration is working!"

### Step 3: Trigger Interview Scheduling
Run:
```bash
python trigger_interview_schedule.py
```

This will:
- Check interviewer's calendar (`akkireddy41473@gmail.com`) for available slots
- Send interview invitation emails to interested candidates
- Email will be sent to BOTH the candidate AND the interviewer

## Current Status

✅ Service account credentials: CORRECT
✅ Calendar shared with service account: DONE  
❌ Google Calendar API enabled: **NEEDS TO BE DONE**

## What Happens After Enabling

Once you enable the API and run `trigger_interview_schedule.py`:
1. System checks `akkireddy41473@gmail.com` calendar for tomorrow
2. Finds 3 available time slots (9 AM - 5 PM)
3. Sends email to:
   - **To**: `srikanthtata8374@gmail.com, akkireddy41473@gmail.com`
   - **From**: `srikanthtata8374@gmail.com`
   - **Subject**: "Interview Invitation - AI Engineer / AI Executive at Tek Leaders"
   - **Body**: Professional email with 3 clickable time slot buttons

## Files Created for Testing

- `test_calendar.py` - Tests Google Calendar integration
- `trigger_interview_schedule.py` - Triggers interview scheduling
- `debug_interviews.py` - Shows current database status
- `debug_sql.py` - Debugs SQL queries

## Next Steps After Email is Sent

1. Candidate clicks on one of the 3 time slot buttons
2. System records the confirmed slot in database
3. Status changes from "pending" to "confirmed"
4. You can view all interviews at: `GET /interviews/status`
