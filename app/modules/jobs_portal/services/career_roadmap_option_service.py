import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.models.career_roadmap import CareerRoadmap
from app.modules.jobs_portal.models.career_roadmap_option import CareerRoadmapOption
from app.modules.jobs_portal.schemas.career_roadmap_option import (
    RoadmapOptionCreate,
    RoadmapOptionOut,
    RoadmapOptionUpdate,
)

OPTION_KINDS = ("category", "level", "industry", "resource_type", "skill_tag")

DEFAULT_OPTIONS: dict[str, list[str]] = {
    "category": [
        "Technology",
        "Software Engineering",
        "Cloud & DevOps",
        "AI & Data",
        "Cybersecurity",
        "Design & Product",
        "Management",
    ],
    "level": ["Beginner", "Intermediate", "Advanced", "All Levels"],
    "industry": ["IT", "Software", "Startup", "E-commerce", "Fintech", "Other"],
    "resource_type": ["course", "article", "video", "project", "certification", "other"],
    "skill_tag": ["React", "Node.js", "Python", "Docker", "Kubernetes", "SQL", "TypeScript", "AWS"],
}


def _normalize_kind(kind: str) -> str:
    value = (kind or "").strip().lower()
    if value not in OPTION_KINDS:
        raise HTTPException(status_code=400, detail=f"Invalid kind. Allowed: {', '.join(OPTION_KINDS)}")
    return value


def _clean_name(name: str) -> str:
    cleaned = " ".join((name or "").strip().split())
    if not cleaned:
        raise HTTPException(status_code=400, detail="Name is required")
    if len(cleaned) > 120:
        raise HTTPException(status_code=400, detail="Name must be 120 characters or fewer")
    return cleaned


async def _usage_count(db: AsyncSession, kind: str, name: str) -> int:
    if kind == "category":
        return (
            await db.execute(
                select(func.count()).select_from(CareerRoadmap).where(CareerRoadmap.category == name)
            )
        ).scalar() or 0
    if kind == "level":
        return (
            await db.execute(
                select(func.count()).select_from(CareerRoadmap).where(CareerRoadmap.level == name)
            )
        ).scalar() or 0
    if kind == "industry":
        rows = (await db.execute(select(CareerRoadmap.industries))).scalars().all()
        return sum(1 for industries in rows if isinstance(industries, list) and name in industries)
    if kind == "skill_tag":
        rows = (await db.execute(select(CareerRoadmap.skill_tags))).scalars().all()
        return sum(1 for tags in rows if isinstance(tags, list) and name in tags)
    if kind == "resource_type":
        rows = (await db.execute(select(CareerRoadmap.resources))).scalars().all()
        count = 0
        for resources in rows:
            if not isinstance(resources, list):
                continue
            for item in resources:
                if isinstance(item, dict) and str(item.get("type") or "") == name:
                    count += 1
                    break
        return count
    return 0


