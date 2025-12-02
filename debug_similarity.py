import os
import psycopg2
from db import get_connection

def debug_similarity():
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # Get latest JD
        cur.execute("SELECT id, title FROM memories WHERE type='job' ORDER BY created_at DESC LIMIT 1")
        jd = cur.fetchone()
        if not jd:
            print("No JD found")
            return

        print(f"Latest JD: {jd[1]} ({jd[0]})")
        
        # Get latest Resume
        cur.execute("SELECT id, candidate_name FROM resumes WHERE type='resume' ORDER BY created_at DESC LIMIT 1")
        resume = cur.fetchone()
        if not resume:
            print("No Resume found")
            return
            
        print(f"Latest Resume: {resume[1]} ({resume[0]})")
        
        # Calculate distances
        cur.execute("""
            SELECT 
                embedding <=> (SELECT embedding FROM memories WHERE id = %s) as cosine_dist,
                embedding <-> (SELECT embedding FROM memories WHERE id = %s) as euclidean_dist
            FROM resumes 
            WHERE id = %s
        """, (jd[0], jd[0], resume[0]))
        
        row = cur.fetchone()
        if row:
            cosine_dist = float(row[0])
            euclidean_dist = float(row[1])
            
            print(f"Cosine Distance: {cosine_dist}")
            print(f"Cosine Similarity (1 - dist): {1 - cosine_dist}")
            print(f"Euclidean Distance: {euclidean_dist}")
            print(f"Euclidean Similarity (1 - dist): {1 - euclidean_dist}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    debug_similarity()
