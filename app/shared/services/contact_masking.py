"""Candidate contact info masking service for privacy & credit-lock compliance."""
import re
from typing import Optional, Set

SHORTLISTED_APPLICATION_STATUSES: Set[str] = {
    "shortlisted",
    "interviewing",
    "selected",
}


def is_status_shortlisted(status: Optional[str]) -> bool:
    """Return True if an application or candidate status is considered shortlisted."""
    if not status:
        return False
    val = str(status.value if hasattr(status, "value") else status).strip().lower()
    return val in SHORTLISTED_APPLICATION_STATUSES


def mask_email(email: Optional[str]) -> Optional[str]:
    """Mask email address (e.g. 'john.doe@example.com' -> 'jo******@ex****.com')."""
    if not email:
        return email
    clean = str(email).strip()
    if "@" not in clean:
        return "••••••••"
    local_part, domain = clean.split("@", 1)
    if len(local_part) <= 2:
        masked_local = (local_part[0] + "***") if local_part else "***"
    else:
        masked_local = local_part[:2] + "*" * min(6, len(local_part) - 2)

    if "." in domain:
        domain_name, domain_tld = domain.rsplit(".", 1)
        if len(domain_name) <= 2:
            masked_domain = (domain_name[0] + "***") if domain_name else "***"
        else:
            masked_domain = domain_name[:2] + "*" * min(4, len(domain_name) - 2)
        return f"{masked_local}@{masked_domain}.{domain_tld}"
    return f"{masked_local}@{domain}"


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """Mask phone number preserving country code/prefix if present, e.g. '+91 ••••••3210'."""
    if not phone:
        return phone
    raw = str(phone).strip()
    digits = re.findall(r"\d", raw)
    if len(digits) < 4:
        return "••••••••••"

    last_four = "".join(digits[-4:])
    if len(digits) == 10:
        return f"+91 ••••••{last_four}"
    elif len(digits) > 10:
        prefix = "".join(digits[:-10])
        return f"+{prefix} ••••••{last_four}"
    else:
        return f"••••••{last_four}"
