import json
import re
from typing import List, Optional
from app.core.config import settings
from openai import AsyncOpenAI
import google.genai as genai


def get_gemini_client():
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def get_openai_client():
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_job_descriptions(
    title: str, exp_min: Optional[str] = None, exp_max: Optional[str] = None,
    sal_min: Optional[str] = None, sal_max: Optional[str] = None, salary_range: Optional[str] = None,
    location: Optional[str] = None, job_type: Optional[str] = None, employment_type: Optional[str] = None,
    shift: Optional[str] = None, required_skills: Optional[List[str]] = None, perks: Optional[List[str]] = None
):
    if not title:
        raise ValueError("title is required")

    # Set defaults for display
    exp_min_display = exp_min if exp_min else "not specified"
    exp_max_display = exp_max if exp_max else "not specified"
    sal_min_display = sal_min if sal_min else "not specified"
    sal_max_display = sal_max if sal_max else "not specified"
    
    # Use provided salary_range or construct from min/max
    if not salary_range and sal_min and sal_max:
        salary_range = f"{sal_min}-{sal_max} LPA"
    elif not salary_range:
        salary_range = "not specified"
    
    location_display = location if location else "not specified"
    job_type_display = job_type if job_type else "not specified"
    employment_type_display = employment_type if employment_type else "not specified"
    shift_display = shift if shift else "not specified"
    
    # Format skills and perks
    skills_str = ", ".join(required_skills) if required_skills else "not specified"
    perks_str = ", ".join(perks) if perks else "not specified"

    exp_info = ""
    if exp_min or exp_max:
        exp_parts = []
        if exp_min:
            exp_parts.append(f"Minimum: {exp_min} years")
        if exp_max:
            exp_parts.append(f"Maximum: {exp_max} years")
        exp_info = f"Experience: {', '.join(exp_parts)}\n"

    sal_info = ""
    if sal_min or sal_max:
        sal_parts = []
        if sal_min:
            sal_parts.append(f"Minimum: {sal_min}")
        if sal_max:
            sal_parts.append(f"Maximum: {sal_max}")
        sal_info = f"Salary: {', '.join(sal_parts)}\n"

    prompt = f"""
    Generate exactly 2 different job descriptions.

    JOB_TITLE: {title}
    {exp_info}
    {sal_info}
    LOCATION: {location_display}
    JOB_TYPE: {job_type_display}
    EMPLOYMENT_TYPE: {employment_type_display}
    SHIFT: {shift_display}
    REQUIRED_SKILLS: {skills_str}
    PERKS: {perks_str}
    
    Rules:
    - Use the provided details to create comprehensive job descriptions
    - Each description should be a paragraph (not bullet points) that flows naturally
    - Keep them different in tone and focus
    - First description should be concise and professional
    - Second description should be more engaging and candidate-focused
    - Include all relevant information from the payload

    Return ONLY valid JSON:
    {{
      "description_1": "string",
      "description_2": "string"
    }}
    """

    # Try Gemini first
    try:
        client = get_gemini_client()
        system_instruction = "You are a professional technical recruiter."
        response = client.models.generate_content(
            model=settings.GEMINI_CHAT_MODEL,
            contents=[system_instruction, prompt],
            config={"temperature": 0.4, "response_mime_type": "application/json"},
        )
        content = response.text
        data = json.loads(content)
        return {
            "description_1": data.get("description_1", ""),
            "description_2": data.get("description_2", ""),
        }
    except Exception as e:
        print(f"Gemini failed for job descriptions: {e}")
        # Fallback to OpenAI
        pass

    # Fallback to OpenAI
    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional technical recruiter.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return {
            "description_1": data.get("description_1", ""),
            "description_2": data.get("description_2", ""),
        }
    except Exception as e:
        print("OpenAI JSON PARSE ERROR:", str(e))
        print("RAW:", content if "content" in locals() else "No content")
        raise ValueError("Invalid AI response format")


