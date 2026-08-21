from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.super_admin.controllers.import_users_controller import (
    import_seekers as ctrl_import_seekers,
    import_providers as ctrl_import_providers,
)

router = APIRouter(prefix="/import", tags=["Import"])


@router.post("/seekers")
async def import_seekers(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await ctrl_import_seekers(file, db)


@router.post("/providers")
async def import_providers(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await ctrl_import_providers(file, db)
