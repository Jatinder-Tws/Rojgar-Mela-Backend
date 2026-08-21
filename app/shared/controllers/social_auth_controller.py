from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_otp, otp_expiry
from app.shared.models.auth_session import AuthSession
from app.shared.models.otp import OTPRecord
from app.shared.models.user import User
from app.shared.schemas.auth import LoginResponse
from app.shared.schemas.social_auth import (
    CompleteProfileRequest,
    ConfirmEmailRequest,
    ConfirmEmailVerifyRequest,
    SocialTwoFactorRequest,
)
from app.shared.services import auth_provider_settings_service as provider_settings
from app.shared.services.auth_session_service import (
    create_session_and_tokens,
    revoke_all_sessions,
    revoke_session,
)
from app.shared.services.oauth_providers import (
    PROVIDERS,
    authorization_url,
    exchange_code,
    fetch_profile,
    provider_configured,
)
from app.shared.services.return_to import sanitize_return_to
from app.shared.services.social_auth_service import (
    IdentityResult,
    RequestMeta,
    complete_profile as complete_profile_flow,
    frontend_redirect,
    link_provider_to_user,
    resolve_identity,
    to_login_response,
)
from app.shared.services.token_crypto import (
    decode_oauth_state,
    decode_pending_token,
    generate_pkce_pair,
    sign_oauth_state,
)
from app.shared.services.totp_service import totp_service
from app.shared.services.celery_tasks import send_otp_email_task


LAST_LOGIN_COOKIE = "last_login_method"
COOKIE_MAX_AGE = 180 * 24 * 60 * 60


def _meta(request: Request) -> RequestMeta:
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    return RequestMeta(ip_address=ip, user_agent=request.headers.get("user-agent"))


def _error_redirect(message: str) -> RedirectResponse:
    url = f"{settings.FRONTEND_URL.rstrip('/')}/login?error={quote(message)}"
    return RedirectResponse(url=url, status_code=302)