async def generate_job_skills(
    title: str, exp_min: Optional[str] = None, exp_max: Optional[str] = None
):
    if not title:
        raise ValueError("title is required")

    exp_min_display = exp_min if exp_min else "not specified"
    exp_max_display = exp_max if exp_max else "not specified"

    exp_info = ""
    if exp_min or exp_max:
        exp_parts = []
        if exp_min:
            exp_parts.append(f"Minimum: {exp_min} years")
        if exp_max:
            exp_parts.append(f"Maximum: {exp_max} years")
        exp_info = f"Experience: {', '.join(exp_parts)}\n"

    prompt = f"""
    Generate skills for the job.

    JOB_TITLE: {title}
    {exp_info}
    Rules:
    - Use the provided experience range ({exp_min_display} to {exp_max_display} years) if given
    - Return 10–15 skills
    - Only single keywords (no sentences)
    - Include tools, technologies, and soft skills
    - No explanations

    Return ONLY JSON:
    {{
      "skills": ["skill1", "skill2", "skill3"]
    }}
    """

    # Try Gemini first
    try:
        client = get_gemini_client()
        system_instruction = "You are a technical hiring expert."
        response = client.models.generate_content(
            model=settings.GEMINI_CHAT_MODEL,
            contents=[system_instruction, prompt],
            config={"temperature": 0.3, "response_mime_type": "application/json"},
        )
        content = response.text
        data = json.loads(content)
        return {"skills": data.get("skills", [])}
    except Exception as e:
        print(f"Gemini failed for job skills: {e}")
        # Fallback to OpenAI
        pass

    # Fallback to OpenAI
    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a technical hiring expert."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return {"skills": data.get("skills", [])}
    except Exception as e:
        print("OpenAI JSON PARSE ERROR:", str(e))
        print("RAW:", content if "content" in locals() else "No content")
        raise ValueError("Invalid AI response format")


_EMPLOYMENT = {
    "full time": "full_time",
    "full-time": "full_time",
    "part time": "part_time",
    "part-time": "part_time",
    "contract": "contract",
    "internship": "internship",
    "intern": "internship",
    "freelance": "freelance",
}
_ENGAGEMENT = {
    "permanent": "permanent",
    "temporary": "temporary",
    "contractual": "contractual",
    "consultant": "consultant",
}
_WORK_MODE = {
    "on-site": "in_office",
    "onsite": "in_office",
    "on site": "in_office",
    "in office": "in_office",
    "office": "in_office",
    "remote": "wfh",
    "work from home": "wfh",
    "wfh": "wfh",
    "hybrid": "hybrid",
}
_EDUCATION = ("10th", "12th", "diploma", "graduate", "post graduate", "doctorate", "any")
_INTERVIEW = ("walk-in", "phone screen", "technical round", "hr round", "technical + hr", "ai interview")
_BENEFITS = (
    "Health Insurance",
    "Flexible Hours",
    "Transport",
    "Food Allowance",
    "Weekly Payout",
    "Joining Bonus",
    "Remote Work",
    "Performance Bonus",
    "Paid Time Off",
)


def _loads_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def _annual_from_amount(value) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    try:
        num = float(str(value).replace(",", "").strip())
    except ValueError:
        return None
    if num <= 0:
        return None
    if num <= 500:
        num = num * 100000
    return str(int(round(num)))


def _clean_str(value, limit: int = 1000) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def _clean_skills(value) -> list:
    if not isinstance(value, list):
        return []
    skills = []
    for item in value:
        text = str(item).strip()
        if text and text not in skills:
            skills.append(text[:40])
    return skills[:20]


