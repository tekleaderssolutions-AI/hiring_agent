
import psycopg2
from contextlib import contextmanager

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def get_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    # If pgvector is installed, register the vector adapter so we can
    # pass Python lists or pgvector.Vector objects as parameters.
    try:
        from pgvector.psycopg2 import register_vector

        register_vector(conn)
    except Exception:
        # If pgvector is not installed or registration fails, continue
        # without adapter (raw SQL operations still work).
        pass

    return conn

@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
