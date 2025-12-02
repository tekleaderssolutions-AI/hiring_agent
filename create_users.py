"""
Script to create initial admin and recruiter users
"""
import psycopg2
import hashlib
from db import get_connection

def hash_password(password):
    """Simple password hashing using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_default_users():
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # Create default admin user
        admin_password = hash_password("admin123")
        cur.execute("""
            INSERT INTO users (username, password_hash, role, email)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ("admin", admin_password, "admin", "admin@company.com"))
        
        # Create default recruiter user
        recruiter_password = hash_password("recruiter123")
        cur.execute("""
            INSERT INTO users (username, password_hash, role, email)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ("recruiter", recruiter_password, "recruiter", "recruiter@company.com"))
        
        conn.commit()
        print("Default users created successfully!")
        print("Admin credentials: username=admin, password=admin123")
        print("Recruiter credentials: username=recruiter, password=recruiter123")
        
    except Exception as e:
        print(f"Error creating users: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_default_users()
