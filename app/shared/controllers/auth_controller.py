from datetime import datetime, timezone
from typing import Optional
import secrets
import string
import pyotp
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, BackgroundTasks, Request

from app.core.config import settings
from app.core.token_blacklist import blacklist_jti, is_jti_blacklisted
from app.shared.models.user import User
from app.shared.models.otp import OTPRecord
from app.shared.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    VerifyOtpRequest,
    ResendOtpRequest,
    LoginRequest,
    GoogleLoginRequest,
    UserOut,
    OnboardingRequest,
    UpdateSettingsRequest,
    SendPhoneOtpRequest,
    VerifyPhoneOtpRequest,
    TOTPVerifyRequest,
    LoginResponse,
    TokenResponse,
    TOTPSetupResponse,
    TOTPStatusResponse,
    TOTPLoginRequest,
    CreateTestUserRequest,
    CreateTestUserResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    VerifyResetOtpRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from app.core.dependencies import (
    hash_password,
    verify_password,
    async_hash_password,
    async_verify_password,
    create_access_token,
    create_refresh_token,
    generate_otp,
    otp_expiry,
)
from app.shared.services.email_service import send_otp_email, send_password_email
from app.shared.services.celery_tasks import send_otp_email_task
from app.shared.services.totp_service import totp_service


def _generate_temp_password(length: int = 12) -> str:
    """Generate a random temporary password meeting validation requirements."""
    upper = secrets.choice(string.ascii_uppercase)
    lower = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    symbol = secrets.choice("!@#$%^&*")
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
    remaining = [secrets.choice(all_chars) for _ in range(length - 4)]
    password_list = [upper, lower, digit, symbol] + remaining
    secrets.SystemRandom().shuffle(password_list)
    return "".join(password_list)


def _split_full_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


async def register(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    resume_file=None,
    registration_ip: str | None = None,
) -> RegisterResponse:
    duplicate_filters = [User.email == body.email]
    if body.phone:
        duplicate_filters.append(User.phone == body.phone)
    existing = await db.execute(select(User).where(or_(*duplicate_filters)))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="An account with this email or phone already exists"
        )

    if body.role == "provider":
        first_name = body.company_name or ""
        last_name = ""
        company_name = body.company_name
        phone = None
        experience = None
        preferred_locations = None
    else:
        full_name = (body.full_name or f"{body.first_name or ''} {body.last_name or ''}").strip()
        first_name, last_name = _split_full_name(full_name)
        company_name = None
        phone = body.phone
        experience = body.work_status
        preferred_locations = [body.current_city] if body.work_status == "fresher" and body.current_city else None

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=body.email,
        phone=phone,
        role=body.role,
        company_name=company_name,
        experience=experience,
        preferred_locations=preferred_locations,
        registration_ip=registration_ip,
        is_verified=False,
        onboarding_complete=False,
        is_assessment_done=(body.role == "seeker"),
        hashed_password=await async_hash_password(body.password),
    )

    db.add(user)
    await db.flush()

    if resume_file and body.role == "seeker":
        try:
            from app.modules.jobs_portal.controllers.resumes_controller import upload_resume
            await upload_resume(background_tasks, resume_file, user, db)
        except Exception as e:
            print(f"[REGISTER] Optional resume upload failed: {e}")

    if user.email:
        otp_code = generate_otp()
        otp_record = OTPRecord(
            email=user.email, code=otp_code, expires_at=otp_expiry()
        )
        db.add(otp_record)

    await db.commit()
    await db.refresh(user)

    if user.email:
        send_otp_email_task.delay(user.email, otp_code, user.first_name or "there")

    return RegisterResponse(
        message="Registration successful. Please check your email for the verification code.",
        requires_otp=True,
    )


