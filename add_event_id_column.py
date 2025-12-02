import psycopg2
from db import get_connection

def add_event_id_column():
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        print("Adding event_id column to interview_schedules table...")
        
        cur.execute("""
            ALTER TABLE interview_schedules
            ADD COLUMN IF NOT EXISTS event_id VARCHAR(255);
        """)
        
        cur.execute("""
            ALTER TABLE interview_schedules
            ADD COLUMN IF NOT EXISTS event_link TEXT;
        """)
        
        conn.commit()
        cur.close()
        print("Successfully added event_id and event_link columns.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error adding columns: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    add_event_id_column()
