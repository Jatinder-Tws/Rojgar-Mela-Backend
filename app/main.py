from contextlib import asynccontextmanager
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from app.core.config import settings, get_upload_dir, get_cors_allow_origins, get_cors_origin_regex
from app.core.dependencies import require_authenticated
from app.shared.models.user import User
from app.core.database import (
    init_db,
    AsyncSessionLocal,
)

logger = logging.getLogger(__name__)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await init_db()

#     from app.modules.super_admin.controllers.super_admin_controller import ensure_super_admin_user
#     await ensure_super_admin_user()

#     async with AsyncSessionLocal() as session:
#         from app.shared.services.auth_provider_settings_service import seed_provider_settings
#         await seed_provider_settings(session)

#     yield


app = FastAPI(
    title="RojgarMela Modular API",
    description="AI-powered Job Match & Training Portal Backend",
    version="2.0.0",
    # lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = {}
    for error in exc.errors():
        field = error['loc'][-1] if error['loc'] else 'general'
        msg = error['msg']
        if field == 'email':
            if 'valid email' in msg.lower():
                errors['email'] = 'Please enter a valid email address'
            else:
                errors['email'] = msg
        elif field == 'password':
            errors['password'] = msg
        else:
            errors['general'] = msg

    return JSONResponse(
        status_code=400,
        content={"detail": errors if errors else {"general": "Invalid input"}},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allow_origins(),
    allow_origin_regex=get_cors_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Import and Register All Routers ─────────────────────────────────────────
from app.shared.routers import (
    auth, master_data, notifications, users
)
from app.modules.jobs_portal.routers import (
    ai_coach, ai_coach_live_ws, ai_interview, analytics, applications, assessment, career_enquiry,
    company_internships, dashboard, external_candidate, interviews, interview_scheduling,
    jobs, job_fair, master, matches, onboarding, portfolio, resumes, resume_builder,
    roadmap, saved_jobs
)
from app.modules.training_portal.routers import (
    google_calendar, training_courses, training_portal_categories,
    training_portal_courses, training_portal_internships, training_portal_runtime,
    training_portal_teachers
)
# Registers ORM event listeners (import for side effects) so every
# TrainingPortalCandidateNotification insert is pushed live over SSE.
from app.modules.training_portal.services import training_portal_notification_stream  # noqa: F401
from app.modules.super_admin.routers import (
    attendance, email_admin, help_desk_bot, import_users, superadmin,
    super_admin, super_admin_support, support
)

API_PREFIX = ""

routers = [
    jobs.router,
    resumes.router,
    attendance.router,
    matches.router,
    applications.router,
    saved_jobs.router,
    notifications.router,
    interviews.router,
    assessment.router,
    portfolio.router,
    analytics.router,
    dashboard.router,
    resume_builder.router,
    onboarding.router,
    master.router,
    ai_interview.router,
    roadmap.router,
    ai_coach.router,
    ai_coach_live_ws.router,
    interview_scheduling.router,
    import_users.router,
    super_admin.router,
    super_admin_support.router,
    support.router,
    help_desk_bot.router,
    career_enquiry.public_router,
    career_enquiry.admin_router,
    job_fair.router,
    email_admin.router,
    company_internships.router,
    training_courses.router,
    training_portal_courses.router,
    training_portal_categories.router,
    training_portal_teachers.router,
    training_portal_internships.router,
    training_portal_runtime.router,
    google_calendar.router,
]

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(external_candidate.router)
app.include_router(master_data.router)

for router in routers:
    app.include_router(router, prefix=API_PREFIX)

app.mount(
    f"{API_PREFIX}/uploads",
    StaticFiles(directory=str(get_upload_dir())),
    name="uploads",
)







@app.get("/api/notifications/stream/{user_id}")
async def api_stream_notifications_alias(user_id: str, request: Request):
    from app.core.dependencies import require_authenticated, get_current_user
    from app.shared.routers.notifications import stream_notifications
    from fastapi.security import HTTPBearer
    bearer = HTTPBearer()
    creds = await bearer(request)
    db = await AsyncSessionLocal().__aenter__()
    try:
        user = await require_authenticated(user=await get_current_user(creds, db))
        return await stream_notifications(user_id=user_id, current_user=user)
    finally:
        await db.close()


@app.get("/health")
async def health():
    db_ok = False
    redis_ok = False
    details = {}

    # 1. Check PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
            details["postgres"] = "connected"
    except Exception as e:
        details["postgres"] = f"error: {str(e)}"

    # 2. Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        if await r.ping():
            redis_ok = True
            details["redis"] = "connected"
        await r.aclose()
    except Exception as e:
        details["redis"] = f"error: {str(e)}"

    status_str = "ok" if (db_ok and redis_ok) else "degraded"
    status_code = 200 if (db_ok and redis_ok) else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_str,
            "service": "RojgarMela Modular API",
            "details": details,
        },
    )


@app.get("/health/ocr")
async def health_ocr():
    from app.shared.services.resume_parser import get_ocr_readiness

    status = get_ocr_readiness()
    return {
        "status": "ok" if status.get("ready") else "degraded",
        "ocr": status,
    }
