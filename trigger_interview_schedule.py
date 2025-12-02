"""
Test script to trigger interview scheduling for the correct JD
"""
import requests
from datetime import datetime, timedelta

# Calculate tomorrow's date
tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

# API endpoint
url = "http://localhost:8000/schedule-interviews"

# Use the JD ID that has interested candidates
data = {
    "jd_id": "a8dfeeb0-24d1-4b21-9cf0-a2f5060330cd",  # This JD has interested candidates
    "interview_date": tomorrow
}

print("Triggering Interview Scheduling...")
print(f"JD ID: {data['jd_id']}")
print(f"Interview Date: {data['interview_date']}")
print("=" * 60)

try:
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print("\nSUCCESS!")
        print(f"Total candidates: {result.get('total', 0)}")
        print(f"Scheduled: {result.get('scheduled', 0)}")
        print(f"Failed: {result.get('failed', 0)}")
        
        if 'results' in result:
            print("\nDetails:")
            for r in result['results']:
                status_icon = "✓" if r.get('status') == 'success' else "✗"
                print(f"  {status_icon} {r.get('candidate_name')} ({r.get('email')}): {r.get('status')}")
                if r.get('status') == 'error':
                    print(f"    Error: {r.get('message')}")
                    
        print("\n" + "=" * 60)
        print("Check your email inbox for interview invitation!")
        print("=" * 60)
    else:
        print(f"\nERROR: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\nERROR: {e}")
    print("\nMake sure the server is running:")
    print("  python -m uvicorn main:app --reload")
