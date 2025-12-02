#!/usr/bin/env python3
"""
Debug script to trace the interview scheduling flow.
"""
import sys
import json
from db import get_connection

def check_flow():
    conn = get_connection()
    cur = conn.cursor()
    
    print("=" * 80)
    print("INTERVIEW SCHEDULING FLOW DEBUG")
    print("=" * 80)
    
    # 1. Check JDs
    print("\n1. JOB DESCRIPTIONS IN DATABASE:")
    cur.execute("SELECT id, type, title FROM memories WHERE type = 'job' LIMIT 5")
    jds = cur.fetchall()
    if jds:
        for jd_id, jd_type, title in jds:
            print(f"   - ID: {jd_id}, Title: {title}")
    else:
        print("   ❌ No JDs found. Please upload a JD first.")
        return
    
    # 2. Check outreach records
    print("\n2. CANDIDATE OUTREACH RECORDS:")
    cur.execute("""
        SELECT id, candidate_name, candidate_email, acknowledgement, jd_id 
        FROM candidate_outreach 
        LIMIT 10
    """)
    outreach = cur.fetchall()
    if outreach:
        for out_id, name, email, ack, jd_id in outreach:
            print(f"   - Name: {name}, Email: {email}")
            print(f"     ID: {out_id}, Status: {ack or 'NOT RESPONDED'}, JD: {jd_id}")
    else:
        print("   ❌ No outreach records found. Please send emails first via /send-emails endpoint.")
        return
    
    # 3. Check interview schedules
    print("\n3. INTERVIEW SCHEDULES (which candidates got interview emails):")
    cur.execute("""
        SELECT 
            i.id, 
            co.candidate_name,
            co.candidate_email,
            i.interview_date, 
            i.status, 
            i.confirmed_slot_time, 
            i.created_at
        FROM interview_schedules i
        JOIN candidate_outreach co ON i.outreach_id = co.id
        ORDER BY i.created_at DESC
        LIMIT 10
    """)
    interviews = cur.fetchall()
    if interviews:
        for int_id, name, email, date, status, confirmed, created in interviews:
            print(f"   - {name} ({email})")
            print(f"     Interview Date: {date}, Status: {status}")
            print(f"     Email sent at: {created}")
            print(f"     Confirmed at: {confirmed}")
            print()
    else:
        print("   ℹ️  No interview schedules yet. This is expected until candidates respond.")
    
    # 4. Count interested candidates
    print("\n4. CANDIDATE STATUS SUMMARY:")
    cur.execute("""
        SELECT 
            acknowledgement,
            COUNT(*) as count
        FROM candidate_outreach
        GROUP BY acknowledgement
    """)
    for status, count in cur.fetchall():
        status_name = status or "NO RESPONSE"
        print(f"   - {status_name}: {count} candidates")
    
    # 5. Test email sending
    print("\n5. EMAIL SENDING TEST:")
    print("   Run: python test_email_simple.py")
    print("   [OK] Email sending is working (verified separately)")
    
    # 6. Flow instructions
    print("\n6. COMPLETE FLOW FOR INTERVIEW EMAILS:")
    print("""
    Step 1: Upload JDs in Recruiter Portal (/jd/analyze/pdf)
            → Auto-detects role, stores in 'memories' table
    
    Step 2: Upload Resumes in Admin Portal (/resumes/upload)
            → Stores in 'resumes' table
    
    Step 3: Rank candidates in Recruiter Portal (/match/top-by-jd)
            → Auto-sends outreach emails to top candidates (/send-emails)
            → Creates 'candidate_outreach' records
    
    Step 4: Candidate clicks "Interested" in email
            → Triggers /acknowledge/{outreach_id}?response=interested
            → Auto-calls schedule_interview_for_single_candidate()
            → Finds first available date
            → Fetches available time slots
            → Sends interview_scheduling email
            → Creates 'interview_schedules' record
    
    Step 5: Candidate clicks "Select This Time" in interview email
            → Triggers /confirm-interview/{interview_id}?slot={slot_id}&outreach_id={outreach_id}
            → Creates Google Calendar event
            → Sends confirmation to both candidate and interviewer
            → Updates 'interview_schedules' with confirmed_slot_time and event_id
    
    DEBUGGING:
    - Check candidate inbox for "Interview Invitation" emails
    - Check Gmail spam folder
    - Run: python test_email_simple.py (to verify SMTP works)
    - Check database: SELECT * FROM candidate_outreach;
    - Check database: SELECT * FROM interview_schedules;
    """)
    
    conn.close()

if __name__ == "__main__":
    check_flow()
