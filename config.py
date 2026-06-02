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


    # AI_MODE: "openai" | "gemini" | "mock"
    AI_MODE: str = "openai"

    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "JobMatch AI <emr@tekkiwebsolutions.com>"
    SMTP_TLS: bool = True

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS — set FRONTEND_URL and/or CORS_ORIGINS on the server to match where the SPA is served
    # FRONTEND_URL: str = "http://localhost:5173"
    FRONTEND_URL: str = "http://192.168.0.211:9014/login"


    CORS_ORIGINS: str = ""  # comma-separated extra origins, e.g. http://10.0.0.5:8080,https://app.example.com
    # Empty = allow typical LAN/dev hosts (192.168.x.x, 10.x, 172.16–31.x) + any port via regex.
    # Set to "none" to disable regex (only explicit origins). Or set a custom regex string.
    CORS_ORIGIN_REGEX: str = ""

    # Files
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 10

    # Matching thresholds
    AUTO_MATCH_THRESHOLD: float = 0.70
    PROVIDER_MATCH_THRESHOLD: float = 0.75

    # Super admin (seeded on startup if missing)
    SUPER_ADMIN_EMAIL: str = "superadmin@hirely.com"
    SUPER_ADMIN_PASSWORD: str = ""
    SUPERADMIN_SECRET_KEY: str = ""


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
        "http://192.168.100.15:5041"
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
