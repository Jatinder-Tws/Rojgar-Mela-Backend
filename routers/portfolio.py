import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User, UserRole
from models.portfolio import Portfolio
from schemas.portfolio import PortfolioUpdate, PortfolioOut, PortfolioCompletionOut
from services.auth_service import require_verified, require_seeker, require_provider
from services.portfolio_service import calculate_completion, portfolio_json_fields

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

ALLOWED_VIDEO_EXT = {".mp4", ".webm", ".mov", ".avi"}
ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".webm"}
MAX_MEDIA_MB = 50


def _calculate_completion(portfolio: Portfolio, user: User) -> tuple[int, list[str], list[str]]:
    return calculate_completion(portfolio, user)


def _portfolio_to_out(portfolio: Portfolio, user: User) -> dict:
    pct, filled, missing = _calculate_completion(portfolio, user)
    json_fields = portfolio_json_fields(portfolio)
    data = {
        "id": str(portfolio.id),
        "user_id": str(portfolio.user_id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "profile_pic_url": user.profile_pic_url,
        "headline": portfolio.headline,
        "bio": portfolio.bio,
        "date_of_birth": portfolio.date_of_birth,
        "gender": portfolio.gender or getattr(user, "gender", None),
        "city": portfolio.city,
        "state": portfolio.state,
        "linkedin_url": portfolio.linkedin_url,
        "github_url": portfolio.github_url,
        "website_url": portfolio.website_url,
        "total_experience_years": portfolio.total_experience_years,
        "current_company": portfolio.current_company,
        "current_role": portfolio.current_role,
        **json_fields,
        "intro_video_filename": portfolio.intro_video_filename,
        "intro_audio_filename": portfolio.intro_audio_filename,
        "has_intro_video": bool(portfolio.intro_video_path),
        "has_intro_audio": bool(portfolio.intro_audio_path),
        "completion_percentage": pct,
        "created_at": portfolio.created_at,
        "updated_at": portfolio.updated_at,
    }
    return data


async def _get_or_create_portfolio(user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        portfolio = Portfolio(user_id=user.id)
        db.add(portfolio)
        await db.flush()
        await db.refresh(portfolio)
    return portfolio


@router.get("/me", response_model=PortfolioOut)
async def get_my_portfolio(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await _get_or_create_portfolio(user, db)
    return _portfolio_to_out(portfolio, user)


@router.put("/me", response_model=PortfolioOut)
async def update_my_portfolio(
    body: PortfolioUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await _get_or_create_portfolio(user, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in ("first_name", "last_name", "email"):
            setattr(user, key, value)
        elif key in ("skills", "work_experiences", "education", "certifications", "languages", "projects"):
            setattr(portfolio, key, [item.model_dump() if hasattr(item, "model_dump") else item for item in value] if value else value)
        else:
            setattr(portfolio, key, value)

    await db.commit()
    await db.refresh(portfolio)

    # Trigger AI re-matching in background when profile changes
    from services.seeker_matching_service import invalidate_seeker_matches
    background_tasks.add_task(invalidate_seeker_matches, user.id)

    return _portfolio_to_out(portfolio, user)


@router.get("/me/completion", response_model=PortfolioCompletionOut)
async def get_completion(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await _get_or_create_portfolio(user, db)
    pct, filled, missing = _calculate_completion(portfolio, user)
    return {"percentage": pct, "filled_sections": filled, "missing_sections": missing}


@router.get("/search", response_model=list[PortfolioOut])
async def search_candidates(
    q: Optional[str] = None,
    title: Optional[str] = None,
    skills: Optional[str] = None,
    provider: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    """Search candidates (seekers only)."""
    q = (q or "").strip() or None
    title = (title or "").strip() or None
    skills = (skills or "").strip() or None

    stmt = (
        select(Portfolio, User)
        .join(User, Portfolio.user_id == User.id)
        .where(User.role == UserRole.seeker, User.onboarding_complete.is_(True))
    )

    text_filters = []
    if q:
        search_term = f"%{q}%"
        text_filters.append(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term),
                Portfolio.headline.ilike(search_term),
                Portfolio.bio.ilike(search_term),
                Portfolio.current_role.ilike(search_term),
                Portfolio.city.ilike(search_term),
            )
        )

    if title:
        title_term = f"%{title}%"
        text_filters.append(
            or_(
                Portfolio.headline.ilike(title_term),
                Portfolio.current_role.ilike(title_term),
            )
        )

    if text_filters:
        stmt = stmt.where(or_(*text_filters))

    if skills:
        skill_list = [s.strip() for s in skills.split(",") if s.strip()]
        if skill_list:
            skill_conditions = [
                cast(Portfolio.skills, String).ilike(f"%{s}%") for s in skill_list
            ]
            stmt = stmt.where(or_(*skill_conditions))

    result = await db.execute(stmt)
    rows = result.all()

    return [_portfolio_to_out(port, usr) for port, usr in rows]


def _media_upload_dir(user_id: str) -> Path:
    base = Path(settings.UPLOAD_DIR)
    if not base.is_absolute():
        base = Path(__file__).parent.parent / base
    d = base / "portfolio" / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/me/media/{media_type}", response_model=PortfolioOut)
async def upload_media(
    media_type: str,
    file: UploadFile = File(...),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
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


@router.delete("/me/media/{media_type}", response_model=PortfolioOut)
async def delete_media(
    media_type: str,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
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


@router.get("/me/media/{media_type}")
async def stream_media(
    media_type: str,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    if media_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="media_type must be 'video' or 'audio'")

    portfolio = await _get_or_create_portfolio(user, db)
    path = portfolio.intro_video_path if media_type == "video" else portfolio.intro_audio_path

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No {media_type} uploaded")

    return FileResponse(path, filename=portfolio.intro_video_filename if media_type == "video" else portfolio.intro_audio_filename)


async def _provider_has_match_with_seeker(provider_id: str, seeker_id: str, db: AsyncSession) -> bool:
    """Check if provider has any job with a match for this seeker."""
    from models.match import Match
    from models.job import JobPosting
    result = await db.execute(
        select(Match)
        .join(JobPosting, JobPosting.id == Match.job_id)
        .where(JobPosting.provider_id == provider_id, Match.seeker_id == seeker_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


@router.get("/{user_id}/media/{media_type}")
async def stream_user_media(
    user_id: str,
    media_type: str,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """Providers and seekers can stream a candidate's intro video/audio."""
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


@router.get("/{user_id}", response_model=PortfolioOut)
async def get_user_portfolio(
    user_id: str,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """Providers can view a seeker's portfolio (must have a match)."""
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    target_result = await db.execute(select(User).where(User.id == user_id))
    target_user = target_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    return _portfolio_to_out(portfolio, target_user)
