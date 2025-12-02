"""Helpers for inserting/updating embeddings and performing ANN searches.

This module uses the `pgvector` adapter (registered in `db.get_connection`) so
you can pass Python lists or `pgvector.Vector` objects as the embedding parameter.
"""
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from db import db_cursor


def _to_vector(obj: Iterable[float]):
    try:
        # Try to use pgvector.Vector if available
        from pgvector import Vector

        return Vector(obj)
    except Exception:
        # Fallback: pass plain list, adapter registration may still cast it
        return list(obj)


def upsert_memory(
    id: UUID,
    type: str,
    title: Optional[str],
    text: Optional[str],
    embedding: Iterable[float],
    metadata: Optional[Dict[str, Any]] = None,
    canonical_json: Optional[Dict[str, Any]] = None,
):
    """Insert or update a memory row with its embedding."""
    vec = _to_vector(embedding)
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO memories (id, type, title, text, embedding, metadata, canonical_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
              type = EXCLUDED.type,
              title = EXCLUDED.title,
              text = EXCLUDED.text,
              embedding = EXCLUDED.embedding,
              metadata = EXCLUDED.metadata,
              canonical_json = EXCLUDED.canonical_json,
              updated_at = NOW();
            """,
            (str(id), type, title, text, vec, metadata, canonical_json),
        )


def upsert_resume(
    id: UUID,
    candidate_name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    type: str,
    title: Optional[str],
    text: Optional[str],
    embedding: Iterable[float],
    metadata: Optional[Dict[str, Any]] = None,
    canonical_json: Optional[Dict[str, Any]] = None,
):
    """Insert or update a resume row with its embedding."""
    vec = _to_vector(embedding)
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO resumes (id, candidate_name, email, phone, type, title, text, embedding, metadata, canonical_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
              candidate_name = EXCLUDED.candidate_name,
              email = EXCLUDED.email,
              phone = EXCLUDED.phone,
              type = EXCLUDED.type,
              title = EXCLUDED.title,
              text = EXCLUDED.text,
              embedding = EXCLUDED.embedding,
              metadata = EXCLUDED.metadata,
              canonical_json = EXCLUDED.canonical_json,
              updated_at = NOW();
            """,
            (
                str(id),
                candidate_name,
                email,
                phone,
                type,
                title,
                text,
                vec,
                metadata,
                canonical_json,
            ),
        )


def search_memories_by_embedding(query_embedding: Iterable[float], limit: int = 10):
    """Return nearest memories by cosine distance using the ivfflat index.

    Orders by cosine distance (smaller is better).
    """
    vec = _to_vector(query_embedding)
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, type, title, text, metadata, canonical_json, created_at, updated_at
            FROM memories
            ORDER BY embedding <#> %s
            LIMIT %s;
            """,
            (vec, limit),
        )
        rows = cur.fetchall()
    return rows


def search_resumes_by_embedding(query_embedding: Iterable[float], limit: int = 10):
    """Return nearest resumes by cosine distance."""
    vec = _to_vector(query_embedding)
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, candidate_name, email, phone, type, title, text, metadata, canonical_json, created_at, updated_at
            FROM resumes
            ORDER BY embedding <#> %s
            LIMIT %s;
            """,
            (vec, limit),
        )
        rows = cur.fetchall()
    return rows


if __name__ == "__main__":
    # Quick self-check: nothing runs here unless DB is configured.
    print("embeddings module loaded. Use `migrations.init_db()` to initialize DB.")
