"""
Test script to verify interview date overlap prevention.
"""
import requests
from db import get_connection
from datetime import datetime, timedelta
import uuid

print("Testing Interview Date Overlap Prevention")
print("=" * 60)

conn = get_connection()
cur = conn.cursor()

# 1. Setup: Find a JD and create two test candidates
cur.execute("SELECT id, title FROM memories WHERE type = 'job' LIMIT 1")
jd_row = cur.fetchone()
if not jd_row:
    print("Error: No JD found")
    exit()
jd_id, jd_title = jd_row
print(f"Using JD: {jd_title}")

# Find a resume with email
cur.execute("SELECT id, candidate_name, email FROM resumes WHERE email IS NOT NULL LIMIT 1")
resume_row = cur.fetchone()
if not resume_row:
    print("Error: No resume found")
    exit()
resume_id, candidate_name, email = resume_row

# Create Candidate 1
outreach_id_1 = str(uuid.uuid4())
cur.execute("""
    INSERT INTO candidate_outreach 
    (id, resume_id, jd_id, candidate_name, candidate_email, ats_score, created_at)
    VALUES (%s, %s, %s, %s, %s, 85, NOW())
    RETURNING id
""", [outreach_id_1, resume_id, jd_id, f"Test Candidate 1", "test1@example.com"])
print(f"Created Candidate 1 (Outreach ID: {outreach_id_1})")

# Create Candidate 2
outreach_id_2 = str(uuid.uuid4())
cur.execute("""
    INSERT INTO candidate_outreach 
    (id, resume_id, jd_id, candidate_name, candidate_email, ats_score, created_at)
    VALUES (%s, %s, %s, %s, %s, 85, NOW())
    RETURNING id
""", [outreach_id_2, resume_id, jd_id, f"Test Candidate 2", "test2@example.com"])
print(f"Created Candidate 2 (Outreach ID: {outreach_id_2})")

conn.commit()
conn.close()

# 2. Schedule Candidate 1
print("\nScheduling Candidate 1...")
url = f"http://localhost:8000/acknowledge/{outreach_id_1}?response=interested"
try:
    resp1 = requests.get(url)
    if resp1.status_code == 200:
        print("SUCCESS: Candidate 1 acknowledged")
    else:
        print(f"Error: {resp1.status_code} - {resp1.text}")
except Exception as e:
    print(f"Exception: {e}")

# 3. Schedule Candidate 2
print("\nScheduling Candidate 2...")
url = f"http://localhost:8000/acknowledge/{outreach_id_2}?response=interested"
try:
    resp2 = requests.get(url)
    if resp2.status_code == 200:
        print("SUCCESS: Candidate 2 acknowledged")
    else:
        print(f"Error: {resp2.status_code} - {resp2.text}")
except Exception as e:
    print(f"Exception: {e}")

# 4. Verify Dates
print("\nVerifying Dates...")
conn = get_connection()
cur = conn.cursor()

cur.execute("""
    SELECT outreach_id, interview_date 
    FROM interview_schedules 
    WHERE outreach_id IN (%s, %s)
""", [outreach_id_1, outreach_id_2])

rows = cur.fetchall()
dates = {}
for oid, date in rows:
    dates[oid] = date

date1 = dates.get(outreach_id_1)
date2 = dates.get(outreach_id_2)

print(f"Candidate 1 Date: {date1}")
print(f"Candidate 2 Date: {date2}")

if date1 and date2:
    if date1 != date2:
        print("\nSUCCESS! Dates are different.")
    else:
        print("\nFAILURE! Dates are the same.")
else:
    print("\nFAILURE! Could not retrieve both dates.")

conn.close()
print("=" * 60)
