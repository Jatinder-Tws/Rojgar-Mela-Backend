from datetime import datetime
from typing import Union
import pyotp
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from database import get_db
from models.user import User
from models.otp import OTPRecord
from schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    VerifyOtpRequest,
    ResendOtpRequest,
    LoginRequest,
    TokenResponse,
    UserOut,
    OnboardingRequest,
    UpdateSettingsRequest,
    UnverifiedLoginResponse,
    SendPhoneOtpRequest,
    VerifyPhoneOtpRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    LoginResponse,
    TOTPStatusResponse,
    TOTPLoginRequest,
    CreateTestUserRequest,
    CreateTestUserResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    VerifyResetOtpRequest
)


from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    generate_otp,
    otp_expiry,
    get_current_user,
    require_verified,
)
from services.email_service import send_otp_email, send_welcome_email, send_password_email
from services.totp_service import totp_service


router = APIRouter(prefix="/auth", tags=["auth"])


def _generate_temp_password(length: int = 12) -> str:
    """Generate a random temporary password meeting validation requirements."""
    import secrets
    import string

    # Ensure at least one of each required character type
    upper = secrets.choice(string.ascii_uppercase)
    lower = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    symbol = secrets.choice("!@#$%^&*")

    # Fill the rest with random characters from all allowed types
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
    remaining = [secrets.choice(all_chars) for _ in range(length - 4)]

    # Shuffle and join
    password_list = [upper, lower, digit, symbol] + remaining
    secrets.SystemRandom().shuffle(password_list)
    return "".join(password_list)


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate email or phone
    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.phone == body.phone))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="An account with this email or phone already exists"
        )

    # Generate TOTP secret
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
        is_assessment_done=(body.role == "seeker"),  # Assuming and marking if seeker
    )
    if body.password:
        user.hashed_password = hash_password(body.password)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate and send OTP for email verification
    if user.email:
        otp_code = generate_otp()
        otp_record = OTPRecord(
            email=user.email, code=otp_code, expires_at=otp_expiry()
        )
        db.add(otp_record)
        await db.commit()
        
        # Send OTP email asynchronously
        background_tasks.add_task(
            send_otp_email, user.email, otp_code, user.first_name
        )
        # print(sent_otp_email)
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


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()

    # Find valid OTP
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

    # Mark used
    otp_record.used = True

    # Verify user
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    await db.commit()

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/send-phone-otp")
async def send_phone_otp(body: SendPhoneOtpRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()

    is_new_user = False
    if not user:
        is_new_user = True
        # Create a stub user to store the TOTP secret
        user = User(
            phone=body.phone,
            is_verified=False,
            onboarding_complete=False,
            is_assessment_done=False,
        )
        db.add(user)
        await db.flush()

    if not user.totp_secret or user.is_first_login:
        # First time or forced first login: generate/show QR code
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
        # Subsequent times: just signal that TOTP is needed
        return LoginResponse(
            message="Please enter the code from your authenticator app.",
            requires_totp=True,
        )


@router.post("/verify-phone-otp", response_model=TokenResponse)
async def verify_phone_otp(
    body: VerifyPhoneOtpRequest, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.phone == body.phone))
    print("The user result",result)
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

    # Debug: show what codes would be valid right now
    totp = pyotp.TOTP(user.totp_secret)
    print(f"[DEBUG] Current valid code (now): {totp.now()}")
    print(f"[DEBUG] Current valid code (now-30s): {totp.now()}")
    print(
        f"[DEBUG] Verify result: {totp_service.verify_code(user.totp_secret, body.code)}"
    )

    if totp_service.verify_code(user.totp_secret, body.code):
        user.is_verified = True
        user.totp_enabled = (
            True  # Mark enabled once first successful verification happens
        )
        user.is_first_login = False  # First login successfully completed
        await db.commit()

        token = create_access_token({"sub": user.id})
        return TokenResponse(access_token=token, user=UserOut.model_validate(user))
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired TOTP code")


