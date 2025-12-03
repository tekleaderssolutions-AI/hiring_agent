"""
Script to create initial admin and recruiter users, or custom users via CLI.
Usage:
    python create_users.py
    python create_users.py --username myadmin --password mypass --role admin --email admin@example.com
"""
import psycopg2
import hashlib
import argparse
import sys
from db import get_connection

def hash_password(password):
    """Simple password hashing using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, role, email):
    conn = get_connection()
    try:
        cur = conn.cursor()
        password_hash = hash_password(password)
        
        cur.execute("""
            INSERT INTO users (username, password_hash, role, email)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
            RETURNING id
        """, (username, password_hash, role, email))
        
        user_id = cur.fetchone()
        conn.commit()
        
        if user_id:
            print(f"User '{username}' created successfully with role '{role}'.")
        else:
            print(f"User '{username}' already exists.")
            
    except Exception as e:
        print(f"Error creating user: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def create_default_users():
    print("Creating default users...")
    create_user("admin", "admin123", "admin", "admin@company.com")
    create_user("recruiter", "recruiter123", "recruiter", "recruiter@company.com")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create users for the Hiring Agent app')
    parser.add_argument('--username', help='Username for the new user')
    parser.add_argument('--password', help='Password for the new user')
    parser.add_argument('--role', choices=['admin', 'recruiter'], help='Role (admin or recruiter)')
    parser.add_argument('--email', help='Email address')
    
    args = parser.parse_args()
    
    if args.username and args.password and args.role:
        email = args.email or f"{args.username}@example.com"
        create_user(args.username, args.password, args.role, email)
    else:
        # If no args provided, create defaults
        create_default_users()

