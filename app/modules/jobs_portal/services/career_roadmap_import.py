"""Parse scraped or CMS roadmap JSON into CareerRoadmapCreate payloads."""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import urlparse

from app.modules.jobs_portal.schemas.career_roadmap import (
    CareerInsightsIn,
    CareerRoadmapCreate,
    RoadmapFaqIn,
    RoadmapStepIn,
    RoadmapSubStepIn,
)


def slugify(text: str) -> str:
    text = (text or "").lower().strip().lstrip("/")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-") or "roadmap"

IMPORT_LIMIT = 200
IMPORT_MAX_BYTES = 8 * 1024 * 1024

CATEGORY_MAP = {
    "software development": "Software Engineering",
    "software engineering": "Software Engineering",
    "data & analytics": "AI & Data",
    "data and analytics": "AI & Data",
    "data & ai": "AI & Data",
    "ai & data": "AI & Data",
    "ai, ml & data": "AI & Data",
}

SKIP_STEP_TITLES = {
    "learning",
    "connect",
    "career overview",
    "skills you'll master",
    "skills you’ll master",
    "learning path",
    "career insights",
    "frequently asked questions",
    "explore",
    "assessment",
    "growth & tracking",
    "updates",
    "community",
}

NAV_NOISE = (
    "home explore",
    "all courses",
    "browse 200+",
    "ctrl+k",
    "login",
    "skillexus",
    "help center",
)

FAQ_SPLIT_RE = re.compile(
    r"(Do I need|How much time|Is a PhD|Should I learn|Can I|What is|When should)\b",
    re.I,
)
OVERVIEW_RE = re.compile(
    r"Duration\s+(.+?)\s+Salary\s+(.+?)\s+Growth\s+(.+?)\s+Openings\s+(.+?)(?:\s+Difficulty Level\s+(.+))?$",
    re.I,
)
PHASE_META_RE = re.compile(
    r"(\d+(?:\s*-\s*\d+)?)\s*(months?|weeks?).*(?:•|\*)\s*(\d+)\s*steps?",
    re.I,
)
NUMBERED_STEP_RE = re.compile(r"^\d+\.\s+")
PLUS_COUNT_RE = re.compile(r"^\+\d+$")
SKILL_PAIR_SECONDS = {
    "learning",
    "visualization",
    "science",
    "analytics",
    "development",
    "engineering",
    "testing",
    "design",
    "security",
    "ops",
}
PATH_RE = re.compile(
    r"((?:[A-Z][A-Za-z+#./]*)(?:\s+[A-Z][A-Za-z+#./]*)*?)\s+"
    r"(Developer|Engineer|Analyst|Scientist|Researcher|Designer|Architect|Manager)",
)
IN_DEMAND_SKILL_RE = re.compile(
    r"Python|JavaScript|TypeScript|Node\.js|React|AWS|Docker|SQL|TensorFlow|PyTorch|"
    r"Machine Learning|Deep Learning|Statistics|Kubernetes|Java|Go|Git",
    re.I,
)


