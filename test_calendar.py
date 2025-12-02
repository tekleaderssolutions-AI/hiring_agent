"""
Simple test to verify Google Calendar API is enabled and credentials work.
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build

def test_credentials():
    print("Testing Google Calendar API Setup...")
    print("=" * 60)
    
    try:
        # Load credentials
        print("\n1. Loading credentials from credentials.json...")
        credentials = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        print("   SUCCESS: Credentials loaded")
        print(f"   Service Account: {credentials.service_account_email}")
        
        # Build service
        print("\n2. Building Calendar API service...")
        service = build('calendar', 'v3', credentials=credentials)
        print("   SUCCESS: Service created")
        
        # Try to access calendar
        print("\n3. Testing API access...")
        print("   Attempting to query calendar for: akkireddy41473@gmail.com")
        
        from datetime import datetime, timedelta
        tomorrow = datetime.now() + timedelta(days=1)
        start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        end = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)
        
        body = {
            "timeMin": start.isoformat() + 'Z',
            "timeMax": end.isoformat() + 'Z',
            "items": [{"id": "akkireddy41473@gmail.com"}],
            "timeZone": "Asia/Kolkata"
        }
        
        result = service.freebusy().query(body=body).execute()
        print("   SUCCESS: API call completed!")
        print(f"\n   Calendar access verified for: akkireddy41473@gmail.com")
        
        if 'akkireddy41473@gmail.com' in result.get('calendars', {}):
            busy_times = result['calendars']['akkireddy41473@gmail.com'].get('busy', [])
            print(f"   Found {len(busy_times)} busy periods")
            print("\n" + "=" * 60)
            print("SUCCESS! Google Calendar integration is working!")
            print("=" * 60)
        else:
            print("\n   WARNING: Calendar not found in response")
            print("   This might mean the calendar hasn't been shared with the service account")
            
    except Exception as e:
        print(f"\n   ERROR: {str(e)}")
        print("\n" + "=" * 60)
        print("TROUBLESHOOTING:")
        print("=" * 60)
        print("1. Make sure Google Calendar API is enabled:")
        print("   https://console.cloud.google.com/apis/library/calendar-json.googleapis.com")
        print("\n2. Share the calendar with:")
        print("   interview-scheduler@interview-agent-479906.iam.gserviceaccount.com")
        print("\n3. Grant permission: 'See all event details' or 'Make changes to events'")
        print("=" * 60)

if __name__ == "__main__":
    test_credentials()
