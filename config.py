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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o"

    # Google Gemini
    GOOGLE_API_KEY: str = ""
    # GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    # GEMINI_CHAT_MODEL: str = "gemini-1.5-flash"
    # GEMINI_CHAT_MODEL: str = "gemini-2.0-flash"
    GEMINI_CHAT_MODEL: str = "gemini-2.5-flash"
    GEMINI_LIVE_MODEL: str = "gemini-3.1-flash-live-preview"


    # AI_MODE: "openai" | "gemini" | "mock"
    AI_MODE: str = "openai"

    # SMTP (defaults: Mailtrap sandbox for dev)
    SMTP_HOST: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 2525
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "Rojgar Mela <noreply@rojgarmela.ai>"
    SMTP_TLS: bool = True

    # Platform support (used in transactional emails)
    SUPPORT_EMAIL: str = "info@rojgarmela.ai"
    SUPPORT_PHONES: str = "+91-9915137531, +91-9915130531"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS — set FRONTEND_URL and/or CORS_ORIGINS on the server to match where the SPA is served
    FRONTEND_URL: str = "http://localhost:5173"
    TRAINING_URL: str = "http://localhost:5000"
    CORS_ORIGINS: str = ""  # comma-separated extra origins, e.g. http://10.0.0.5:8080,https://app.example.com
    # Empty = allow typical LAN/dev hosts (192.168.x.x, 10.x, 172.16–31.x) + any port via regex.
    # Set to "none" to disable regex (only explicit origins). Or set a custom regex string.
    CORS_ORIGIN_REGEX: str = ""

    # Files
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 50
    TESSERACT_CMD: str = ""

    # Matching thresholds
    AUTO_MATCH_THRESHOLD: float = 0.70
    PROVIDER_MATCH_THRESHOLD: float = 0.75

    # Super admin (seeded on startup if missing)
    SUPER_ADMIN_EMAIL: str = "superadmin@rojgarmela.ai"
    SUPER_ADMIN_PASSWORD: str = "SuperAdmin@123"

    # Razorpay (training portal payments)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Google Sign-In (Login with Google). Use a Web client ID from Google Cloud Console
    # with Authorized JavaScript origins for the frontend (e.g. http://localhost:5173).
    # Falls back to GOOGLE_CALENDAR_CLIENT_ID when empty.
    GOOGLE_OAUTH_CLIENT_ID: str = ""

    # Google Calendar integration (training class schedule sync)
    # Leave OAuth keys empty to disable per-user auto-sync; ICS email invites
    # still work as long as SMTP is configured.
    GOOGLE_CALENDAR_ICS_ENABLED: bool = True
    GOOGLE_CALENDAR_CLIENT_ID: str = ""
    GOOGLE_CALENDAR_CLIENT_SECRET: str = ""
    # Must exactly match an Authorized redirect URI in the Google Cloud OAuth client.
    GOOGLE_CALENDAR_REDIRECT_URI: str = "http://localhost:8000/google-calendar/callback"
    # Where users land after connecting (training portal). Empty = TRAINING_URL.
    GOOGLE_CALENDAR_POST_CONNECT_URL: str = ""

    @property
    def google_sign_in_client_id(self) -> str:
        return (self.GOOGLE_OAUTH_CLIENT_ID or self.GOOGLE_CALENDAR_CLIENT_ID or "").strip()

    def google_calendar_oauth_configured(self) -> bool:
        return bool(self.GOOGLE_CALENDAR_CLIENT_ID and self.GOOGLE_CALENDAR_CLIENT_SECRET)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def get_cors_allow_origins() -> list[str]:
    """Origins allowed for browser requests (REST + WebSocket). Include every URL users open the app from."""
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
        "http://127.0.0.1:5000"
    ):
        add(dev)
    return out


def get_cors_origin_regex() -> str | None:
    """
    Starlette fullmatches the browser Origin against this regex.
    Covers http://192.168.x.x:5174 style access (Vite bound to LAN IP).
    """
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
