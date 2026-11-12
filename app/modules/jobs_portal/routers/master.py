from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import require_authenticated
from app.modules.jobs_portal.services import master_industry_service as industry_svc
from app.modules.jobs_portal.services.master_industry_service import (
    MasterIndustryCreate,
    MasterIndustryOut,
    MasterIndustryUpdate,
)
from app.modules.jobs_portal.services import master_role_service as role_svc
from app.modules.jobs_portal.services.master_role_service import MasterRoleCreate, MasterRoleOut
from app.shared.models.master import MasterState, MasterCity, MasterLanguage
from app.shared.models.user import User

router = APIRouter(prefix="/master", tags=["master-data"])

class MasterItemOut(BaseModel):
    id: int
    name: str

class MasterStateOut(MasterItemOut):
    code: str | None = None

class MasterCityOut(MasterItemOut):
    state_id: int

@router.get("/states", response_model=List[MasterStateOut])
async def get_states(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MasterState).order_by(MasterState.name))
    return result.scalars().all()

@router.get("/cities/{state_id}", response_model=List[MasterCityOut])
async def get_cities(state_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MasterCity).where(MasterCity.state_id == state_id).order_by(MasterCity.name)
    )
    return result.scalars().all()

@router.get("/industries", response_model=List[MasterIndustryOut])
async def get_industries(db: AsyncSession = Depends(get_db)):
    return await industry_svc.list_industries(db)

@router.post("/industries", response_model=MasterIndustryOut, status_code=status.HTTP_201_CREATED)
async def create_industry(
    body: MasterIndustryCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_authenticated),
):
    return await industry_svc.create_industry(db, body)

@router.put("/industries/{industry_id}", response_model=MasterIndustryOut)
async def update_industry(
    industry_id: str,
    body: MasterIndustryUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_authenticated),
):
    return await industry_svc.update_industry(db, industry_id, body)

@router.delete("/industries/{industry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_industry(
    industry_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_authenticated),
):
    await industry_svc.delete_industry(db, industry_id)
    return None

@router.get("/languages", response_model=List[MasterItemOut])
async def get_languages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MasterLanguage).order_by(MasterLanguage.name))
    return result.scalars().all()

@router.get("/roles", response_model=List[MasterRoleOut])
async def get_roles(db: AsyncSession = Depends(get_db)):
    return await role_svc.list_roles(db)


@router.post("/roles", response_model=MasterRoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: MasterRoleCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_authenticated),
):
    return await role_svc.create_role(db, body)


@router.get("/industries/{industry_id}/roles", response_model=List[MasterRoleOut])
async def get_roles_by_industry(industry_id: int, db: AsyncSession = Depends(get_db)):
    # MasterRole has no industry_id column today; return full list for picker compatibility.
    _ = industry_id
    return await role_svc.list_roles(db)
