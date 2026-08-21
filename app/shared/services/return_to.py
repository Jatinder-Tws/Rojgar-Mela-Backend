from __future__ import annotations

from urllib.parse import urlparse

# PRD 6.7 aliases mapped onto this app's real routes.
_ALIASES = {
    "/dashboard/jobs": "/browse-jobs",
    "/dashboard/provider": "/dashboard",
    "/dashboard/teacher": "/dashboard",
    "/admin": "/super-admin/dashboard",
}

_BLOCKED_PREFIXES = (
    "/login",
    "/register",
    "/register-info",
    "/reset-password",
    "/verify-email",
    "/verify-totp",
    "/complete-profile",
    "/auth/",
    "/setup-totp",
)


def sanitize_return_to(value: str | None, *, max_len: int = 2048) -> str | None:
    """Allow only relative internal paths. Reject open redirects (PRD 6.7.2)."""
    if not value:
        return None
    raw = value.strip()
    if not raw or len(raw) > max_len:
        return None
    if raw.startswith("//") or "\\" in raw:
        return None
    lowered = raw.lower()
    if lowered.startswith("http://") or lowered.startswith("https://") or lowered.startswith("javascript:"):
        return None
    if not raw.startswith("/"):
        return None

    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        return None
    path = parsed.path or "/"
    if path.startswith("//") or ":" in path:
        return None
    if path == "/":
        return None
    for prefix in _BLOCKED_PREFIXES:
        clean = prefix.rstrip("/")
        if path == clean or path.startswith(clean + "/"):
            return None

    mapped = _ALIASES.get(path, path)
    query = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{mapped}{query}{fragment}"
