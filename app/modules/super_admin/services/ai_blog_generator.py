import asyncio
import base64
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import get_upload_dir, settings
from app.modules.super_admin.schemas.ai_blog import (
    AIBlogAuthor,
    AIBlogEditRequest,
    AIBlogFAQ,
    AIBlogGenerateRequest,
    AIBlogGenerateResponse,
    AIBlogSection,
)

logger = logging.getLogger(__name__)

DEFAULT_COVER_IMAGE = "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?auto=format&fit=crop&w=1200&q=80"
DEFAULT_AUTHOR_AVATAR = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")[:80]


def _save_blog_image_bytes(image_bytes: bytes, ext: str = ".png") -> str:
    """Save binary image data to uploads/blog_images directory and return public URL."""
    upload_dir = get_upload_dir() / "blog_images"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"blog_ai_{uuid.uuid4().hex}{ext}"
    filepath = upload_dir / filename
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    public_base = settings.BACKEND_PUBLIC_URL.rstrip("/")
    return f"{public_base}/uploads/blog_images/{filename}"


async def generate_blog_image_with_ai(title: str, subtitle: Optional[str] = None, category: Optional[str] = None) -> Optional[str]:
    """Generate a high-quality blog editorial cover image using Gemini Image model / OpenAI DALL-E, saving to local uploads/blog_images."""
    image_prompt = (
        f"A professional, high-resolution editorial photograph for a career and technology publication titled '{title}'. "
        f"Context & Theme: {subtitle or category or 'Professional workplace'}. "
        f"Clean minimalist modern aesthetic, crisp cinematic lighting, 16:9 banner composition, elegant color palette, high fidelity, no cluttered text."
    )

    # 1. Attempt Google Gemini Image Generation via google.generativeai
    if settings.GOOGLE_API_KEY:
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GOOGLE_API_KEY)

            for model_name in ["gemini-2.5-flash-image", "gemini-3.1-flash-image"]:
                try:
                    model = genai.GenerativeModel(model_name)
                    resp = await model.generate_content_async(image_prompt)
                    if resp and resp.candidates and resp.candidates[0].content:
                        for part in resp.candidates[0].content.parts:
                            if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                                mime = getattr(part.inline_data, "mime_type", "image/png")
                                ext = ".png" if "png" in mime else ".jpg"
                                img_bytes = part.inline_data.data
                                saved_url = _save_blog_image_bytes(img_bytes, ext)
                                logger.info("Successfully generated blog image with Gemini (%s): %s", model_name, saved_url)
                                return saved_url
                except Exception as model_err:
                    logger.warning("Gemini model %s generation failed: %s", model_name, model_err)
        except Exception as e:
            logger.warning("Google Gemini image generation failed: %s", e)

    # 2. Attempt OpenAI DALL-E 3 fallback
    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI

            openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            dalle_resp = await openai_client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                size="1024x1024",
                response_format="b64_json",
                n=1,
            )
            if dalle_resp.data and dalle_resp.data[0].b64_json:
                img_bytes = base64.b64decode(dalle_resp.data[0].b64_json)
                saved_url = _save_blog_image_bytes(img_bytes, ".jpg")
                logger.info("Successfully generated blog image with OpenAI DALL-E: %s", saved_url)
                return saved_url
        except Exception as e:
            logger.warning("OpenAI DALL-E image generation failed: %s", e)

    return None


def _normalize_paragraphs(raw_paragraphs: Any) -> List[str]:
    """Clean, split, and normalize paragraphs so that jammed multi-point lists become separate clean paragraphs."""
    if isinstance(raw_paragraphs, str):
        raw_paragraphs = [raw_paragraphs]
    if not isinstance(raw_paragraphs, list):
        return []

    cleaned: List[str] = []
    for para in raw_paragraphs:
        if not para or not isinstance(para, str):
            continue
        p = para.strip()
        if not p:
            continue
        # Split on double newlines
        parts = re.split(r"\n\s*\n", p)
        for part in parts:
            part_str = part.strip()
            if part_str:
                cleaned.append(part_str)
    return cleaned


