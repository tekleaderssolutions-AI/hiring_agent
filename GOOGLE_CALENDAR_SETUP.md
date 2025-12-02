# Google Calendar API Setup Guide

## Overview
This guide explains how to set up Google Calendar API credentials for the interview scheduling feature.

## Steps

### 1. Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID

### 2. Enable Google Calendar API
1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google Calendar API"
3. Click "Enable"

### 3. Create Service Account Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the service account details:
   - Name: `interview-scheduler`
   - Description: `Service account for interview scheduling`
4. Click "Create and Continue"
5. Skip the optional steps and click "Done"

### 4. Generate JSON Key
1. Click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Click "Create"
6. The JSON file will download automatically
7. **Rename this file to `credentials.json`** and place it in your project root directory

### 5. Share Calendar with Service Account
1. Open Google Calendar
2. Go to Settings > Settings for my calendars
3. Select the calendar you want to use for interviews
4. Scroll down to "Share with specific people"
5. Click "Add people"
6. Enter the service account email (found in the JSON file, looks like `interview-scheduler@project-id.iam.gserviceaccount.com`)
7. Set permission to "Make changes to events"
8. Click "Send"

### 6. Update Environment Variables
Make sure your `.env` file has:
```
GOOGLE_CALENDAR_CREDENTIALS_PATH="credentials.json"
INTERVIEWER_EMAIL="your-email@gmail.com"
INTERVIEW_DURATION_MINUTES="60"
```

## Testing
1. Install dependencies: `pip install -r requirements.txt`
2. Run database migrations: `python -c "from migrations import init_db; init_db()"`
3. Start the server: `python -m uvicorn main:app --reload`
4. Test the calendar integration by calling `/schedule-interviews` endpoint

## Troubleshooting

### "credentials.json not found"
- Make sure the file is in the project root directory
- Check the path in your `.env` file

### "Permission denied" errors
- Verify the service account email has been added to your calendar
- Check that it has "Make changes to events" permission

### "No available slots found"
- Check that your calendar has free time on the specified date
- Verify the working hours (9 AM - 5 PM) in `google_calendar.py`
