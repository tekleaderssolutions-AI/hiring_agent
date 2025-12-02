"""
Co-ordinates resume parsing + persistence for uploaded documents.
"""
from typing import Dict, Any, Optional

from resume_parser import parse_resume_text
from resume_memory import save_parsed_resume_and_memory


def process_resume_text(
    raw_text: str,
    *,
    source_url: Optional[str] = None,
    file_name: Optional[str] = None,
) -> Dict[str, Any]:
    if not raw_text.strip():
        raise ValueError("Resume text is empty")

    parsed = parse_resume_text(raw_text)
    resume_id = save_parsed_resume_and_memory(
        parsed_resume=parsed,
        raw_text=raw_text,
        source_url=source_url or file_name,
        file_name=file_name,
    )

    return {
        "resume_id": resume_id,
        "parsed": parsed,
    }


