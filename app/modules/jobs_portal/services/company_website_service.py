"""Website Open Graph / JSON-LD fallback when Google Places is unavailable."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def normalize_website(url: Optional[str]) -> Optional[str]:
    raw = (url or "").strip()
    if not raw:
        return None
    if not re.match(r"^https?://", raw, re.I):
        raw = f"https://{raw}"
    return raw[:500]


def _meta(soup: BeautifulSoup, *keys: str) -> Optional[str]:
    for key in keys:
        tag = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            value = str(tag["content"]).strip()
            if value:
                return value
    return None


def _abs_url(page_url: str, maybe: Optional[str]) -> Optional[str]:
    if not maybe:
        return None
    value = maybe.strip()
    if not value:
        return None
    return urljoin(page_url, value)


def _first_json_ld_org(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (script.string or script.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        if isinstance(data, dict) and isinstance(data.get("@graph"), list):
            items = data["@graph"]
        for item in items:
            if not isinstance(item, dict):
                continue
            types = item.get("@type")
            type_list = types if isinstance(types, list) else [types]
            type_list = [str(t).lower() for t in type_list if t]
            if any(t in {"organization", "localbusiness", "corporation", "employer"} for t in type_list):
                return item
    return {}


def _address_from_ld(org: dict[str, Any]) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    addr = org.get("address")
    if isinstance(addr, list) and addr:
        addr = addr[0]
    if isinstance(addr, str):
        return addr, None, None, addr
    if not isinstance(addr, dict):
        return None, None, None, None
    street = addr.get("streetAddress")
    city = addr.get("addressLocality")
    state = addr.get("addressRegion")
    postal = addr.get("postalCode")
    country = addr.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    parts = [p for p in (street, city, state, postal, country) if p]
    location = ", ".join(p for p in (city, state) if p)
    return " ".join(str(p) for p in parts) or None, city, state, location or None


async def fetch_website_preview(url: str) -> dict[str, Any]:
    page_url = normalize_website(url)
    if not page_url:
        return {}
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            follow_redirects=True,
            timeout=12.0,
        ) as client:
            response = await client.get(page_url)
            response.raise_for_status()
            final_url = str(response.url)
            html = response.text
    except Exception as exc:
        logger.info("Website metadata fetch failed for %s: %s", page_url, exc)
        return {"company_website": page_url}

    soup = BeautifulSoup(html, "html.parser")
    org = _first_json_ld_org(soup)
    address, city, state, location = _address_from_ld(org)
    logo = org.get("logo")
    if isinstance(logo, dict):
        logo = logo.get("url")
    if isinstance(logo, list) and logo:
        logo = logo[0]
    title = (
        (org.get("name") or "").strip()
        or _meta(soup, "og:site_name", "og:title", "twitter:title")
        or (soup.title.string.strip() if soup.title and soup.title.string else None)
    )
    about = (
        (org.get("description") or "").strip()
        or _meta(soup, "og:description", "description", "twitter:description")
        or None
    )
    image = _abs_url(final_url, (logo if isinstance(logo, str) else None) or _meta(soup, "og:image", "twitter:image"))
    website = normalize_website(org.get("url") if isinstance(org.get("url"), str) else None) or final_url
    if about:
        about = re.sub(r"\s+", " ", about).strip()[:4000]
    return {
        "company_name": (title or "").strip()[:200] or None,
        "company_website": website,
        "company_about": about,
        "company_address": address,
        "company_location": location,
        "company_city": city,
        "company_state": state,
        "logo_url": image,
        "company_rating_source": "manual",
    }
