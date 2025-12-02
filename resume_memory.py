# resume_memory.py
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

import google.generativeai as genai
from psycopg2.extras import Json

from config import EMBEDDING_MODEL, GEMINI_API_KEY
from db import get_connection

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)


def embedding_to_literal(vec: List[float]) -> str:
    return "[" + ",".join(str(x) for x in vec) + "]"


def build_resume_embedding_text(parsed: Dict[str, Any]) -> str:
    """
    {title} | {location} | skills: {skills_csv} | experience: {yrs} | summary: {one-line summary}
    """
    title = parsed.get("current_title") or ""
    location = parsed.get("location") or ""
    skills = parsed.get("skills") or []
    skills_csv = ", ".join(skills)
    exp_years = parsed.get("total_experience_yrs") or 0

    summary = f"{title} with {exp_years} years experience in {skills_csv}".strip()
    return f"{title} | {location} | skills: {skills_csv} | experience: {exp_years} | summary: {summary}"


def get_embedding(text: str) -> List[float]:
    """Generate embedding using Gemini's embedding API."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")

    # Use Gemini's embedding model
    result = genai.embed_content(
        model=f"models/{EMBEDDING_MODEL}",
        content=text,
        task_type="retrieval_document"
    )
    
    return result["embedding"]


def save_parsed_resume_and_memory(
    parsed_resume: Dict[str, Any],
    raw_text: str,
    source_url: str | None = None,
    file_name: str | None = None,
) -> str:
    """
    Persist a parsed resume into the resumes table (including its embedding and metadata).
    Returns the resume_id.
    """
    resume_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    embed_text = build_resume_embedding_text(parsed_resume)
    embedding = get_embedding(embed_text)
    embedding_literal = embedding_to_literal(embedding)

    resume_metadata = {
        "current_company": parsed_resume.get("current_company"),
        "location": parsed_resume.get("location"),
        "total_experience_yrs": parsed_resume.get("total_experience_yrs"),
        "skills": parsed_resume.get("skills") or [],
        "domain": parsed_resume.get("domain"),
        "education": parsed_resume.get("education"),
        "certifications": parsed_resume.get("certifications"),
        "projects": parsed_resume.get("projects"),
        "source_url": source_url,
        "file_name": file_name,
        "raw_text_snippet": raw_text[:800],
        "embedding_model": EMBEDDING_MODEL,
        "created_at": now_iso,
    }

    # --- Insert RESUME row ---
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO resumes (
              id,
              candidate_name,
              email,
              phone,
              type,
              title,
              text,
              embedding,
              metadata,
              canonical_json,
              created_at,
              updated_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector,%s,%s,NOW(),NOW())
            """,
            [
                resume_id,
                parsed_resume.get("candidate_name"),
                parsed_resume.get("email"),
                parsed_resume.get("phone"),
                "resume",
                parsed_resume.get("current_title"),
                embed_text,
                embedding_literal,
                Json(resume_metadata),
                Json(parsed_resume),
            ],
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()

    return resume_id
