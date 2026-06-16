from datetime import datetime
import secrets
import string
import pyotp
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, BackgroundTasks

from config import settings
from models.user import User
from models.otp import OTPRecord
from schemas.auth import (
    RegisterRequest,
    VerifyOtpRequest,
    ResendOtpRequest,
    LoginRequest,
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
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_otp,
    otp_expiry,
)
from services.email_service import send_otp_email, send_welcome_email, send_password_email
from services.totp_service import totp_service


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


async def register(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> LoginResponse:
    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.phone == body.phone))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="An account with this email or phone already exists"
        )

    secret = totp_service.generate_secret()
    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        role=body.role,
        totp_secret=secret,
        is_verified=False,
        onboarding_complete=False,
        is_assessment_done=(body.role == "seeker"),
    )
    if body.password:
        user.hashed_password = hash_password(body.password)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    if user.email:
        otp_code = generate_otp()
        otp_record = OTPRecord(
            email=user.email, code=otp_code, expires_at=otp_expiry()
        )
        db.add(otp_record)
        await db.commit()
        background_tasks.add_task(send_otp_email, user.email, otp_code, user.first_name)
        print(user.email)
        print(otp_code)
        print(user.first_name)

    uri = totp_service.get_provisioning_uri(user.email or user.phone, secret)
    qr_base64 = totp_service.generate_qr_base64(uri)

    return LoginResponse(
        message="Registration initiated. Please check your email for the OTP and scan the QR code to set up TOTP.",
        requires_setup=True,
        qr_code_base64=f"data:image/png;base64,{qr_base64}",
        user=UserOut.model_validate(user),
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

    background_tasks.add_task(send_otp_email, body.email, otp_code, user.first_name)
    return {"message": "OTP resent successfully"}


async def login(
    body: LoginRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    referer: str | None = None,
) -> LoginResponse:
    try:
        result = await db.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=400, detail={"email": "No account found with this email"}
            )

        if not user.hashed_password:
            raise HTTPException(
                status_code=400,
                detail={"general": "Password not set. Contact your administrator."},
            )
        if getattr(user, "is_super_admin", False):
            expected_referer = f"{settings.FRONTEND_URL.rstrip('/')}/super-admin/login"
            if not referer or not referer.startswith(expected_referer):
                raise HTTPException(
                    status_code=400,
                    detail={"general": "Invalid login source for superadmin."},
                )

        if not verify_password(body.password, user.hashed_password):
            raise HTTPException(
                status_code=400, detail={"general": "Incorrect password"}
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
            return LoginResponse(
                message="TOTP verification required.",
                requires_totp=True,
                email=body.email,
            )

        token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})
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

    background_tasks.add_task(send_otp_email, body.email, otp_code, user.first_name)
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

    user.hashed_password = hash_password(body.new_password)
    await db.commit()

    token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
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
        await db.commit()
        return {"message": "TOTP disabled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


async def totp_verify(body: TOTPLoginRequest, db: AsyncSession) -> LoginResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP is not enabled for this user")

    if totp_service.verify_code(user.totp_secret, body.code):
        token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})
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
        hashed_password=hash_password(temp_password),
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

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: Optional[str] = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_exception

    new_access_token = create_access_token({"sub": user.id})
    new_refresh_token = create_refresh_token({"sub": user.id})
    return RefreshTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )
