import os
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, or_, and_, cast, String, func, literal, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings, get_upload_dir
from app.modules.jobs_portal.models.portfolio import Portfolio
from app.shared.models.user import User, UserRole
from app.modules.jobs_portal.models.external_candidate import ExternalCandidate
from app.modules.jobs_portal.models.job import JobPosting
from app.modules.jobs_portal.models.application import Application
from app.modules.jobs_portal.schemas.portfolio import (
    PortfolioUpdate,
    PortfolioOut,
    PortfolioCompletionOut,
    CandidateSearchItemOut,
    CandidateSearchListResponse,
)
from app.modules.jobs_portal.services.portfolio_service import calculate_completion, portfolio_json_fields

ALLOWED_VIDEO_EXT = {".mp4", ".webm", ".mov", ".avi"}
ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".webm"}
MAX_MEDIA_MB = 50


def _calculate_completion(portfolio: Portfolio, user: User) -> tuple[int, list, list]:
    return calculate_completion(portfolio, user)


def _portfolio_to_out(portfolio: Optional[Portfolio], user: User) -> dict:
    if portfolio is None:
        pct = 0
        json_fields = {
            "skills": [],
            "work_experiences": [],
            "education": [],
            "certifications": [],
            "languages": [],
            "projects": [],
        }
        portfolio_id = str(user.id)
        created_at = user.created_at
        updated_at = user.created_at
        headline = bio = date_of_birth = city = state = None
        linkedin_url = github_url = website_url = None
        total_experience_years = current_company = current_role = None
        intro_video_filename = intro_audio_filename = None
        has_intro_video = has_intro_audio = False
        gender = getattr(user, "gender", None)
    else:
        pct, filled, missing = _calculate_completion(portfolio, user)
        json_fields = portfolio_json_fields(portfolio)
        portfolio_id = str(portfolio.id)
        created_at = portfolio.created_at
        updated_at = portfolio.updated_at
        headline = portfolio.headline
        bio = portfolio.bio
        date_of_birth = portfolio.date_of_birth
        gender = portfolio.gender or getattr(user, "gender", None)
        city = portfolio.city
        state = portfolio.state
        linkedin_url = portfolio.linkedin_url
        github_url = portfolio.github_url
        website_url = portfolio.website_url
        total_experience_years = portfolio.total_experience_years
        current_company = portfolio.current_company
        current_role = portfolio.current_role
        intro_video_filename = portfolio.intro_video_filename
        intro_audio_filename = portfolio.intro_audio_filename
        has_intro_video = bool(portfolio.intro_video_path)
        has_intro_audio = bool(portfolio.intro_audio_path)

    return {
        "id": portfolio_id,
        "user_id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "industry": user.industry,
        "job_role": user.job_role,
        "onboarding_complete": bool(user.onboarding_complete),
        "profile_pic_url": user.profile_pic_url,
        "headline": headline,
        "bio": bio,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "city": city,
        "state": state,
        "linkedin_url": linkedin_url,
        "github_url": github_url,
        "website_url": website_url,
        "total_experience_years": total_experience_years,
        "current_company": current_company,
        "current_role": current_role,
        **json_fields,
        "intro_video_filename": intro_video_filename,
        "intro_audio_filename": intro_audio_filename,
        "has_intro_video": has_intro_video,
        "has_intro_audio": has_intro_audio,
        "completion_percentage": pct,
        "created_at": created_at,
        "updated_at": updated_at,
    }


async def _get_or_create_portfolio(user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        portfolio = Portfolio(user_id=user.id)
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)
    return portfolio


def _media_upload_dir(user_id: str) -> Path:
    base = get_upload_dir()
    if not base.is_absolute():
        base = Path(__file__).parent.parent / base
    d = base / "portfolio" / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


async def get_my_portfolio(user: User, db: AsyncSession) -> dict:
    portfolio = await _get_or_create_portfolio(user, db)
    return _portfolio_to_out(portfolio, user)


async def update_my_portfolio(body: PortfolioUpdate, background_tasks: BackgroundTasks, user: User, db: AsyncSession) -> dict:
    portfolio = await _get_or_create_portfolio(user, db)
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in ("first_name", "last_name", "email", "industry", "job_role"):
            setattr(user, key, value)
        elif key in ("skills", "work_experiences", "education", "certifications", "languages", "projects"):
            setattr(portfolio, key, [item.model_dump() if hasattr(item, "model_dump") else item for item in value] if value else value)
        else:
            setattr(portfolio, key, value)
    await db.commit()
    await db.refresh(portfolio)
    await db.refresh(user)
    from app.shared.services.celery_tasks import invalidate_seeker_matches_task
    invalidate_seeker_matches_task.delay(str(user.id))
    return _portfolio_to_out(portfolio, user)


