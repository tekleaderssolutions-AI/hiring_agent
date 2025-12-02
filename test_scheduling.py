#!/usr/bin/env python3
"""
Test the interview scheduling flow to find the exact error.
"""
from interview_scheduler import schedule_interview_for_single_candidate
from db import get_connection

# Get the most recent "interested" candidate that wasn't emailed
conn = get_connection()
cur = conn.cursor()

# Find a candidate marked interested but NOT emailed (no interview_schedules record)
cur.execute("""
    SELECT co.id 
    FROM candidate_outreach co
    WHERE co.acknowledgement = 'interested'
    AND NOT EXISTS (
        SELECT 1 FROM interview_schedules WHERE outreach_id = co.id
    )
    ORDER BY co.acknowledged_at DESC
    LIMIT 1
""")

result = cur.fetchone()
conn.close()

if not result:
    print("No candidates found who are 'interested' but not emailed.")
    print("All interested candidates have received interview emails.")
else:
    outreach_id = result[0]
    print(f"Testing scheduling for outreach_id: {outreach_id}")
    print("=" * 80)
    
    try:
        result = schedule_interview_for_single_candidate(outreach_id, num_slots=3)
        print("\nScheduling Result:")
        print(result)
    except Exception as e:
        print(f"\nError during scheduling: {e}")
        import traceback
        traceback.print_exc()