def decode_import_payload(raw: bytes) -> Any:
    """Accept a JSON array, a single object, concatenated objects, or a missing outer []."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("File must be valid UTF-8 JSON") from exc
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    if not text:
        raise ValueError("Empty file")

    for candidate in (text, f"[{text.rstrip().rstrip(',')}]"):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    decoder = json.JSONDecoder()
    docs: list[Any] = []
    idx = 0
    length = len(text)
    while idx < length:
        while idx < length and text[idx] in " \t\r\n,":
            idx += 1
        if idx >= length:
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            break
        docs.append(obj)
        idx = end
    if docs:
        return docs if len(docs) > 1 else docs[0]
    raise ValueError("File must be valid UTF-8 JSON")


def extract_import_items(payload: Any) -> list[dict]:
    if payload is None:
        return []
    if isinstance(payload, list):
        items: list[dict] = []
        for item in payload:
            if isinstance(item, dict):
                items.append(item)
            elif isinstance(item, list):
                items.extend(extract_import_items(item))
        return items
    if not isinstance(payload, dict):
        return []
    for key in ("items", "roadmaps", "data", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return extract_import_items(value)
    if payload.get("title") or payload.get("detail_title") or payload.get("slug"):
        return [payload]
    return []


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _looks_like_cms(item: dict) -> bool:
    steps = item.get("steps")
    if not isinstance(steps, list) or not steps:
        return bool(item.get("slug") and item.get("skill_tags") and "category" in item)
    first = steps[0]
    return isinstance(first, dict) and ("sub_steps" in first or "content" in first or "title" in first) and "details" not in first


def _map_category(raw: str) -> str:
    text = _clean_text(raw)
    if not text:
        return "Technology"
    return CATEGORY_MAP.get(text.lower(), text)


def _slug_from_item(item: dict, title: str) -> str:
    url = _clean_text(item.get("url") or item.get("source_url"))
    if url:
        path = urlparse(url).path.rstrip("/").split("/")[-1]
        if path:
            return slugify(path)
    return slugify(_clean_text(item.get("slug") or title))


def _section_map(item: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for section in item.get("sections") or []:
        if not isinstance(section, dict):
            continue
        heading = _clean_text(section.get("heading")).lower()
        content = _clean_text(section.get("content"))
        if heading:
            out[heading] = content
    return out


def _stats_map(item: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in item.get("stats") or []:
        if not isinstance(row, dict):
            continue
        label = _clean_text(row.get("label")).lower()
        val = _clean_text(row.get("val") or row.get("value"))
        if label and val:
            out[label] = val
    return out


def _parse_overview(text: str) -> dict[str, str]:
    match = OVERVIEW_RE.search(_clean_text(text))
    if not match:
        return {}
    duration, salary, growth, openings, level = match.groups()
    return {
        "duration": _clean_text(duration),
        "salary": _clean_text(salary),
        "growth": _clean_text(growth),
        "openings": _clean_text(openings).replace(",", ""),
        "level": _clean_text(level),
    }


def _skills_from_item(item: dict, sections: dict[str, str]) -> list[str]:
    tags: list[str] = []
    for raw in item.get("skills") or item.get("skill_tags") or []:
        text = _clean_text(raw)
        if text and not PLUS_COUNT_RE.match(text):
            tags.append(text)
    blob = sections.get("skills you'll master") or sections.get("skills you’ll master") or ""
    blob = re.split(r"Learning Path", blob, maxsplit=1, flags=re.I)[0]
    blob = re.sub(r"^Skills You'll Master\s*", "", blob, flags=re.I)
    extra_text = blob
    for tag in sorted(tags, key=len, reverse=True):
        extra_text = re.sub(rf"\b{re.escape(tag)}\b", " ", extra_text, flags=re.I)
    tokens = [part for part in extra_text.split() if part and not PLUS_COUNT_RE.match(part) and not part.isdigit()]
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and tokens[i + 1].lower() in SKILL_PAIR_SECONDS:
            extra = f"{tokens[i]} {tokens[i + 1]}"
            i += 2
        else:
            extra = tokens[i]
            i += 1
        if extra.lower() not in {t.lower() for t in tags} and extra.lower() not in SKIP_STEP_TITLES:
            tags.append(extra)
    seen: set[str] = set()
    unique: list[str] = []
    for tag in tags:
        key = tag.lower()
        if key in seen or key in SKIP_STEP_TITLES or re.fullmatch(r"\d+", tag):
            continue
        seen.add(key)
        unique.append(tag)
    return unique[:24]


def _parse_insights(text: str) -> CareerInsightsIn:
    blob = _clean_text(text)
    companies: list[str] = []
    skills: list[str] = []
    paths: list[str] = []
    company_match = re.search(
        r"Top Hiring Companies\s+(.+?)(?:Most In-Demand Skills|Related Career Paths|$)",
        blob,
        re.I,
    )
    skill_match = re.search(
        r"Most In-Demand Skills\s+(.+?)(?:Related Career Paths|$)",
        blob,
        re.I,
    )
    path_match = re.search(r"Related Career Paths\s+(.+)$", blob, re.I)
    if company_match:
        companies = company_match.group(1).split()
    if skill_match:
        skills = [m.group(0) for m in IN_DEMAND_SKILL_RE.finditer(skill_match.group(1))]
        if not skills:
            skills = re.findall(r"[A-Za-z][A-Za-z+#.]{1,}", skill_match.group(1))
    if path_match:
        paths = [" ".join(part).strip() for part in PATH_RE.findall(path_match.group(1))]
        paths = [_clean_text(p) for p in paths if _clean_text(p)]
    return CareerInsightsIn(
        top_hiring_companies=companies[:12],
        in_demand_skills=skills[:12],
        related_career_paths=paths[:8],
    )


def _parse_faqs(text: str) -> list[RoadmapFaqIn]:
    blob = _clean_text(text)
    blob = re.sub(r"^Frequently Asked Questions\s*", "", blob, flags=re.I)
    blob = re.sub(r"Ready to Start Your Journey\?.*$", "", blob, flags=re.I)
    if not blob:
        return []
    parts = FAQ_SPLIT_RE.split(blob)
    faqs: list[RoadmapFaqIn] = []
    if len(parts) <= 1:
        return faqs
    # split keeps delimiters: [prefix, delim, rest, delim, rest, ...]
    i = 1
    while i + 1 < len(parts):
        question_start = parts[i].strip()
        rest = parts[i + 1].strip()
        q_end = rest.find("?")
        if q_end >= 0:
            question = f"{question_start} {rest[: q_end + 1]}".strip()
            answer = rest[q_end + 1 :].strip()
        else:
            question = f"{question_start}?".strip()
            answer = rest
        # Trim next question bleed
        next_q = FAQ_SPLIT_RE.search(answer)
        if next_q and next_q.start() > 12:
            answer = answer[: next_q.start()].strip()
        if question and answer:
            faqs.append(RoadmapFaqIn(question=question, answer=answer))
        i += 2
    return faqs[:12]


def _parse_learning_path(item: dict) -> list[RoadmapStepIn]:
    phases: list[RoadmapStepIn] = []
    current: Optional[RoadmapStepIn] = None
    for raw in item.get("steps") or []:
        if not isinstance(raw, dict):
            continue
        title = _clean_text(raw.get("step") or raw.get("title"))
        details = _clean_text(raw.get("details") or raw.get("subtitle") or raw.get("content"))
        if not title or any(noise in f"{title} {details}".lower() for noise in NAV_NOISE):
            continue
        if title.lower() in SKIP_STEP_TITLES:
            continue
        if NUMBERED_STEP_RE.match(title):
            if current is None:
                continue
            clean_title = NUMBERED_STEP_RE.sub("", title).strip()
            if any(sub.title.lower() == clean_title.lower() for sub in current.sub_steps):
                continue
            current.sub_steps.append(
                RoadmapSubStepIn(title=clean_title, subtitle=details, skill_tags=[])
            )
            current.lessons_count = len(current.sub_steps)
            continue
        meta = PHASE_META_RE.search(details)
        duration = None
        if meta:
            duration = f"{meta.group(1).replace(' ', '')} {meta.group(2)}"
        elif re.search(r"\d+\s*-\s*\d+\s*(months?|weeks?)", details, re.I):
            duration = details.split("•")[0].strip()
        else:
            continue
        if current and current.title.lower() == title.lower():
            continue
        current = RoadmapStepIn(title=title, content="", duration=duration, sub_steps=[])
        phases.append(current)
    return phases


def _step_blob(item: dict, title_match: str) -> str:
    needle = title_match.lower()
    for raw in item.get("steps") or []:
        if not isinstance(raw, dict):
            continue
        title = _clean_text(raw.get("step") or raw.get("title")).lower()
        if needle in title:
            return _clean_text(raw.get("details") or raw.get("content"))
    return ""


def _insights_from_item(item: dict, sections: dict[str, str]) -> CareerInsightsIn:
    candidates = [
        sections.get("career insights", ""),
        _step_blob(item, "career insight"),
        _clean_text(item.get("full_content")),
    ]
    for blob in candidates:
        parsed = _parse_insights(blob)
        if parsed.top_hiring_companies or parsed.in_demand_skills or parsed.related_career_paths:
            return parsed
    return CareerInsightsIn()


def _faqs_from_item(item: dict, sections: dict[str, str]) -> list[RoadmapFaqIn]:
    candidates = [
        sections.get("frequently asked questions", ""),
        sections.get("do i need a computer science degree?", ""),
        sections.get("is a phd required for data science?", ""),
        _step_blob(item, "frequently asked"),
        _clean_text(item.get("full_content")),
    ]
    for blob in candidates:
        faqs = _parse_faqs(blob)
        if faqs:
            return faqs
    return []


def _duration_from_stats(stats: dict[str, str], overview: dict[str, str]) -> Optional[str]:
    if overview.get("duration"):
        return overview["duration"]
    raw = stats.get("duration")
    if not raw:
        return None
    if re.search(r"month|week|year", raw, re.I):
        return raw
    return f"{raw} months"


def parse_scraped_item(item: dict, sort_order: int = 0) -> CareerRoadmapCreate:
    sections = _section_map(item)
    stats = _stats_map(item)
    overview = _parse_overview(sections.get("career overview", "")) or _parse_overview(
        _clean_text(item.get("full_content"))
    )
    title = _clean_text(item.get("detail_title") or item.get("title")) or "Untitled roadmap"
    skills = _skills_from_item(item, sections)
    insights = _insights_from_item(item, sections)
    faqs = _faqs_from_item(item, sections)
    steps = _parse_learning_path(item)
    salary = overview.get("salary") or stats.get("salary")
    if salary and re.search(r"₹0\s*k", salary, re.I):
        salary = overview.get("salary") if overview.get("salary") and not re.search(r"₹0\s*k", overview["salary"], re.I) else None
    growth = overview.get("growth") or stats.get("growth")
    openings = overview.get("openings") or stats.get("openings")
    level = overview.get("level") or _clean_text(item.get("level")) or "Intermediate"
    return CareerRoadmapCreate(
        title=title,
        slug=_slug_from_item(item, title),
        category=_map_category(item.get("category") or ""),
        level=level,
        industries=[],
        short_description=_clean_text(item.get("card_summary") or item.get("short_description")) or None,
        long_description=_clean_text(item.get("subtitle") or item.get("long_description")) or None,
        skill_tags=skills,
        duration_months=_duration_from_stats(stats, overview),
        salary_lpa=salary,
        growth_percent=growth,
        openings_count=openings,
        steps=steps,
        resources=[],
        career_insights=insights,
        faqs=faqs,
        is_published=True,
        is_featured=bool(item.get("featured") or item.get("is_featured")),
        is_trending=bool(item.get("trending") or item.get("is_trending")),
        sort_order=int(item.get("index") or item.get("sort_order") or sort_order or 0),
        video_link=_clean_text(item.get("video_link") or item.get("videoLink") or item.get("video_url")) or None,
    )


def parse_cms_item(item: dict, sort_order: int = 0) -> CareerRoadmapCreate:
    data = dict(item)
    data.setdefault("sort_order", sort_order)
    data.setdefault("is_published", True)
    data["category"] = _map_category(data.get("category") or "")
    if not data.get("slug"):
        data["slug"] = _slug_from_item(item, _clean_text(item.get("title")))
    return CareerRoadmapCreate.model_validate(data)


def to_create_payload(item: dict, sort_order: int = 0) -> CareerRoadmapCreate:
    if _looks_like_cms(item) and item.get("title"):
        try:
            return parse_cms_item(item, sort_order)
        except Exception:
            return parse_scraped_item(item, sort_order)
    return parse_scraped_item(item, sort_order)
