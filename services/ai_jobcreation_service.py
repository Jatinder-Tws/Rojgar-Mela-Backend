import json
from typing import List, Optional
from config import settings
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
