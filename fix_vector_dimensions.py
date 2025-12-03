"""
Migration script to fix vector dimensions from 1536 to 768.
Run this script to update existing database tables.
"""
import psycopg2
from db import get_connection

def fix_vector_dimensions():
    """
    Alter vector columns from 1536 to 768 dimensions.
    This is necessary when switching from OpenAI embeddings to Gemini embeddings.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        print("Fixing vector dimensions in database...")
        
        # Drop and recreate memories table with correct dimensions
        cur.execute("""
            DROP TABLE IF EXISTS candidate_outreach CASCADE;
            DROP TABLE IF EXISTS interview_schedules CASCADE;
            DROP TABLE IF EXISTS resumes CASCADE;
            DROP TABLE IF EXISTS memories CASCADE;
        """)
        
        # Recreate memories table with 768 dimensions
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
        
        # Recreate resumes table with 768 dimensions
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
        
        # Recreate candidate_outreach table
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
        
        # Recreate interview_schedules table
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
        
        # Create indexes
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
        
        conn.commit()
        cur.close()
        print("✅ Vector dimensions fixed successfully!")
        print("⚠️  Note: All existing data in memories, resumes, candidate_outreach, and interview_schedules has been cleared.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error fixing vector dimensions: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    fix_vector_dimensions()
