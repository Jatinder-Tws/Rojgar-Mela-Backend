from typing import Literal

from fastapi import APIRouter, Depends, BackgroundTasks, Request, Response, File, UploadFile, Form, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.shared.schemas.auth import (
    RegisterRequest, RegisterResponse, VerifyOtpRequest, ResendOtpRequest, LoginRequest,
    GoogleLoginRequest,
    UserOut, SendPhoneOtpRequest, VerifyPhoneOtpRequest, TOTPVerifyRequest,
    LoginResponse, TokenResponse, TOTPSetupResponse, TOTPStatusResponse,
    TOTPLoginRequest, CreateTestUserRequest, CreateTestUserResponse,
    ForgotPasswordRequest, ForgotPasswordResponse, ResetPasswordRequest,
    ResetPasswordResponse, VerifyResetOtpRequest, RefreshTokenRequest,
    RefreshTokenResponse, LogoutRequest,
)
from app.shared.schemas.social_auth import (
    CompleteProfileRequest,
    ConfirmEmailRequest,
    ConfirmEmailVerifyRequest,
    SocialTwoFactorRequest,
)
from app.core.dependencies import (
    get_current_session_id,
    get_current_user,
    require_verified,
    bearer_scheme,
)
from app.core.rate_limit import rate_limit
from app.shared.controllers.auth_controller import (
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
    logout as ctrl_logout,
)
from app.shared.controllers import social_auth_controller as social_ctrl
from app.shared.services import auth_provider_settings_service as provider_settings

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
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    referer = request.headers.get("referer")
    result = await ctrl_login(
        body,
        background_tasks,
        db,
        referer,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    if result.access_token:
        response.set_cookie(
            social_ctrl.LAST_LOGIN_COOKIE,
            "password",
            max_age=social_ctrl.COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return result


@router.post("/google", response_model=LoginResponse)
async def google_login(body: GoogleLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    return await ctrl_google_login(body, db, request)


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
async def totp_setup(
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    return await ctrl_totp_setup(user, db)


@router.post("/totp/enable")
async def totp_enable(
    body: TOTPVerifyRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    return await ctrl_totp_enable(body, user, db)


@router.post("/totp/disable")
async def totp_disable(
    body: TOTPVerifyRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    return await ctrl_totp_disable(body, user, db)


@router.post("/totp/verify", response_model=LoginResponse)
async def totp_verify(
    body: TOTPLoginRequest,
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    return await ctrl_totp_verify(body, db)


@router.post("/2fa/setup")
async def twofa_setup(
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    return await ctrl_totp_setup(user, db)


@router.post("/2fa/verify")
async def twofa_verify(
    body: TOTPVerifyRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    return await ctrl_totp_enable(body, user, db)


@router.post("/2fa/disable")
async def twofa_disable(
    body: TOTPVerifyRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    return await ctrl_totp_disable(body, user, db)


@router.post("/create-test-user", response_model=CreateTestUserResponse, status_code=201)
async def create_test_user(body: CreateTestUserRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    return await ctrl_create_test_user(body, background_tasks, db)


@router.get("/check-email")
async def check_email(email: str, db: AsyncSession = Depends(get_db)):
    return await ctrl_check_email(email, db)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_refresh_token(body, db)


@router.get("/config")
async def auth_config(request: Request, db: AsyncSession = Depends(get_db)):
    last_method = request.cookies.get(social_ctrl.LAST_LOGIN_COOKIE)
    return await provider_settings.public_config(db, last_method)


@router.get("/{provider}")
async def start_social_login(
    provider: Literal["google", "github", "linkedin"],
    request: Request,
    intent: str = "login",
    role: str | None = None,
    next: str | None = None,
):
    return await social_ctrl.start_oauth(provider, request, intent=intent, role=role, next_path=next)


@router.get("/{provider}/callback")
async def social_callback(
    provider: Literal["google", "github", "linkedin"],
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    return await social_ctrl.handle_callback(provider, request, db)


@router.post("/complete-profile", response_model=LoginResponse)
async def complete_profile(body: CompleteProfileRequest, request: Request, db: AsyncSession = Depends(get_db)):
    return await social_ctrl.complete_profile(body, request, db)


@router.post("/confirm-email")
async def confirm_email(body: ConfirmEmailRequest, db: AsyncSession = Depends(get_db)):
    return await social_ctrl.request_confirm_email(body, db)


@router.post("/confirm-email/verify", response_model=LoginResponse)
async def confirm_email_verify(body: ConfirmEmailVerifyRequest, request: Request, db: AsyncSession = Depends(get_db)):
    return await social_ctrl.verify_confirm_email(body, request, db)


@router.post("/2fa/challenge", response_model=LoginResponse)
async def social_2fa_challenge(
    body: SocialTwoFactorRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(rate_limit(20, 60)),
):
    return await social_ctrl.challenge_2fa(body, request, db)


@router.get("/linked-accounts")
async def linked_accounts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await social_ctrl.list_linked_accounts(user, db)


@router.post("/link/{provider}")
async def link_provider(provider: str, request: Request, user: User = Depends(get_current_user)):
    return await social_ctrl.start_link(provider, user, request)


@router.delete("/unlink/{provider}")
async def unlink_provider(provider: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.shared.services.social_auth_service import unlink_provider as unlink_flow
    return await unlink_flow(db, user, provider)


@router.post("/logout")
async def logout(
    body: LogoutRequest | None = None,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
    sid: str | None = Depends(get_current_session_id),
    db: AsyncSession = Depends(get_db),
):
    await social_ctrl.logout_current(user, sid, db)
    return await ctrl_logout(credentials.credentials, body.refresh_token if body else None)


@router.post("/logout-all")
async def logout_all(
    user: User = Depends(get_current_user),
    sid: str | None = Depends(get_current_session_id),
    db: AsyncSession = Depends(get_db),
):
    return await social_ctrl.logout_all(user, db, except_id=sid)


@router.get("/sessions")
async def list_sessions(
    user: User = Depends(get_current_user),
    sid: str | None = Depends(get_current_session_id),
    db: AsyncSession = Depends(get_db),
):
    return await social_ctrl.list_sessions(user, sid, db)


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await social_ctrl.delete_session(user, session_id, db)
