# google_calendar.py
"""
Google Calendar integration for fetching interviewer availability.
Supports both service account (server-to-server) and installed-app OAuth flows.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import os
import uuid
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GOOGLE_CALENDAR_CREDENTIALS_PATH, INTERVIEWER_EMAIL, INTERVIEW_DURATION_MINUTES

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",  # Check availability
    "https://www.googleapis.com/auth/calendar.events"    # Create events
]
TOKEN_PATH = Path('token.json')


def _get_oauth_credentials():
    """
    Get installed-app OAuth credentials, refreshing or prompting for auth if needed.
    Saves token to token.json for reuse.
    """
    creds = None
    credentials_path = Path('credentials.json')
    
    # Load existing token if available
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    
    # Refresh or obtain new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(f"Missing OAuth credentials: {credentials_path}. Please set up OAuth first.")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
    
    return creds


def get_calendar_service():
    """
    Create and return a Google Calendar API service instance.
    Tries installed-app OAuth first, falls back to service account.
    """
    try:
        # Try installed-app OAuth (desktop app flow with token.json)
        if Path('credentials.json').exists():
            try:
                creds = _get_oauth_credentials()
                service = build('calendar', 'v3', credentials=creds)
                return service
            except Exception as oauth_error:
                print(f"OAuth flow failed, attempting service account: {oauth_error}")
        
        # Fall back to service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CALENDAR_CREDENTIALS_PATH,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events'
            ]
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except Exception as e:
        raise Exception(f"Failed to create Calendar service: {str(e)}")


def get_available_slots(date: datetime, num_slots: int = 3) -> List[Dict[str, Any]]:
    """
    Fetch available time slots for a given date.
    
    Args:
        date: The date to check availability (datetime object)
        num_slots: Number of time slots to return (default: 3)
    
    Returns:
        List of dictionaries with 'start_time' and 'end_time' datetime objects
    """
    try:
        service = get_calendar_service()
        
        # Define working hours (9 AM to 5 PM)
        start_of_day = date.replace(hour=9, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Query free/busy information
        body = {
            "timeMin": start_of_day.isoformat() + 'Z',
            "timeMax": end_of_day.isoformat() + 'Z',
            "items": [{"id": INTERVIEWER_EMAIL}],
            "timeZone": "Asia/Kolkata"
        }
        
        freebusy_result = service.freebusy().query(body=body).execute()
        busy_times = freebusy_result['calendars'][INTERVIEWER_EMAIL].get('busy', [])
        
        # Convert busy times to datetime objects
        busy_periods = []
        for busy in busy_times:
            busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
            busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
            busy_periods.append((busy_start, busy_end))
        
        # Find available slots
        available_slots = []
        current_time = start_of_day
        slot_duration = timedelta(minutes=INTERVIEW_DURATION_MINUTES)
        
        while current_time + slot_duration <= end_of_day and len(available_slots) < num_slots:
            slot_end = current_time + slot_duration
            
            # Check if this slot overlaps with any busy period
            is_available = True
            for busy_start, busy_end in busy_periods:
                if (current_time < busy_end and slot_end > busy_start):
                    is_available = False
                    # Jump to the end of this busy period
                    current_time = busy_end
                    break
            
            if is_available:
                available_slots.append({
                    'start_time': current_time,
                    'end_time': slot_end
                })
                # Move to next potential slot (30 minutes after this one starts)
                current_time += timedelta(minutes=30)
            
        return available_slots
        
    except HttpError as error:
        raise Exception(f"Google Calendar API error: {error}")
    except Exception as e:
        raise Exception(f"Error fetching available slots: {str(e)}")


def format_time_slot(slot: Dict[str, Any]) -> str:
    """
    Format a time slot for display in email.
    
    Args:
        slot: Dictionary with 'start_time' and 'end_time'
    
    Returns:
        Formatted string like "2:00 PM - 3:00 PM"
    """
    start = slot['start_time']
    end = slot['end_time']
    return f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"


def create_calendar_event(
    summary: str,
    description: str,
    start_dt: datetime,
    end_dt: datetime,
    organizer_email: str,
    attendees_emails: List[str],
    timezone: str = "Asia/Kolkata",
    send_updates: str = "none"
) -> Dict[str, Any]:
    """
    Create a Google Calendar event with a Meet conference and return event data.
    Falls back to a simpler event creation if conference setup fails.

    Returns event resource (dict) on success.
    """
    try:
        service = get_calendar_service()

        # Ensure attendees are unique and valid
        unique_attendees = list(set(attendees_emails))
        attendees = [{"email": e.strip(), "responseStatus": "needsAction"} for e in unique_attendees]

        event_body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone},
            "attendees": attendees,
            # Request creation of a Google Meet link
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-{uuid.uuid4().hex[:16]}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            },
            "guestCanModify": False,
            "guestCanInviteOthers": False,
            "guestCanSeeOtherGuests": True
        }

        try:
            # Try to insert with conference data
            event = service.events().insert(
                calendarId=organizer_email,
                body=event_body,
                conferenceDataVersion=1,
                sendUpdates=send_updates,
                maxAttendees=10
            ).execute()
            
            return event
        except HttpError as e:
            # If conference creation fails, try without it and add Meet separately
            if "conferenceData" in str(e):
                print(f"Conference data creation failed: {e}, retrying without Meet link")
                del event_body["conferenceData"]
                event = service.events().insert(
                    calendarId=organizer_email,
                    body=event_body,
                    sendUpdates=send_updates,
                    maxAttendees=10
                ).execute()
                
                # Attempt to add Meet link after creation
                try:
                    event_id = event.get('id')
                    update_body = {
                        "conferenceData": {
                            "createRequest": {
                                "requestId": f"meet-{uuid.uuid4().hex[:16]}",
                                "conferenceSolutionKey": {"type": "hangoutsMeet"}
                            }
                        }
                    }
                    event = service.events().patch(
                        calendarId=organizer_email,
                        eventId=event_id,
                        body=update_body,
                        conferenceDataVersion=1
                    ).execute()
                except Exception as patch_err:
                    print(f"Could not add Meet link after event creation: {patch_err}")
                
                return event
            else:
                raise
                
    except HttpError as error:
        error_msg = f"Google Calendar API error: {error.resp.status} - {error.content.decode() if hasattr(error, 'content') else str(error)}"
        raise Exception(error_msg)
    except Exception as e:
        raise Exception(f"Error creating calendar event: {str(e)}")

