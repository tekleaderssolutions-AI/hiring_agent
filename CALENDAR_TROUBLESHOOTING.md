# Google Calendar Event Creation - Troubleshooting Guide

## What Changed
I've improved error handling and added fallback mechanisms for Google Calendar event creation. The main improvements:

1. **Better Error Messages**: Now includes actual API error details instead of generic messages
2. **Fallback to Simple Event**: If conference data fails, creates event without Meet link, then attempts to add it
3. **Timezone Handling**: Automatically adds UTC+5:30 (Asia/Kolkata) timezone to naive datetime objects
4. **Unique Request IDs**: Uses shortened UUID hex for conference request IDs

## Diagnostic Tools

Run these commands from the project directory to diagnose the issue:

```bash
# Check credentials setup
python check_calendar_setup.py

# Test calendar event creation directly
python test_calendar_event.py
```

## Common Issues & Solutions

### 1. **HTTP 403 - Permission Denied**
**Cause**: Service account lacks calendar write permissions

**Solution**:
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Select your project
- Go to APIs & Services > Credentials
- Find your service account
- Enable "Domain-wide delegation"
- Add OAuth scopes:
  - `https://www.googleapis.com/auth/calendar.readonly`
  - `https://www.googleapis.com/auth/calendar.events`

### 2. **HTTP 400 - Invalid conferenceData**
**Cause**: Calendar type doesn't support Meet (e.g., resource calendar)

**Solution**:
- Use a regular user Gmail account's calendar as INTERVIEWER_EMAIL
- Not a shared calendar or resource calendar
- Ensure the service account has access to that calendar

### 3. **HTTP 404 - Calendar not found**
**Cause**: Service account trying to write to a calendar it doesn't have access to

**Solution**:
- Verify `INTERVIEWER_EMAIL` in `.env` is correct
- Ensure service account has been granted access to that calendar
- Try using the service account's own email as INTERVIEWER_EMAIL temporarily for testing

### 4. **Invalid dateTime Format**
**Cause**: Datetime missing timezone information

**Solution**: Already fixed in the updated code - it now auto-adds UTC+5:30 if timezone is missing

## Testing the Fix

After making changes:

1. Stop the running app (Ctrl+C)
2. Run diagnostic: `python check_calendar_setup.py`
3. Run calendar test: `python test_calendar_event.py`
4. Restart app: `uvicorn main:app --reload`
5. Try confirming an interview slot again

## What to Check in Your Setup

- [ ] `credentials.json` exists in the project root
- [ ] Service account has "Domain-wide delegation" enabled
- [ ] Service account has calendar OAuth scopes authorized
- [ ] `INTERVIEWER_EMAIL` in config/`.env` is a valid calendar to write to
- [ ] Service account can access the interviewer's calendar

## Environment Variables

Make sure these are set in `.env`:
```
INTERVIEWER_EMAIL=your-interviewer@gmail.com
GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials.json
```

## Next Steps

1. Run the diagnostic tools
2. Check the error message from `test_calendar_event.py`
3. Address the specific Google Cloud Console setting needed
4. Test again

If you're still getting errors after these steps, share the exact error message from `test_calendar_event.py` output for more targeted help.
