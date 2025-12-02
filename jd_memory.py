# memory_store.py
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import google.generativeai as genai
from psycopg2.extras import Json

from config import EMBEDDING_MODEL, GEMINI_API_KEY
from db import db_cursor

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)


def _ensure_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")


def build_embedding_text(structured_jd: Dict[str, Any], summary: str | None = None) -> str:
    role = structured_jd.get("role") or ""
    location = structured_jd.get("location") or ""
    primary_skills = structured_jd.get("primary_skills") or []
    exp = structured_jd.get("experience") or {}
    exp_min = exp.get("min")
    exp_max = exp.get("max")

    primary_csv = ", ".join(primary_skills)

    if exp_min is not None or exp_max is not None:
        exp_str = f"{exp_min or ''}-{exp_max or ''}".strip("-")
    else:
        exp_str = ""

    if not summary:
        summary = f"{role} in {location} with skills {primary_csv}".strip()

    return f"{role} | {location} | skills: {primary_csv} | experience: {exp_str} | summary: {summary}"


def get_embedding_vector(text: str) -> List[float]:
    """Generate embedding using Gemini's embedding API."""
    _ensure_key()
    
    # Use Gemini's embedding model
    result = genai.embed_content(
        model=f"models/{EMBEDDING_MODEL}",
        content=text,
        task_type="retrieval_document"
    )
    
    return result["embedding"]


def embedding_to_literal(vec: List[float]) -> str:
    return "[" + ",".join(str(x) for x in vec) + "]"


def build_summary(structured_jd: Dict[str, Any], raw_jd_text: str) -> str:
    role = structured_jd.get("role") or "Unknown role"
    location = structured_jd.get("location") or "Unspecified location"
    employment_type = structured_jd.get("employment_type") or "unspecified"
    exp = structured_jd.get("experience") or {}
    exp_text = ""
    if exp.get("min") is not None or exp.get("max") is not None:
        exp_text = f"{exp.get('min') or ''}-{exp.get('max') or ''} years"

    primary = ", ".join(structured_jd.get("primary_skills") or [])
    responsibilities = structured_jd.get("responsibilities") or []

    parts = [
        f"{role} opportunity based in {location} ({employment_type}).",
    ]

    if exp_text:
        parts.append(f"Experience: {exp_text}.")

    if primary:
        parts.append(f"Primary skills: {primary}.")

    if responsibilities:
        resp_sentence = "Responsibilities include " + "; ".join(responsibilities[:4]) + "."
        parts.append(resp_sentence)

    summary = " ".join(parts).strip()

    if len(summary) < 150:
        filler = raw_jd_text[: max(0, 150 - len(summary))]
        summary = f"{summary} {filler}".strip()

    if len(summary) > 800:
        summary = summary[:800].rsplit(" ", 1)[0]

    return summary


def create_memory(
    structured_jd: Dict[str, Any],
    job_id: str | None,
    raw_jd_text: str,
    source_url: str | None = None,
    created_by: str = "system",
    pii_flag: bool = False,
) -> Dict[str, Any]:
    
    memory_uuid = str(uuid.uuid4())

    now_iso = datetime.now(timezone.utc).isoformat()

    title = structured_jd.get("role") or "Untitled role"
    raw_text_snippet = raw_jd_text[:800]

    summary = build_summary(structured_jd, raw_jd_text)
    embed_text = build_embedding_text(structured_jd, summary=summary)
    embedding = get_embedding_vector(embed_text)
    embedding_literal = embedding_to_literal(embedding)

    exp = structured_jd.get("experience") or {}
    salary = structured_jd.get("salary") or {}

    metadata: Dict[str, Any] = {
        "job_id": job_id,
        "location": structured_jd.get("location"),
        "employment_type": structured_jd.get("employment_type"),
        "experience_min": exp.get("min"),
        "experience_max": exp.get("max"),
        "primary_skills": structured_jd.get("primary_skills") or [],
        "secondary_skills": structured_jd.get("secondary_skills") or [],
        "salary_min": salary.get("min"),
        "salary_max": salary.get("max"),
        "version": 1,
        "created_by": created_by,
        "created_at": now_iso,
        "source_url": source_url,
        "pii_flag": pii_flag,
        "raw_text_snippet": raw_text_snippet,
        "embedding_model": EMBEDDING_MODEL,
        "chunk_index": 0,
    }

    canonical_json = structured_jd

    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO memories (id, type, title, text, embedding, metadata, canonical_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s::vector, %s, %s, NOW(), NOW())
            """,
            [
                memory_uuid,
                "job",
                title,
                embed_text,
                embedding_literal,
                Json(metadata),
                Json(canonical_json),
            ],
        )

    memory_id = f"job:{job_id}:v1" if job_id else f"job:{memory_uuid}"

    return {
        "id": memory_uuid,  # Database UUID for embedding-based matching
        "memory_id": memory_id,
        "type": "job",
        "title": title,
        "summary": summary,
        "text": embed_text,
        "raw_text_snippet": raw_text_snippet,
        "metadata": metadata,
        "canonical_json": canonical_json,
        "embedding_model": EMBEDDING_MODEL,
        "embedding": embedding,
        "chunk_index": 0,
        "source_url": source_url,
        "pii_flag": pii_flag,
        "role": structured_jd.get("role"),  # Add role for display
    }