AI_BLOG_SYSTEM_PROMPT = """You are the Senior Executive Content Architect for 'Rojgar Mela' (India's premier AI career and recruitment portal).
Your mission is to generate comprehensive, publication-ready, deeply practical career and technology articles formatted as strict JSON.

Rules for generated content:
1. Provide in-depth, actionable, real-world substance tailored for the modern job market (tech roadmaps, Indian workplace policies, CTC breakdowns, ATS resume formatting, or behavioral frameworks).
2. "paragraphs": An array of well-written, informative paragraph strings.
   - Write natural, coherent paragraphs with clean formatting.
   - NEVER cram bulleted lists or sub-items onto a single line with hyphens (e.g., do NOT write: "**Heading:** - **Item 1:** text - **Item 2:** text").
   - If explaining multiple components, allowances, rules, or steps, format them as distinct, separate paragraph entries in the "paragraphs" array.
3. Sections must include:
   - "heading": Descriptive title
   - "paragraphs": 2-4 substantive, informative paragraphs
   - "keyTakeaways": 2-4 bullet points
   - "templateSnippet": (Optional but mandatory when appropriate) Must include a realistic, copy-pasteable email format, resignation letter, code snippet, or resume template in "content", along with "title" and "description".
   - "qaList": (Optional but mandatory when appropriate) Interview questions with "question", "answer", "sampleAnswer", and "proTip".
4. Provide 2-4 realistic FAQs at the end.
5. Output MUST be ONLY valid JSON adhering strictly to the JSON schema without Markdown code fences, text before, or text after.

JSON SCHEMA:
{
  "title": "String (engaging, high-converting)",
  "slug": "String (url-friendly-slug)",
  "subtitle": "String (concise 1-sentence value proposition)",
  "excerpt": "String (2-3 sentences summary)",
  "category": "String (e.g., Engineering & Tech Careers, Resume & Cover Letters, Leave Applications & Requests, Salary & Compensation, Communication & Soft Skills, Freshers & Campus Placements, Roles & Responsibilities)",
  "tags": ["Array", "Of", "4-6", "Tags"],
  "readTime": "String (e.g., '6 min read')",
  "sections": [
    {
      "id": "section-slug-id",
      "heading": "Section Heading",
      "paragraphs": ["Paragraph 1...", "Paragraph 2..."],
      "keyTakeaways": ["Key takeaway 1...", "Key takeaway 2..."],
      "templateSnippet": {
        "title": "Template Title",
        "description": "Short explanation",
        "content": "Subject: ...\\n\\nDear [Name],\\n..."
      },
      "qaList": [
        {
          "question": "Sample Question",
          "answer": "Core guidance...",
          "sampleAnswer": "Actual script to say in interview...",
          "proTip": "Golden rule..."
        }
      ]
    }
  ],
  "faqs": [
    {"question": "FAQ Question?", "answer": "Detailed answer..."}
  ]
}
"""


