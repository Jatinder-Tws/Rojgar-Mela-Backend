"""Fetch title, description, and thumbnail from external URLs for free-course resources."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.modules.training_portal.services.youtube_playlist_service import (
    YouTubeImportError,
    fetch_playlist,
    parse_youtube_ids,
)

logger = logging.getLogger(__name__)

RESOURCE_CATEGORIES = (
    "video",
    "github_repo",
    "book",
    "research_paper",
    "course",
    "guide",
    "pdf",
)

SPECIFIC_CATEGORIES = frozenset({"video", "github_repo", "book", "research_paper", "course", "pdf"})

USER_AGENT = "RojgarMelaBot/1.0 (+https://rojgarmela.ai)"


class UrlMetadataError(Exception):
    """Raised when URL metadata cannot be fetched."""


@dataclass
class UrlMetadata:
    url: str
    title: str
    description: str = ""
    thumbnail_url: Optional[str] = None
    category: str = "guide"
    metadata: dict[str, Any] = field(default_factory=dict)
    is_youtube: bool = False
    youtube_video_id: Optional[str] = None


def is_hosted_upload_url(url: str) -> bool:
    raw = (url or "").strip().lower()
    return raw.startswith("/uploads/") or "/uploads/training_portal_free_course_files/" in raw


def is_pdf_url(url: str) -> bool:
    raw = (url or "").strip().lower().split("?", 1)[0]
    return raw.endswith(".pdf") or "training_portal_free_course_files" in raw


def pdf_metadata_from_url(
    url: str,
    *,
    title: Optional[str] = None,
    original_filename: Optional[str] = None,
) -> UrlMetadata:
    raw = (url or "").strip()
    name = original_filename or raw.rstrip("/").split("/")[-1].split("?")[0]
    stem = re.sub(r"^[0-9a-f]{32}", "", Path(name).stem, flags=re.I)
    stem = stem.replace("_", " ").replace("-", " ").strip() or "PDF document"
    return UrlMetadata(
        url=raw,
        title=(title or stem)[:300],
        description="",
        thumbnail_url=None,
        category="pdf",
        metadata={
            "file_type": "pdf",
            "original_filename": original_filename or name,
        },
    )


def _normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise UrlMetadataError("URL is required.")
    if is_hosted_upload_url(raw):
        return raw
    if not re.match(r"^https?://", raw, re.I):
        raw = f"https://{raw}"
    return raw


def _detect_category(url: str, host: str) -> str:
    host = host.lower().replace("www.", "")
    if host in {"youtube.com", "youtu.be", "m.youtube.com"}:
        return "video"
    if host == "github.com":
        return "github_repo"
    if host == "arxiv.org":
        return "research_paper"
    if host.endswith("huggingface.co"):
        return "course"
    if any(
        token in host
        for token in (
            "manning.com",
            "oreilly.com",
            "udlbook.github.io",
            "github.io",
        )
    ):
        return "book"
    if any(token in host for token in ("kaggle.com", "anthropic.com", "openai.com", "cdn.openai.com")):
        return "guide"
    if url.lower().endswith(".pdf") or is_pdf_url(url):
        return "pdf"
    return "guide"


def _meta_content(soup: BeautifulSoup, *keys: str) -> Optional[str]:
    for key in keys:
        tag = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            value = str(tag["content"]).strip()
            if value:
                return value
    if soup.title and soup.title.string:
        value = soup.title.string.strip()
        if value:
            return value
    return None


async def _fetch_html(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    final_url = str(response.url)
    return final_url, response.text


async def _fetch_github_repo(client: httpx.AsyncClient, url: str) -> UrlMetadata:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise UrlMetadataError("Invalid GitHub repository URL.")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    response = await client.get(api_url)
    if response.status_code == 404:
        raise UrlMetadataError("GitHub repository not found.")
    response.raise_for_status()
    data = response.json()
    license_info = data.get("license") if isinstance(data.get("license"), dict) else {}
    return UrlMetadata(
        url=url,
        title=(data.get("full_name") or f"{owner}/{repo}").strip(),
        description=(data.get("description") or "").strip(),
        thumbnail_url=(data.get("owner") or {}).get("avatar_url"),
        category="github_repo",
        metadata={
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "watchers": data.get("subscribers_count") or data.get("watchers_count"),
            "open_issues": data.get("open_issues_count"),
            "language": data.get("language"),
            "topics": data.get("topics") or [],
            "license": license_info.get("spdx_id") if license_info else None,
            "default_branch": data.get("default_branch"),
            "html_url": data.get("html_url") or url,
        },
    )


async def _fetch_arxiv(client: httpx.AsyncClient, url: str) -> UrlMetadata:
    parsed = urlparse(url)
    match = re.search(r"/abs/([\w.-]+)", parsed.path)
    if not match:
        raise UrlMetadataError("Invalid arXiv URL.")
    paper_id = match.group(1)
    api_url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
    response = await client.get(api_url)
    response.raise_for_status()
    text = response.text
    title_match = re.search(r"<title>([^<]+)</title>", text)
    summary_match = re.search(r"<summary>([^<]+)</summary>", text, re.S)
    title = title_match.group(1).strip() if title_match else paper_id
    if title.lower().startswith("arxiv query:"):
        title = paper_id
    description = re.sub(r"\s+", " ", summary_match.group(1)).strip() if summary_match else ""
    return UrlMetadata(
        url=url,
        title=title,
        description=description,
        category="research_paper",
        metadata={"arxiv_id": paper_id},
    )


async def _fetch_og_page(client: httpx.AsyncClient, url: str, category: str) -> UrlMetadata:
    final_url, html = await _fetch_html(client, url)
    soup = BeautifulSoup(html, "html.parser")
    title = _meta_content(soup, "og:title", "twitter:title") or final_url
    description = _meta_content(soup, "og:description", "description", "twitter:description") or ""
    thumbnail = _meta_content(soup, "og:image", "twitter:image")
    return UrlMetadata(
        url=final_url,
        title=title[:300],
        description=description[:2000],
        thumbnail_url=thumbnail,
        category=category,
    )


def resolve_resource_category(requested: Optional[str], detected: str) -> str:
    """Prefer auto-detected category when URL clearly belongs elsewhere."""
    chosen = (requested or "").strip().lower()
    if chosen and chosen not in RESOURCE_CATEGORIES:
        raise UrlMetadataError(f"Invalid category. Use one of: {', '.join(RESOURCE_CATEGORIES)}")
    if detected in SPECIFIC_CATEGORIES and chosen and chosen != detected:
        return detected
    return chosen or detected


async def fetch_url_metadata(url: str, category: Optional[str] = None) -> UrlMetadata:
    if is_hosted_upload_url(url) or (is_pdf_url(url) and (url or "").strip().startswith("/")):
        chosen = (category or "").strip().lower() or "pdf"
        meta = pdf_metadata_from_url(url)
        if chosen in RESOURCE_CATEGORIES:
            meta.category = chosen
        return meta

    normalized = _normalize_url(url)
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()

    playlist_id, video_id = parse_youtube_ids(normalized)
    if playlist_id or video_id or host.endswith("youtube.com") or host == "youtu.be":
        try:
            imported = await fetch_playlist(normalized)
        except YouTubeImportError as exc:
            raise UrlMetadataError(str(exc)) from exc
        first = imported.videos[0] if imported.videos else None
        return UrlMetadata(
            url=normalized,
            title=imported.title,
            description=imported.description,
            thumbnail_url=imported.thumbnail_url or (first.thumbnail_url if first else None),
            category="video",
            is_youtube=True,
            youtube_video_id=first.video_id if first and len(imported.videos) == 1 else None,
            metadata={
                "video_count": len(imported.videos),
                "playlist_id": imported.playlist_id,
                "channel_title": imported.channel_title,
                "detected_category": "video",
            },
        )

    detected = _detect_category(normalized, host)
    if category:
        chosen = (category or "").strip().lower()
        if chosen and chosen not in RESOURCE_CATEGORIES:
            raise UrlMetadataError(f"Invalid category. Use one of: {', '.join(RESOURCE_CATEGORIES)}")

    async with httpx.AsyncClient(
        timeout=25.0,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        if host == "github.com":
            meta = await _fetch_github_repo(client, normalized)
        elif host == "arxiv.org":
            meta = await _fetch_arxiv(client, normalized)
        else:
            try:
                meta = await _fetch_og_page(client, normalized, detected)
            except httpx.HTTPError as exc:
                logger.warning("URL metadata fetch failed for %s: %s", normalized, exc)
                raise UrlMetadataError("Could not fetch metadata from that URL.") from exc

    meta.metadata = {**(meta.metadata or {}), "detected_category": detected}
    meta.category = detected
    return meta