async def get_completion(user: User, db: AsyncSession) -> dict:
    portfolio = await _get_or_create_portfolio(user, db)
    pct, filled, missing = _calculate_completion(portfolio, user)
    return {"percentage": pct, "filled_sections": filled, "missing_sections": missing}


def _parse_search_terms(q: Optional[str], skills: Optional[str]) -> List[str]:
    terms: List[str] = []
    for raw in (q, skills):
        if raw:
            terms.extend(t.strip() for t in raw.replace(",", " ").split() if t.strip())
    seen = set()
    unique: List[str] = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return unique


def _seeker_search_clause(term: str):
    pattern = f"%{term}%"
    return or_(
        User.first_name.ilike(pattern),
        User.last_name.ilike(pattern),
        User.email.ilike(pattern),
        User.phone.ilike(pattern),
        User.industry.ilike(pattern),
        User.job_role.ilike(pattern),
        Portfolio.headline.ilike(pattern),
        Portfolio.bio.ilike(pattern),
        Portfolio.current_role.ilike(pattern),
        Portfolio.city.ilike(pattern),
        cast(Portfolio.skills, String).ilike(pattern),
    )


def _external_search_clause(term: str):
    pattern = f"%{term}%"
    return or_(
        ExternalCandidate.full_name.ilike(pattern),
        ExternalCandidate.email.ilike(pattern),
        ExternalCandidate.phone.ilike(pattern),
        ExternalCandidate.sub_role.ilike(pattern),
        ExternalCandidate.city.ilike(pattern),
        ExternalCandidate.state.ilike(pattern),
        ExternalCandidate.skills.ilike(pattern),
        cast(ExternalCandidate.industries, String).ilike(pattern),
    )


def _seeker_gender_clause(gender: str):
    g = gender.strip().lower()
    return or_(
        func.lower(Portfolio.gender) == g,
        func.lower(User.gender) == g,
    )


def _external_gender_clause(gender: str):
    return func.lower(ExternalCandidate.gender) == gender.strip().lower()


def _external_industry_clause(industry: str):
    pattern = f"%{industry.strip()}%"
    return cast(ExternalCandidate.industries, String).ilike(pattern)


def _registered_to_candidate_item(
    port: Optional[Portfolio],
    usr: User,
    app_status: Optional[str],
    is_shortlisted: bool,
) -> CandidateSearchItemOut:
    data = _portfolio_to_out(port, usr)
    skills_raw = data.get("skills") or []
    skill_names = [s["name"] for s in skills_raw if isinstance(s, dict) and s.get("name")]
    return CandidateSearchItemOut(
        id=str(data["id"]),
        user_id=str(data["user_id"]),
        first_name=data.get("first_name") or "",
        last_name=data.get("last_name") or "",
        headline=data.get("headline"),
        current_role=data.get("current_role") or data.get("job_role") or data.get("headline"),
        city=data.get("city"),
        total_experience_years=data.get("total_experience_years"),
        is_active=bool(data.get("onboarding_complete")),
        profile_pic_url=data.get("profile_pic_url"),
        email=data.get("email"),
        phone=data.get("phone"),
        date_of_birth=data.get("date_of_birth"),
        gender=data.get("gender"),
        skills=skill_names,
        source="registered",
        resume_url=None,
        completion_percentage=int(data.get("completion_percentage") or 0),
        created_at=data.get("created_at"),
        industry=data.get("industry"),
        application_status=app_status,
        is_shortlisted=is_shortlisted,
    )


def _external_to_candidate_item(
    candidate: ExternalCandidate,
    is_shortlisted: bool,
) -> CandidateSearchItemOut:
    name_parts = (candidate.full_name or "").split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    industry = None
    if isinstance(candidate.industries, list):
        industry = ", ".join(str(i) for i in candidate.industries if i)
    elif candidate.industries:
        industry = str(candidate.industries)
    exp_years = None
    if candidate.total_experience:
        try:
            exp_years = float(str(candidate.total_experience).split()[0])
        except (ValueError, IndexError):
            exp_years = None
    skills = []
    if candidate.skills:
        skills = [s.strip() for s in str(candidate.skills).split(",") if s.strip()]
    return CandidateSearchItemOut(
        id=str(candidate.id),
        user_id=str(candidate.id),
        first_name=first_name,
        last_name=last_name,
        headline=candidate.sub_role,
        current_role=candidate.sub_role,
        city=candidate.city or candidate.state,
        total_experience_years=exp_years,
        is_active=True,
        profile_pic_url=candidate.profile_picture_url,
        email=candidate.email,
        phone=candidate.phone,
        date_of_birth=candidate.date_of_birth,
        gender=candidate.gender,
        skills=skills,
        source="form_apply",
        resume_url=candidate.resume_url,
        completion_percentage=0,
        created_at=candidate.applied_at,
        industry=industry,
        application_status=str(candidate.status or "pending"),
        is_shortlisted=is_shortlisted,
    )


