import re
import secrets
import string


def normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def password_from_csv_row(row: dict) -> tuple[str | None, str | None]:
    """
    Read password column from a CSV row (case-insensitive header).
    Returns (password, error). Empty cell => (None, None) — no password until admin sets one.
    """
    pwd = ""
    for key, val in row.items():
        if key and key.strip().lower() == "password":
            pwd = (val or "").strip()
            break
    if not pwd:
        return None, None
    if len(pwd) < 8:
        return None, "password must be at least 8 characters"
    return pwd, None


def temp_password(length: int = 12) -> str:
    upper = secrets.choice(string.ascii_uppercase)
    lower = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    symbol = secrets.choice("!@#$%^&*")
    rest = [secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for _ in range(length - 4)]
    chars = [upper, lower, digit, symbol] + rest
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)
