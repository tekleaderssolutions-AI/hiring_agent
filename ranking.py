# ranking.py
from typing import List, Dict, Any

from db import get_connection


def get_jd_memory_id_by_role(role_name: str) -> str:
    """
    Find the most recent JD memory that matches a given role name.
    Tries canonical_json->>'role' and title.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id
            FROM memories
            WHERE type = 'job'
              AND (
                    LOWER(canonical_json->>'role') LIKE LOWER('%%' || %s || '%%')
                 OR LOWER(title) LIKE LOWER('%%' || %s || '%%')
              )
            ORDER BY created_at DESC
            LIMIT 1;
            """,
            [role_name, role_name],
        )
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    if not row:
        raise ValueError(f"No JD found for role name='{role_name}'")
    return row[0]  # jd_memory_id


def get_memory_embedding_literal(memory_id: str) -> str:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT embedding FROM memories WHERE id = %s", [memory_id])
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    if not row:
        raise ValueError(f"No memory found with id={memory_id}")
    return row[0]  # e.g. "[0.1,0.2,...]"


def get_top_k_resumes_for_jd_memory(jd_memory_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Core matching: given JD memory id, return top-K resumes with ATS & file_name.
    """
    jd_embedding_literal = get_memory_embedding_literal(jd_memory_id)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            WITH jd AS (SELECT %s::vector AS v)
            SELECT
                r.id AS resume_id,
                r.candidate_name,
                r.title,
                r.metadata->>'file_name' AS file_name,
                1 - (r.embedding <=> (SELECT v FROM jd)) AS similarity
            FROM resumes r
            WHERE r.type = 'resume'
            ORDER BY r.embedding <=> (SELECT v FROM jd)
            LIMIT %s;
            """,
            [jd_embedding_literal, top_k],
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    results: List[Dict[str, Any]] = []
    for rank, (resume_id, name, title, file_name, similarity) in enumerate(rows, start=1):
        ats_score = int(max(0.0, min(1.0, similarity)) * 100)
        results.append(
            {
                "resume_id": resume_id,
                "candidate_name": name,
                "current_title": title,
                "file_name": file_name,
                "similarity": float(similarity),
                "ats_score": ats_score,
                "rank": rank,
            }
        )
    return results


def get_top_k_resumes_for_role(role_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Public API method:
      - takes role_name (e.g. 'Senior Data Scientist')
      - finds JD memory internally
      - returns top-K resumes
    """
    jd_memory_id = get_jd_memory_id_by_role(role_name)
    return get_top_k_resumes_for_jd_memory(jd_memory_id, top_k=top_k)
