from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.shared.models.auth_provider_settings import AuthProviderSettings, AuthSettingsHistory
from app.shared.services.oauth_providers import PROVIDERS, provider_configured

PUBLIC_ROLES = ("seeker", "provider")


async def seed_provider_settings(db: AsyncSession) -> None:
    for index, provider in enumerate(PROVIDERS, start=1):
        existing = await db.scalar(
            select(AuthProviderSettings).where(AuthProviderSettings.provider == provider)
        )
        if existing:
            if existing.display_order is None or int(existing.display_order or 0) <= 0:
                existing.display_order = index
            continue
        db.add(
            AuthProviderSettings(
                provider=provider,
                is_enabled=True,
                enabled_for_roles=["seeker", "provider"],
                enabled_on_register=True,
                enabled_on_login=True,
                display_order=index,
            )
        )
    await db.commit()


async def get_all_settings(db: AsyncSession) -> list[AuthProviderSettings]:
    result = await db.execute(
        select(AuthProviderSettings).order_by(AuthProviderSettings.display_order, AuthProviderSettings.provider)
    )
    rows = list(result.scalars().all())
    if len(rows) < len(PROVIDERS):
        await seed_provider_settings(db)
        result = await db.execute(
            select(AuthProviderSettings).order_by(AuthProviderSettings.display_order, AuthProviderSettings.provider)
        )
        rows = list(result.scalars().all())
    orders = [int(row.display_order or 1) for row in rows]
    if len(rows) > 1 and set(orders) == {1}:
        for row in rows:
            try:
                row.display_order = PROVIDERS.index(row.provider) + 1
            except ValueError:
                row.display_order = 99
        await db.commit()
        result = await db.execute(
            select(AuthProviderSettings).order_by(AuthProviderSettings.display_order, AuthProviderSettings.provider)
        )
        rows = list(result.scalars().all())
    return rows


def _serialize(row: AuthProviderSettings) -> dict:
    roles = [r for r in (row.enabled_for_roles or []) if r in PUBLIC_ROLES]
    env_ok = provider_configured(row.provider)
    return {
        "enabled": bool(row.is_enabled and env_ok),
        "configured": env_ok,
        "roles": roles,
        "onRegister": bool(row.enabled_on_register),
        "onLogin": bool(row.enabled_on_login),
        "sortOrder": int(row.display_order or 99),
    }


async def public_config(db: AsyncSession, last_login_method: Optional[str] = None) -> dict:
    rows = await get_all_settings(db)
    out = {row.provider: _serialize(row) for row in rows}
    for provider in PROVIDERS:
        out.setdefault(
            provider,
            {
                "enabled": False,
                "configured": provider_configured(provider),
                "roles": [],
                "onRegister": False,
                "onLogin": False,
                "sortOrder": 99,
            },
        )
    out["lastLoginMethod"] = last_login_method if last_login_method in PROVIDERS else None
    site_key = (settings.TURNSTILE_SITE_KEY or "").strip()
    secret = (settings.TURNSTILE_SECRET_KEY or "").strip()
    out["captcha"] = {
        "enabled": bool(site_key and secret),
        "siteKey": site_key or None,
    }
    return out


async def get_provider_settings(db: AsyncSession, provider: str) -> Optional[AuthProviderSettings]:
    return await db.scalar(select(AuthProviderSettings).where(AuthProviderSettings.provider == provider))


def provider_allowed_for_intent(row: Optional[AuthProviderSettings], intent: str, role: Optional[str]) -> tuple[bool, str]:
    if not row or not row.is_enabled:
        return False, "This login method is currently unavailable"
    if intent == "register" and not row.enabled_on_register:
        return False, "This login method is not available for registration"
    if intent == "login" and not row.enabled_on_login:
        return False, "This login method is currently unavailable"
    if role and role not in (row.enabled_for_roles or []):
        return False, "This login method isn't available for your account type. Please use email & password."
    return True, ""


async def update_provider_settings(
    db: AsyncSession,
    provider: str,
    *,
    is_enabled: bool,
    enabled_for_roles: list[str],
    enabled_on_register: bool,
    enabled_on_login: bool,
    display_order: Optional[int] = None,
    admin_id: str,
) -> AuthProviderSettings:
    row = await get_provider_settings(db, provider)
    if not row:
        row = AuthProviderSettings(provider=provider)
        db.add(row)
        await db.flush()

    roles = [r for r in enabled_for_roles if r in PUBLIC_ROLES]
    old_value = {
        "is_enabled": row.is_enabled,
        "enabled_for_roles": list(row.enabled_for_roles or []),
        "enabled_on_register": row.enabled_on_register,
        "enabled_on_login": row.enabled_on_login,
        "display_order": row.display_order,
    }
    row.is_enabled = is_enabled
    row.enabled_for_roles = roles
    row.enabled_on_register = enabled_on_register
    row.enabled_on_login = enabled_on_login
    if display_order is not None:
        row.display_order = max(1, int(display_order))
    row.updated_by = admin_id
    new_value = {
        "is_enabled": row.is_enabled,
        "enabled_for_roles": list(row.enabled_for_roles or []),
        "enabled_on_register": row.enabled_on_register,
        "enabled_on_login": row.enabled_on_login,
        "display_order": row.display_order,
    }
    db.add(
        AuthSettingsHistory(
            provider=provider,
            changed_by=admin_id,
            old_value=old_value,
            new_value=new_value,
        )
    )
    await db.commit()
    await db.refresh(row)
    return row