async def search_candidates(
    q: Optional[str],
    title: Optional[str],
    skills: Optional[str],
    status: Optional[str],
    gender: Optional[str],
    industry: Optional[str],
    page: int,
    page_size: int,
    provider: User,
    db: AsyncSession,
) -> CandidateSearchListResponse:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    terms = _parse_search_terms(q, skills)
    title = (title or "").strip() or None
    status = (status or "").strip().lower() or None
    gender = (gender or "").strip() or None
    industry = (industry or "").strip() or None

    seeker_filters = [User.role == UserRole.seeker, User.is_super_admin.is_(False)]
    if status == "active":
        seeker_filters.append(User.onboarding_complete.is_(True))
    elif status in ("closed", "inactive"):
        seeker_filters.append(User.onboarding_complete.is_(False))
    if gender:
        seeker_filters.append(_seeker_gender_clause(gender))
    if industry:
        seeker_filters.append(User.industry.ilike(f"%{industry}%"))
    for term in terms:
        seeker_filters.append(_seeker_search_clause(term))
    if title:
        title_term = f"%{title}%"
        seeker_filters.append(or_(
            Portfolio.headline.ilike(title_term),
            Portfolio.current_role.ilike(title_term),
            User.job_role.ilike(title_term),
        ))

    seeker_ids_stmt = (
        select(User.id.label("record_id"), literal("registered").label("source"), User.created_at.label("sort_at"))
        .select_from(User)
        .outerjoin(Portfolio, Portfolio.user_id == User.id)
        .where(*seeker_filters)
    )

    seeker_emails_subq = (
        select(User.email)
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False), User.email.isnot(None))
    )

    external_filters = [
        or_(JobPosting.provider_id == provider.id, ExternalCandidate.job_id.is_(None)),
        or_(ExternalCandidate.email.is_(None), ExternalCandidate.email.notin_(seeker_emails_subq)),
    ]
    if gender:
        external_filters.append(_external_gender_clause(gender))
    if industry:
        external_filters.append(_external_industry_clause(industry))
    if status in ("closed", "inactive"):
        external_filters.append(ExternalCandidate.id.is_(None))
    for term in terms:
        external_filters.append(_external_search_clause(term))
    if title:
        title_term = f"%{title}%"
        external_filters.append(ExternalCandidate.sub_role.ilike(title_term))

    external_ids_stmt = (
        select(
            ExternalCandidate.id.label("record_id"),
            literal("external").label("source"),
            ExternalCandidate.applied_at.label("sort_at"),
        )
        .outerjoin(JobPosting, ExternalCandidate.job_id == JobPosting.id)
        .where(*external_filters)
    )

    union_stmt = union_all(seeker_ids_stmt, external_ids_stmt).subquery()
    total = await db.scalar(select(func.count()).select_from(union_stmt)) or 0

    page_rows = (
        await db.execute(
            select(union_stmt.c.record_id, union_stmt.c.source, union_stmt.c.sort_at)
            .order_by(union_stmt.c.sort_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    registered_ids = [str(row.record_id) for row in page_rows if row.source == "registered"]
    external_ids = [str(row.record_id) for row in page_rows if row.source == "external"]

    registered_map: dict[str, tuple[Optional[Portfolio], User]] = {}
    if registered_ids:
        reg_result = await db.execute(
            select(Portfolio, User)
            .select_from(User)
            .outerjoin(Portfolio, Portfolio.user_id == User.id)
            .where(User.id.in_(registered_ids))
        )
        for port, usr in reg_result.all():
            registered_map[str(usr.id)] = (port, usr)

    external_map: dict[str, ExternalCandidate] = {}
    if external_ids:
        ext_result = await db.execute(select(ExternalCandidate).where(ExternalCandidate.id.in_(external_ids)))
        for ext in ext_result.scalars().all():
            external_map[str(ext.id)] = ext

    shortlisted_seekers: set[str] = set()
    app_status_by_seeker: dict[str, str] = {}
    if registered_ids:
        apps_result = await db.execute(
            select(Application.seeker_id, Application.status)
            .join(JobPosting, Application.job_id == JobPosting.id)
            .where(
                JobPosting.provider_id == provider.id,
                Application.seeker_id.in_(registered_ids),
            )
            .order_by(Application.applied_at.desc())
        )
        for seeker_id, app_status in apps_result.all():
            sid = str(seeker_id)
            if sid not in app_status_by_seeker:
                app_status_by_seeker[sid] = str(app_status.value if hasattr(app_status, "value") else app_status)
            if str(app_status) in ("shortlisted", "interviewing", "selected") or (
                hasattr(app_status, "value") and app_status.value in ("shortlisted", "interviewing", "selected")
            ):
                shortlisted_seekers.add(sid)

    items: List[CandidateSearchItemOut] = []
    for row in page_rows:
        rid = str(row.record_id)
        if row.source == "registered":
            pair = registered_map.get(rid)
            if not pair:
                continue
            port, usr = pair
            items.append(_registered_to_candidate_item(
                port,
                usr,
                app_status_by_seeker.get(rid),
                rid in shortlisted_seekers,
            ))
        else:
            ext = external_map.get(rid)
            if not ext:
                continue
            items.append(_external_to_candidate_item(
                ext,
                str(ext.status or "").lower() == "shortlisted",
            ))

    return CandidateSearchListResponse(items=items, total=total, page=page, page_size=page_size)


async def upload_media(media_type: str, file: UploadFile, user: User, db: AsyncSession) -> dict:
    if media_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="media_type must be 'video' or 'audio'")
    ext = Path(file.filename or "media").suffix.lower()
    allowed = ALLOWED_VIDEO_EXT if media_type == "video" else ALLOWED_AUDIO_EXT
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported {media_type} format. Allowed: {', '.join(allowed)}")
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_MEDIA_MB:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_MEDIA_MB}MB for {media_type}.")
    upload_dir = _media_upload_dir(user.id)
    safe_name = f"{media_type}_{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / safe_name
    with open(file_path, "wb") as f:
        f.write(content)
    portfolio = await _get_or_create_portfolio(user, db)
    if media_type == "video":
        if portfolio.intro_video_path and os.path.exists(portfolio.intro_video_path):
            os.remove(portfolio.intro_video_path)
        portfolio.intro_video_path = str(file_path)
        portfolio.intro_video_filename = file.filename
    else:
        if portfolio.intro_audio_path and os.path.exists(portfolio.intro_audio_path):
            os.remove(portfolio.intro_audio_path)
        portfolio.intro_audio_path = str(file_path)
        portfolio.intro_audio_filename = file.filename
    await db.commit()
    await db.refresh(portfolio)
    return _portfolio_to_out(portfolio, user)


async def delete_media(media_type: str, user: User, db: AsyncSession) -> dict:
    if media_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="media_type must be 'video' or 'audio'")
    portfolio = await _get_or_create_portfolio(user, db)
    if media_type == "video":
        if portfolio.intro_video_path and os.path.exists(portfolio.intro_video_path):
            os.remove(portfolio.intro_video_path)
        portfolio.intro_video_path = None
        portfolio.intro_video_filename = None
    else:
        if portfolio.intro_audio_path and os.path.exists(portfolio.intro_audio_path):
            os.remove(portfolio.intro_audio_path)
        portfolio.intro_audio_path = None
        portfolio.intro_audio_filename = None
    await db.commit()
    await db.refresh(portfolio)
    return _portfolio_to_out(portfolio, user)


async def stream_media(media_type: str, user: User, db: AsyncSession) -> FileResponse:
    if media_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="media_type must be 'video' or 'audio'")
    portfolio = await _get_or_create_portfolio(user, db)
    path = portfolio.intro_video_path if media_type == "video" else portfolio.intro_audio_path
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No {media_type} uploaded")
    return FileResponse(path, filename=portfolio.intro_video_filename if media_type == "video" else portfolio.intro_audio_filename)


async def stream_user_media(user_id: str, media_type: str, db: AsyncSession) -> FileResponse:
    if media_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="media_type must be 'video' or 'audio'")
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    path = portfolio.intro_video_path if media_type == "video" else portfolio.intro_audio_path
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No {media_type} uploaded")
    filename = portfolio.intro_video_filename if media_type == "video" else portfolio.intro_audio_filename
    return FileResponse(path, filename=filename)


async def get_user_portfolio(user_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    target_result = await db.execute(select(User).where(User.id == user_id))
    target_user = target_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    return _portfolio_to_out(portfolio, target_user)
