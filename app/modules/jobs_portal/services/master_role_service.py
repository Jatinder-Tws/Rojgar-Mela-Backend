"""List + create for master_roles — shared seeker/admin job-role picker."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.master import MasterRole
from app.shared.validators.job_role import normalize_job_role, validate_job_role_value

CANONICAL_ROLES: List[str] = [
    "Accountant",
    "Customer Support",
    "Data Analyst",
    "Driver",
    "Electrician",
    "HR Executive",
    "Marketing Executive",
    "Nurse",
    "Receptionist",
    "Sales Executive",
    "Software Developer",
    "Store Manager",
    "Teacher",
    "Welder",
]


class MasterRoleOut(BaseModel):
    id: str
    name: str


class MasterRoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


def _to_out(row: MasterRole) -> MasterRoleOut:
    return MasterRoleOut(id=str(row.id), name=row.name)


async def ensure_seeded(db: AsyncSession) -> None:
    existing = (await db.execute(select(func.count()).select_from(MasterRole))).scalar_one()
    if int(existing or 0) > 0:
        return
    for name in CANONICAL_ROLES:
        db.add(MasterRole(id=str(uuid.uuid4()), name=name))
    await db.commit()


async def list_roles(db: AsyncSession) -> List[MasterRoleOut]:
    await ensure_seeded(db)
    rows = (await db.execute(select(MasterRole).order_by(MasterRole.name.asc()))).scalars().all()
    return [_to_out(row) for row in rows]


async def create_role(db: AsyncSession, body: MasterRoleCreate) -> MasterRoleOut:
    await ensure_seeded(db)
    try:
        name = validate_job_role_value(body.name, required=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    assert name is not None

    dup = (
        await db.execute(select(MasterRole).where(func.lower(MasterRole.name) == name.lower()))
    ).scalar_one_or_none()
    if dup:
        return _to_out(dup)

    row = MasterRole(id=str(uuid.uuid4()), name=name)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_out(row)


async def find_or_create_role(db: AsyncSession, raw_name: str) -> MasterRoleOut:
    cleaned = normalize_job_role(raw_name)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Enter a real job role (e.g. Software Developer)")
    return await create_role(db, MasterRoleCreate(name=cleaned))
