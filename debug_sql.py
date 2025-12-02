"""
Direct SQL debug to find why candidates aren't being found
"""
from db import get_connection

jd_id = "a8dfeeb0-24d1-4b21-9cf0-a2f5060330cd"

conn = get_connection()
cur = conn.cursor()

print("Debugging Interview Scheduling Query")
print("=" * 60)
print(f"JD ID: {jd_id}\n")

# Check candidate_outreach table
print("1. Checking candidate_outreach table:")
cur.execute("""
    SELECT id, resume_id, candidate_name, candidate_email, acknowledgement
    FROM candidate_outreach
    WHERE jd_id = %s
""", [jd_id])
outreach_records = cur.fetchall()
print(f"   Found {len(outreach_records)} outreach records for this JD")
for rec in outreach_records:
    print(f"   - {rec[2]} ({rec[3]}): {rec[4]}")

# Check if resumes exist
print("\n2. Checking if resumes exist:")
cur.execute("""
    SELECT co.resume_id, r.id, r.candidate_name
    FROM candidate_outreach co
    LEFT JOIN resumes r ON r.id = co.resume_id
    WHERE co.jd_id = %s AND co.acknowledgement = 'interested'
""", [jd_id])
resume_check = cur.fetchall()
print(f"   Found {len(resume_check)} resume matches")
for rec in resume_check:
    if rec[1]:
        print(f"   ✓ Resume exists: {rec[2]} (ID: {rec[0]})")
    else:
        print(f"   ✗ Resume MISSING for outreach resume_id: {rec[0]}")

# Run the actual query from interview_scheduler
print("\n3. Running the actual scheduler query:")
cur.execute("""
    SELECT 
        co.id as outreach_id,
        co.resume_id,
        co.candidate_email,
        co.candidate_name,
        r.canonical_json
    FROM candidate_outreach co
    JOIN resumes r ON r.id = co.resume_id
    WHERE co.jd_id = %s 
      AND co.acknowledgement = 'interested'
      AND co.resume_id NOT IN (
          SELECT resume_id FROM interview_schedules 
          WHERE jd_id = %s AND status NOT IN ('cancelled', 'declined')
      )
""", [jd_id, jd_id])

candidates = cur.fetchall()
print(f"   Found {len(candidates)} candidates ready for scheduling")
for c in candidates:
    print(f"   - {c[3]} ({c[2]})")

conn.close()
