from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from config import settings, get_cors_allow_origins, get_cors_origin_regex
from database import init_db, patch_email_admin_schema, patch_interview_application_schema, patch_dashboard_indexes, patch_support_bot_schema, patch_company_internships_schema, patch_teacher_role_schema, patch_training_portal_schema, patch_users_registration_schema, AsyncSessionLocal, engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="JobMatch AI API",
    description="AI-powered bidirectional job matching platform",
    version="1.0.0",
)


@app.on_event("startup")
async def ensure_db_tables():
    """Create any missing tables and patch email admin schema."""
    await init_db()
    await patch_email_admin_schema()
    await patch_interview_application_schema()
    await patch_dashboard_indexes()
    await patch_support_bot_schema()
    await patch_company_internships_schema()
    await patch_teacher_role_schema()
    await patch_training_portal_schema()
    await patch_users_registration_schema()
    from controllers.super_admin_controller import ensure_super_admin_user
    await ensure_super_admin_user()

# ── Custom Exception Handler for Validation Errors ──────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convert Pydantic validation errors to a cleaner format."""
    errors = {}
    for error in exc.errors():
        field = error['loc'][-1] if error['loc'] else 'general'
        msg = error['msg']
        
        # Map field names and provide friendly error messages
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

# ── CORS ────────────────────────────────────────────────────────────────────
# Explicit origins + optional regex (default regex allows private LAN IPs on any port, e.g. http://192.168.100.15:5174).
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allow_origins(),
    allow_origin_regex=get_cors_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
from routers import auth, users, jobs, resumes, matches, applications, notifications, interviews, assessment, portfolio, analytics, resume_builder, onboarding, master, ai_interview, roadmap, external_candidate, master_data, ai_coach ,interview_scheduling, import_users, superadmin, super_admin, super_admin_support, support, help_desk_bot, attendance, job_fair, email_admin, dashboard, company_internships, training_courses, training_portal_courses, training_portal_categories, training_portal_teachers, training_portal_internships, training_portal_runtime # noqa


API_PREFIX = ""

routers = [
    jobs.router,
    resumes.router,
    attendance.router,
    matches.router,
    applications.router,
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
    interview_scheduling.router,
    import_users.router,
    super_admin.router,
    super_admin_support.router,
    support.router,
    help_desk_bot.router,
    job_fair.router,
    email_admin.router,
    company_internships.router,
    training_courses.router,
    training_portal_courses.router,
    training_portal_categories.router,
    training_portal_teachers.router,
    training_portal_internships.router,
    training_portal_runtime.router,
]

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(external_candidate.router)
app.include_router(master_data.router)

for router in routers:
    app.include_router(router, prefix=API_PREFIX)

app.mount(
    f"{API_PREFIX}/uploads",
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="uploads",
)


# ── WebSockets ──────────────────────────────────────────────────────────────
from fastapi import WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from services.websocket_manager import manager


async def _validate_ws_token(token: str, user_id: str) -> bool:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return str(payload.get("sub")) == str(user_id)
    except JWTError:
        return False


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str = Query(...)):
    if not await _validate_ws_token(token, user_id):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception:
        manager.disconnect(user_id, websocket)


@app.websocket("/ws/helpdesk/{user_id}")
async def helpdesk_bot_websocket(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(...),
    mode: str = Query("text"),
):
    from routers.help_desk_bot import helpdesk_websocket_handler

    await helpdesk_websocket_handler(websocket, user_id, token, mode)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "JobMatch AI"}


@app.get("/health/ocr")
async def health_ocr():
    from services.resume_parser import get_ocr_readiness

    status = get_ocr_readiness()
    return {
        "status": "ok" if status.get("ready") else "degraded",
        "ocr": status,
    }
