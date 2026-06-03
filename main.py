from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pathlib import Path

from config import settings, get_cors_allow_origins, get_cors_origin_regex
from database import init_db, AsyncSessionLocal, engine
from seed_master import seed_master_data

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    # Create upload directories
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    # Initialize DB tables
    await init_db()
    
    # Run seeder
    async with AsyncSessionLocal() as session:
        await seed_master_data(session)

    # Super admin column + default account
    from sqlalchemy import text
    from routers.super_admin import ensure_super_admin_user

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_super_admin BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS welcome_email_status VARCHAR(20)"
            )
        )
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS welcome_email_error TEXT")
        )
    await ensure_super_admin_user()

    # OCR readiness status (for scanned resume parsing)
    from services.resume_parser import get_ocr_readiness

    ocr_status = get_ocr_readiness()
    if ocr_status.get("ready"):
        logger.info("[OCR] Ready: %s", ocr_status.get("details", "available"))
    else:
        logger.warning("[OCR] Not ready: %s", ocr_status.get("details", "missing configuration"))

    yield


app = FastAPI(
    title="JobMatch AI API",
    description="AI-powered bidirectional job matching platform",
    version="1.0.0",
    lifespan=lifespan,
)

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
from routers import auth, users, jobs, resumes, matches, applications, notifications, interviews, assessment, portfolio, analytics, resume_builder, onboarding, master, ai_interview, roadmap, external_candidate, master_data, ai_coach ,interview_scheduling, import_users, superadmin, super_admin # noqa

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(interviews.router, prefix="/api")
app.include_router(assessment.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(resume_builder.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(master.router, prefix="/api")
app.include_router(ai_interview.router, prefix="/api")
app.include_router(roadmap.router, prefix="/api")
app.include_router(ai_coach.router, prefix="/api")
app.include_router(external_candidate.router)
app.include_router(master_data.router)
app.include_router(interview_scheduling.router,prefix="/api")
app.include_router(import_users.router, prefix="/api")
app.include_router(super_admin.router, prefix="/api")
# ── Static Files (Uploads) ──────────────────────────────────────────────────
app.mount("/api/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ── WebSockets ──────────────────────────────────────────────────────────────
from fastapi import WebSocket, WebSocketDisconnect
from services.websocket_manager import manager

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive, we don't expect messages from client yet
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception:
        manager.disconnect(user_id, websocket)


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
