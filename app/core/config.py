from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://jobmatch:secret@localhost:5432/jobmatch_db"
    )

    # JWT
    SECRET_KEY: str = "change-this-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10  # 10 minute
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o"

    # Google Gemini
    GOOGLE_API_KEY: str = ""
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_CHAT_MODEL: str = "gemini-2.5-flash"
    GEMINI_LIVE_MODEL: str = "gemini-2.5-flash-native-audio-latest"

    # AI_MODE: "openai" | "gemini" | "mock"
    AI_MODE: str = "openai"

    # SMTP
    SMTP_HOST: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 2525
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "Rojgar Mela <noreply@rojgarmela.ai>"
    SMTP_TLS: bool = True

    # Platform support
    SUPPORT_EMAIL: str = "info@rojgarmela.ai"
    SUPPORT_PHONES: str = "+91-8968455531"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"
    TRAINING_URL: str = "http://localhost:5000"
    CORS_ORIGINS: str = ""
    CORS_ORIGIN_REGEX: str = ""

    # Files
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 50
    TESSERACT_CMD: str = ""

    # Matching thresholds
    AUTO_MATCH_THRESHOLD: float = 0.70
    PROVIDER_MATCH_THRESHOLD: float = 0.75

    # Super admin
    SUPER_ADMIN_EMAIL: str = "superadmin@rojgarmela.ai"
    SUPER_ADMIN_PASSWORD: str = "SuperAdmin@123"

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Training Portal — course seat-booking token payment (₹)
    TRAINING_TOKEN_BOOKING_AMOUNT: float = 2000.0
    TRAINING_TOKEN_VENUE_VISIT_DAYS: int = 5

    # Google Sign-In
    GOOGLE_OAUTH_CLIENT_ID: str = ""

    # Social login — OAuth code flow (Google / GitHub / LinkedIn)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_CALLBACK_URL: str = "http://localhost:8000/auth/google/callback"
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_CALLBACK_URL: str = "http://localhost:8000/auth/github/callback"
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_CALLBACK_URL: str = "http://localhost:8000/auth/linkedin/callback"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"
    TOKEN_ENCRYPTION_KEY: str = ""
    TURNSTILE_SECRET_KEY: str = ""
    TURNSTILE_SITE_KEY: str = ""
    SESSION_EXPIRE_DAYS: int = 30

    # Google Calendar integration
    GOOGLE_CALENDAR_ICS_ENABLED: bool = True
    GOOGLE_CALENDAR_CLIENT_ID: str = ""
    GOOGLE_CALENDAR_CLIENT_SECRET: str = ""
    GOOGLE_CALENDAR_REDIRECT_URI: str = "http://localhost:8000/google-calendar/callback"
    GOOGLE_CALENDAR_POST_CONNECT_URL: str = ""

    @property
    def google_sign_in_client_id(self) -> str:
        return (
            self.GOOGLE_OAUTH_CLIENT_ID
            or self.GOOGLE_CLIENT_ID
            or self.GOOGLE_CALENDAR_CLIENT_ID
            or ""
        ).strip()

    def google_oauth_configured(self) -> bool:
        return bool((self.GOOGLE_CLIENT_ID or self.google_sign_in_client_id) and self.GOOGLE_CLIENT_SECRET)

    def github_oauth_configured(self) -> bool:
        return bool(self.GITHUB_CLIENT_ID and self.GITHUB_CLIENT_SECRET)

    def linkedin_oauth_configured(self) -> bool:
        return bool(self.LINKEDIN_CLIENT_ID and self.LINKEDIN_CLIENT_SECRET)

    def google_calendar_oauth_configured(self) -> bool:
        return bool(self.GOOGLE_CALENDAR_CLIENT_ID and self.GOOGLE_CALENDAR_CLIENT_SECRET)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def get_cors_allow_origins() -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        u = (url or "").strip()
        if not u or u in seen:
            return
        seen.add(u)
        out.append(u)

    add(settings.FRONTEND_URL)
    add(settings.TRAINING_URL)
    for part in settings.CORS_ORIGINS.split(","):
        add(part.strip())
    for dev in (
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://0.0.0.0:5173",
        "http://0.0.0.0:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://192.168.100.15:5041",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ):
        add(dev)
    return out


def get_cors_origin_regex() -> str | None:
    raw = (settings.CORS_ORIGIN_REGEX or "").strip()
    if raw.lower() in ("none", "false", "0", "off"):
        return None
    if raw:
        return raw
    return (
        r"^https?://("
        r"localhost|127\.0\.0\.1"
        r"|192\.168\.\d{1,3}\.\d{1,3}"
        r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
        r")(?::\d+)?$"
    )


def get_upload_dir() -> Path:
    """Returns absolute Path to the root uploads directory."""
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent.parent
    upload_path = Path(settings.UPLOAD_DIR)
    if not upload_path.is_absolute():
        upload_path = base / upload_path
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path
