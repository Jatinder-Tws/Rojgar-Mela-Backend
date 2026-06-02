"""
Resume Parser – uses PyMuPDF for text extraction + heuristic skill/exp parsing.
No GPT calls to keep costs minimal.
"""
import re
from pathlib import Path
from typing import Optional

COMMON_SKILLS = {
    "python", "javascript", "typescript", "react", "angular", "vue", "node.js",
    "java", "c++", "c#", "go", "rust", "sql", "postgresql", "mysql", "mongodb",
    "redis", "docker", "kubernetes", "aws", "azure", "gcp", "fastapi", "django",
    "flask", "spring", "html", "css", "git", "linux", "machine learning", "pytorch",
    "tensorflow", "pandas", "numpy", "data analysis", "agile", "scrum",
}


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(pages).strip()
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}")


def extract_text_from_doc(file_path: str) -> str:
    """Fallback: read plain text from .txt or .doc files."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception as e:
        raise ValueError(f"Failed to read file: {e}")


def parse_resume_to_json(text: str) -> dict:
    """
    Heuristic extraction of structured fields from resume text.
    Returns: {skills, experience_years, education, email, phone, name}
    """
    text_lower = text.lower()

    # Skills – match against known skill list
    found_skills = sorted(skill for skill in COMMON_SKILLS if skill in text_lower)

    # Experience years – look for "X years" patterns
    years_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)", text_lower)
    experience_years = int(years_match.group(1)) if years_match else None

    # Email
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    email = email_match.group(0) if email_match else None

    # Phone
    phone_match = re.search(r"(?:\+?91[-\s]?)?[6-9]\d{9}", text)
    if not phone_match:
        phone_match = re.search(r"\b\d{10}\b", text)
    phone = phone_match.group(0) if phone_match else None

    # Education keywords
    edu_keywords = ["bachelor", "master", "b.tech", "m.tech", "b.e", "m.e", "bca", "mca", "phd", "degree"]
    education = [kw.upper() for kw in edu_keywords if kw in text_lower]

    return {
        "skills": found_skills,
        "experience_years": experience_years,
        "education": education[:3],
        "email": email,
        "phone": phone,
    }


def parse_resume(file_path: str, filename: str) -> tuple[str, dict]:
    """
    Full parsing pipeline.
    Returns (raw_text, structured_json)
    """
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    else:
        raw_text = extract_text_from_doc(file_path)

    structured = parse_resume_to_json(raw_text)
    return raw_text, structured
