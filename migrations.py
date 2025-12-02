import psycopg2
from db import get_connection

def init_db():
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # 1. Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # 2. Create memories table (for JDs)
        # Columns inferred from jd_memory.py insert statement:
        # id, type, title, text, embedding, metadata, canonical_json, created_at, updated_at
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id UUID PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT,
                text TEXT,
                embedding vector(768),
                metadata JSONB,
                canonical_json JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # 3. Create resumes table
        # Columns inferred from resume_memory.py insert statement:
        # id, candidate_name, email, phone, type, title, text, embedding, metadata, canonical_json, created_at, updated_at
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id UUID PRIMARY KEY,
                candidate_name TEXT,
                email TEXT,
                phone TEXT,
                type TEXT NOT NULL,
                title TEXT,
                text TEXT,
                embedding vector(768),
                metadata JSONB,
                canonical_json JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # 4. Create candidate_outreach table for email tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidate_outreach (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                resume_id UUID REFERENCES resumes(id),
                jd_id UUID REFERENCES memories(id),
                candidate_email VARCHAR(255) NOT NULL,
                candidate_name VARCHAR(255),
                email_subject TEXT,
                email_body TEXT,
                embedding vector(768),
                sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                acknowledgement VARCHAR(20),
                acknowledged_at TIMESTAMP WITH TIME ZONE,
                ats_score INTEGER,
                rank INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # 4. Create interview_schedules table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS interview_schedules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                resume_id UUID REFERENCES resumes(id),
                jd_id UUID REFERENCES memories(id),
                outreach_id UUID REFERENCES candidate_outreach(id),
                interview_date DATE NOT NULL,
                proposed_slots JSONB,
                selected_slot VARCHAR(10),
                confirmed_slot_time TIMESTAMP WITH TIME ZONE,
                event_id VARCHAR(255),
                event_link TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Create indexes for candidate_outreach
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_candidate_outreach_resume 
            ON candidate_outreach(resume_id);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_candidate_outreach_jd 
            ON candidate_outreach(jd_id);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_candidate_outreach_email 
            ON candidate_outreach(candidate_email);
        """)
        
        # Add missing columns to interview_schedules if they don't exist
        cur.execute("""
            ALTER TABLE interview_schedules
            ADD COLUMN IF NOT EXISTS event_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS event_link TEXT;
        """)
        
        conn.commit()
        cur.close()
        print("Database initialized successfully.")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