async def generate_blog_with_ai(request: AIBlogGenerateRequest) -> AIBlogGenerateResponse:
    """Generate a structured blog post using the AI subsystem with OpenAI/Gemini and local image generation."""
    user_prompt = f"""Generate a comprehensive career blog post for the following topic:

TOPIC / PROMPT: {request.prompt}
TARGET CATEGORY: {request.category or 'Auto-detect best category'}
DESIRED TONE: {request.tone or 'professional'}
INCLUDE READY-TO-COPY TEMPLATES: {'Yes' if request.include_templates else 'No'}
INCLUDE INTERVIEW Q&A: {'Yes' if request.include_qa else 'No'}

Ensure realistic depth, practical examples, clear formatting, and strict JSON compliance."""

    raw_json_str = ""

    # 1. Attempt OpenAI if key is present
    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL or "gpt-4o",
                messages=[
                    {"role": "system", "content": AI_BLOG_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            raw_json_str = response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("OpenAI Blog generation failed, trying Gemini / fallback: %s", e)

    # 2. Attempt Google Gemini if OpenAI was not available or failed
    if not raw_json_str and settings.GOOGLE_API_KEY:
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_CHAT_MODEL or "gemini-1.5-flash",
                system_instruction=AI_BLOG_SYSTEM_PROMPT,
            )
            resp = await model.generate_content_async(
                user_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
            )
            raw_json_str = resp.text or ""
        except Exception as e:
            logger.warning("Gemini Blog generation failed, using intelligent deterministic fallback: %s", e)

    # 3. Parse JSON response or fallback to dynamic rich template generator
    parsed: Dict[str, Any] = {}
    if raw_json_str:
        try:
            cleaned = raw_json_str.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned.strip())
        except Exception as e:
            logger.error("JSON parsing error on AI output: %s", e)

    # If parsing failed or no AI keys configured, create a high-fidelity dynamic fallback
    if not parsed or not parsed.get("title") or not parsed.get("sections"):
        clean_topic = request.prompt.strip()
        detected_category = request.category or "Career Advice & Development"
        safe_slug = slugify(clean_topic)

        parsed = {
            "title": f"Mastering {clean_topic.title()}: The Definitive Guide for 2026",
            "slug": safe_slug or "mastering-career-growth",
            "subtitle": f"Proven strategies, practical blueprints, and expert frameworks to excel in {clean_topic}.",
            "excerpt": f"Everything you need to know about {clean_topic}, including step-by-step methodologies, common pitfalls, and real-world templates.",
            "category": detected_category,
            "tags": [clean_topic.split()[0] if clean_topic else "Career", "Strategy", "JobPrep", "Growth"],
            "readTime": "6 min read",
            "sections": [
                {
                    "id": "strategic-overview",
                    "heading": f"Why {clean_topic.title()} is Critical in Today's Market",
                    "paragraphs": [
                        f"In today's fast-moving hiring and workplace landscape, understanding {clean_topic} gives candidates and working professionals a clear strategic advantage.",
                        "Recruiters and hiring managers consistently prioritize individuals who can demonstrate measurable outcomes, clear communication, and structured problem-solving.",
                    ],
                    "keyTakeaways": [
                        "Prioritize high-impact foundational principles before diving into advanced nuances.",
                        "Align your work with measurable business outcomes and team velocity.",
                    ],
                    "templateSnippet": {
                        "title": f"Ready-to-Use {clean_topic.title()} Framework",
                        "description": "Standard structure you can immediately adapt.",
                        "content": f"[Subject: {clean_topic.title()} - Action Plan]\n\nDear Team / Hiring Manager,\n\nI am outlining the key milestones for {clean_topic} below:\n1. Assessment & Discovery\n2. Implementation & Optimization\n3. Verification & Follow-up\n\nBest regards,\n[Your Name]",
                    }
                    if request.include_templates
                    else None,
                },
                {
                    "id": "step-by-step-execution",
                    "heading": "Step-by-Step Execution Playbook",
                    "paragraphs": [
                        "Step 1: Conduct a thorough self-audit of your current skills and past projects.",
                        "Step 2: Tailor your communication using quantifiable metrics (e.g., reduced latency by 30%, increased revenue by 18%).",
                    ],
                    "keyTakeaways": [
                        "Always validate assumptions with real data.",
                        "Iterate weekly based on feedback from mentors and peers.",
                    ],
                    "qaList": [
                        {
                            "question": f"What is the most common mistake made in {clean_topic}?",
                            "answer": "Focusing on surface-level tactics without mastering fundamental principles.",
                            "sampleAnswer": f"In my past roles, I addressed {clean_topic} by first standardizing the core workflows and measuring baseline performance.",
                            "proTip": "Always cite specific metrics and frameworks.",
                        }
                    ]
                    if request.include_qa
                    else None,
                },
            ],
            "faqs": [
                {
                    "question": f"How long does it take to see results with {clean_topic}?",
                    "answer": "Consistent application over 4 to 8 weeks typically yields substantial progress and recognition.",
                },
                {
                    "question": "Can beginners apply these strategies immediately?",
                    "answer": "Yes, start with the core templates and iterate as your familiarity grows.",
                },
            ],
        }

    # 4. Generate AI Blog Cover Image and persist to uploads/blog_images
    gen_title = parsed.get("title", request.prompt.title())
    gen_subtitle = parsed.get("subtitle")
    gen_category = parsed.get("category") or request.category or "Career Advice"

    generated_cover_image = await generate_blog_image_with_ai(
        title=gen_title,
        subtitle=gen_subtitle,
        category=gen_category,
    )
    cover_image_url = generated_cover_image or parsed.get("coverImage") or DEFAULT_COVER_IMAGE

    # Author is always "Rojgar Mela Content Team"
    author_info = AIBlogAuthor(
        name="Rojgar Mela Content Team",
        role="Career Research & Editorial Advisory",
        avatar=DEFAULT_AUTHOR_AVATAR,
        bio="The official Rojgar Mela Content Team delivers curated career guidance, interview frameworks, ATS templates, and industry compensation insights.",
    )

    # Construct validated Pydantic model
    return AIBlogGenerateResponse(
        title=gen_title,
        slug=slugify(parsed.get("slug") or gen_title or request.prompt),
        subtitle=gen_subtitle,
        excerpt=parsed.get("excerpt", f"In-depth guide and strategies for {request.prompt}."),
        category=gen_category,
        tags=parsed.get("tags") or ["CareerGrowth", "JobPrep", "TechCareers"],
        readTime=parsed.get("readTime", "6 min read"),
        coverImage=cover_image_url,
        author=author_info,
        sections=[
            AIBlogSection(
                id=sec.get("id") or f"section-{idx}",
                heading=sec.get("heading", f"Key Insights {idx+1}"),
                paragraphs=_normalize_paragraphs(sec.get("paragraphs") or []),
                keyTakeaways=sec.get("keyTakeaways"),
                templateSnippet=sec.get("templateSnippet"),
                qaList=sec.get("qaList"),
                tableData=sec.get("tableData"),
            )
            for idx, sec in enumerate(parsed.get("sections", []))
        ],
        faqs=[
            AIBlogFAQ(
                question=f.get("question", "Frequently Asked Question"),
                answer=f.get("answer", "Answer details."),
            )
            for f in parsed.get("faqs", [])
        ],
    )


