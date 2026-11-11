"""CRUD for master_industries — shared seeker/admin industry picker."""

from __future__ import annotations

import re
import uuid
from typing import List

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.models.job import JobPosting
from app.shared.models.master import MasterIndustry
from app.shared.models.user import User

CANONICAL_INDUSTRIES: List[str] = [
    "Agriculture",
    "Automotive",
    "Aviation",
    "Banking & Finance",
    "BPO/KPO",
    "Construction",
    "Consulting",
    "Education",
    "Energy",
    "Fashion & Textiles",
    "FMCG",
    "Government",
    "Healthcare",
    "Hospitality",
    "Human Resources",
    "Information Technology",
    "IT & Software",
    "Legal",
    "Logistics",
    "Manufacturing",
    "Media & Entertainment",
    "Pharmaceuticals",
    "Real Estate",
    "Retail & E-Commerce",
    "Startups & Entrepreneurship",
    "Telecommunications",
]


class MasterIndustryOut(BaseModel):
    id: str
    name: str
    usage_count: int = 0


class MasterIndustryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class MasterIndustryUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


def _clean_name(raw: str) -> str:
    name = re.sub(r"\s+", " ", (raw or "").strip())
    if not name:
        raise HTTPException(status_code=400, detail="Industry name is required")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Industry name must be at most 100 characters")
    if name.isdigit():
        raise HTTPException(status_code=400, detail="Industry name cannot be only numbers")
    return name


def _to_out(row: MasterIndustry, usage_count: int = 0) -> MasterIndustryOut:
    return MasterIndustryOut(id=str(row.id), name=row.name, usage_count=usage_count)


async def _usage_count(db: AsyncSession, name: str) -> int:
    users = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(func.lower(func.trim(User.industry)) == name.lower())
        )
    ).scalar_one()
    jobs = (
        await db.execute(
            select(func.count())
            .select_from(JobPosting)
            .where(func.lower(func.trim(JobPosting.industry)) == name.lower())
        )
    ).scalar_one()
    return int(users or 0) + int(jobs or 0)


async def ensure_seeded(db: AsyncSession) -> None:
    existing = (await db.execute(select(func.count()).select_from(MasterIndustry))).scalar_one()
    if int(existing or 0) > 0:
        return
    for name in CANONICAL_INDUSTRIES:
        db.add(MasterIndustry(id=str(uuid.uuid4()), name=name))
    await db.commit()


async def list_industries(db: AsyncSession) -> List[MasterIndustryOut]:
    await ensure_seeded(db)
    rows = (await db.execute(select(MasterIndustry).order_by(MasterIndustry.name.asc()))).scalars().all()
    out: List[MasterIndustryOut] = []
    for row in rows:
        out.append(_to_out(row, await _usage_count(db, row.name)))
    return out


async def create_industry(db: AsyncSession, body: MasterIndustryCreate) -> MasterIndustryOut:
    await ensure_seeded(db)
    name = _clean_name(body.name)
    dup = (
        await db.execute(
            select(MasterIndustry).where(func.lower(MasterIndustry.name) == name.lower())
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail="Industry already exists")
    row = MasterIndustry(id=str(uuid.uuid4()), name=name)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_out(row, 0)


async def update_industry(
    db: AsyncSession, industry_id: str, body: MasterIndustryUpdate
) -> MasterIndustryOut:
    name = _clean_name(body.name)
    row = (
        await db.execute(select(MasterIndustry).where(MasterIndustry.id == industry_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Industry not found")

    if name.lower() != row.name.lower():
        dup = (
            await db.execute(
                select(MasterIndustry).where(
                    func.lower(MasterIndustry.name) == name.lower(),
                    MasterIndustry.id != industry_id,
                )
            )
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(status_code=400, detail="Industry already exists")

        old_name = row.name
        row.name = name
        await db.execute(
            update(User)
            .where(User.industry == old_name)
            .values(industry=name)
        )
        await db.execute(
            update(JobPosting)
            .where(JobPosting.industry == old_name)
            .values(industry=name)
        )
    else:
        row.name = name

    await db.commit()
    await db.refresh(row)
    return _to_out(row, await _usage_count(db, row.name))


async def delete_industry(db: AsyncSession, industry_id: str) -> None:
    row = (
        await db.execute(select(MasterIndustry).where(MasterIndustry.id == industry_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Industry not found")

    usage = await _usage_count(db, row.name)
    if usage > 0:
        raise HTTPException(
            status_code=400,
            detail=f'Cannot delete "{row.name}" — used by {usage} profile(s) or job(s)',
        )

    await db.delete(row)
    await db.commit()
