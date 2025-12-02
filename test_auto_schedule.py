"""
Test automatic interview scheduling on candidate acknowledgement
"""
import requests
from db import get_connection

print("Testing Automatic Interview Scheduling")
print("=" * 60)

# First, let's create a test outreach record
conn = get_connection()
cur = conn.cursor()

# Find a JD and resume that haven't been used yet
cur.execute("""
    SELECT m.id, r.id, r.candidate_name, r.email
    FROM memories m
    CROSS JOIN resumes r
    WHERE m.type = 'job'
    AND NOT EXISTS (
        SELECT 1 FROM candidate_outreach co 
        WHERE co.jd_id = m.id AND co.resume_id = r.id
    )
    LIMIT 1
""")

result = cur.fetchone()

if not result:
    print("No available JD/Resume combinations for testing")
    print("Using existing outreach record instead...")
    
    # Find an existing outreach that's not interested yet
    cur.execute("""
        SELECT id, candidate_name, candidate_email
        FROM candidate_outreach
        WHERE acknowledgement IS NULL OR acknowledgement = 'not_interested'
        LIMIT 1
    """)
    
    existing = cur.fetchone()
    if existing:
        outreach_id = existing[0]
        print(f"Using existing outreach: {existing[1]} ({existing[2]})")
    else:
        print("No test data available")
        conn.close()
        exit()
else:
    jd_id, resume_id, candidate_name, email = result
    
    # Create a test outreach record
    import uuid
    outreach_id = str(uuid.uuid4())
    
    cur.execute("""
        INSERT INTO candidate_outreach 
        (id, resume_id, jd_id, candidate_name, candidate_email, ats_score, created_at)
        VALUES (%s, %s, %s, %s, %s, 85, NOW())
        RETURNING id
    """, [outreach_id, resume_id, jd_id, candidate_name, email])
    
    conn.commit()
    print(f"Created test outreach for: {candidate_name} ({email})")

conn.close()

# Now test the acknowledgement endpoint
print(f"\nOutreach ID: {outreach_id}")
print("\nSimulating candidate clicking 'I'm Interested'...")
print("-" * 60)

url = f"http://localhost:8000/acknowledge/{outreach_id}?response=interested"

try:
    response = requests.get(url)
    
    if response.status_code == 200:
        print("✓ Acknowledgement recorded successfully")
        print("\nChecking if interview was scheduled...")
        
        # Check database for interview
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, interview_date, status
            FROM interview_schedules
            WHERE outreach_id = %s
        """, [outreach_id])
        
        interview = cur.fetchone()
        conn.close()
        
        if interview:
            print(f"✓ Interview scheduled!")
            print(f"  Interview ID: {interview[0]}")
            print(f"  Date: {interview[1]}")
            print(f"  Status: {interview[2]}")
            print("\n✓ SUCCESS! Automatic scheduling is working!")
        else:
            print("✗ No interview found in database")
            print("  (This might be expected if candidate was already scheduled)")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"✗ Error: {e}")
    print("\nMake sure the server is running:")
    print("  python -m uvicorn main:app --reload")

print("\n" + "=" * 60)
