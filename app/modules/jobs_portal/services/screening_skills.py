"""Skill alias normalization for AI resume screening (deterministic, no LLM)."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Set, Tuple

# Canonical skill -> aliases (lowercase)
SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python", "python3", "py"),
    "JavaScript": ("javascript", "js", "ecmascript"),
    "TypeScript": ("typescript", "ts"),
    "React": ("react", "react.js", "reactjs"),
    "Node.js": ("node", "nodejs", "node.js"),
    "Java": ("java", "jdk", "jre"),
    "C#": ("c#", "csharp", "c sharp"),
    "C++": ("c++", "cpp", "cplusplus"),
    "SQL": ("sql", "structured query language"),
    "PostgreSQL": ("postgresql", "postgres", "psql"),
    "MySQL": ("mysql"),
    "MongoDB": ("mongodb", "mongo"),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "Docker": ("docker", "containers"),
    "Kubernetes": ("kubernetes", "k8s"),
    "Git": ("git", "github", "gitlab"),
    "Django": ("django"),
    "Flask": ("flask"),
    "FastAPI": ("fastapi", "fast api"),
    "Next.js": ("next", "nextjs", "next.js"),
    "Angular": ("angular", "angularjs"),
    "Vue.js": ("vue", "vuejs", "vue.js"),
    "HTML": ("html", "html5"),
    "CSS": ("css", "css3"),
    "Tailwind CSS": ("tailwind", "tailwindcss", "tailwind css"),
    "Machine Learning": ("machine learning", "ml"),
    "Deep Learning": ("deep learning", "dl"),
    "NLP": ("nlp", "natural language processing"),
    "Excel": ("excel", "ms excel", "microsoft excel"),
    "Power BI": ("power bi", "powerbi"),
    "Tableau": ("tableau"),
    "Salesforce": ("salesforce", "sfdc"),
    "REST API": ("rest", "rest api", "restful"),
    "GraphQL": ("graphql"),
    "Linux": ("linux", "ubuntu", "centos"),
    "Agile": ("agile", "scrum"),
}

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in SKILL_ALIASES.items():
    _ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for a in aliases:
        _ALIAS_TO_CANONICAL[a.lower()] = canonical


def _norm_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def normalize_skill(name: str) -> str:
    key = _norm_key(name)
    if not key:
        return ""
    return _ALIAS_TO_CANONICAL.get(key, name.strip())


def normalize_skills(skills: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for raw in skills or []:
        if not isinstance(raw, str):
            continue
        n = normalize_skill(raw)
        if not n:
            continue
        key = n.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def skill_present_in_text(skill: str, text: str) -> bool:
    """Word-boundary aware skill presence check to reduce false positives."""
    if not skill or not text:
        return False
    aliases = {_norm_key(skill)}
    canon = normalize_skill(skill)
    aliases.add(_norm_key(canon))
    for a in SKILL_ALIASES.get(canon, ()):
        aliases.add(_norm_key(a))
    hay = text.lower()
    for alias in aliases:
        if not alias:
            continue
        # Escape and allow flexible separators for multi-word skills
        parts = [re.escape(p) for p in alias.split() if p]
        if not parts:
            continue
        pattern = r"(?<!\w)" + r"[\s\-_/]*".join(parts) + r"(?!\w)"
        if re.search(pattern, hay, flags=re.IGNORECASE):
            return True
    return False


def match_skills(
    required: Iterable[str],
    preferred: Iterable[str],
    candidate_skills: Iterable[str],
    evidence_text: str = "",
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Returns (matched_required, partial_required, missing_required, matched_preferred).
    Partial = found in evidence text but not in explicit skills list.
    """
    cand_norm = {s.lower(): s for s in normalize_skills(candidate_skills)}
    matched_req: List[str] = []
    partial_req: List[str] = []
    missing_req: List[str] = []
    for raw in required or []:
        n = normalize_skill(raw)
        if not n:
            continue
        if n.lower() in cand_norm:
            matched_req.append(n)
        elif skill_present_in_text(n, evidence_text):
            partial_req.append(n)
        else:
            missing_req.append(n)

    matched_pref: List[str] = []
    for raw in preferred or []:
        n = normalize_skill(raw)
        if not n:
            continue
        if n.lower() in cand_norm or skill_present_in_text(n, evidence_text):
            matched_pref.append(n)
    return matched_req, partial_req, missing_req, matched_pref


def parse_experience_years(value: Optional[object]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None
