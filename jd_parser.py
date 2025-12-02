import json
from typing import Any, Dict, Iterable

import yaml
import google.generativeai as genai

from config import CHAT_MODEL, GEMINI_API_KEY

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

FUNCTION_SCHEMA = {
    "name": "extract_jd",
    "description": "Extract structured fields from a job description",
    "parameters": {
        "type": "object",
        "properties": {
            "role": {"type": ["string", "null"]},
            "team": {"type": ["string", "null"]},
            "location": {"type": ["string", "null"]},
            "employment_type": {"type": ["string", "null"]},
            "experience": {
                "type": ["object", "null"],
                "properties": {
                    "min": {"type": ["integer", "null"]},
                    "max": {"type": ["integer", "null"]},
                    "units": {"type": ["string", "null"]},
                },
            },
            "salary": {
                "type": ["object", "null"],
                "properties": {
                    "min": {"type": ["number", "null"]},
                    "max": {"type": ["number", "null"]},
                    "currency": {"type": ["string", "null"]},
                },
            },
            "primary_skills": {"type": "array", "items": {"type": "string"}},
            "secondary_skills": {"type": "array", "items": {"type": "string"}},
            "responsibilities": {"type": "array", "items": {"type": "string"}},
            "education": {"type": "array", "items": {"type": "string"}},
            "nice_to_have": {"type": "array", "items": {"type": "string"}},
            "keywords": {"type": "array", "items": {"type": "string"}},
        },
    },
}

FALLBACK_PROMPT = (
    "You are a structured job-description parser. Output only valid JSON matching this schema: "
    "{ 'role': string|null, 'team': string|null, 'location': string|null, 'employment_type': string|null, "
    "'experience': {'min': int|null, 'max': int|null, 'units': 'years'|null}|null, "
    "'salary': {'min': number|null, 'max': number|null, 'currency': string|null}|null, "
    "'primary_skills': [strings], 'secondary_skills': [strings], 'responsibilities': [strings], "
    "'education': [strings], 'nice_to_have': [strings], 'keywords': [strings] }. Return ONLY JSON."
)


def _ensure_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")


def _call_llm_with_schema(jd_text: str) -> Dict[str, Any]:
    """Call Gemini API with structured schema for JD parsing."""
    _ensure_key()
    
    # Create the model
    model = genai.GenerativeModel(CHAT_MODEL)
    
    # Create structured prompt
    prompt = f"""You are a precise JD parsing assistant. Extract structured fields from this job description.

Job Description:
{jd_text}

Extract and return a JSON object with the following fields:
- role: Job title (string or null)
- team: Team name (string or null)
- location: Job location (string or null)
- employment_type: Type of employment like Full-time, Part-time, Contract (string or null)
- experience: Object with min (integer), max (integer), units (string like 'years') or null
- salary: Object with min (number), max (number), currency (string) or null
- primary_skills: Array of required/primary technical skills
- secondary_skills: Array of nice-to-have/secondary skills
- responsibilities: Array of key job responsibilities
- education: Array of educational requirements
- nice_to_have: Array of additional nice-to-have qualifications
- keywords: Array of important keywords from the JD

Return ONLY a valid JSON object. Do not include any explanation or markdown formatting."""

    # Generate content
    response = model.generate_content(prompt)
    
    # Extract and parse response
    response_text = response.text.strip()
    
    # Remove markdown code blocks if present
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    
    response_text = response_text.strip()
    
    return json.loads(response_text)


def _extract_structured_json(content: str) -> Dict[str, Any]:
    """
    Try multiple strategies to coerce a JSON-like string into a real dict.
    LLMs sometimes wrap JSON with prose or swap double quotes for single ones,
    so we progressively clean until parsing succeeds.
    """

    def _candidates(raw: str) -> Iterable[str]:
        stripped = raw.strip()
        if stripped:
            yield stripped

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            yield stripped[start : end + 1]

    for candidate in _candidates(content):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        try:
            parsed = yaml.safe_load(candidate)
            if isinstance(parsed, dict):
                return parsed
        except yaml.YAMLError:
            pass

    raise ValueError("LLM response missing valid JSON")


def _fallback_parse(jd_text: str) -> Dict[str, Any]:
    """Fallback parsing method using simple prompt."""
    _ensure_key()
    
    model = genai.GenerativeModel(CHAT_MODEL)
    
    prompt = f"""{FALLBACK_PROMPT}

Job Description:
{jd_text}"""
    
    response = model.generate_content(prompt)
    content = response.text or ""
    
    return _extract_structured_json(content)


def parse_jd_with_function_call(jd_text: str) -> Dict[str, Any]:
    """
    Parse job description text using Gemini API.
    
    Tries structured parsing first, falls back to simpler method if needed.
    """
    try:
        return _call_llm_with_schema(jd_text)
    except Exception:
        return _fallback_parse(jd_text)