def normalize_spoken_job(data: dict) -> dict:
    employment = str(data.get("employment_type") or "").strip().lower().replace("_", " ")
    engagement = str(data.get("engagement") or "").strip().lower()
    mode = str(data.get("job_type") or "").strip().lower().replace("_", " ")
    education = str(data.get("education") or "").strip().lower()
    interview = str(data.get("interview_process") or "").strip().lower()
    benefits = []
    for item in data.get("benefits") or []:
        label = str(item).strip()
        match = next((b for b in _BENEFITS if b.lower() == label.lower()), None)
        if match and match not in benefits:
            benefits.append(match)
    deadline = _clean_str(data.get("application_deadline"), 10)
    if deadline and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline):
        deadline = None
    return {
        "title": _clean_str(data.get("title"), 200),
        "employment_type": _EMPLOYMENT.get(employment) or (employment.replace(" ", "_") if employment.replace(" ", "_") in _EMPLOYMENT.values() else None),
        "engagement": _ENGAGEMENT.get(engagement),
        "exp_min": _clean_str(data.get("exp_min"), 4),
        "exp_max": _clean_str(data.get("exp_max"), 4),
        "relevant_exp_min": _clean_str(data.get("relevant_exp_min"), 4),
        "relevant_exp_max": _clean_str(data.get("relevant_exp_max"), 4),
        "post_count": _clean_str(data.get("post_count"), 4),
        "sal_min_annual": _annual_from_amount(data.get("sal_min_annual") or data.get("sal_min")),
        "sal_max_annual": _annual_from_amount(data.get("sal_max_annual") or data.get("sal_max")),
        "city": _clean_str(data.get("city"), 80),
        "state": _clean_str(data.get("state"), 80),
        "country": _clean_str(data.get("country"), 80),
        "job_type": _WORK_MODE.get(mode) or (mode if mode in {"in_office", "wfh", "hybrid"} else None),
        "summary": _clean_str(data.get("summary"), 500),
        "responsibilities": _clean_str(data.get("responsibilities"), 1000),
        "required_skills": _clean_skills(data.get("required_skills")),
        "preferred_skills": _clean_skills(data.get("preferred_skills")),
        "qualifications": _clean_str(data.get("qualifications"), 1000),
        "education": education if education in _EDUCATION else None,
        "application_deadline": deadline,
        "interview_process": interview if interview in _INTERVIEW else None,
        "benefits": benefits,
        "additional_notes": _clean_str(data.get("additional_notes"), 500),
    }


def heuristic_spoken_job(transcript: str) -> dict:
    text = re.sub(r"\s+", " ", transcript or "").strip()
    low = text.lower()
    data: dict = {}
    title_match = re.search(
        r"(?:job|role|position|opening)\s+(?:for|of)\s+(?:an?\s+)?(.+?)(?:\s+at\s+|\s+full|\s+part|\s+with|\s+location|\s+in\s+|\s+salary|,|\.|$)",
        text,
        re.I,
    )
    if title_match:
        data["title"] = title_match.group(1).strip(" .")
    for phrase, value in _EMPLOYMENT.items():
        if phrase in low:
            data["employment_type"] = value
            break
    for phrase, value in _ENGAGEMENT.items():
        if phrase in low:
            data["engagement"] = value
            break
    for phrase, value in _WORK_MODE.items():
        if phrase in low:
            data["job_type"] = value
            break
    lpa = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lakhs)", low)
    if lpa:
        data["sal_min_annual"] = str(int(float(lpa.group(1)) * 100000))
        data["sal_max_annual"] = str(int(float(lpa.group(2)) * 100000))
    else:
        rupee = re.search(r"(?:₹|rs\.?|inr)?\s*(\d{5,8})\s*(?:to|-)\s*(?:₹|rs\.?|inr)?\s*(\d{5,8})", low)
        if rupee:
            data["sal_min_annual"] = rupee.group(1)
            data["sal_max_annual"] = rupee.group(2)
    years = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*years?", low)
    if years:
        data["exp_min"] = years.group(1)
        data["exp_max"] = years.group(2)
    else:
        one_year = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", low)
        if one_year:
            data["exp_min"] = one_year.group(1)
            data["exp_max"] = one_year.group(1)
    openings = re.search(r"(\d+)\s*(?:vacancies|vacancy|openings|opening|positions)", low)
    if openings:
        data["post_count"] = openings.group(1)
    location = re.search(r"(?:location|located in|based in)\s+([A-Za-z][A-Za-z .,]+)", text, re.I)
    if location:
        place = location.group(1).strip(" .")
        place = re.split(r"\b(salary|full|part|with)\b", place, flags=re.I)[0].strip(" .,")
        if "," in place:
            city, state = [part.strip() for part in place.split(",", 1)]
            data["city"] = city
            data["state"] = state
        elif place:
            data["city"] = place
    skills = re.search(r"(?:skills?|tech stack)\s*(?:are|include|:)?\s+([A-Za-z0-9+#., /]+)", text, re.I)
    if skills:
        data["required_skills"] = [s.strip() for s in re.split(r",| and ", skills.group(1)) if s.strip()]
    return normalize_spoken_job(data)


