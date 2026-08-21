from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.shared.models.oauth_account import OAuthAccount
from app.shared.models.user import User, UserRole
from app.shared.schemas.auth import LoginResponse, UserOut
from app.shared.services import auth_provider_settings_service as provider_settings
from app.shared.services.auth_session_service import (
    create_session_and_tokens,
    is_new_device_and_location,
    log_login_attempt,
)
from app.shared.services.oauth_providers import ProviderProfile
from app.shared.services.return_to import sanitize_return_to
from app.shared.services.token_crypto import create_pending_token, encrypt_secret

STAFF_ROLES = {UserRole.teacher, UserRole.superadmin}
PUBLIC_ROLES = {"seeker", "provider"}


@dataclass
class RequestMeta:
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class IdentityResult:
    kind: str  # login | complete_profile | confirm_email | totp | error | linked | set_password
    message: Optional[str] = None
    error: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[User] = None
    pending_token: Optional[str] = None
    need_role: bool = False
    need_phone: bool = False
    linked: bool = False
    email: Optional[str] = None

    def frontend_params(self) -> dict:
        params = {}
        if self.kind == "error":
            params["error"] = self.error or "Social login failed"
            return params
        if self.kind == "set_password":
            params["reason"] = "set_password"
            if self.email:
                params["email"] = self.email
            if self.error:
                params["message"] = self.error
            return params
        if self.kind == "complete_profile":
            params["token"] = self.pending_token or ""
            params["need_role"] = "1" if self.need_role else "0"
            params["need_phone"] = "1" if self.need_phone else "0"
            if self.email:
                params["email"] = self.email
            return params
        if self.kind == "confirm_email":
            params["token"] = self.pending_token or ""
            return params
        if self.kind == "totp":
            params["requires_totp"] = "1"
            params["token"] = self.pending_token or ""
            if self.email:
                params["email"] = self.email
            return params
        if self.access_token:
            params["access_token"] = self.access_token
        if self.refresh_token:
            params["refresh_token"] = self.refresh_token
        if self.linked:
            params["linked"] = "1"
        if self.message:
            params["message"] = self.message
        return params


def _is_staff(user: User) -> bool:
    if getattr(user, "is_super_admin", False):
        return True
    return user.role in STAFF_ROLES


def _split_name(profile: ProviderProfile) -> tuple[Optional[str], Optional[str]]:
    given = profile.given_name
    family = profile.family_name
    if given or family:
        return given, family
    parts = [p for p in (profile.name or "").split() if p]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _profile_pending_payload(profile: ProviderProfile, extra: Optional[dict] = None) -> dict:
    payload = {
        "provider": profile.provider,
        "provider_user_id": profile.provider_user_id,
        "email": profile.email,
        "email_verified": profile.email_verified,
        "name": profile.name,
        "given_name": profile.given_name,
        "family_name": profile.family_name,
        "avatar_url": profile.avatar_url,
    }
    if extra:
        payload.update(extra)
    return payload


async def _get_oauth_row(db: AsyncSession, provider: str, provider_user_id: str) -> Optional[OAuthAccount]:
    return await db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == str(provider_user_id),
        )
    )


async def _get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    if not email:
        return None
    return await db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def _notify_user(user: User, title: str, message: str) -> None:
    if not user.email:
        return
    try:
        from app.shared.services.celery_tasks import send_notification_email_task
        send_notification_email_task.delay(
            user.email, title, message, user.first_name or "there"
        )
    except Exception:
        pass


async def _oauth_rows_for_user(db: AsyncSession, user_id: str) -> list[OAuthAccount]:
    return list(
        (await db.execute(select(OAuthAccount).where(OAuthAccount.user_id == user_id))).scalars().all()
    )


async def _only_this_provider(db: AsyncSession, user: User, provider: str) -> bool:
    if user.hashed_password:
        return False
    rows = await _oauth_rows_for_user(db, user.id)
    if not rows:
        return True
    return all(row.provider == provider for row in rows)


async def _provider_block_result(
    db: AsyncSession,
    user: Optional[User],
    profile: ProviderProfile,
    settings_row,
    *,
    intent: str,
    role: Optional[str],
) -> Optional[IdentityResult]:
    allowed, reason = provider_settings.provider_allowed_for_intent(settings_row, intent, role)
    if allowed:
        return None
    if user and await _only_this_provider(db, user, profile.provider):
        return IdentityResult(
            kind="set_password",
            email=user.email,
            error="This login method has been disabled. Please set a password to continue.",
        )
    return IdentityResult(kind="error", error=reason)


