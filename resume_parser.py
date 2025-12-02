"""
Resume Parser using Google Gemini API.

This module parses resumes using Gemini's structured output capabilities.
"""
import json
from typing import Dict, Any
import google.generativeai as genai
from config import GEMINI_API_KEY, CHAT_MODEL

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Define the schema for resume parsing
RESUME_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_name": {
            "type": "string",
            "description": "Full name of the candidate"
        },
        "email": {
            "type": "string",
            "description": "Email address"
        },
        "phone": {
            "type": "string",
            "description": "Phone number"
        },
        "current_title": {
            "type": "string",
            "description": "Current or most recent job title"
        },
        "location": {
            "type": "string",
            "description": "Current location (city, state, country)"
        },
        "total_experience_years": {
            "type": "number",
            "description": "Total years of professional experience"
        },
        "skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of technical skills"
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "degree": {"type": "string"},
                    "institution": {"type": "string"},
                    "year": {"type": "string"}
                }
            },
            "description": "Educational background"
        },
        "work_experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "company": {"type": "string"},
                    "duration": {"type": "string"},
                    "responsibilities": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "description": "Work experience history"
        },
        "certifications": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Professional certifications"
        },
        "summary": {
            "type": "string",
            "description": "Professional summary or objective"
        }
    },
    "required": ["candidate_name"]
}


def parse_resume_text(resume_text: str) -> Dict[str, Any]:
    """
    Parse a resume using Gemini's structured output.
    
    Args:
        resume_text: Raw resume text
        
    Returns:
        Dictionary containing structured resume information
    """
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text cannot be empty")
    
    try:
        # Create the model
        model = genai.GenerativeModel(CHAT_MODEL)
        
        # Create the prompt
        prompt = f"""You are an expert at parsing resumes. Extract structured information from the following resume.

Resume:
{resume_text}

Extract the following information:
- candidate_name: Full name of the candidate
- email: Email address
- phone: Phone number
- current_title: Current or most recent job title
- location: Current location
- total_experience_years: Total years of professional experience (as a number)
- skills: List of technical skills
- education: Educational background (degree, institution, year)
- work_experience: Work history (title, company, duration, responsibilities)
- certifications: Professional certifications
- summary: Professional summary or objective

Return the information as a JSON object matching this structure:
{json.dumps(RESUME_SCHEMA, indent=2)}

If any field is not mentioned in the resume, omit it or use null/empty array as appropriate."""

        # Generate content
        response = model.generate_content(prompt)
        
        # Extract the response text
        response_text = response.text.strip()
        
        # Try to parse JSON from the response
        # Gemini might wrap it in markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Remove ```json
        if response_text.startswith("```"):
            response_text = response_text[3:]  # Remove ```
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Remove trailing ```
        
        response_text = response_text.strip()
        
        # Parse the JSON
        parsed_resume = json.loads(response_text)
        
        # Ensure required fields exist
        if "candidate_name" not in parsed_resume or not parsed_resume["candidate_name"]:
            parsed_resume["candidate_name"] = "Unknown Candidate"
            
        return parsed_resume
        
    except json.JSONDecodeError as e:
        # If JSON parsing fails, return a minimal structure
        print(f"JSON parsing error: {e}")
        print(f"Response text: {response_text}")
        return {
            "candidate_name": "Unknown Candidate",
            "error": f"Failed to parse resume: {str(e)}"
        }
    except Exception as e:
        print(f"Error parsing resume: {e}")
        raise RuntimeError(f"Failed to parse resume: {str(e)}")
