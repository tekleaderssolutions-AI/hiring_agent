"""
Direct test of interview scheduling with detailed logging
"""
from interview_scheduler import schedule_interviews_for_interested_candidates
from datetime import datetime, timedelta
import json

# Use tomorrow's date
tomorrow = datetime.now() + timedelta(days=1)

print("Testing Interview Scheduling...")
print("=" * 60)
print(f"Date: {tomorrow.strftime('%Y-%m-%d')}")
print()

# Try all JD IDs that have interested candidates
jd_ids = [
    "a8dfeeb0-24d1-4b21-9cf0-a2f5060330cd",
    "8d737e14-92e4-480c-a2a1-34dfa993ace6",
    "5987f46a-f497-4b38-b7d6-c3816be45ba4"
]

for jd_id in jd_ids:
    print(f"\nTrying JD ID: {jd_id}")
    print("-" * 60)
    
    result = schedule_interviews_for_interested_candidates(
        jd_id=jd_id,
        interview_date=tomorrow,
        num_slots=3
    )
    
    print(json.dumps(result, indent=2, default=str))
    
    if result.get('scheduled', 0) > 0:
        print("\n✓ SUCCESS! Emails sent!")
        break
    elif 'error' in result:
        print(f"\n✗ Error: {result['error']}")
    else:
        print(f"\n- No candidates for this JD")

print("\n" + "=" * 60)