async def _attach_oauth(db: AsyncSession, user: User, profile: ProviderProfile) -> OAuthAccount:
    existing = await _get_oauth_row(db, profile.provider, profile.provider_user_id)
    if existing:
        existing.user_id = user.id
        existing.provider_email = profile.email
        existing.access_token = encrypt_secret(profile.access_token)
        existing.refresh_token = encrypt_secret(profile.refresh_token)
        return existing
    row = OAuthAccount(
        user_id=user.id,
        provider=profile.provider,
        provider_user_id=str(profile.provider_user_id),
        provider_email=profile.email,
        access_token=encrypt_secret(profile.access_token),
        refresh_token=encrypt_secret(profile.refresh_token),
    )
    db.add(row)
    return row


async def _issue_login(
    db: AsyncSession,
    user: User,
    profile: ProviderProfile,
    meta: RequestMeta,
    *,
    linked: bool = False,
    message: Optional[str] = None,
) -> IdentityResult:
    if user.totp_enabled:
        pending = create_pending_token(
            {
                "purpose": "2fa",
                "sub": user.id,
                "provider": profile.provider,
                "email": user.email,
            }
        )
        return IdentityResult(
            kind="totp",
            pending_token=pending,
            email=user.email,
            message="Enter the 6-digit authenticator code to continue.",
        )
    suspicious = await is_new_device_and_location(
        db, user.id, ip_address=meta.ip_address, user_agent=meta.user_agent
    )
    access, refresh, _session = await create_session_and_tokens(
        db,
        user,
        method=profile.provider,
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    if profile.avatar_url and not user.profile_pic_url:
        user.profile_pic_url = profile.avatar_url
    if not user.is_verified and profile.email_verified:
        user.is_verified = True
    await db.commit()
    await db.refresh(user)
    if linked:
        _notify_user(
            user,
            "A social account was linked to your profile",
            f"A {profile.provider.title()} account was just linked to your Rojgar Mela profile. "
            "If this wasn't you, reset your password and review connected accounts in Settings.",
        )
    if suspicious:
        _notify_user(
            user,
            "New login detected on Rojgar Mela",
            f"We noticed a new sign-in with {profile.provider.title()} from a device/location we haven't seen before. "
            "If this wasn't you, secure your account from Settings → Active sessions.",
        )
    return IdentityResult(
        kind="login",
        access_token=access,
        refresh_token=refresh,
        user=user,
        linked=linked,
        message=message,
    )


async def _create_user_from_profile(
    db: AsyncSession,
    profile: ProviderProfile,
    role: str,
    *,
    phone: Optional[str] = None,
    location: Optional[str] = None,
) -> User:
    if role not in PUBLIC_ROLES:
        raise HTTPException(status_code=400, detail="Role must be seeker or provider")
    given, family = _split_name(profile)
    user = User(
        email=profile.email,
        first_name=given,
        last_name=family,
        profile_pic_url=profile.avatar_url,
        role=UserRole(role),
        phone=phone,
        preferred_locations=[location] if location else None,
        hashed_password=None,
        is_verified=bool(profile.email_verified or profile.provider in {"google", "linkedin"}),
        is_first_login=True,
        onboarding_complete=False,
        is_assessment_done=(role == "seeker"),
        registration_ip=None,
    )
    if role == "provider":
        user.company_name = (given or (profile.email or "My Company").split("@")[0]).strip() or "My Company"
    db.add(user)
    await db.flush()
    await _attach_oauth(db, user, profile)
    return user


async def resolve_identity(
    db: AsyncSession,
    profile: ProviderProfile,
    *,
    intent: str,
    role: Optional[str],
    meta: RequestMeta,
) -> IdentityResult:
    if not profile.provider_user_id:
        return IdentityResult(kind="error", error="Could not read your account from the provider.")

    settings_row = await provider_settings.get_provider_settings(db, profile.provider)

    oauth_row = await _get_oauth_row(db, profile.provider, profile.provider_user_id)
    if oauth_row:
        user = await db.scalar(select(User).where(User.id == oauth_row.user_id))
        if not user:
            return IdentityResult(kind="error", error="Linked account is no longer available.")
        if _is_staff(user):
            await log_login_attempt(
                db, user_id=user.id, method=profile.provider, status="blocked",
                ip_address=meta.ip_address, user_agent=meta.user_agent,
            )
            await db.commit()
            return IdentityResult(kind="error", error="This account requires email & password login.")
        user_role = getattr(user.role, "value", user.role)
        blocked = await _provider_block_result(
            db, user, profile, settings_row, intent="login", role=user_role
        )
        if blocked:
            return blocked
        oauth_row.provider_email = profile.email or oauth_row.provider_email
        oauth_row.access_token = encrypt_secret(profile.access_token)
        oauth_row.refresh_token = encrypt_secret(profile.refresh_token) or oauth_row.refresh_token
        return await _issue_login(db, user, profile, meta)

    if not profile.email:
        blocked = await _provider_block_result(
            db, None, profile, settings_row, intent=intent if intent in {"login", "register"} else "login", role=role
        )
        if blocked:
            return blocked
        pending = create_pending_token(_profile_pending_payload(profile, {"purpose": "confirm_email", "intent": intent, "role": role}))
        return IdentityResult(kind="confirm_email", pending_token=pending)

    existing = await _get_user_by_email(db, profile.email)
    if existing:
        if _is_staff(existing):
            await log_login_attempt(
                db, user_id=existing.id, method=profile.provider, status="blocked",
                ip_address=meta.ip_address, user_agent=meta.user_agent,
            )
            await db.commit()
            return IdentityResult(kind="error", error="This account requires email & password login.")
        user_role = getattr(existing.role, "value", existing.role)
        blocked = await _provider_block_result(
            db, existing, profile, settings_row, intent="login", role=user_role
        )
        if blocked:
            return blocked
        await _attach_oauth(db, existing, profile)
        role_label = "Job Seeker" if user_role == "seeker" else "Provider"
        msg = f"{profile.provider.title()} account linked to your existing profile."
        if intent == "register" and role and role != user_role:
            msg = f"Account already exists — logged in as {role_label}."
        return await _issue_login(db, existing, profile, meta, linked=True, message=msg)

    # Brand-new person
    if intent == "register":
        chosen = (role or "").strip().lower()
        if chosen not in PUBLIC_ROLES:
            return IdentityResult(kind="error", error="Please choose Job Seeker or Employer before continuing.")
        blocked = await _provider_block_result(
            db, None, profile, settings_row, intent="register", role=chosen
        )
        if blocked:
            return blocked
        user = await _create_user_from_profile(db, profile, chosen)
        if not user.phone:
            pending = create_pending_token(
                _profile_pending_payload(profile, {"purpose": "complete_profile", "sub": user.id, "need_role": False, "need_phone": True})
            )
            await db.commit()
            return IdentityResult(
                kind="complete_profile",
                pending_token=pending,
                need_role=False,
                need_phone=True,
                email=user.email,
                user=user,
            )
        return await _issue_login(db, user, profile, meta)

    # intent == login, no account
    blocked = await _provider_block_result(
        db, None, profile, settings_row, intent="login", role=None
    )
    if blocked:
        return blocked
    pending = create_pending_token(
        _profile_pending_payload(profile, {"purpose": "complete_profile", "intent": "login", "need_role": True, "need_phone": True})
    )
    return IdentityResult(
        kind="complete_profile",
        pending_token=pending,
        need_role=True,
        need_phone=True,
        email=profile.email,
        message="No account found with this email. Choose how you'd like to join.",
    )


async def complete_profile(
    db: AsyncSession,
    pending: dict,
    *,
    role: Optional[str],
    phone: Optional[str],
    location: Optional[str],
    meta: RequestMeta,
) -> IdentityResult:
    profile = ProviderProfile(
        provider=pending.get("provider"),
        provider_user_id=str(pending.get("provider_user_id") or ""),
        email=(pending.get("email") or None),
        email_verified=bool(pending.get("email_verified")),
        name=pending.get("name"),
        given_name=pending.get("given_name"),
        family_name=pending.get("family_name"),
        avatar_url=pending.get("avatar_url"),
    )
    user_id = pending.get("sub")
    need_role = bool(pending.get("need_role"))
    chosen = (role or "").strip().lower() if need_role else None

    if user_id:
        user = await db.scalar(select(User).where(User.id == user_id))
        if not user:
            return IdentityResult(kind="error", error="Your signup session expired. Please try again.")
        if pending.get("need_phone") and not phone:
            return IdentityResult(kind="error", error="Phone number is required.")
        if phone:
            user.phone = phone
        if location:
            locs = list(user.preferred_locations or [])
            if location not in locs:
                locs.append(location)
            user.preferred_locations = locs
        return await _issue_login(db, user, profile, meta)

    if chosen not in PUBLIC_ROLES:
        return IdentityResult(kind="error", error="Please choose Job Seeker or Employer.")
    if not phone:
        return IdentityResult(kind="error", error="Phone number is required.")
    if not profile.email:
        return IdentityResult(kind="error", error="Email is required to create an account.")

    settings_row = await provider_settings.get_provider_settings(db, profile.provider)
    allowed, reason = provider_settings.provider_allowed_for_intent(settings_row, "register", chosen)
    if not allowed:
        return IdentityResult(kind="error", error=reason)

    existing = await _get_user_by_email(db, profile.email)
    if existing:
        if _is_staff(existing):
            return IdentityResult(kind="error", error="This account requires email & password login.")
        await _attach_oauth(db, existing, profile)
        return await _issue_login(db, existing, profile, meta, linked=True, message="Account already exists — signed in.")

    user = await _create_user_from_profile(db, profile, chosen, phone=phone, location=location)
    return await _issue_login(db, user, profile, meta)


async def link_provider_to_user(
    db: AsyncSession,
    user: User,
    profile: ProviderProfile,
) -> IdentityResult:
    if _is_staff(user):
        return IdentityResult(kind="error", error="Staff accounts cannot link social logins.")
    existing = await _get_oauth_row(db, profile.provider, profile.provider_user_id)
    if existing and existing.user_id != user.id:
        return IdentityResult(
            kind="error",
            error=f"This {profile.provider.title()} account is already linked to another Rojgar Mela profile.",
        )
    same_provider = await db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user.id,
            OAuthAccount.provider == profile.provider,
        )
    )
    if same_provider and same_provider.provider_user_id != str(profile.provider_user_id):
        return IdentityResult(
            kind="error",
            error="This email is already associated with a different provider connection.",
        )
    await _attach_oauth(db, user, profile)
    await db.commit()
    return IdentityResult(kind="linked", message=f"{profile.provider.title()} connected.", user=user, linked=True)


