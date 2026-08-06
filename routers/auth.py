from fastapi import APIRouter, Depends, BackgroundTasks, Request, File, UploadFile, Form, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.auth import (
    RegisterRequest, RegisterResponse, VerifyOtpRequest, ResendOtpRequest, LoginRequest,
    GoogleLoginRequest,
    UserOut, SendPhoneOtpRequest, VerifyPhoneOtpRequest, TOTPVerifyRequest,
    LoginResponse, TokenResponse, TOTPSetupResponse, TOTPStatusResponse,
    TOTPLoginRequest, CreateTestUserRequest, CreateTestUserResponse,
    ForgotPasswordRequest, ForgotPasswordResponse, ResetPasswordRequest,
    ResetPasswordResponse, VerifyResetOtpRequest, RefreshTokenRequest,
    RefreshTokenResponse,
)
from services.auth_service import get_current_user, require_verified
from controllers.auth_controller import (
    register as ctrl_register,
    verify_otp as ctrl_verify_otp,
    send_phone_otp as ctrl_send_phone_otp,
    verify_phone_otp as ctrl_verify_phone_otp,
    resend_otp as ctrl_resend_otp,
    login as ctrl_login,
    google_login as ctrl_google_login,
    verify_reset_otp as ctrl_verify_reset_otp,
    forgot_password as ctrl_forgot_password,
    reset_password as ctrl_reset_password,
    get_totp_status as ctrl_get_totp_status,
    totp_setup as ctrl_totp_setup,
    totp_enable as ctrl_totp_enable,
    totp_disable as ctrl_totp_disable,
    totp_verify as ctrl_totp_verify,
    create_test_user as ctrl_create_test_user,
    check_email as ctrl_check_email,
    refresh_token as ctrl_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


def _validation_error_detail(exc: ValidationError) -> dict:
    errors: dict[str, str] = {}
    for error in exc.errors():
        field = error["loc"][-1] if error["loc"] else "general"
        msg = error["msg"]
        if field == "email" and "valid email" in msg.lower():
            msg = "Please enter a valid email address"
        elif msg.startswith("Value error, "):
            msg = msg.removeprefix("Value error, ")
        key = field if field in {
            "email", "password", "full_name", "phone", "company_name",
            "work_status", "current_city", "role",
        } else "general"
        errors[key] = msg
    return errors or {"general": "Invalid input"}


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("seeker"),
    full_name: str | None = Form(None),
    phone: str | None = Form(None),
    company_name: str | None = Form(None),
    work_status: str | None = Form(None),
    current_city: str | None = Form(None),
    resume: UploadFile | None = File(None),
):
    try:
        body = RegisterRequest(
            full_name=full_name,
            email=email,
            password=password,
            role=role,
            phone=phone,
            company_name=company_name,
            work_status=work_status,
            current_city=current_city,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=_validation_error_detail(exc)) from exc
    return await ctrl_register(
        body,
        background_tasks,
        db,
        resume_file=resume,
        registration_ip=_client_ip(request),
    )


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_verify_otp(body, db)


@router.post("/phone/send-otp", response_model=LoginResponse)
async def send_phone_otp(body: SendPhoneOtpRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_send_phone_otp(body, db)


@router.post("/phone/verify-otp", response_model=TokenResponse)
async def verify_phone_otp(body: VerifyPhoneOtpRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_verify_phone_otp(body, db)


@router.post("/resend-otp")
async def resend_otp(body: ResendOtpRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    return await ctrl_resend_otp(body, background_tasks, db)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    referer = request.headers.get("referer")
    return await ctrl_login(body, background_tasks, db, referer)


@router.post("/google", response_model=LoginResponse)
async def google_login(body: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_google_login(body, db)


@router.post("/verify-reset-otp", response_model=LoginResponse)
async def verify_reset_otp(body: VerifyResetOtpRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_verify_reset_otp(body, db)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(body: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    return await ctrl_forgot_password(body, background_tasks, db)


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_reset_password(body, db)


@router.get("/totp/status")
async def get_totp_status(user: User = Depends(get_current_user)):
    return await ctrl_get_totp_status(user)


@router.post("/totp/setup")
async def totp_setup(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_totp_setup(user, db)


@router.post("/totp/enable")
async def totp_enable(body: TOTPVerifyRequest, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_totp_enable(body, user, db)


@router.post("/totp/disable")
async def totp_disable(body: TOTPVerifyRequest, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_totp_disable(body, user, db)


@router.post("/totp/verify", response_model=LoginResponse)
async def totp_verify(body: TOTPLoginRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_totp_verify(body, db)


@router.post("/create-test-user", response_model=CreateTestUserResponse, status_code=201)
async def create_test_user(body: CreateTestUserRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    return await ctrl_create_test_user(body, background_tasks, db)


@router.get("/check-email")
async def check_email(email: str, db: AsyncSession = Depends(get_db)):
    return await ctrl_check_email(email, db)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_refresh_token(body, db)
