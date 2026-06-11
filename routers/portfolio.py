from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.portfolio import PortfolioUpdate, PortfolioOut, PortfolioCompletionOut
from services.auth_service import require_verified, require_seeker, require_provider
from controllers.portfolio_controller import (
    get_my_portfolio as ctrl_get_my_portfolio,
    update_my_portfolio as ctrl_update_my_portfolio,
    get_completion as ctrl_get_completion,
    search_candidates as ctrl_search_candidates,
    upload_media as ctrl_upload_media,
    delete_media as ctrl_delete_media,
    stream_media as ctrl_stream_media,
    stream_user_media as ctrl_stream_user_media,
    get_user_portfolio as ctrl_get_user_portfolio,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/me", response_model=PortfolioOut)
async def get_my_portfolio(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_my_portfolio(user, db)


@router.put("/me", response_model=PortfolioOut)
async def update_my_portfolio(body: PortfolioUpdate, background_tasks: BackgroundTasks, user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_update_my_portfolio(body, background_tasks, user, db)


@router.get("/me/completion", response_model=PortfolioCompletionOut)
async def get_completion(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_completion(user, db)


@router.get("/search", response_model=list[PortfolioOut])
async def search_candidates(q: Optional[str] = None, title: Optional[str] = None, skills: Optional[str] = None, provider: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_search_candidates(q, title, skills, provider, db)


@router.post("/me/media/{media_type}", response_model=PortfolioOut)
async def upload_media(media_type: str, file: UploadFile = File(...), user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_upload_media(media_type, file, user, db)


@router.delete("/me/media/{media_type}", response_model=PortfolioOut)
async def delete_media(media_type: str, user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_delete_media(media_type, user, db)


@router.get("/me/media/{media_type}")
async def stream_media(media_type: str, user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_stream_media(media_type, user, db)


@router.get("/{user_id}/media/{media_type}")
async def stream_user_media(user_id: str, media_type: str, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_stream_user_media(user_id, media_type, db)


@router.get("/{user_id}", response_model=PortfolioOut)
async def get_user_portfolio(user_id: str, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_user_portfolio(user_id, db)
