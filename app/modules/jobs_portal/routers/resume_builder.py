"""
Resume Builder router – generate a professional resume from portfolio data.
"""
import os
import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Any

from app.core.database import get_db
from app.shared.models.user import User
from app.modules.jobs_portal.models.resume import Resume
from app.modules.jobs_portal.models.portfolio import Portfolio
from app.core.dependencies import require_seeker
# ── Resume generation uses Gemini exclusively ──
# OpenAI adapter is not used for resume building
import google.genai as google_genai
from app.core.config import settings

router = APIRouter(prefix="/resume-builder", tags=["resume-builder"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ResumeBuilderRequest(BaseModel):
    template: str = "modern"  # modern, classic, minimal, creative, executive
    summary_override: Optional[str] = None
    include_projects: bool = True
    include_certifications: bool = True
    portfolio_data: Optional[dict] = None


class AIAssistRequest(BaseModel):
    section: str  # summary, headline, experience, skills, projects, education, certifications, languages
    action: Optional[str] = "generate"  # generate, enhance, shorten, ats_optimize, suggest_skills
    current_text: Optional[str] = None
    custom_instruction: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    skills: Optional[List[str]] = None
    context: Optional[dict] = None


class AIAssistResponse(BaseModel):
    section: str
    suggested_text: Optional[str] = None
    suggested_skills: Optional[List[str]] = None
    structured_data: Optional[Any] = None
    message: str = "Success"


class PortfolioDataWrapper:
    """Wraps either a DB Portfolio model, a dict, or merged data."""
    def __init__(self, portfolio_obj=None, override_dict=None):
        self._obj = portfolio_obj
        self._dict = override_dict or {}

    def _get(self, key, default=None):
        if key in self._dict and self._dict[key] is not None:
            return self._dict[key]
        if self._obj is not None:
            return getattr(self._obj, key, default)
        return default

    @property
    def city(self): return self._get("city")
    @property
    def state(self): return self._get("state")
    @property
    def linkedin_url(self): return self._get("linkedin_url")
    @property
    def github_url(self): return self._get("github_url")
    @property
    def headline(self): return self._get("headline")
    @property
    def bio(self): return self._get("bio")
    @property
    def skills(self): return self._get("skills", [])
    @property
    def work_experiences(self): return self._get("work_experiences", [])
    @property
    def education(self): return self._get("education", [])
    @property
    def certifications(self): return self._get("certifications", [])
    @property
    def projects(self): return self._get("projects", [])
    @property
    def languages(self): return self._get("languages", [])


class UserDataWrapper:
    """Wraps user fields so user edits can also override user header."""
    def __init__(self, user_obj=None, override_dict=None):
        self._obj = user_obj
        self._dict = override_dict or {}

    def _get(self, key, default=""):
        if key in self._dict and self._dict[key] is not None:
            return self._dict[key]
        if self._obj is not None:
            return getattr(self._obj, key, default)
        return default

    @property
    def first_name(self): return self._get("first_name")
    @property
    def last_name(self): return self._get("last_name")
    @property
    def email(self): return self._get("email")
    @property
    def phone(self): return self._get("phone")


def _resolve_data(user: User, portfolio_from_db: Optional[Portfolio], override_data: Optional[dict]):
    if override_data:
        p_wrap = PortfolioDataWrapper(portfolio_from_db, override_data)
        user_dict = override_data.get("user") or override_data
        u_wrap = UserDataWrapper(user, user_dict)
        return u_wrap, p_wrap
    return user, portfolio_from_db


class ResumeSection(BaseModel):
    name: str
    content: str


def _format_date_str(date_str: Optional[str]) -> str:
    """Helper to format YYYY-MM or YYYY-MM-DD to 'MMM YYYY'. Defaults to 'Present' if empty."""
    if not date_str or str(date_str).lower() == "present":
        return "Present"
    try:
        from datetime import datetime
        d_str = str(date_str).strip()
        # YYYY-MM
        if len(d_str) == 7 and d_str[4] == '-':
            dt = datetime.strptime(d_str, "%Y-%m")
            return dt.strftime("%b %Y")
        # YYYY-MM-DD
        if len(d_str) >= 10 and d_str[4] == '-' and d_str[7] == '-':
            dt = datetime.strptime(d_str[:10], "%Y-%m-%d")
            return dt.strftime("%b %Y")
        return d_str
    except Exception:
        return str(date_str)


def _portfolio_to_resume_text(portfolio: Portfolio, user: User) -> str:
    """Convert portfolio data into structured resume text for AI polishing."""
    sections = []

    # Header
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    sections.append(f"Name: {name}")
    if user.email:
        sections.append(f"Email: {user.email}")
    if user.phone:
        sections.append(f"Phone: {user.phone}")
    if portfolio.city or portfolio.state:
        sections.append(f"Location: {portfolio.city or ''}, {portfolio.state or ''}")
    if portfolio.linkedin_url:
        sections.append(f"LinkedIn: {portfolio.linkedin_url}")
    if portfolio.github_url:
        sections.append(f"GitHub: {portfolio.github_url}")

    # Headline / Summary
    if portfolio.headline:
        sections.append(f"\nProfessional Headline: {portfolio.headline}")
    if portfolio.bio:
        sections.append(f"\nProfessional Summary:\n{portfolio.bio}")

    # Skills
    if portfolio.skills:
        skill_names = [s.get("name", s) if isinstance(s, dict) else s for s in portfolio.skills]
        sections.append(f"\nSkills: {', '.join(skill_names)}")

    # Work Experience
    if portfolio.work_experiences:
        sections.append("\nWork Experience:")
        for exp in portfolio.work_experiences:
            if isinstance(exp, dict):
                role = exp.get("role", exp.get("title", ""))
                company = exp.get("company", "")
                start = _format_date_str(exp.get("start_date"))
                end = _format_date_str(exp.get("end_date"))
                desc = exp.get("description", "")
                sections.append(f"  - {role} at {company} ({start} - {end})")
                if desc:
                    sections.append(f"    {desc}")

    # Education
    if portfolio.education:
        sections.append("\nEducation:")
        for edu in portfolio.education:
            if isinstance(edu, dict):
                degree = edu.get("degree", "")
                institution = edu.get("institution", "")
                field = edu.get("field", "")
                year = edu.get("end_year", "")
                sections.append(f"  - {degree} in {field} from {institution} ({year})")

    # Certifications
    if portfolio.certifications:
        sections.append("\nCertifications:")
        for cert in portfolio.certifications:
            if isinstance(cert, dict):
                sections.append(f"  - {cert.get('name', '')} by {cert.get('issuer', '')} ({cert.get('date', '')})")

    # Projects
    if portfolio.projects:
        sections.append("\nProjects:")
        for proj in portfolio.projects:
            if isinstance(proj, dict):
                title = proj.get("title", "")
                desc = proj.get("description", "")
                techs = ", ".join(proj.get("technologies", []))
                sections.append(f"  - {title}: {desc}")
                if techs:
                    sections.append(f"    Technologies: {techs}")

    # Languages
    if portfolio.languages:
        sections.append("\nLanguages:")
        for lang in portfolio.languages:
            if isinstance(lang, dict):
                sections.append(f"  - {lang.get('language', '')} ({lang.get('proficiency', '')})")

    return "\n".join(sections)


def _generate_html_resume(resume_text: str, polished_text: str, template: str, user: User, portfolio: Portfolio) -> str:
    """Generate a styled HTML resume with distinct visual layouts per template."""
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    # --- SHARED DATA EXTRACTION ---
    contact_parts = []
    if user.email: contact_parts.append(user.email)
    if user.phone: contact_parts.append(user.phone)
    if portfolio.city or portfolio.state:
        contact_parts.append(f"{portfolio.city or ''}, {portfolio.state or ''}")

    link_parts = []
    if portfolio.linkedin_url: link_parts.append(f'<a href="{portfolio.linkedin_url}" style="color:inherit">LinkedIn</a>')
    if portfolio.github_url: link_parts.append(f'<a href="{portfolio.github_url}" style="color:inherit">GitHub</a>')

    skill_names = [sk.get("name", sk) if isinstance(sk, dict) else sk for sk in (portfolio.skills or [])]

    # --- TEMPLATE: MODERN ---
    if template == "modern":
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif; color:#1f2937; line-height:1.6; background:#fff; }}
  .resume {{ max-width:800px; margin:0 auto; padding:40px; }}
  .header {{ text-align:center; margin-bottom:30px; padding-bottom:20px; border-bottom:3px solid #2563eb; }}
  .header h1 {{ font-size:28px; color:#1e293b; letter-spacing:-0.5px; }}
  .header .subtitle {{ color:#2563eb; font-size:14px; font-weight:500; margin-top:4px; }}
  .header .contact {{ color:#64748b; font-size:13px; margin-top:8px; }}
  .header .contact a {{ color:#2563eb; text-decoration:none; }}
  .section {{ margin-bottom:22px; }}
  .section h2 {{ font-size:13px; color:#2563eb; border-bottom:2px solid #2563eb; padding-bottom:4px; margin-bottom:12px; text-transform:uppercase; letter-spacing:2px; font-weight:700; }}
  .section p {{ font-size:12px; color:#374151; }}
  .skills {{ display:flex; flex-wrap:wrap; gap:6px; }}
  .skill-tag {{ background:linear-gradient(135deg,#eff6ff,#dbeafe); color:#1d4ed8; padding:4px 10px; border-radius:6px; font-size:13px; font-weight:600; border:1px solid #bfdbfe; }}
  .exp-item {{ margin-bottom:14px; padding-left:14px; border-left:3px solid #dbeafe; }}
  .exp-item h3 {{ font-size:14px; font-weight:700; color:#111827; }}
  .exp-item .meta {{ color:#2563eb; font-size:13px; font-weight:500; }}
  .exp-item .desc {{ font-size:12px; color:#4b5563; margin-top:4px; }}
  ul {{ list-style:none; padding:0; }} li {{ font-size:12px; margin-bottom:3px; padding-left:12px; position:relative; }}
  li::before {{ content:'\\2022'; position:absolute; left:0; color:#2563eb; }}
  @media print {{
    @page {{ size:A4 portrait; margin:8mm 10mm; }}
    html, body {{ background:#fff !important; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
    .resume {{ max-width:100% !important; padding:0 !important; }}
    .header {{ border-bottom:3px solid #2563eb !important; }}
    .skill-tag {{ background:#eff6ff !important; color:#1d4ed8 !important; border:1px solid #bfdbfe !important; }}
  }}
</style></head><body><div class="resume">
  <div class="header">
    <h1>{name}</h1>
    {'<div class="subtitle">' + portfolio.headline + '</div>' if portfolio.headline else ''}
    <div class="contact">{' &bull; '.join(contact_parts)}</div>
    {'<div class="contact" style="margin-top:4px">' + ' | '.join(link_parts) + '</div>' if link_parts else ''}
  </div>
"""

    # --- TEMPLATE: CLASSIC ---
    elif template == "classic":
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Georgia','Times New Roman',serif; color:#2d2d2d; line-height:1.55; background:#fff; }}
  .resume {{ max-width:800px; margin:0 auto; padding:40px 50px; }}
  .header {{ text-align:center; margin-bottom:20px; padding-bottom:14px; border-top:3px double #333; border-bottom:3px double #333; }}
  .header h1 {{ font-size:26px; color:#1a1a2e; letter-spacing:3px; text-transform:uppercase; font-weight:normal; }}
  .header .subtitle {{ font-style:italic; color:#555; font-size:13px; margin-top:4px; }}
  .header .contact {{ color:#666; font-size:13px; margin-top:8px; letter-spacing:0.5px; }}
  .header .contact a {{ color:#1a1a2e; }}
  .section {{ margin-bottom:18px; }}
  .section h2 {{ font-size:14px; color:#1a1a2e; border-bottom:1px solid #999; padding-bottom:3px; margin-bottom:10px; text-transform:uppercase; letter-spacing:2px; font-weight:normal; font-variant:small-caps; font-size:16px; }}
  .section p {{ font-size:12px; color:#333; text-align:justify; }}
  .skills-list {{ font-size:12px; color:#333; font-style:italic; }}
  .exp-item {{ margin-bottom:12px; }}
  .exp-item h3 {{ font-size:13px; font-weight:bold; color:#1a1a2e; }}
  .exp-item .meta {{ color:#555; font-size:13px; font-style:italic; }}
  .exp-item .desc {{ font-size:12px; color:#444; margin-top:3px; text-align:justify; }}
  ul {{ list-style:none; padding:0; }} li {{ font-size:12px; margin-bottom:3px; padding-left:14px; position:relative; }}
  li::before {{ content:'—'; position:absolute; left:0; color:#999; }}
  @media print {{
    @page {{ size:A4 portrait; margin:8mm 10mm; }}
    html, body {{ background:#fff !important; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
    .resume {{ max-width:100% !important; padding:0 !important; }}
  }}
</style></head><body><div class="resume">
  <div class="header">
    <h1>{name}</h1>
    {'<div class="subtitle">' + portfolio.headline + '</div>' if portfolio.headline else ''}
    <div class="contact">{' | '.join(contact_parts)}</div>
    {'<div class="contact" style="margin-top:4px">' + ' | '.join(link_parts) + '</div>' if link_parts else ''}
  </div>
"""

    # --- TEMPLATE: MINIMAL ---
    elif template == "minimal":
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'IBM Plex Sans','Helvetica Neue',sans-serif; color:#222; line-height:1.7; background:#fff; }}
  .resume {{ max-width:760px; margin:0 auto; padding:50px 40px; }}
  .header {{ margin-bottom:35px; }}
  .header h1 {{ font-size:32px; font-weight:300; color:#000; letter-spacing:-1px; }}
  .header .subtitle {{ font-weight:400; color:#555; font-size:13px; margin-top:2px; }}
  .header .contact {{ color:#888; font-size:10px; margin-top:10px; letter-spacing:1px; text-transform:uppercase; }}
  .header .contact a {{ color:#555; text-decoration:none; }}
  .divider {{ border:none; border-top:1px solid #e0e0e0; margin:20px 0; }}
  .section {{ margin-bottom:24px; }}
  .section h2 {{ font-size:10px; color:#999; text-transform:uppercase; letter-spacing:3px; font-weight:600; margin-bottom:10px; }}
  .section p {{ font-size:12px; color:#444; font-weight:300; }}
  .skills-min {{ font-size:12px; color:#333; font-weight:300; }}
  .exp-item {{ margin-bottom:14px; }}
  .exp-item h3 {{ font-size:13px; font-weight:500; color:#111; }}
  .exp-item .meta {{ color:#888; font-size:13px; font-weight:300; }}
  .exp-item .desc {{ font-size:12px; color:#555; font-weight:300; margin-top:3px; }}
  ul {{ list-style:none; padding:0; }} li {{ font-size:12px; margin-bottom:3px; color:#555; font-weight:300; }}
  @media print {{
    @page {{ size:A4 portrait; margin:8mm 10mm; }}
    html, body {{ background:#fff !important; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
    .resume {{ max-width:100% !important; padding:0 !important; }}
  }}
</style></head><body><div class="resume">
  <div class="header">
    <h1>{name}</h1>
    {'<div class="subtitle">' + portfolio.headline + '</div>' if portfolio.headline else ''}
    <div class="contact">{' &nbsp;/&nbsp; '.join(contact_parts)}</div>
    {'<div class="contact" style="margin-top:4px">' + ' &nbsp;/&nbsp; '.join(link_parts) + '</div>' if link_parts else ''}
  </div>
  <hr class="divider">
"""

    # --- TEMPLATE: CREATIVE (Two-column sidebar) ---
    elif template == "creative":
        sidebar_items = []
        if contact_parts: sidebar_items.append(('<strong>Contact</strong><br>' + '<br>'.join(contact_parts)))
        if link_parts: sidebar_items.append(('<strong>Links</strong><br>' + '<br>'.join(link_parts)))
        if skill_names: sidebar_items.append(('<strong>Skills</strong><br>' + '<br>'.join(f'• {s}' for s in skill_names)))
        if portfolio.languages:
            langs = [f"• {l.get('language','')} ({l.get('proficiency','')})" for l in portfolio.languages if isinstance(l, dict)]
            if langs: sidebar_items.append(('<strong>Languages</strong><br>' + '<br>'.join(langs)))

        sidebar_html = '</div><div class="sidebar-section">'.join(sidebar_items)

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Poppins',sans-serif; color:#333; line-height:1.6; background:#fff; }}
  .resume {{ max-width:800px; margin:0 auto; display:flex; min-height:100vh; }}
  .sidebar {{ width:260px; background:linear-gradient(180deg,#312e81,#4338ca); color:#fff; padding:35px 22px; flex-shrink:0; }}
  .sidebar h1 {{ font-size:22px; font-weight:700; margin-bottom:4px; }}
  .sidebar .subtitle {{ font-size:12px; opacity:0.8; margin-bottom:25px; font-weight:300; }}
  .sidebar-section {{ margin-bottom:20px; font-size:13px; line-height:1.8; }}
  .sidebar-section strong {{ font-size:10px; text-transform:uppercase; letter-spacing:2px; display:block; margin-bottom:6px; opacity:0.7; }}
  .sidebar a {{ color:#c7d2fe; text-decoration:none; }}
  .main {{ flex:1; padding:35px 30px; }}
  .section {{ margin-bottom:22px; }}
  .section h2 {{ font-size:13px; color:#4338ca; text-transform:uppercase; letter-spacing:2px; font-weight:700; margin-bottom:10px; padding-bottom:4px; border-bottom:2px solid #e0e7ff; }}
  .section p {{ font-size:12px; color:#444; }}
  .exp-item {{ margin-bottom:14px; }}
  .exp-item h3 {{ font-size:13px; font-weight:600; color:#1e1b4b; }}
  .exp-item .meta {{ color:#6366f1; font-size:13px; font-weight:500; }}
  .exp-item .desc {{ font-size:12px; color:#555; margin-top:3px; }}
  ul {{ list-style:none; padding:0; }} li {{ font-size:12px; margin-bottom:3px; padding-left:12px; position:relative; }}
  li::before {{ content:'▸'; position:absolute; left:0; color:#6366f1; }}
  @media print {{
    @page {{ size:A4 portrait; margin:0; }}
    html, body {{ background:#fff !important; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
    .resume {{ display:flex !important; flex-direction:row !important; min-height:100% !important; max-width:100% !important; }}
    .sidebar {{ width:240px !important; background:#312e81 !important; color:#fff !important; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
    .main {{ flex:1 !important; padding:25px 25px !important; }}
  }}
</style></head><body><div class="resume">
  <div class="sidebar">
    <h1>{name}</h1>
    {'<div class="subtitle">' + portfolio.headline + '</div>' if portfolio.headline else '<div class="subtitle">&nbsp;</div>'}
    <div class="sidebar-section">{sidebar_html}</div>
  </div>
  <div class="main">
"""

    # --- TEMPLATE: EXECUTIVE ---
    else:  # executive
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+3:wght@300;400;600&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Source Sans 3',sans-serif; color:#2d2d2d; line-height:1.6; background:#fff; }}
  .resume {{ max-width:800px; margin:0 auto; }}
  .header {{ background:#1a1a2e; color:#fff; padding:35px 40px; text-align:center; }}
  .header h1 {{ font-family:'Playfair Display',serif; font-size:30px; font-weight:700; letter-spacing:2px; }}
  .header .subtitle {{ color:#d4a855; font-size:13px; font-weight:300; margin-top:4px; letter-spacing:1px; }}
  .header .contact {{ color:rgba(255,255,255,0.6); font-size:13px; margin-top:10px; }}
  .header .contact a {{ color:#d4a855; text-decoration:none; }}
  .gold-bar {{ height:4px; background:linear-gradient(90deg,#d4a855,#f0d78c,#d4a855); }}
  .content {{ padding:30px 40px; }}
  .section {{ margin-bottom:22px; }}
  .section h2 {{ font-family:'Playfair Display',serif; font-size:16px; color:#1a1a2e; border-bottom:2px solid #d4a855; padding-bottom:4px; margin-bottom:12px; letter-spacing:1px; }}
  .section p {{ font-size:12px; color:#444; }}
  .skill-tag {{ display:inline-block; background:#fef3c7; color:#92400e; padding:3px 10px; border-radius:4px; font-size:13px; font-weight:600; margin-right:4px; margin-bottom:4px; }}
  .exp-item {{ margin-bottom:14px; padding-left:14px; border-left:3px solid #d4a855; }}
  .exp-item h3 {{ font-size:14px; font-weight:600; color:#1a1a2e; font-family:'Playfair Display',serif; }}
  .exp-item .meta {{ color:#d4a855; font-size:13px; font-weight:600; }}
  .exp-item .desc {{ font-size:12px; color:#555; margin-top:4px; }}
  ul {{ list-style:none; padding:0; }} li {{ font-size:12px; margin-bottom:3px; padding-left:12px; position:relative; }}
  li::before {{ content:'◆'; position:absolute; left:0; color:#d4a855; font-size:8px; top:3px; }}
  @media print {{
    @page {{ size:A4 portrait; margin:0; }}
    html, body {{ background:#fff !important; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
    .resume {{ max-width:100% !important; }}
    .header {{ background:#1a1a2e !important; color:#fff !important; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
    .gold-bar {{ background:#d4a855 !important; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
    .content {{ padding:20px 30px !important; }}
  }}
</style></head><body><div class="resume">
  <div class="header">
    <h1>{name}</h1>
    {'<div class="subtitle">' + portfolio.headline + '</div>' if portfolio.headline else ''}
    <div class="contact">{' &bull; '.join(contact_parts)}</div>
    {'<div class="contact" style="margin-top:4px">' + ' | '.join(link_parts) + '</div>' if link_parts else ''}
  </div>
  <div class="gold-bar"></div>
  <div class="content">
"""

    # --- CONTENT SECTIONS (shared across all templates) ---
    # For creative template, skills/languages are in sidebar, skip them in main
    is_creative = template == "creative"

    if portfolio.bio:
        html += f'  <div class="section"><h2>Professional Summary</h2><p>{portfolio.bio}</p></div>\n'

    if skill_names and not is_creative:
        if template == "classic":
            html += f'  <div class="section"><h2>Skills</h2><p class="skills-list">{", ".join(skill_names)}</p></div>\n'
        elif template == "minimal":
            html += f'  <div class="section"><h2>Skills</h2><p class="skills-min">{" · ".join(skill_names)}</p></div>\n'
        else:
            html += '  <div class="section"><h2>Skills</h2><div class="skills">'
            for sk in skill_names:
                html += f'<span class="skill-tag">{sk}</span>'
            html += '</div></div>\n'

    if portfolio.work_experiences:
        html += '  <div class="section"><h2>Experience</h2>'
        for exp in portfolio.work_experiences:
            if isinstance(exp, dict):
                html += f'''<div class="exp-item">
<h3>{exp.get("role", exp.get("title", ""))}</h3>
<div class="meta">{exp.get("company", "")} | {_format_date_str(exp.get("start_date"))} – {_format_date_str(exp.get("end_date"))}</div>
<div class="desc">{exp.get("description", "")}</div>
</div>'''
        html += '</div>\n'

    if portfolio.education:
        html += '  <div class="section"><h2>Education</h2>'
        for edu in portfolio.education:
            if isinstance(edu, dict):
                html += f'''<div class="exp-item">
<h3>{edu.get("degree", "")} in {edu.get("field", "")}</h3>
<div class="meta">{edu.get("institution", "")} | {edu.get("end_year", "")}</div>
</div>'''
        html += '</div>\n'

    if portfolio.projects:
        html += '  <div class="section"><h2>Projects</h2>'
        for proj in portfolio.projects:
            if isinstance(proj, dict):
                techs = ", ".join(proj.get("technologies", []))
                html += f'''<div class="exp-item">
<h3>{proj.get("title", "")}</h3>
<div class="desc">{proj.get("description", "")}</div>
{f'<div class="meta">Technologies: {techs}</div>' if techs else ''}
</div>'''
        html += '</div>\n'

    if portfolio.certifications:
        html += '  <div class="section"><h2>Certifications</h2><ul>'
        for cert in portfolio.certifications:
            if isinstance(cert, dict):
                html += f'<li>{cert.get("name", "")} – {cert.get("issuer", "")} ({cert.get("date", "")})</li>'
        html += '</ul></div>\n'

    if portfolio.languages and not is_creative:
        html += '  <div class="section"><h2>Languages</h2><ul>'
        for lang in portfolio.languages:
            if isinstance(lang, dict):
                html += f'<li>{lang.get("language", "")} – {lang.get("proficiency", "")}</li>'
        html += '</ul></div>\n'

    # Close template wrappers
    if template == "creative":
        html += '</div>'  # close .main
    elif template == "executive":
        html += '</div>'  # close .content

    html += '''
  <script>
    window.addEventListener('message', function(e) {
      if (e.data === 'print_resume') {
        window.focus();
        window.print();
      }
    });
  </script>
</div></body></html>'''
    return html



@router.post("/ai-assist", response_model=AIAssistResponse)
async def ai_assist_section(
    body: AIAssistRequest,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    """
    AI assistant to generate, improve, or suggest content for specific resume sections:
    summary, headline, experience, skills, projects.
    """
    section = (body.section or "summary").lower().strip()
    action = (body.action or "generate").lower().strip()

    if not settings.GOOGLE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="AI assistant service is currently unconfigured (missing Google Gemini API key)."
        )

    try:
        gemini_client = google_genai.Client(api_key=settings.GOOGLE_API_KEY)

        import json, re

        system_instructions = {
            "summary": (
                "You are an executive resume writer. Craft a punchy, ATS-friendly professional summary (3-4 sentences max). "
                "Highlight key expertise, quantifiable impact, and core strengths. "
                "Use strong action verbs. Do not use generic buzzwords or conversational filler. "
                "Output ONLY the summary text, no quotes, no headings."
            ),
            "headline": (
                "You are a tech recruiter. Craft a sharp, punchy one-line professional headline "
                "for a resume and LinkedIn profile (max 10-12 words). "
                "Example: 'Senior Full-Stack Developer | React, Node.js & Cloud Architecture'. "
                "Output ONLY the headline, no quotes or prefix."
            ),
            "skills": (
                "You are an expert technical recruiter and talent scout. "
                "The user will provide their existing skills and an edit instruction (e.g. to add or remove skills, or suggest new ones). "
                "Apply their instructions strictly. If instructed to add or remove specific skills, do so accurately. "
                "Return ONLY a comma-separated list of the final skills, with NO bullet points, NO numbering, and NO conversational filler."
            ),
            "experience": (
                "You are an ATS resume editor. The user wants to add, edit, or remove work experience entries or improve descriptions. "
                "You MUST output valid JSON ONLY inside a ```json ... ``` code block containing an array of objects. "
                "Each object must have the following keys: "
                '{"role": "Job Title", "company": "Company Name", "start_date": "YYYY-MM", "end_date": "YYYY-MM or Present", "description": "• Quantifiable achievement with metrics\\n• Core responsibility..."}. '
                "Do NOT write any conversational explanation before or after the JSON block."
            ),
            "projects": (
                "You are a technical resume coach. The user wants to add, edit, or remove project entries. "
                "You MUST output valid JSON ONLY inside a ```json ... ``` code block containing an array of objects. "
                "Each object must have: "
                '{"title": "Project Title", "technologies": ["Tech1", "Tech2"], "description": "• Built feature X using Y...\\n• Delivered result Z..."}. '
                "Do NOT write any conversational explanation before or after the JSON block."
            ),
            "education": (
                "You are an academic resume coach. The user wants to add, edit, or remove education entries. "
                "You MUST output valid JSON ONLY inside a ```json ... ``` code block containing an array of objects. "
                "Each object must have: "
                '{"degree": "Degree (e.g. B.Tech / MBA / B.Sc)", "field": "Field of Study", "institution": "College / University Name", "end_year": "YYYY"}. '
                "Do NOT write any conversational explanation before or after the JSON block."
            ),
            "certifications": (
                "You are a professional certification advisor. The user wants to add, edit, or remove certifications. "
                "You MUST output valid JSON ONLY inside a ```json ... ``` code block containing an array of objects. "
                "Each object must have: "
                '{"name": "Certification Name", "issuer": "Issuing Authority (e.g. AWS, Google, Coursera)", "date": "YYYY"}. '
                "Do NOT write any conversational explanation before or after the JSON block."
            ),
            "languages": (
                "You are a multilingual career advisor. The user wants to add, edit, or remove languages. "
                "You MUST output valid JSON ONLY inside a ```json ... ``` code block containing an array of objects. "
                "Each object must have: "
                '{"language": "Language Name", "proficiency": "Basic / Conversational / Fluent / Native"}. '
                "Do NOT write any conversational explanation before or after the JSON block."
            ),
        }

        system_prompt = system_instructions.get(section, system_instructions["summary"])

        user_prompt_parts = [f"Target section: {section}"]
        if body.role:
            user_prompt_parts.append(f"Candidate Role / Job Title: {body.role}")
        if body.company:
            user_prompt_parts.append(f"Company: {body.company}")
        if body.skills:
            user_prompt_parts.append(f"Current Skills: {', '.join(body.skills)}")
        if body.context:
            try:
                user_prompt_parts.append(f"Current Structured Section Data:\n{json.dumps(body.context, indent=2)}")
            except Exception:
                pass
        if body.current_text:
            user_prompt_parts.append(f"Current Section Text / Content:\n{body.current_text}")
        if body.custom_instruction:
            user_prompt_parts.append(
                f"User Edit Request (Strictly follow this instruction to add, remove, or modify entries in this section):\n"
                f"{body.custom_instruction}"
            )
        if action == "ats_optimize":
            user_prompt_parts.append("Goal: Optimize strictly for ATS keywords and high recruiter readability.")
        elif action == "shorten":
            user_prompt_parts.append("Goal: Make it exceptionally concise and compact.")

        full_prompt = f"{system_prompt}\n\n" + "\n".join(user_prompt_parts)

        response = gemini_client.models.generate_content(
            model=settings.GEMINI_CHAT_MODEL,
            contents=[full_prompt],
            config={"temperature": 0.2, "max_output_tokens": 2048},
        )

        generated_text = (response.text or "").strip()

        suggested_skills = None
        structured_data = None

        # Check for JSON block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', generated_text)
        if json_match:
            try:
                structured_data = json.loads(json_match.group(1))
            except Exception:
                pass
        elif (generated_text.startswith('[') and generated_text.endswith(']')) or (generated_text.startswith('{') and generated_text.endswith('}')):
            try:
                structured_data = json.loads(generated_text)
            except Exception:
                pass

        # If wrapped in a dictionary, unwrap it to list
        if isinstance(structured_data, dict):
            for k in ("items", "entries", "roles", "experience", "work_experiences", "projects", "education", "certifications", "languages"):
                if k in structured_data and isinstance(structured_data[k], list):
                    structured_data = structured_data[k]
                    break

        # Fallback text parser if model returned bullet points instead of JSON
        if structured_data is None and section in ("experience", "projects", "education", "certifications", "languages"):
            lines = [l.strip() for l in generated_text.splitlines() if l.strip()]
            if section == "experience":
                parsed_exps = []
                cur_exp = None
                for line in lines:
                    match = re.match(r'^(?:[-*•\d.]+\s*)?([^|–\-]+?)\s+(?:at|@)\s+([^|(–\-]+)(?:\s*[(|–\-]\s*(.*?)[)|–\-]?\s*)?$', line, re.IGNORECASE)
                    if match:
                        if cur_exp:
                            parsed_exps.append(cur_exp)
                        role_str = match.group(1).strip()
                        comp_str = match.group(2).strip()
                        date_str = match.group(3) or "2023 - Present"
                        parts = date_str.split("-") if "-" in date_str else date_str.split("–")
                        start_d = parts[0].strip() if len(parts) > 0 else "2023-01"
                        end_d = parts[1].strip() if len(parts) > 1 else "Present"
                        cur_exp = {
                            "role": role_str,
                            "company": comp_str,
                            "start_date": start_d,
                            "end_date": end_d,
                            "description": "",
                        }
                    elif cur_exp:
                        cur_exp["description"] += ("\n" if cur_exp["description"] else "") + line
                if cur_exp:
                    parsed_exps.append(cur_exp)
                if parsed_exps:
                    structured_data = parsed_exps

            elif section == "projects":
                parsed_projs = []
                cur_proj = None
                for line in lines:
                    match = re.match(r'^(?:[-*•\d.]+\s*)?([^:]+?):\s*(.*)$', line)
                    if match:
                        if cur_proj:
                            parsed_projs.append(cur_proj)
                        cur_proj = {
                            "title": match.group(1).strip(),
                            "technologies": ["React", "Node.js"],
                            "description": match.group(2).strip(),
                        }
                    elif cur_proj:
                        cur_proj["description"] += ("\n" if cur_proj["description"] else "") + line
                if cur_proj:
                    parsed_projs.append(cur_proj)
                if parsed_projs:
                    structured_data = parsed_projs

            elif section == "education":
                parsed_edu = []
                for line in lines:
                    m = re.match(r'^(?:[-*•\d.]+\s*)?([^,]+?)\s+(?:in|of)\s+([^,]+?)(?:,\s*|\s+(?:from|at)\s+)([^,(]+)(?:\s*\((.*?)\))?$', line, re.IGNORECASE)
                    if m:
                        parsed_edu.append({
                            "degree": m.group(1).strip(),
                            "field": m.group(2).strip(),
                            "institution": m.group(3).strip(),
                            "end_year": m.group(4).strip() if m.group(4) else "2024",
                        })
                if parsed_edu:
                    structured_data = parsed_edu

            elif section == "certifications":
                parsed_cert = []
                for line in lines:
                    m = re.match(r'^(?:[-*•\d.]+\s*)?([^–\-|(]+?)(?:\s*(?:by|from|–|-)\s*([^–\-|(]+))?(?:\s*\((.*?)\))?$', line, re.IGNORECASE)
                    if m:
                        parsed_cert.append({
                            "name": m.group(1).strip(),
                            "issuer": m.group(2).strip() if m.group(2) else "Authority",
                            "date": m.group(3).strip() if m.group(3) else "2024",
                        })
                if parsed_cert:
                    structured_data = parsed_cert

            elif section == "languages":
                parsed_lang = []
                for line in lines:
                    m = re.match(r'^(?:[-*•\d.]+\s*)?([A-Za-z]+)(?:\s*[(–\-:]\s*(.*?)[)]?)?$', line)
                    if m:
                        parsed_lang.append({
                            "language": m.group(1).strip(),
                            "proficiency": m.group(2).strip() if m.group(2) else "Fluent",
                        })
                if parsed_lang:
                    structured_data = parsed_lang

        if section == "skills":
            raw_skills = [
                s.strip().lstrip("•-*0123456789. ")
                for s in generated_text.replace("\n", ",").split(",")
                if s.strip()
            ]
            suggested_skills = [s for s in raw_skills if 1 < len(s) < 40][:20]

        return AIAssistResponse(
            section=section,
            suggested_text=generated_text,
            suggested_skills=suggested_skills,
            structured_data=structured_data,
            message="AI suggestion generated successfully."
        )
    except Exception as e:
        logger.exception(f"[RESUME_AI_ASSIST] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate AI suggestion: {str(e)}")


@router.post("/preview")
async def preview_resume(
    body: ResumeBuilderRequest,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    """Preview the resume that would be generated from portfolio data or live overrides."""
    portfolio = None
    if not body.portfolio_data:
        portfolio_result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = portfolio_result.scalar_one_or_none()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Please complete your portfolio first")

    eff_user, eff_portfolio = _resolve_data(user, portfolio, body.portfolio_data)
    resume_text = _portfolio_to_resume_text(eff_portfolio, eff_user)
    html = _generate_html_resume(resume_text, resume_text, body.template, eff_user, eff_portfolio)
    return HTMLResponse(content=html)


@router.post("/generate")
async def generate_resume(
    body: ResumeBuilderRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    """Generate a polished resume from portfolio data using AI, save as active resume."""
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolio = portfolio_result.scalar_one_or_none()
    if not portfolio and not body.portfolio_data:
        raise HTTPException(status_code=404, detail="Please complete your portfolio first")

    eff_user, eff_portfolio = _resolve_data(user, portfolio, body.portfolio_data)
    raw_text = _portfolio_to_resume_text(eff_portfolio, eff_user)
    
    # ── Gemini AI resume polish (OpenAI not used) ────────────────────
    polished_text = raw_text
    try:
        gemini_client = google_genai.Client(api_key=settings.GOOGLE_API_KEY)
        system_prompt = (
            "You are a professional resume writer. Given raw resume data, produce a polished, "
            "ATS-friendly resume in plain text format. Keep it concise, professional, and well-structured. "
            "Use action verbs, quantify achievements where possible, and highlight key skills. "
            "Do NOT invent information – only use what is provided."
        )
        combined = f"{system_prompt}\n\nPolish this resume:\n\n{raw_text}"
        response = gemini_client.models.generate_content(
            model=settings.GEMINI_CHAT_MODEL,
            contents=[combined],
            config={"temperature": 0.3, "max_output_tokens": 8192},
        )
        if response.text:
            polished_text = response.text
    except Exception as e:
        logger.warning(f"[RESUME_BUILDER] AI polish fallback to raw: {e}")

    # Generate professional HTML content
    html_content = _generate_html_resume(raw_text, polished_text, body.template, eff_user, eff_portfolio)

    # Convert HTML to PDF using xhtml2pdf
    file_id = str(uuid.uuid4())
    filename = f"resume_built_{file_id[:8]}.pdf"
    file_path = str(UPLOAD_DIR / filename)
    
    from xhtml2pdf import pisa
    with open(file_path, "wb") as f:
        pisa.CreatePDF(html_content, dest=f)

    # Upsert resume record
    existing_result = await db.execute(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()).limit(1)
    )
    existing = existing_result.scalar_one_or_none()

    # Build parsed_json from portfolio
    parsed_json = {
        "name": f"{getattr(eff_user, 'first_name', '')} {getattr(eff_user, 'last_name', '')}".strip(),
        "email": getattr(eff_user, "email", user.email),
        "phone": getattr(eff_user, "phone", user.phone),
        "skills": [s.get("name", s) if isinstance(s, dict) else s for s in (eff_portfolio.skills or [])],
        "experience": [
            {
                "title": exp.get("role", exp.get("title", "")),
                "company": exp.get("company", ""),
                "start_date": _format_date_str(exp.get("start_date")),
                "end_date": _format_date_str(exp.get("end_date")),
                "description": exp.get("description", ""),
            }
            for exp in (eff_portfolio.work_experiences or []) if isinstance(exp, dict)
        ],
        "education": [
            {
                "degree": edu.get("degree", ""),
                "institution": edu.get("institution", ""),
                "field": edu.get("field", ""),
                "graduation_date": edu.get("end_year", ""),
            }
            for edu in (eff_portfolio.education or []) if isinstance(edu, dict)
        ],
        "summary": eff_portfolio.bio or eff_portfolio.headline or "",
    }

    if existing:
        existing.filename = filename
        existing.file_path = file_path
        existing.file_size_bytes = os.path.getsize(file_path)
        existing.parsed_text = polished_text
        existing.parsed_json = parsed_json
        existing.source = "builder"
        existing.embedding = None
        await db.commit()
        await db.refresh(existing)
        resume = existing
    else:
        resume = Resume(
            user_id=user.id,
            filename=filename,
            file_path=file_path,
            file_size_bytes=os.path.getsize(file_path),
            parsed_text=polished_text,
            parsed_json=parsed_json,
            source="builder",
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

    # Background: embed and match
    async def _process(rid: str):
        from app.core.database import AsyncSessionLocal
        from app.modules.jobs_portal.services.seeker_matching_service import embed_and_store_resume, proactive_match_resume_to_jobs
        from sqlalchemy import text as sa_text
        async with AsyncSessionLocal() as s:
            try:
                r = await s.get(Resume, rid)
                if not r or not r.parsed_text:
                    return
                # Clear old matches
                from app.modules.jobs_portal.models.match import Match
                from sqlalchemy import delete
                await s.execute(delete(Match).where(Match.seeker_id == r.user_id))
                await s.commit()
                await embed_and_store_resume(r, s)
                await proactive_match_resume_to_jobs(rid)
                logger.info(f"[BUILDER] Resume {rid} processed and matched")
            except Exception as e:
                logger.exception(f"[BUILDER] Failed: {e}")

    background_tasks.add_task(_process, resume.id)

    return {
        "id": str(resume.id),
        "filename": resume.filename,
        "source": resume.source,
        "message": "Resume generated successfully! AI matching will update shortly.",
    }


@router.get("/download-pdf")
async def download_pdf(
    template: str = "modern",
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    """Download the built resume as an HTML file (can be printed as PDF from browser)."""
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolio = portfolio_result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Please complete your portfolio first")

    resume_text = _portfolio_to_resume_text(portfolio, user)
    html = _generate_html_resume(resume_text, resume_text, template, user, portfolio)

    # Convert HTML to PDF using xhtml2pdf
    pdf_id = str(uuid.uuid4())[:8]
    filename = f"resume_temp_{pdf_id}.pdf"
    file_path = str(UPLOAD_DIR / filename)
    
    from xhtml2pdf import pisa
    with open(file_path, "wb") as f:
        pisa.CreatePDF(html, dest=f)
    
    user_name = f"{user.first_name or ''}_{user.last_name or ''}".strip() or "seeker"
    return FileResponse(
        path=file_path,
        filename=f"resume_{user_name}.pdf",
        media_type="application/pdf"
    )


@router.post("/download")
async def download_resume_post(
    body: ResumeBuilderRequest,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    """Download the built resume matching the exact template."""
    portfolio = None
    if not body.portfolio_data:
        portfolio_result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = portfolio_result.scalar_one_or_none()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Please complete your portfolio first")

    eff_user, eff_portfolio = _resolve_data(user, portfolio, body.portfolio_data)
    resume_text = _portfolio_to_resume_text(eff_portfolio, eff_user)
    html = _generate_html_resume(resume_text, resume_text, body.template, eff_user, eff_portfolio)

    pdf_id = str(uuid.uuid4())[:8]
    filename = f"resume_temp_{pdf_id}.pdf"
    file_path = str(UPLOAD_DIR / filename)

    from xhtml2pdf import pisa
    with open(file_path, "wb") as f:
        pisa.CreatePDF(html, dest=f)

    user_name = f"{getattr(eff_user, 'first_name', '')}_{getattr(eff_user, 'last_name', '')}".strip() or "seeker"
    return FileResponse(
        path=file_path,
        filename=f"resume_{user_name}.pdf",
        media_type="application/pdf"
    )