def _to_out(row: CareerRoadmapOption, usage_count: int = 0) -> RoadmapOptionOut:
    return RoadmapOptionOut(
        id=row.id,
        kind=row.kind,
        name=row.name,
        sort_order=row.sort_order or 0,
        usage_count=usage_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _collect_existing_values(db: AsyncSession) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {kind: set() for kind in OPTION_KINDS}
    rows = (await db.execute(select(CareerRoadmap))).scalars().all()
    for row in rows:
        if row.category:
            found["category"].add(str(row.category).strip())
        if row.level:
            found["level"].add(str(row.level).strip())
        for industry in row.industries or []:
            if str(industry).strip():
                found["industry"].add(str(industry).strip())
        for tag in row.skill_tags or []:
            if str(tag).strip():
                found["skill_tag"].add(str(tag).strip())
        for resource in row.resources or []:
            if isinstance(resource, dict) and str(resource.get("type") or "").strip():
                found["resource_type"].add(str(resource.get("type")).strip())
    return found


async def seed_defaults(db: AsyncSession) -> None:
    existing = (
        await db.execute(select(CareerRoadmapOption.kind, CareerRoadmapOption.name))
    ).all()
    existing_map: dict[str, set[str]] = {kind: set() for kind in OPTION_KINDS}
    for kind, name in existing:
        existing_map.setdefault(kind, set()).add(name.lower())

    from_roadmaps = await _collect_existing_values(db)
    now = datetime.utcnow()
    added = False
    for kind in OPTION_KINDS:
        names: list[str] = []
        seen_lower: set[str] = set(existing_map.get(kind, set()))
        for source in (DEFAULT_OPTIONS.get(kind, []), sorted(from_roadmaps.get(kind, set()))):
            for name in source:
                key = name.lower()
                if not name or key in seen_lower:
                    continue
                seen_lower.add(key)
                names.append(name)
        if not names:
            continue
        max_order = (
            await db.execute(
                select(func.coalesce(func.max(CareerRoadmapOption.sort_order), -1)).where(
                    CareerRoadmapOption.kind == kind
                )
            )
        ).scalar()
        start = int(max_order or -1) + 1
        for idx, name in enumerate(names):
            db.add(
                CareerRoadmapOption(
                    id=str(uuid.uuid4()),
                    kind=kind,
                    name=name,
                    sort_order=start + idx,
                    created_at=now,
                    updated_at=now,
                )
            )
            added = True
    if added:
        await db.commit()


async def list_options(db: AsyncSession, kind: str) -> list[RoadmapOptionOut]:
    kind = _normalize_kind(kind)
    await seed_defaults(db)
    rows = (
        await db.execute(
            select(CareerRoadmapOption)
            .where(CareerRoadmapOption.kind == kind)
            .order_by(CareerRoadmapOption.sort_order.asc(), CareerRoadmapOption.name.asc())
        )
    ).scalars().all()
    out = []
    for row in rows:
        out.append(_to_out(row, await _usage_count(db, kind, row.name)))
    return out


async def create_option(db: AsyncSession, kind: str, body: RoadmapOptionCreate) -> RoadmapOptionOut:
    kind = _normalize_kind(kind)
    name = _clean_name(body.name)
    dup = (
        await db.execute(
            select(CareerRoadmapOption).where(
                CareerRoadmapOption.kind == kind,
                CareerRoadmapOption.name.ilike(name),
            )
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail="Option already exists")

    max_order = (
        await db.execute(
            select(func.coalesce(func.max(CareerRoadmapOption.sort_order), 0)).where(
                CareerRoadmapOption.kind == kind
            )
        )
    ).scalar() or 0
    now = datetime.utcnow()
    row = CareerRoadmapOption(
        id=str(uuid.uuid4()),
        kind=kind,
        name=name,
        sort_order=int(max_order) + 1,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_out(row, 0)


async def _rename_in_json_list(db: AsyncSession, column, old: str, new: str) -> None:
    rows = (await db.execute(select(CareerRoadmap))).scalars().all()
    changed = False
    for row in rows:
        values = getattr(row, column.key)
        if not isinstance(values, list):
            continue
        next_values = [new if item == old else item for item in values]
        if next_values != values:
            setattr(row, column.key, next_values)
            changed = True
    if changed:
        await db.flush()


async def _rename_resource_types(db: AsyncSession, old: str, new: str) -> None:
    rows = (await db.execute(select(CareerRoadmap))).scalars().all()
    changed = False
    for row in rows:
        resources = row.resources
        if not isinstance(resources, list):
            continue
        next_resources = []
        row_changed = False
        for item in resources:
            if not isinstance(item, dict):
                next_resources.append(item)
                continue
            if str(item.get("type") or "") == old:
                next_resources.append({**item, "type": new})
                row_changed = True
            else:
                next_resources.append(item)
        if row_changed:
            row.resources = next_resources
            changed = True
    if changed:
        await db.flush()


async def update_option(
    db: AsyncSession, kind: str, option_id: str, body: RoadmapOptionUpdate
) -> RoadmapOptionOut:
    kind = _normalize_kind(kind)
    name = _clean_name(body.name)
    row = (
        await db.execute(
            select(CareerRoadmapOption).where(
                CareerRoadmapOption.id == option_id,
                CareerRoadmapOption.kind == kind,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Option not found")

    if name.lower() != row.name.lower():
        dup = (
            await db.execute(
                select(CareerRoadmapOption).where(
                    CareerRoadmapOption.kind == kind,
                    CareerRoadmapOption.name.ilike(name),
                    CareerRoadmapOption.id != option_id,
                )
            )
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(status_code=400, detail="Option name already exists")

        old_name = row.name
        row.name = name
        row.updated_at = datetime.utcnow()

        if kind == "category":
            await db.execute(
                update(CareerRoadmap)
                .where(CareerRoadmap.category == old_name)
                .values(category=name, updated_at=datetime.utcnow())
            )
        elif kind == "level":
            await db.execute(
                update(CareerRoadmap)
                .where(CareerRoadmap.level == old_name)
                .values(level=name, updated_at=datetime.utcnow())
            )
        elif kind == "industry":
            await _rename_in_json_list(db, CareerRoadmap.industries, old_name, name)
        elif kind == "skill_tag":
            await _rename_in_json_list(db, CareerRoadmap.skill_tags, old_name, name)
        elif kind == "resource_type":
            await _rename_resource_types(db, old_name, name)
    else:
        row.name = name
        row.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(row)
    return _to_out(row, await _usage_count(db, kind, row.name))


async def delete_option(db: AsyncSession, kind: str, option_id: str) -> None:
    kind = _normalize_kind(kind)
    row = (
        await db.execute(
            select(CareerRoadmapOption).where(
                CareerRoadmapOption.id == option_id,
                CareerRoadmapOption.kind == kind,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Option not found")

    usage = await _usage_count(db, kind, row.name)
    if usage > 0:
        raise HTTPException(
            status_code=400,
            detail=f'Cannot delete "{row.name}" — used by {usage} roadmap(s)',
        )

    await db.delete(row)
    await db.commit()
