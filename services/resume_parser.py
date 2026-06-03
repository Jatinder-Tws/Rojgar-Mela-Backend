"""
Resume Parser – uses PyMuPDF for text extraction + heuristic skill/exp parsing.
No GPT calls to keep costs minimal.
"""
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from config import settings
from services.ai_service import get_ai

logger = logging.getLogger(__name__)


def get_ocr_readiness() -> dict[str, Any]:
    """
    Check if OCR stack is available and return a diagnostics payload.
    """
    info: dict[str, Any] = {
        "ready": False,
        "engine": "tesseract",
        "tesseract_cmd": settings.TESSERACT_CMD or "tesseract",
        "details": "",
    }
    try:
        import pytesseract

        if settings.TESSERACT_CMD.strip():
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD.strip()
        cmd = pytesseract.pytesseract.tesseract_cmd
        binary_ok = bool(shutil.which(cmd)) if cmd else False
        if not binary_ok:
            info["details"] = f"Tesseract binary not found in PATH for command '{cmd}'."
            return info
        version = pytesseract.get_tesseract_version()
        info["ready"] = True
        info["details"] = f"Tesseract available (version: {version})."
        return info
    except Exception as e:
        info["details"] = f"OCR unavailable: {e}"
        return info


def _configure_tesseract_cmd() -> None:
    """Apply configured tesseract command path when provided."""
    if not settings.TESSERACT_CMD.strip():
        return
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD.strip()
    except Exception:
        return
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
        text = "\n".join(pages).strip()
        if _should_trigger_ocr(text):
            ocr_text = _ocr_pdf_with_tesseract(file_path)
            if len(ocr_text.strip()) > len(text.strip()):
                return ocr_text.strip()
        return text
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}")


def extract_text_from_doc(file_path: str) -> str:
    """Fallback: read plain text from .txt or .doc files."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception as e:
        raise ValueError(f"Failed to read file: {e}")


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from .docx documents."""
    try:
        import docx

        document = docx.Document(file_path)
        lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        return "\n".join(lines).strip()
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX: {e}")


def _should_trigger_ocr(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return True
    # Heuristic: very short content or mostly non-word chars means likely scanned PDF.
    if len(cleaned) < 300:
        return True
    words = re.findall(r"[A-Za-z0-9]{2,}", cleaned)
    return len(words) < 60


def _ocr_pdf_with_tesseract(file_path: str) -> str:
    """
    OCR fallback for scanned/image PDFs.
    Uses pypdfium2 to rasterize pages and pytesseract for OCR.
    """
    try:
        import pypdfium2 as pdfium
        import pytesseract

        _configure_tesseract_cmd()
    except Exception:
        return ""

    extracted_pages: list[str] = []
    try:
        pdf = pdfium.PdfDocument(file_path)
        total_pages = len(pdf)
        max_pages = min(total_pages, 10)  # protect latency/cost for huge files
        for page_index in range(max_pages):
            page = pdf.get_page(page_index)
            pil_image = page.render(scale=2.0).to_pil()
            page.close()
            page_text = pytesseract.image_to_string(pil_image) or ""
            if page_text.strip():
                extracted_pages.append(page_text.strip())
        pdf.close()
        return "\n\n".join(extracted_pages)
    except Exception:
        return ""


def _ocr_image_with_tesseract(file_path: str) -> str:
    """OCR for uploaded image resumes (.jpg/.jpeg/.png)."""
    try:
        from PIL import Image
        import pytesseract

        _configure_tesseract_cmd()
        with Image.open(file_path) as image:
            return (pytesseract.image_to_string(image) or "").strip()
    except Exception:
        return ""


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
    elif ext == ".docx":
        raw_text = extract_text_from_docx(file_path)
    elif ext in {".jpg", ".jpeg", ".png"}:
        raw_text = _ocr_image_with_tesseract(file_path)
    else:
        raw_text = extract_text_from_doc(file_path)

    structured = parse_resume_to_json(raw_text)
    return raw_text, structured


def _safe_json_loads(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


async def extract_profile_fields_with_ai(raw_text: str, parsed_json: dict) -> dict[str, Any]:
    """
    AI-assisted extraction for mapping resume data into users/portfolio fields.
    Falls back to heuristic values if AI is unavailable.
    """
    if not raw_text:
        return {}

    ai = get_ai()
    system_prompt = """
You are a resume information extraction engine for a job-seeker profile system.
Extract fields from resume text into valid JSON only.
Map each fact to the correct field in the schema (personal info, portfolio, skills, experience, education, etc.).
If a field is not present in the resume, use null or an empty list.
Never add markdown or commentary.
"""
    user_prompt = f"""
Return JSON with this exact shape:
{{
  "first_name": "string|null",
  "last_name": "string|null",
  "full_name": "string|null",
  "email": "string|null",
  "phone": "string|null",
  "date_of_birth": "string|null",
  "gender": "string|null",
  "city": "string|null",
  "state": "string|null",
  "linkedin_url": "string|null",
  "github_url": "string|null",
  "website_url": "string|null",
  "headline": "string|null",
  "bio": "string|null",
  "total_experience_years": "number|null",
  "current_company": "string|null",
  "current_role": "string|null",
  "highest_qualification": "string|null",
  "stream_specialization": "string|null",
  "college_institute_name": "string|null",
  "preferred_job_sector": "string|null",
  "job_role": "string|null",
  "skills": [{{"name":"string","level":"Beginner|Intermediate|Advanced|Expert"}}],
  "work_experiences": [
    {{
      "company":"string|null",
      "role":"string|null",
      "start_date":"string|null",
      "end_date":"string|null",
      "description":"string|null",
      "is_current":"boolean"
    }}
  ],
  "education": [
    {{
      "institution":"string|null",
      "degree":"string|null",
      "field":"string|null",
      "start_year":"string|null",
      "end_year":"string|null"
    }}
  ],
  "certifications": [
    {{"name":"string|null","issuer":"string|null","date":"string|null","url":"string|null"}}
  ],
  "languages": [
    {{"language":"string|null","proficiency":"Basic|Conversational|Fluent|Native"}}
  ],
  "projects": [
    {{"title":"string|null","description":"string|null","url":"string|null","technologies":["string"]}}
  ]
}}

Heuristic parsed data (can be used as hints):
{json.dumps(parsed_json, ensure_ascii=True)}

Resume text:
{raw_text[:12000]}
"""
    try:
        response = await ai.chat_completion(system_prompt, user_prompt)
        data = _safe_json_loads(response)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}