def _apply_last_login_cookie(response: RedirectResponse, method: Optional[str]) -> RedirectResponse:
    if method in PROVIDERS or method == "password":
        response.set_cookie(
            LAST_LOGIN_COOKIE,
            method,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response


def _redirect_result(result: IdentityResult, next_path: Optional[str] = None) -> RedirectResponse:
    response = RedirectResponse(url=frontend_redirect(result, next_path), status_code=302)
    if result.kind == "login" and result.user is not None:
        method = getattr(result.user, "last_login_method", None)
        _apply_last_login_cookie(response, method)
    return response


async def start_oauth(
    provider: str,
    request: Request,
    *,
    intent: str = "login",
    role: Optional[str] = None,
    next_path: Optional[str] = None,
    link_user_id: Optional[str] = None,
) -> RedirectResponse:
    provider = (provider or "").strip().lower()
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown provider")
    if not provider_configured(provider):
        return _error_redirect("This login method is not configured yet.")

    intent = (intent or "login").strip().lower()
    if intent not in {"login", "register", "link"}:
        intent = "login"
    if role:
        role = "seeker" if role.strip().lower() == "candidate" else role.strip().lower()
        if role not in {"seeker", "provider"}:
            return _error_redirect("Invalid role for social signup.")

    next_path = sanitize_return_to(next_path)
    verifier, challenge = generate_pkce_pair()
    state = sign_oauth_state(
        {
            "provider": provider,
            "intent": intent,
            "role": role,
            "cv": verifier,
            "next": next_path,
            "user_id": link_user_id,
        }
    )
    return RedirectResponse(url=authorization_url(provider, state, challenge), status_code=302)


async def handle_callback(provider: str, request: Request, db: AsyncSession) -> RedirectResponse:
    provider = (provider or "").strip().lower()
    error = request.query_params.get("error")
    if error:
        return _error_redirect("Sign-in was cancelled. Try another method.")
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        return _error_redirect("Missing OAuth code. Please try again.")
    try:
        state_data = decode_oauth_state(state)
    except ValueError:
        return _error_redirect("Your sign-in session expired. Please try again.")
    if state_data.get("provider") != provider:
        return _error_redirect("Invalid OAuth state.")

    intent = state_data.get("intent") or "login"
    role = state_data.get("role")
    if intent == "link":
        settings_row = await provider_settings.get_provider_settings(db, provider)
        allowed, reason = provider_settings.provider_allowed_for_intent(settings_row, "login", None)
        if not allowed:
            return _error_redirect(reason)

    try:
        token_payload = await exchange_code(provider, code, state_data.get("cv") or "")
        profile = await fetch_profile(provider, token_payload)
    except Exception:
        return _error_redirect("Could not complete sign-in with this provider. Try another method.")

    meta = _meta(request)
    if intent == "link":
        user_id = state_data.get("user_id")
        if not user_id:
            return _error_redirect("Please sign in before linking an account.")
        user = await db.scalar(select(User).where(User.id == user_id))
        if not user:
            return _error_redirect("Account not found.")
        result = await link_provider_to_user(db, user, profile)
        return _redirect_result(result)

    result = await resolve_identity(db, profile, intent=intent, role=role, meta=meta)
    return _redirect_result(result, state_data.get("next"))


async def complete_profile(body: CompleteProfileRequest, request: Request, db: AsyncSession) -> LoginResponse:
    try:
        pending = decode_pending_token(body.token)
    except ValueError:
        raise HTTPException(status_code=400, detail="Your signup session expired. Please try again.")
    if pending.get("purpose") != "complete_profile":
        raise HTTPException(status_code=400, detail="Invalid token")
    result = await complete_profile_flow(
        db,
        pending,
        role=body.role,
        phone=body.phone,
        location=body.location,
        meta=_meta(request),
    )
    return to_login_response(result)


async def request_confirm_email(body: ConfirmEmailRequest, db: AsyncSession) -> dict:
    try:
        pending = decode_pending_token(body.token)
    except ValueError:
        raise HTTPException(status_code=400, detail="Your session expired. Please try again.")
    if pending.get("purpose") != "confirm_email":
        raise HTTPException(status_code=400, detail="Invalid token")
    email = str(body.email).strip().lower()
    otp_code = generate_otp()
    db.add(OTPRecord(email=email, code=otp_code, expires_at=otp_expiry()))
    await db.commit()
    send_otp_email_task.delay(email, otp_code)
    return {"message": "Verification code sent to your email", "email": email}


async def verify_confirm_email(
    body: ConfirmEmailVerifyRequest,
    request: Request,
    db: AsyncSession,
) -> LoginResponse:
    try:
        pending = decode_pending_token(body.token)
    except ValueError:
        raise HTTPException(status_code=400, detail="Your session expired. Please try again.")
    if pending.get("purpose") != "confirm_email":
        raise HTTPException(status_code=400, detail="Invalid token")

    now = datetime.utcnow()
    email = str(body.email).strip().lower()
    otp = await db.scalar(
        select(OTPRecord).where(
            OTPRecord.email == email,
            OTPRecord.code == body.code,
            OTPRecord.used.is_(False),
            OTPRecord.expires_at > now,
        )
    )
    if not otp:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    otp.used = True

    from app.shared.services.oauth_providers import ProviderProfile
    from app.shared.services.social_auth_service import to_login_response

    profile = ProviderProfile(
        provider=pending.get("provider"),
        provider_user_id=str(pending.get("provider_user_id") or ""),
        email=email,
        email_verified=True,
        name=pending.get("name"),
        given_name=pending.get("given_name"),
        family_name=pending.get("family_name"),
        avatar_url=pending.get("avatar_url"),
    )
    result = await resolve_identity(
        db,
        profile,
        intent=pending.get("intent") or "login",
        role=pending.get("role"),
        meta=_meta(request),
    )
    return to_login_response(result)


async def challenge_2fa(body: SocialTwoFactorRequest, request: Request, db: AsyncSession) -> LoginResponse:
    try:
        pending = decode_pending_token(body.token)
    except ValueError:
        raise HTTPException(status_code=400, detail="Your session expired. Please log in again.")
    if pending.get("purpose") != "2fa":
        raise HTTPException(status_code=400, detail="Invalid token")
    user = await db.scalar(select(User).where(User.id == pending.get("sub")))
    if not user or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled.")
    if not totp_service.verify_code(user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")
    meta = _meta(request)
    access, refresh, _session = await create_session_and_tokens(
        db,
        user,
        method=pending.get("provider") or "password",
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    await db.commit()
    await db.refresh(user)
    return LoginResponse(access_token=access, refresh_token=refresh, user=UserOut.model_validate(user))


async def list_linked_accounts(user: User, db: AsyncSession) -> list[dict]:
    from app.shared.models.oauth_account import OAuthAccount

    rows = (await db.execute(select(OAuthAccount).where(OAuthAccount.user_id == user.id))).scalars().all()
    return [
        {
            "provider": row.provider,
            "provider_email": row.provider_email,
            "connected_at": row.connected_at,
        }
        for row in rows
    ]


async def start_link(provider: str, user: User, request: Request) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown provider")
    if not provider_configured(provider):
        raise HTTPException(status_code=400, detail="This login method is not configured yet.")
    verifier, challenge = generate_pkce_pair()
    state = sign_oauth_state(
        {
            "provider": provider,
            "intent": "link",
            "cv": verifier,
            "user_id": user.id,
        }
    )
    return {"authorize_url": authorization_url(provider, state, challenge)}


async def list_sessions(user: User, current_sid: Optional[str], db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(AuthSession)
            .where(AuthSession.user_id == user.id, AuthSession.is_revoked.is_(False))
            .order_by(AuthSession.last_active_at.desc())
        )
    ).scalars().all()
    now = datetime.utcnow()
    out = []
    for row in rows:
        if row.expires_at <= now:
            continue
        out.append(
            {
                "id": row.id,
                "login_method": row.login_method,
                "device_label": row.device_label,
                "ip_address": row.ip_address,
                "last_active_at": row.last_active_at,
                "created_at": row.created_at,
                "is_current": bool(current_sid and current_sid == row.id),
            }
        )
    return out


async def delete_session(user: User, session_id: str, db: AsyncSession) -> dict:
    row = await db.scalar(
        select(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == user.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    await revoke_session(db, row)
    await db.commit()
    return {"message": "Session revoked"}


async def logout_current(user: User, current_sid: Optional[str], db: AsyncSession) -> dict:
    if current_sid:
        row = await db.scalar(
            select(AuthSession).where(AuthSession.id == current_sid, AuthSession.user_id == user.id)
        )
        if row:
            await revoke_session(db, row)
            await db.commit()
    return {"message": "Logged out"}


async def logout_all(user: User, db: AsyncSession, except_id: Optional[str] = None) -> dict:
    await revoke_all_sessions(db, user.id, except_id=except_id)
    await db.commit()
    return {"message": "Other sessions revoked" if except_id else "All sessions revoked"}
