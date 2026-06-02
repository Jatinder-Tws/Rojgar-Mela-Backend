from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from database import get_db
from models.master import MasterState, MasterCity, MasterIndustry, MasterLanguage, MasterRole

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

@router.get("/industries", response_model=List[MasterItemOut])
async def get_industries(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MasterIndustry).order_by(MasterIndustry.name))
    return result.scalars().all()

@router.get("/languages", response_model=List[MasterItemOut])
async def get_languages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MasterLanguage).order_by(MasterLanguage.name))
    return result.scalars().all()

@router.get("/roles", response_model=List[MasterItemOut])
async def get_roles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MasterRole).order_by(MasterRole.name))
    return result.scalars().all()


# Add this route to your routers/master.py
@router.get("/industries/{industry_id}/roles", response_model=List[MasterItemOut])
async def get_roles_by_industry(industry_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MasterRole)
        .where(MasterRole.industry_id == industry_id)
        .order_by(MasterRole.name)
    )
    return result.scalars().all()
