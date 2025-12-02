"""
Thin wrapper around the lower-level ranking helpers to keep FastAPI clean.
"""
from typing import List, Dict, Any

from ranking import get_top_k_resumes_for_role


def get_top_matches_for_role(role_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
    if not role_name.strip():
        raise ValueError("role_name is required")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    return get_top_k_resumes_for_role(role_name=role_name, top_k=top_k)


