"""Google Places lookup for provider company profiles.

Uses GOOGLE_PLACES_API_KEY or GOOGLE_MAPS_API_KEY. Never uses GOOGLE_API_KEY (Gemini).
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

PLACES_BASE = "https://maps.googleapis.com/maps/api/place"
DETAILS_FIELDS = (
    "place_id,name,formatted_address,address_component,website,url,rating,"
    "user_ratings_total,reviews,photos,geometry,editorial_summary"
)


def places_enabled() -> bool:
    return settings.google_places_configured()


def _key() -> str:
    return settings.google_places_api_key


def _host_from_url(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().replace("www.", "")
    return host


def _city_state_from_components(components: list[dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    city = None
    state = None
    for part in components or []:
        types = part.get("types") or []
        name = (part.get("long_name") or "").strip()
        if not name:
            continue
        if "locality" in types or "administrative_area_level_2" in types:
            if "locality" in types or not city:
                city = name
        if "administrative_area_level_1" in types:
            state = name
    return city, state


def _sanitize_reviews(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for item in raw[:5]:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        rating = item.get("rating")
        try:
            rating_val = float(rating) if rating is not None else None
        except (TypeError, ValueError):
            rating_val = None
        out.append(
            {
                "author_name": (item.get("author_name") or "").strip() or None,
                "rating": rating_val,
                "text": text[:1000],
                "relative_time": (item.get("relative_time_description") or "").strip() or None,
            }
        )
    return out


def _photo_refs(raw: Any, limit: int = 8) -> list[str]:
    out: list[str] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        ref = (item.get("photo_reference") or "").strip()
        if ref:
            out.append(ref)
        if len(out) >= limit:
            break
    return out


def details_to_preview(details: dict[str, Any]) -> dict[str, Any]:
    city, state = _city_state_from_components(details.get("address_components") or [])
    location = ", ".join(p for p in (city, state) if p)
    editorial = details.get("editorial_summary") or {}
    about = (editorial.get("overview") or "").strip() or None
    rating = details.get("rating")
    try:
        rating_val = round(float(rating), 1) if rating is not None else None
    except (TypeError, ValueError):
        rating_val = None
    return {
        "company_name": (details.get("name") or "").strip() or None,
        "company_website": (details.get("website") or "").strip() or None,
        "company_about": about,
        "company_address": (details.get("formatted_address") or "").strip() or None,
        "company_location": location or None,
        "company_city": city,
        "company_state": state,
        "company_rating": rating_val,
        "company_review_count": details.get("user_ratings_total"),
        "company_reviews": _sanitize_reviews(details.get("reviews")),
        "company_rating_source": "google" if rating_val is not None else None,
        "google_place_id": details.get("place_id"),
        "google_maps_url": (details.get("url") or "").strip() or None,
        "logo_url": None,
        "photo_references": _photo_refs(details.get("photos")),
    }


def candidate_from_result(item: dict[str, Any]) -> dict[str, Any]:
    rating = item.get("rating")
    try:
        rating_val = round(float(rating), 1) if rating is not None else None
    except (TypeError, ValueError):
        rating_val = None
    return {
        "place_id": item.get("place_id"),
        "name": (item.get("name") or "").strip() or None,
        "address": (item.get("formatted_address") or item.get("vicinity") or "").strip() or None,
        "rating": rating_val,
        "review_count": item.get("user_ratings_total"),
    }


async def _get(client: httpx.AsyncClient, path: str, params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, "key": _key()}
    response = await client.get(f"{PLACES_BASE}/{path}", params=params, timeout=12.0)
    response.raise_for_status()
    data = response.json()
    status = data.get("status")
    if status in {"OK", "ZERO_RESULTS"}:
        return data
    logger.warning("Google Places %s status=%s error=%s", path, status, data.get("error_message"))
    raise RuntimeError(data.get("error_message") or f"Google Places returned {status}")


async def text_search(query: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        data = await _get(client, "textsearch/json", {"query": query})
    results = data.get("results") or []
    out = []
    for item in results[:5]:
        if item.get("place_id"):
            out.append(candidate_from_result(item))
    return out


async def fetch_place_details(place_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        data = await _get(
            client,
            "details/json",
            {"place_id": place_id, "fields": DETAILS_FIELDS},
        )
    result = data.get("result") or {}
    if not result:
        raise RuntimeError("Google Place details were empty")
    return details_to_preview(result)


async def download_place_photo(photo_reference: str, maxwidth: int = 1200) -> bytes:
    params = {
        "photo_reference": photo_reference,
        "maxwidth": maxwidth,
        "key": _key(),
    }
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(f"{PLACES_BASE}/photo", params=params, timeout=20.0)
        response.raise_for_status()
        content_type = (response.headers.get("content-type") or "").lower()
        if "image" not in content_type and not response.content:
            raise RuntimeError("Google Place photo was not an image")
        return response.content


async def lookup_places(*, website: Optional[str], query: Optional[str], place_id: Optional[str]) -> dict[str, Any]:
    if not places_enabled():
        return {"enabled": False, "preview": {}, "candidates": [], "error": None}

    try:
        if place_id:
            preview = await fetch_place_details(place_id)
            return {"enabled": True, "preview": preview, "candidates": [], "error": None}

        search_terms: list[str] = []
        if query:
            search_terms.append(query)
        if website:
            host = _host_from_url(website)
            if host:
                search_terms.append(host.split(".")[0].replace("-", " "))
                search_terms.append(host)

        seen_ids: set[str] = set()
        candidates: list[dict[str, Any]] = []
        for term in search_terms:
            term = (term or "").strip()
            if not term:
                continue
            for item in await text_search(term):
                pid = item.get("place_id")
                if not pid or pid in seen_ids:
                    continue
                seen_ids.add(pid)
                candidates.append(item)
            if candidates:
                break

        preview: dict[str, Any] = {}
        if len(candidates) == 1:
            preview = await fetch_place_details(candidates[0]["place_id"])
        elif candidates:
            preview = await fetch_place_details(candidates[0]["place_id"])

        return {"enabled": True, "preview": preview, "candidates": candidates, "error": None}
    except Exception as exc:
        logger.warning("Google Places lookup failed: %s", exc)
        return {"enabled": True, "preview": {}, "candidates": [], "error": str(exc)}