async def verify_otp(body: VerifyOtpRequest, db: AsyncSession) -> TokenResponse:
    now = datetime.utcnow()
    result = await db.execute(
        select(OTPRecord).where(
            and_(
                OTPRecord.email == body.email,
                OTPRecord.code == body.code,
                OTPRecord.used == False,  # noqa
                OTPRecord.expires_at > now,
            )
        )
    )
    otp_record = result.scalar_one_or_none()
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code")

    otp_record.used = True
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    await db.commit()

    token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    return TokenResponse(access_token=token, refresh_token=refresh_token, user=UserOut.model_validate(user))


async def send_phone_otp(body: SendPhoneOtpRequest, db: AsyncSession) -> LoginResponse:
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            phone=body.phone,
            is_verified=False,
            onboarding_complete=False,
            is_assessment_done=False,
        )
        db.add(user)
        await db.flush()

    if not user.totp_secret or user.is_first_login:
        if not user.totp_secret:
            secret = totp_service.generate_secret()
            user.totp_secret = secret
            await db.commit()
        else:
            secret = user.totp_secret

        uri = totp_service.get_provisioning_uri(user.phone, secret)
        qr_base64 = totp_service.generate_qr_base64(uri)

        return LoginResponse(
            message="Please scan the QR code to set up TOTP.",
            requires_setup=True,
            qr_code_base64=f"data:image/png;base64,{qr_base64}",
            requires_otp=not user.is_assessment_done,
        )
    else:
        return LoginResponse(
            message="Please enter the code from your authenticator app.",
            requires_totp=True,
        )


async def verify_phone_otp(body: VerifyPhoneOtpRequest, db: AsyncSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.phone == body.phone))
    print("The user result", result)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404, detail="User not found. Please initiate login first."
        )

    if not user.totp_secret:
        raise HTTPException(
            status_code=400, detail="TOTP not set up for this phone number."
        )

    print(f"[DEBUG] Phone: {body.phone}")
    print(f"[DEBUG] TOTP Secret: {user.totp_secret}")
    print(f"[DEBUG] Code entered: {body.code}")

    totp = pyotp.TOTP(user.totp_secret)
    print(f"[DEBUG] Current valid code (now): {totp.now()}")
    print(f"[DEBUG] Current valid code (now-30s): {totp.now()}")
    print(f"[DEBUG] Verify result: {totp_service.verify_code(user.totp_secret, body.code)}")

    if totp_service.verify_code(user.totp_secret, body.code):
        user.is_verified = True
        user.totp_enabled = True
        user.is_first_login = False
        await db.commit()
        token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})
        return TokenResponse(access_token=token, refresh_token=refresh_token, user=UserOut.model_validate(user))
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired TOTP code")