async def unlink_provider(db: AsyncSession, user: User, provider: str) -> dict:
    rows = (await db.execute(select(OAuthAccount).where(OAuthAccount.user_id == user.id))).scalars().all()
    target = next((r for r in rows if r.provider == provider), None)
    if not target:
        raise HTTPException(status_code=404, detail="This provider is not connected.")
    has_password = bool(user.hashed_password)
    other_providers = [r for r in rows if r.provider != provider]
    if not has_password and not other_providers:
        raise HTTPException(
            status_code=400,
            detail="Set a password or connect another method before disconnecting.",
        )
    await db.delete(target)
    await db.commit()
    return {"message": f"{provider.title()} disconnected."}


def to_login_response(result: IdentityResult) -> LoginResponse:
    if result.kind == "error":
        raise HTTPException(status_code=400, detail=result.error or "Social login failed")
    if result.kind == "set_password":
        raise HTTPException(
            status_code=400,
            detail=result.error or "This login method has been disabled. Please set a password to continue.",
        )
    user_out = UserOut.model_validate(result.user) if result.user else None
    return LoginResponse(
        message=result.message,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        user=user_out,
        requires_totp=result.kind == "totp",
        requires_complete_profile=result.kind == "complete_profile",
        pending_token=result.pending_token,
        linked=result.linked,
        email=result.email,
    )


def frontend_redirect(result: IdentityResult, next_path: Optional[str] = None) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    params = result.frontend_params()
    safe_next = sanitize_return_to(next_path)
    if result.kind == "error":
        return f"{base}/login?{urlencode(params)}"
    if result.kind == "set_password":
        return f"{base}/reset-password?{urlencode(params)}"
    if result.kind == "complete_profile":
        if safe_next:
            params["next"] = safe_next
        return f"{base}/complete-profile?{urlencode(params)}"
    if result.kind == "confirm_email":
        if safe_next:
            params["next"] = safe_next
        return f"{base}/auth/confirm-email?{urlencode(params)}"
    if result.kind == "totp":
        if safe_next:
            params["next"] = safe_next
        return f"{base}/verify-totp?{urlencode(params)}"
    if result.kind == "linked" and not result.access_token:
        return f"{base}/settings?linked=1&{urlencode({'message': result.message or 'Connected'})}"
    if safe_next:
        params["next"] = safe_next
    return f"{base}/auth/callback?{urlencode(params)}"
