"""
Debug script to check interview scheduling flow
"""
from db import get_connection

def check_interview_setup():
    print("Checking Interview Scheduling Setup...")
    print("=" * 60)
    
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # Check for interested candidates
        print("\n1. Checking for interested candidates...")
        cur.execute("""
            SELECT 
                co.id,
                co.candidate_name,
                co.candidate_email,
                co.acknowledgement,
                m.title as jd_title,
                co.jd_id
            FROM candidate_outreach co
            JOIN memories m ON m.id = co.jd_id
            WHERE co.acknowledgement = 'interested'
            ORDER BY co.created_at DESC
            LIMIT 5
        """)
        
        interested = cur.fetchall()
        
        if interested:
            print(f"   Found {len(interested)} interested candidate(s):")
            for outreach_id, name, email, ack, jd_title, jd_id in interested:
                print(f"   - {name} ({email}) for {jd_title}")
                print(f"     JD ID: {jd_id}")
        else:
            print("   NO interested candidates found!")
            print("   TIP: Candidates need to click 'I'm Interested' in the outreach email first")
        
        # Check for scheduled interviews
        print("\n2. Checking scheduled interviews...")
        cur.execute("""
            SELECT 
                i.id,
                r.candidate_name,
                i.interview_date,
                i.status,
                i.created_at
            FROM interview_schedules i
            JOIN resumes r ON r.id = i.resume_id
            ORDER BY i.created_at DESC
            LIMIT 5
        """)
        
        interviews = cur.fetchall()
        
        if interviews:
            print(f"   Found {len(interviews)} scheduled interview(s):")
            for int_id, name, date, status, created in interviews:
                print(f"   - {name} on {date} (Status: {status})")
        else:
            print("   No interviews scheduled yet")
        
        # Check email configuration
        print("\n3. Checking email configuration...")
        from config import SMTP_USER, FROM_EMAIL, INTERVIEWER_EMAIL
        print(f"   SMTP User: {SMTP_USER}")
        print(f"   From Email: {FROM_EMAIL}")
        print(f"   Interviewer Email: {INTERVIEWER_EMAIL}")
        
        # Check if there are any JDs
        print("\n4. Checking available JDs...")
        cur.execute("""
            SELECT id, title, created_at
            FROM memories
            WHERE type = 'job'
            ORDER BY created_at DESC
            LIMIT 3
        """)
        
        jds = cur.fetchall()
        if jds:
            print(f"   Found {len(jds)} JD(s):")
            for jd_id, title, created in jds:
                print(f"   - {title} (ID: {jd_id})")
        else:
            print("   No JDs found")
        
        cur.close()
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        
        if not interested:
            print("1. Make sure candidates have clicked 'I'm Interested'")
            print("2. Check the candidate_outreach table for acknowledgement status")
        else:
            jd_id_to_use = interested[0][5] if interested else (jds[0][0] if jds else 'JD-ID-HERE')
            print("1. Use the /schedule-interviews endpoint with:")
            print(f"   - jd_id: {jd_id_to_use}")
            print("   - interview_date: 2025-12-05 (or any future date)")
            print("\n2. Example curl command:")
            print(f'   curl -X POST http://localhost:8000/schedule-interviews -F "jd_id={jd_id_to_use}" -F "interview_date=2025-12-05"')
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    check_interview_setup()