async def resend_otp(
    body: ResendOtpRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> dict:
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    otp_code = generate_otp()
    otp_record = OTPRecord(email=body.email, code=otp_code, expires_at=otp_expiry())
    db.add(otp_record)
    await db.commit()

    send_otp_email_task.delay(body.email, otp_code, user.first_name or "there")
    return {"message": "OTP resent successfully"}


async def login(
    body: LoginRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    referer: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> LoginResponse:
    try:
        identifier = (body.email or "").strip()
        result = await db.execute(select(User).where(func.lower(User.email) == identifier.lower()))
        user = result.scalar_one_or_none()

        # Fallback: training-portal teachers are issued a login username that may
        # differ from their account email. Resolve it to the linked user account.
        if not user:
            from app.modules.training_portal.models.training_portal_teacher import TrainingPortalTeacher

            teacher_res = await db.execute(
                select(TrainingPortalTeacher).where(
                    func.lower(TrainingPortalTeacher.login_username) == identifier.lower()
                )
            )
            teacher = teacher_res.scalar_one_or_none()
            if teacher and teacher.user_id:
                user_res = await db.execute(select(User).where(User.id == teacher.user_id))
                user = user_res.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=400, detail={"email": "No account found with this email or username"}
            )

        locked_until = getattr(user, "locked_until", None)
        if locked_until and locked_until > datetime.utcnow():
            minutes = max(1, int((locked_until - datetime.utcnow()).total_seconds() // 60))
            raise HTTPException(
                status_code=400,
                detail={"general": f"Too many attempts, try again in {minutes} minutes"},
            )

        from app.shared.services.captcha_service import captcha_configured, verify_turnstile

        attempts_so_far = int(getattr(user, "failed_login_attempts", 0) or 0)
        if attempts_so_far >= 3:
            if captcha_configured():
                ok = await verify_turnstile(body.captcha_token, ip_address)
                if not ok:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "general": "Please complete the CAPTCHA and try again.",
                            "requires_captcha": True,
                        },
                    )
            elif not (body.captcha_token or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail={
                        "general": "Please confirm you are not a robot and try again.",
                        "requires_captcha": True,
                    },
                )

        if not user.hashed_password:
            raise HTTPException(
                status_code=400,
                detail={"general": "Password not set. Contact your administrator."},
            )
        if getattr(user, "is_super_admin", False):
            expected_fe_referer = f"{settings.FRONTEND_URL.rstrip('/')}/super-admin/login"
            expected_tr_referer = f"{settings.TRAINING_URL.rstrip('/')}/login"
            is_valid_referer = False
            if referer:
                if referer.startswith(expected_fe_referer) or referer.startswith(expected_tr_referer) or referer.startswith(settings.TRAINING_URL.rstrip('/')):
                    is_valid_referer = True
            if not is_valid_referer:
                raise HTTPException(
                    status_code=400,
                    detail={"general": "Invalid login source for superadmin."},
                )

        if not await async_verify_password(body.password, user.hashed_password):
            attempts = int(getattr(user, "failed_login_attempts", 0) or 0) + 1
            user.failed_login_attempts = attempts
            status = "failed"
            if attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                status = "blocked"
            from app.shared.services.auth_session_service import log_login_attempt

            await log_login_attempt(
                db,
                user_id=user.id,
                method="password",
                status=status,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await db.commit()
            if status == "blocked":
                raise HTTPException(
                    status_code=400,
                    detail={"general": "Too many attempts, try again in 15 minutes"},
                )
            extra = {}
            if attempts >= 3:
                extra = {"requires_captcha": True}
            raise HTTPException(
                status_code=400,
                detail={"general": "Incorrect password", **extra},
            )

        if not user.is_verified:
            otp_code = generate_otp()
            otp_record = OTPRecord(
                email=body.email, code=otp_code, expires_at=otp_expiry()
            )
            db.add(otp_record)
            await db.commit()
            background_tasks.add_task(send_otp_email, body.email, otp_code, user.first_name)
            return LoginResponse(
                message="Email verification required. A new OTP has been sent to your email.",
                requires_otp=True,
                email=body.email,
            )

        if user.totp_enabled:
            from app.shared.services.token_crypto import create_pending_token
            pending = create_pending_token(
                {
                    "purpose": "2fa",
                    "sub": user.id,
                    "provider": "password",
                    "email": user.email,
                }
            )
            return LoginResponse(
                message="Enter the 6-digit authenticator code to continue.",
                requires_totp=True,
                pending_token=pending,
                email=user.email,
            )

        from app.shared.services.auth_session_service import (
            create_session_and_tokens,
            is_new_device_and_location,
        )

        suspicious = await is_new_device_and_location(
            db, user.id, ip_address=ip_address, user_agent=user_agent
        )
        token, refresh_token, _session = await create_session_and_tokens(
            db, user, method="password", ip_address=ip_address, user_agent=user_agent
        )
        await db.commit()
        await db.refresh(user)
        if suspicious and user.email:
            try:
                from app.shared.services.celery_tasks import send_notification_email_task
                send_notification_email_task.delay(
                    user.email,
                    "New login detected on Rojgar Mela",
                    "We noticed a new sign-in from a device/location we haven't seen before. "
                    "If this wasn't you, reset your password and review active sessions in Settings.",
                    user.first_name or "there",
                )
            except Exception:
                pass
        return LoginResponse(access_token=token, refresh_token=refresh_token, user=UserOut.model_validate(user))

    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=400,
            detail={"general": "An error occurred during login. Please try again."},
        )


async def verify_reset_otp(body: VerifyResetOtpRequest, db: AsyncSession) -> LoginResponse:
    now = datetime.utcnow()
    result = await db.execute(
        select(OTPRecord).where(
            and_(
                OTPRecord.email == body.email,
                OTPRecord.code == body.code,
                OTPRecord.used == False,
                OTPRecord.expires_at > now,
            )
        )
    )
    otp_record = result.scalar_one_or_none()
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    user = await db.scalar(select(User).where(User.email == body.email))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return LoginResponse(
        message="OTP verified. You can now reset your password.",
        email=body.email,
    )


async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> ForgotPasswordResponse:
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")

    otp_code = generate_otp()
    otp_record = OTPRecord(email=body.email, code=otp_code, expires_at=otp_expiry())
    db.add(otp_record)
    await db.commit()

    send_otp_email_task.delay(body.email, otp_code, user.first_name or "there")
    return ForgotPasswordResponse(message="Password reset OTP sent to your email", email=body.email)


async def reset_password(body: ResetPasswordRequest, db: AsyncSession) -> ResetPasswordResponse:
    now = datetime.utcnow()
    result = await db.execute(
        select(OTPRecord).where(
            and_(
                OTPRecord.email == body.email,
                OTPRecord.code == body.code,
                OTPRecord.used == False,
                OTPRecord.expires_at > now,
            )
        )
    )
    otp_record = result.scalar_one_or_none()
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    otp_record.used = True
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = await async_hash_password(body.new_password)
    from app.shared.services.auth_session_service import create_session_and_tokens, revoke_all_sessions

    await revoke_all_sessions(db, user.id)
    token, refresh_token, _session = await create_session_and_tokens(db, user, method="password")
    await db.commit()
    await db.refresh(user)
    return ResetPasswordResponse(
        message="Password reset successfully",
        access_token=token,
        refresh_token=refresh_token,
    )


async def get_totp_status(user: User) -> TOTPStatusResponse:
    return {"enabled": user.totp_enabled}


async def totp_setup(user: User, db: AsyncSession) -> dict:
    secret = totp_service.generate_secret()
    user.totp_secret = secret
    await db.commit()

    uri = totp_service.get_provisioning_uri(user.email, secret)
    qr_base64 = totp_service.generate_qr_base64(uri)

    return {
        "secret": secret,
        "qr_code_uri": uri,
        "qr_code_base64": f"data:image/png;base64,{qr_base64}",
    }


async def totp_enable(body: TOTPVerifyRequest, user: User, db: AsyncSession) -> dict:
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP setup not initiated")

    if totp_service.verify_code(user.totp_secret, body.code):
        user.totp_enabled = True
        from app.shared.services.auth_session_service import revoke_all_sessions
        await revoke_all_sessions(db, user.id)
        await db.commit()
        return {"message": "TOTP enabled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


async def totp_disable(body: TOTPVerifyRequest, user: User, db: AsyncSession) -> dict:
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP is not enabled")

    if totp_service.verify_code(user.totp_secret, body.code):
        user.totp_enabled = False
        user.totp_secret = None
        from app.shared.services.auth_session_service import revoke_all_sessions
        await revoke_all_sessions(db, user.id)
        await db.commit()
        return {"message": "TOTP disabled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


async def totp_verify(body: TOTPLoginRequest, db: AsyncSession) -> LoginResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not await async_verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP is not enabled for this user")

    if totp_service.verify_code(user.totp_secret, body.code):
        from app.shared.services.auth_session_service import create_session_and_tokens

        token, refresh_token, _session = await create_session_and_tokens(db, user, method="password")
        await db.commit()
        await db.refresh(user)
        return LoginResponse(access_token=token, refresh_token=refresh_token, user=UserOut.model_validate(user))
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


async def create_test_user(
    body: CreateTestUserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> CreateTestUserResponse:
    """
    Admin/Developer endpoint to create a test user with auto-generated password.
    The password is sent to the user's email and stored (hashed) in the database.
    TOTP setup will be required on first login.
    """
    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.phone == body.phone))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="An account with this email or phone already exists",
        )

    temp_password = _generate_temp_password()
    secret = totp_service.generate_secret()

    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        role=body.role,
        hashed_password=await async_hash_password(temp_password),
        totp_secret=secret,
        is_verified=True,
        totp_enabled=False,
        is_first_login=True,
        onboarding_complete=False,
        is_assessment_done=(body.role == "seeker"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    background_tasks.add_task(
        send_password_email, body.email, body.first_name, temp_password, body.role
    )

    return CreateTestUserResponse(
        message=f"Test user created. Password sent to {body.email}",
        user_id=user.id,
        email=body.email,
        role=body.role,
    )


async def check_email(email: str, db: AsyncSession) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    return {"exists": user is not None}


async def refresh_token(body: RefreshTokenRequest, db: AsyncSession) -> RefreshTokenResponse:
    from jose import JWTError, jwt
    from fastapi import status
    from typing import Optional
    from app.shared.services.auth_session_service import (
        get_session_by_refresh,
        is_session_valid,
        rotate_session,
    )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # jwt.decode validates the exp claim by default — expired tokens raise JWTError here.
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: Optional[str] = payload.get("type")
        jti: Optional[str] = payload.get("jti")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        # Token is expired, tampered, or otherwise invalid → 401
        raise credentials_exception

    if jti and await is_jti_blacklisted(jti):
        raise credentials_exception

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_exception

    # Issue a new short-lived access token only.
    # The refresh token is NOT rotated — it retains its original expiry.
    # Once it expires, jwt.decode above will raise JWTError → 401 → user must log in again.
    new_access_token = create_access_token({"sub": str(user.id)})

    return RefreshTokenResponse(
        access_token=new_access_token,
        refresh_token=body.refresh_token  # return the same refresh token unchanged
    )


async def logout(access_token: Optional[str], refresh_token_str: Optional[str] = None) -> dict:
    """Revoke the given access/refresh tokens by blacklisting their `jti` until natural expiry."""
    from jose import JWTError, jwt

    async def _revoke(token: Optional[str]) -> None:
        if not token:
            return
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": False},
            )
        except JWTError:
            return
        jti = payload.get("jti")
        exp = payload.get("exp")
        if not jti or not exp:
            return
        ttl = int(exp - datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            await blacklist_jti(jti, ttl)

    await _revoke(access_token)
    await _revoke(refresh_token_str)
    return {"message": "Logged out successfully"}


async def google_login(body: GoogleLoginRequest, db: AsyncSession, request: Request | None = None) -> LoginResponse:
    """Verify Google ID token and login or create a user."""
    client_id = settings.google_sign_in_client_id
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail="Google Sign-In is not configured on the server.",
        )

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            client_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Google credential") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not verify Google credential") from exc

    if idinfo.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=400, detail="Invalid Google token issuer")

    email = (idinfo.get("email") or "").strip().lower()
    if not email or not idinfo.get("email_verified", False):
        raise HTTPException(status_code=400, detail="Google account email is not verified")

    from app.shared.services.oauth_providers import ProviderProfile
    from app.shared.services.social_auth_service import RequestMeta, resolve_identity, to_login_response

    given = (idinfo.get("given_name") or "").strip() or None
    family = (idinfo.get("family_name") or "").strip() or None
    full_name = (idinfo.get("name") or "").strip() or None
    profile = ProviderProfile(
        provider="google",
        provider_user_id=str(idinfo.get("sub") or ""),
        email=email,
        email_verified=True,
        name=full_name,
        given_name=given,
        family_name=family,
        avatar_url=idinfo.get("picture"),
    )
    ip = None
    ua = None
    if request is not None:
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
        ua = request.headers.get("user-agent")
    result = await resolve_identity(
        db,
        profile,
        intent=body.intent,
        role=body.role if body.intent == "register" else None,
        meta=RequestMeta(ip_address=ip, user_agent=ua),
    )
    return to_login_response(result)