@router.post("/resend-otp")
async def resend_otp(
    body: ResendOtpRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
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


@router.post("/login")
async def login(
    body: LoginRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

        # Check if user exists
        if not user:
            raise HTTPException(
                status_code=400, detail={"email": "No account found with this email"}
            )

        # Check password
        if not user.hashed_password:
            raise HTTPException(
                status_code=400,
                detail={"general": "Password not set. Contact your administrator."},
            )
        if not verify_password(body.password, user.hashed_password):
            raise HTTPException(
                status_code=400, detail={"general": "Incorrect password"}
            )

        # If email not verified, send OTP automatically
        if not user.is_verified:
            otp_code = generate_otp()
            otp_record = OTPRecord(
                email=body.email, code=otp_code, expires_at=otp_expiry()
            )
            db.add(otp_record)
            await db.commit()

            # Send OTP email asynchronously
            background_tasks.add_task(
                send_otp_email, body.email, otp_code, user.first_name
            )

            return LoginResponse(
                message="Email verification required. A new OTP has been sent to your email.",
                requires_otp=True,
                email=body.email,
            )

        # Check if TOTP is enabled
        if user.totp_enabled:
            return LoginResponse(
                message="TOTP verification required.",
                requires_totp=True,
                email=body.email,
            )

        token = create_access_token({"sub": user.id})
        return LoginResponse(access_token=token, user=UserOut.model_validate(user))

    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=400,
            detail={"general": "An error occurred during login. Please try again."},
        )


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


# ── Forgot Password Endpoints ───────────────────────────────────────────────────

@router.post("/verify-reset-otp", response_model=LoginResponse)
async def verify_reset_otp(body: VerifyResetOtpRequest, db: AsyncSession = Depends(get_db)):
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


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")

    otp_code = generate_otp()
    otp_record = OTPRecord(email=body.email, code=otp_code, expires_at=otp_expiry())
    db.add(otp_record)
    await db.commit()

    background_tasks.add_task(send_otp_email, body.email, otp_code, user.first_name)
    return ForgotPasswordResponse(message="Password reset OTP sent to your email", email=body.email)


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
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
    return ResetPasswordResponse(
        message="Password reset successfully",
        access_token=token,
    )


# ── TOTP Endpoints ─────────────────────────────────────────────────────────


@router.get("/totp/status", response_model=TOTPStatusResponse)
async def get_totp_status(user: User = Depends(get_current_user)):
    return {"enabled": user.totp_enabled}


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def totp_setup(
    user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)
):
    # Generate secret if not exists or if they want to re-setup
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


@router.post("/totp/enable")
async def totp_enable(
    body: TOTPVerifyRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP setup not initiated")

    if totp_service.verify_code(user.totp_secret, body.code):
        user.totp_enabled = True
        await db.commit()
        return {"message": "TOTP enabled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


@router.post("/totp/disable")
async def totp_disable(
    body: TOTPVerifyRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP is not enabled")

    if totp_service.verify_code(user.totp_secret, body.code):
        user.totp_enabled = False
        user.totp_secret = None
        await db.commit()
        return {"message": "TOTP disabled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


@router.post("/totp/verify", response_model=LoginResponse)
async def totp_verify(body: TOTPLoginRequest, db: AsyncSession = Depends(get_db)):
    # Verify password again for security or just assume they are in middle of login
    # For simplicity, we check user by email and verify password then TOTP
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
        return LoginResponse(access_token=token, user=UserOut.model_validate(user))
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")





# ── Admin: Create Test User ─────────────────────────────────────────────


@router.post("/create-test-user", response_model=CreateTestUserResponse, status_code=201)
async def create_test_user(
    body: CreateTestUserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Admin/Developer endpoint to create a test user with auto-generated password.
    The password is sent to the user's email and stored (hashed) in the database.
    TOTP setup will be required on first login.
    """
    # Check if email or phone already exists
    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.phone == body.phone))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="An account with this email or phone already exists",
        )

    # Generate temporary password
    temp_password = _generate_temp_password()

    # Generate TOTP secret
    secret = totp_service.generate_secret()

    # Create user
    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        role=body.role,
        hashed_password=hash_password(temp_password),
        totp_secret=secret,
        is_verified=True,  # Skip OTP verification for admin-created users
        totp_enabled=False,  # Will be set up on first login
        is_first_login=True,
        onboarding_complete=False,
        is_assessment_done=(body.role == "seeker"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send password email in background
    background_tasks.add_task(
        send_password_email, body.email, body.first_name, temp_password, body.role
    )

    return CreateTestUserResponse(
        message=f"Test user created. Password sent to {body.email}",
        user_id=user.id,
        email=body.email,
        role=body.role,
    )