AI_BLOG_EDIT_SYSTEM_PROMPT = """You are the Senior Executive Content Editor & Copilot for 'Rojgar Mela' (India's premier AI career and recruitment portal).
Your mission is to modify, enhance, expand, or polish an EXISTING career/technology blog post according to explicit editorial instructions.

Guidelines:
1. ONLY apply the requested changes or additions. Preserve all existing high-quality sections, factual content, templates, and FAQs that the editor did not ask to modify.
2. If asked to add a new section, create a well-crafted, structured section and place it logically among the existing sections without deleting good existing sections.
3. If asked to rewrite or polish a specific section or tone, update that section cleanly while keeping its core points intact.
4. If asked to add FAQs or templates, append them to the existing list or create them as instructed.
5. "paragraphs": An array of well-written, informative paragraph strings. NEVER cram bullet points onto a single line with hyphens.
6. Output MUST be ONLY valid JSON adhering strictly to the JSON schema without Markdown code fences, text before, or text after.

JSON SCHEMA:
{
  "title": "String",
  "slug": "String",
  "subtitle": "String",
  "excerpt": "String",
  "category": "String",
  "tags": ["Array", "Of", "Tags"],
  "readTime": "String",
  "sections": [
    {
      "id": "section-slug-id",
      "heading": "Section Heading",
      "paragraphs": ["Paragraph 1...", "Paragraph 2..."],
      "keyTakeaways": ["Key takeaway 1...", "Key takeaway 2..."],
      "templateSnippet": {
        "title": "Template Title",
        "description": "Short explanation",
        "content": "Subject: ...\\n\\nDear [Name],\\n..."
      },
      "qaList": [
        {
          "question": "Sample Question",
          "answer": "Core guidance...",
          "sampleAnswer": "Actual script to say in interview...",
          "proTip": "Golden rule..."
        }
      ]
    }
  ],
  "faqs": [
    {"question": "FAQ Question?", "answer": "Detailed answer..."}
  ]
}
"""


async def edit_blog_with_ai(request: AIBlogEditRequest) -> AIBlogGenerateResponse:
    """Edit, enhance, or expand an existing blog post using AI while preserving existing assets."""
    current_data = request.current_blog or {}

    user_prompt = f"""EDITORIAL CHANGE REQUEST:
{request.instruction}

TARGET SCOPE: {request.target_scope or 'auto'}

CURRENT BLOG POST DATA:
{json.dumps(current_data, indent=2)}

Apply the requested changes and output the complete updated article adhering to the JSON schema."""

    raw_json_str = ""

    # 1. Attempt OpenAI if key is present
    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL or "gpt-4o",
                messages=[
                    {"role": "system", "content": AI_BLOG_EDIT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            raw_json_str = response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("OpenAI Blog edit failed, trying Gemini / fallback: %s", e)

    # 2. Attempt Google Gemini if OpenAI was not available or failed
    if not raw_json_str and settings.GOOGLE_API_KEY:
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_CHAT_MODEL or "gemini-1.5-flash",
                system_instruction=AI_BLOG_EDIT_SYSTEM_PROMPT,
            )
            resp = await model.generate_content_async(
                user_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
            )
            raw_json_str = resp.text or ""
        except Exception as e:
            logger.warning("Gemini Blog edit failed, using deterministic fallback: %s", e)

    # 3. Parse JSON response or fallback to current data
    parsed: Dict[str, Any] = {}
    if raw_json_str:
        try:
            cleaned = raw_json_str.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned.strip())
        except Exception as e:
            logger.error("JSON parsing error on AI edit output: %s", e)

    # Fallback to current blog if parsing failed
    if not parsed or not parsed.get("title") or not parsed.get("sections"):
        parsed = dict(current_data)
        existing_sections = list(parsed.get("sections", []))
        existing_sections.append({
            "id": f"enhanced-section-{len(existing_sections) + 1}",
            "heading": f"Updated Guidance: {request.instruction[:40]}...",
            "paragraphs": [
                f"Regarding recent enhancements: {request.instruction}.",
                "Continuous alignment with current industry and recruitment benchmarks is recommended."
            ],
            "keyTakeaways": ["Review practical takeaways regularly.", "Adapt strategies based on team velocity."]
        })
        parsed["sections"] = existing_sections

    # Retain cover image and author from current blog post
    existing_cover = current_data.get("coverImage") or current_data.get("cover_image") or DEFAULT_COVER_IMAGE
    existing_author_name = (
        current_data.get("author", {}).get("name")
        if isinstance(current_data.get("author"), dict)
        else current_data.get("author_name") or "Rojgar Mela Content Team"
    )
    existing_author_role = (
        current_data.get("author", {}).get("role")
        if isinstance(current_data.get("author"), dict)
        else current_data.get("author_role") or "Career Research & Editorial Advisory"
    )
    existing_author_avatar = (
        current_data.get("author", {}).get("avatar")
        if isinstance(current_data.get("author"), dict)
        else current_data.get("author_avatar") or DEFAULT_AUTHOR_AVATAR
    )
    existing_author_bio = (
        current_data.get("author", {}).get("bio")
        if isinstance(current_data.get("author"), dict)
        else current_data.get("author_bio") or "Official Rojgar Mela Content Team"
    )

    return AIBlogGenerateResponse(
        title=parsed.get("title") or current_data.get("title", "Untitled Article"),
        slug=slugify(parsed.get("slug") or current_data.get("slug") or parsed.get("title", "untitled")),
        subtitle=parsed.get("subtitle") or current_data.get("subtitle"),
        excerpt=parsed.get("excerpt") or current_data.get("excerpt", "Article summary."),
        category=parsed.get("category") or current_data.get("category", "Career Advice"),
        tags=parsed.get("tags") or current_data.get("tags") or ["CareerGrowth", "JobPrep"],
        readTime=parsed.get("readTime") or current_data.get("readTime") or current_data.get("read_time") or "6 min read",
        coverImage=existing_cover,
        author=AIBlogAuthor(
            name=existing_author_name,
            role=existing_author_role,
            avatar=existing_author_avatar,
            bio=existing_author_bio,
        ),
        sections=[
            AIBlogSection(
                id=sec.get("id") or f"section-{idx}",
                heading=sec.get("heading", f"Key Insights {idx+1}"),
                paragraphs=_normalize_paragraphs(sec.get("paragraphs") or []),
                keyTakeaways=sec.get("keyTakeaways"),
                templateSnippet=sec.get("templateSnippet"),
                qaList=sec.get("qaList"),
                tableData=sec.get("tableData"),
            )
            for idx, sec in enumerate(parsed.get("sections", []))
        ],
        faqs=[
            AIBlogFAQ(
                question=f.get("question", "Frequently Asked Question"),
                answer=f.get("answer", "Answer details."),
            )
            for f in parsed.get("faqs", [])
        ],
    )

