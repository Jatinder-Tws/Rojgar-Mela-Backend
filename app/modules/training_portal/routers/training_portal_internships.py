import uuid
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.modules.training_portal.models.training_portal_internship import TrainingPortalInternship
from app.modules.training_portal.schemas.training_portal_internship import (
    TrainingPortalInternshipCreate,
    TrainingPortalInternshipUpdate,
    TrainingPortalInternshipOut,
)
from app.core.dependencies import require_super_admin, require_training_portal_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training-portal/internships", tags=["Training Portal Internships"])


def _to_out(internship: TrainingPortalInternship) -> TrainingPortalInternshipOut:
    return TrainingPortalInternshipOut(
        id=internship.id,
        title=internship.title,
        description=internship.description,
        duration=internship.duration,
        is_paid=internship.is_paid,
        fee=internship.fee,
        start_date=internship.start_date,
        end_date=internship.end_date,
        venue=internship.venue,
        max_seats=internship.max_seats,
        seats_filled=internship.seats_filled,
        status=internship.status,
        laptop_required=internship.laptop_required,
        created_at=internship.created_at,
        updated_at=internship.updated_at,
    )


@router.get("/", response_model=List[TrainingPortalInternshipOut])
async def list_portal_internships(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    """List training portal internships."""
    query = select(TrainingPortalInternship).order_by(TrainingPortalInternship.created_at.desc())

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                TrainingPortalInternship.title.ilike(term),
                TrainingPortalInternship.venue.ilike(term),
            )
        )
    if status_filter and status_filter != "all":
        query = query.where(TrainingPortalInternship.status == status_filter.strip())

    result = await db.execute(query)
    return [_to_out(internship) for internship in result.scalars().all()]


@router.post("/", response_model=TrainingPortalInternshipOut, status_code=status.HTTP_201_CREATED)
async def create_portal_internship(
    internship_in: TrainingPortalInternshipCreate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new training portal internship (super admin only)."""
    now = datetime.utcnow()
    internship = TrainingPortalInternship(
        id=str(uuid.uuid4()),
        created_by_id=current_user.id,
        title=internship_in.title.strip(),
        description=internship_in.description.strip(),
        duration=internship_in.duration.strip(),
        is_paid=internship_in.is_paid,
        fee=internship_in.fee if internship_in.is_paid else 0.0,
        start_date=internship_in.start_date.strip(),
        end_date=internship_in.end_date.strip(),
        venue=internship_in.venue.strip(),
        max_seats=internship_in.max_seats,
        seats_filled=internship_in.seats_filled,
        status=internship_in.status,
        laptop_required=internship_in.laptop_required,
        created_at=now,
        updated_at=now,
    )
    db.add(internship)
    await db.commit()
    await db.refresh(internship)
    return _to_out(internship)


@router.get("/{internship_id}", response_model=TrainingPortalInternshipOut)
async def get_portal_internship(
    internship_id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalInternship).where(TrainingPortalInternship.id == internship_id)
    )
    internship = result.scalar_one_or_none()
    if not internship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Internship not found")
    return _to_out(internship)


@router.put("/{internship_id}", response_model=TrainingPortalInternshipOut)
async def update_portal_internship(
    internship_id: str,
    internship_update: TrainingPortalInternshipUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalInternship).where(TrainingPortalInternship.id == internship_id)
    )
    internship = result.scalar_one_or_none()
    if not internship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Internship not found")

    update_data = internship_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(internship, field, value)
    internship.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(internship)
    return _to_out(internship)


@router.delete("/{internship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portal_internship(
    internship_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalInternship).where(TrainingPortalInternship.id == internship_id)
    )
    internship = result.scalar_one_or_none()
    if not internship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Internship not found")
    await db.delete(internship)
    await db.commit()
    return None