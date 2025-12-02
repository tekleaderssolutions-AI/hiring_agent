"""
Test script to verify single candidate scheduling with first available date logic.
"""
import requests
from db import get_connection
from datetime import datetime

print("Testing Single Candidate Scheduling Logic")
print("=" * 60)

# 1. Create a fresh test candidate outreach record
conn = get_connection()
cur = conn.cursor()

# Find a JD
cur.execute("SELECT id, title FROM memories WHERE type = 'job' LIMIT 1")
jd_row = cur.fetchone()

if not jd_row:
    print("Error: No JD found")
    exit()

jd_id, jd_title = jd_row
print(f"Using JD: {jd_title} ({jd_id})")

# Find a resume with valid email
cur.execute("SELECT id, candidate_name, email FROM resumes WHERE email IS NOT NULL LIMIT 1")
resume_row = cur.fetchone()

if not resume_row:
    print("Error: No resume found")
    exit()

resume_id, candidate_name, email = resume_row
print(f"Using Candidate: {candidate_name} ({email})")

# Create a unique outreach record
import uuid
outreach_id = str(uuid.uuid4())

cur.execute("""
    INSERT INTO candidate_outreach 
    (id, resume_id, jd_id, candidate_name, candidate_email, ats_score, created_at)
    VALUES (%s, %s, %s, %s, %s, 85, NOW())
    RETURNING id
""", [outreach_id, resume_id, jd_id, candidate_name, email])

conn.commit()
print(f"Created test outreach ID: {outreach_id}")

conn.close()

# 2. Trigger the acknowledgement endpoint
print("\nSimulating candidate clicking 'I'm Interested'...")
url = f"http://localhost:8000/acknowledge/{outreach_id}?response=interested"

try:
    response = requests.get(url)
    
    if response.status_code == 200:
        print("SUCCESS: Acknowledgement request successful")
        
        # 3. Verify the interview was scheduled
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, interview_date, status, created_at 
            FROM interview_schedules 
            WHERE outreach_id = %s
        """, [outreach_id])
        
        interview = cur.fetchone()
        
        if interview:
            print(f"\nSUCCESS! Interview scheduled automatically.")
            print(f"  Interview ID: {interview[0]}")
            print(f"  Date: {interview[1]} (Should be first available date)")
            print(f"  Status: {interview[2]}")
            
            # Verify it's not just tomorrow (unless tomorrow is the first available)
            today = datetime.now().date()
            scheduled_date = interview[1]
            days_diff = (scheduled_date - today).days
            print(f"  Scheduled for {days_diff} days from now")
            
        else:
            print("\nFAILURE: No interview record found in database.")
            
        conn.close()
        
    else:
        print(f"\nError calling endpoint: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\nException: {e}")

print("\n" + "=" * 60)