def _merge_spoken(primary: dict, fallback: dict) -> dict:
    merged = dict(fallback)
    for key, value in primary.items():
        if value is None or value == "" or value == []:
            continue
        merged[key] = value
    return merged


def _voice_prompt(transcript: str) -> str:
    heard = transcript.strip() or "(no browser transcript; use the audio only)"
    return f"""
The speaker may use Hindi, English, Punjabi, or a mix, including Roman script.
Understand what they mean, then create the job in English only.

Decide where each fact belongs:
- title: a clear English job title
- summary: 2–4 English sentences a candidate would read
- responsibilities: English duties, one per line, only if the speaker described the work
- qualifications, skills, salary, location, vacancies, deadline: only from what was said
- dropdowns: pick the closest allowed value, or null if they did not mention it

Do not invent salary, city, or skills that were not spoken.
Do not leave Hindi or Punjabi text in any field. Translate names of roles and duties into English. Keep city and state names in their usual English spelling.

Browser transcript, which may be imperfect:
{heard}

Return ONLY JSON:
{{
  "title": "English job title or null",
  "employment_type": "full_time | part_time | contract | internship | freelance | null",
  "engagement": "permanent | temporary | contractual | consultant | null",
  "exp_min": "number string or null",
  "exp_max": "number string or null",
  "relevant_exp_min": "number string or null",
  "relevant_exp_max": "number string or null",
  "post_count": "number string or null",
  "sal_min_annual": "annual INR number. 4 LPA = 400000",
  "sal_max_annual": "annual INR number or null",
  "city": "English city name or null",
  "state": "English state name or null",
  "country": "English country name or null",
  "job_type": "in_office | wfh | hybrid | null",
  "summary": "English summary or null",
  "responsibilities": "English plain text or null",
  "required_skills": ["English skill"],
  "preferred_skills": ["English skill"],
  "qualifications": "English plain text or null",
  "education": "10th | 12th | diploma | graduate | post graduate | doctorate | any | null",
  "application_deadline": "yyyy-MM-dd or null",
  "interview_process": "walk-in | phone screen | technical round | hr round | technical + hr | ai interview | null",
  "benefits": ["Health Insurance", "Flexible Hours", "Transport", "Food Allowance"],
  "additional_notes": "English plain text or null"
}}
"""


async def parse_spoken_job(transcript: str, audio_base64: str | None = None, audio_mime: str | None = None) -> dict:
    text = re.sub(r"\s+", " ", (transcript or "").strip())
    audio = b""
    if audio_base64:
        import base64
        try:
            audio = base64.b64decode(audio_base64, validate=False)
        except Exception:
            audio = b""
        if len(audio) > 8_000_000:
            raise ValueError("Recording is too long. Describe the job in a shorter take.")
        if len(audio) < 1000:
            audio = b""
    if len(text) < 8 and not audio:
        raise ValueError("Please say a little more about the job.")
    fallback = heuristic_spoken_job(text) if text else {}
    prompt = _voice_prompt(text)
    parsed = None
    try:
        client = get_gemini_client()
        contents: list = [prompt]
        if audio:
            from google.genai import types
            mime = (audio_mime or "audio/webm").split(";")[0] or "audio/webm"
            contents = [
                "The audio may be Hindi, English, Punjabi, or a mix. Write the job in English.",
                types.Part.from_bytes(data=audio, mime_type=mime),
                prompt,
            ]
        response = client.models.generate_content(
            model=settings.GEMINI_CHAT_MODEL,
            contents=contents,
            config={"temperature": 0.2, "response_mime_type": "application/json"},
        )
        parsed = normalize_spoken_job(_loads_json(response.text or ""))
    except Exception as exc:
        print(f"Gemini failed for spoken job parse: {exc}")

    if parsed is None:
        try:
            client = get_openai_client()
            response = await client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": "You extract structured job fields from speech. Return JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            parsed = normalize_spoken_job(_loads_json(response.choices[0].message.content or ""))
        except Exception as exc:
            print(f"OpenAI failed for spoken job parse: {exc}")

    parsed = fallback if parsed is None else _merge_spoken(parsed, fallback)
    if not any(parsed.get(key) for key in ("title", "summary", "city", "required_skills", "sal_min_annual")):
        raise ValueError("Could not pick out job details. Try again with the role, location, and salary.")
    return parsed
