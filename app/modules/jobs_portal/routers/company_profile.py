from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_provider
from app.modules.jobs_portal.schemas.company_profile import (
    CompanyApplyLookupRequest,
    CompanyLookupRequest,
    CompanyLookupResponse,
    CompanyProfileOut,
    CompanyProfileUpdateRequest,
)
from app.modules.jobs_portal.services import company_profile_service as svc
from app.shared.models.user import User

router = APIRouter(prefix="/providers/me", tags=["provider-company"])


@router.get("/company", response_model=CompanyProfileOut)
async def get_company_profile(
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_company_profile(user, db)


@router.patch("/company", response_model=CompanyProfileOut)
async def update_company_profile(
    body: CompanyProfileUpdateRequest,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await svc.update_company_profile(user, body, db)


@router.post("/company/lookup", response_model=CompanyLookupResponse)
async def lookup_company(
    body: CompanyLookupRequest,
    user: User = Depends(require_provider),
):
    return await svc.lookup_company(body)


@router.post("/company/apply-lookup", response_model=CompanyProfileOut)
async def apply_company_lookup(
    body: CompanyApplyLookupRequest,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await svc.apply_lookup(user, body, db)


@router.post("/company/gallery", response_model=CompanyProfileOut)
async def upload_gallery_image(
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await svc.upload_gallery_image(user, file, db, caption)


@router.delete("/company/gallery/{image_id}", response_model=CompanyProfileOut)
async def delete_gallery_image(
    image_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await svc.delete_gallery_image(user, image_id, db)
