#!/usr/bin/env python3
"""
Diagnostic script to test Google Calendar event creation.
Run this to identify issues with the calendar API.
"""
import sys
from datetime import datetime, timedelta, timezone as dt_timezone

# Add project root to path
sys.path.insert(0, '/root' if sys.platform == 'linux' else '.')

try:
    from google_calendar import create_calendar_event
    from config import INTERVIEWER_EMAIL
    
    print("=" * 60)
    print("Google Calendar Event Creation Test")
    print("=" * 60)
    
    # Test parameters
    now = datetime.now(dt_timezone(timedelta(hours=5, minutes=30)))
    start_time = now.replace(hour=14, minute=0, second=0, microsecond=0)  # 2 PM
    end_time = start_time + timedelta(hours=1)  # 1 hour later
    
    print(f"\nTest Details:")
    print(f"  Start Time: {start_time.isoformat()}")
    print(f"  End Time: {end_time.isoformat()}")
    print(f"  Organizer: {INTERVIEWER_EMAIL}")
    print(f"  Attendees: test@example.com, {INTERVIEWER_EMAIL}")
    
    print(f"\nAttempting to create calendar event...")
    try:
        event = create_calendar_event(
            summary="Test Interview Event",
            description="This is a test event for debugging calendar API issues.",
            start_dt=start_time,
            end_dt=end_time,
            organizer_email=INTERVIEWER_EMAIL,
            attendees_emails=["test@example.com", INTERVIEWER_EMAIL],
            timezone="Asia/Kolkata",
            send_updates="all"
        )
        
        print(f"\n✅ SUCCESS! Event created.")
        print(f"  Event ID: {event.get('id')}")
        print(f"  Event Link: {event.get('htmlLink')}")
        print(f"  Meet Link: {event.get('hangoutLink')}")
        
        conf = event.get('conferenceData', {})
        if conf:
            print(f"  Conference Data: {conf}")
            entry_points = conf.get('entryPoints', [])
            if entry_points:
                for ep in entry_points:
                    print(f"    - {ep.get('entryPointType')}: {ep.get('uri')}")
        else:
            print(f"  No conference data (Meet link may not have been created)")
    
    except Exception as e:
        print(f"\n❌ FAILED!")
        print(f"  Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're in the hiring_agent directory and have all dependencies installed.")
except Exception as e:
    print(f"Setup error: {e}")
    import traceback
    traceback.print_exc()
