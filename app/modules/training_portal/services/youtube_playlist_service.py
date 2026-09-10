"""Extract YouTube playlist / video metadata for free-course import.

Prefers the official YouTube Data API v3 when YOUTUBE_API_KEY is set.
Falls back to yt-dlp extract-only (no video download) so local/dev still works.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_PLAYLIST_ITEMS = 200
SKIP_TITLES = {"private video", "deleted video"}


class YouTubeImportError(Exception):
    """Raised when a playlist/video cannot be imported."""


@dataclass
class PlaylistVideo:
    video_id: str
    title: str
    description: str = ""
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    sort_order: int = 0

    @property
    def youtube_url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


@dataclass
class PlaylistImport:
    title: str
    description: str = ""
    playlist_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    channel_title: Optional[str] = None
    source_url: str = ""
    videos: list[PlaylistVideo] = field(default_factory=list)


def parse_youtube_ids(url: str) -> tuple[Optional[str], Optional[str]]:
    """Return (playlist_id, video_id) from a watch, playlist, shorts, or youtu.be URL."""
    raw = (url or "").strip()
    if not raw:
        return None, None
    if not re.match(r"^https?://", raw, re.I):
        raw = f"https://{raw}"

    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower().replace("www.", "")
    query = parse_qs(parsed.query)
    path = parsed.path or ""

    playlist_id = (query.get("list") or [None])[0]
    video_id = (query.get("v") or [None])[0]

    if host in {"youtu.be"}:
        slug = path.strip("/").split("/")[0]
        if slug and re.fullmatch(r"[\w-]{6,}", slug):
            video_id = video_id or slug
    elif "/embed/" in path:
        slug = path.split("/embed/", 1)[-1].split("/")[0]
        if slug and slug != "videoseries" and re.fullmatch(r"[\w-]{6,}", slug):
            video_id = video_id or slug
    elif "/shorts/" in path:
        slug = path.split("/shorts/", 1)[-1].split("/")[0]
        if slug and re.fullmatch(r"[\w-]{6,}", slug):
            video_id = video_id or slug
    elif "/playlist" in path and not playlist_id:
        playlist_id = (query.get("list") or [None])[0]

    if playlist_id and not re.fullmatch(r"[\w-]{10,}", playlist_id):
        playlist_id = None
    if video_id and not re.fullmatch(r"[\w-]{6,}", video_id):
        video_id = None

    return playlist_id, video_id


def parse_iso8601_duration(value: Optional[str]) -> Optional[int]:
    if not value or not value.startswith("P"):
        return None
    match = re.match(
        r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?",
        value,
    )
    if not match:
        return None
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    total = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total or None


def _best_thumbnail(thumbnails: Optional[dict]) -> Optional[str]:
    if not thumbnails:
        return None
    for key in ("maxres", "standard", "high", "medium", "default"):
        url = (thumbnails.get(key) or {}).get("url")
        if url:
            return url
    return None


def _usable_title(title: Optional[str]) -> bool:
    return bool(title) and title.strip().lower() not in SKIP_TITLES


async def fetch_playlist(url: str) -> PlaylistImport:
    playlist_id, video_id = parse_youtube_ids(url)
    if not playlist_id and not video_id:
        raise YouTubeImportError(
            "Please paste a valid YouTube video or playlist link."
        )

    api_key = (settings.YOUTUBE_API_KEY or "").strip()
    if api_key:
        try:
            if playlist_id:
                return await _fetch_playlist_via_api(api_key, playlist_id, url)
            return await _fetch_video_via_api(api_key, video_id or "", url)
        except YouTubeImportError:
            raise
        except Exception as exc:
            logger.warning("YouTube Data API import failed, trying yt-dlp: %s", exc)

    return await asyncio.to_thread(_fetch_via_ytdlp, url, playlist_id, video_id)


async def _fetch_playlist_via_api(api_key: str, playlist_id: str, source_url: str) -> PlaylistImport:
    params_base = {"key": api_key}
    async with httpx.AsyncClient(timeout=30.0) as client:
        playlist_res = await client.get(
            f"{YOUTUBE_API_BASE}/playlists",
            params={**params_base, "part": "snippet,contentDetails", "id": playlist_id},
        )
        if playlist_res.status_code in (400, 403):
            raise YouTubeImportError(
                "YouTube API rejected the request. Check YOUTUBE_API_KEY and that YouTube Data API v3 is enabled."
            )
        playlist_res.raise_for_status()
        items = playlist_res.json().get("items") or []
        if not items:
            raise YouTubeImportError("Playlist not found. Make sure it is public or unlisted.")

        snippet = items[0].get("snippet") or {}
        title = snippet.get("title") or "Untitled playlist"
        description = snippet.get("description") or ""
        channel_title = snippet.get("channelTitle")
        thumbnail_url = _best_thumbnail(snippet.get("thumbnails"))

        videos: list[PlaylistVideo] = []
        page_token: Optional[str] = None
        while len(videos) < MAX_PLAYLIST_ITEMS:
            page_params = {
                **params_base,
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
            }
            if page_token:
                page_params["pageToken"] = page_token
            page_res = await client.get(f"{YOUTUBE_API_BASE}/playlistItems", params=page_params)
            page_res.raise_for_status()
            payload = page_res.json()
            for entry in payload.get("items") or []:
                entry_snippet = entry.get("snippet") or {}
                resource = (entry_snippet.get("resourceId") or {})
                vid = resource.get("videoId") or (entry.get("contentDetails") or {}).get("videoId")
                video_title = entry_snippet.get("title") or ""
                if not vid or not _usable_title(video_title):
                    continue
                videos.append(
                    PlaylistVideo(
                        video_id=vid,
                        title=video_title.strip(),
                        description=(entry_snippet.get("description") or "").strip(),
                        thumbnail_url=_best_thumbnail(entry_snippet.get("thumbnails")),
                        sort_order=len(videos),
                    )
                )
                if len(videos) >= MAX_PLAYLIST_ITEMS:
                    break
            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        if not videos:
            raise YouTubeImportError("This playlist has no public videos to import.")

        await _attach_durations(client, api_key, videos)

    return PlaylistImport(
        title=title.strip(),
        description=description.strip(),
        playlist_id=playlist_id,
        thumbnail_url=thumbnail_url or videos[0].thumbnail_url,
        channel_title=channel_title,
        source_url=source_url,
        videos=videos,
    )


async def _fetch_video_via_api(api_key: str, video_id: str, source_url: str) -> PlaylistImport:
    if not video_id:
        raise YouTubeImportError("Could not find a video id in that YouTube link.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(
            f"{YOUTUBE_API_BASE}/videos",
            params={"key": api_key, "part": "snippet,contentDetails", "id": video_id},
        )
        res.raise_for_status()
        items = res.json().get("items") or []
        if not items:
            raise YouTubeImportError("Video not found. Make sure it is public.")
        snippet = items[0].get("snippet") or {}
        title = (snippet.get("title") or "Untitled video").strip()
        if not _usable_title(title):
            raise YouTubeImportError("This video is private or deleted.")
        video = PlaylistVideo(
            video_id=video_id,
            title=title,
            description=(snippet.get("description") or "").strip(),
            thumbnail_url=_best_thumbnail(snippet.get("thumbnails")),
            duration_seconds=parse_iso8601_duration((items[0].get("contentDetails") or {}).get("duration")),
            sort_order=0,
        )
        return PlaylistImport(
            title=title,
            description=video.description,
            playlist_id=None,
            thumbnail_url=video.thumbnail_url,
            channel_title=snippet.get("channelTitle"),
            source_url=source_url,
            videos=[video],
        )


async def _attach_durations(client: httpx.AsyncClient, api_key: str, videos: list[PlaylistVideo]) -> None:
    by_id = {v.video_id: v for v in videos}
    ids = list(by_id.keys())
    for i in range(0, len(ids), 50):
        chunk = ids[i : i + 50]
        res = await client.get(
            f"{YOUTUBE_API_BASE}/videos",
            params={"key": api_key, "part": "contentDetails", "id": ",".join(chunk)},
        )
        if res.status_code != 200:
            logger.warning("YouTube videos.list duration lookup failed: %s", res.text[:300])
            return
        for item in res.json().get("items") or []:
            vid = item.get("id")
            if vid in by_id:
                by_id[vid].duration_seconds = parse_iso8601_duration(
                    (item.get("contentDetails") or {}).get("duration")
                )


def _playlist_video_from_ytdlp_entry(entry: dict, sort_order: int) -> Optional[PlaylistVideo]:
    vid = entry.get("id") or entry.get("url")
    title = (entry.get("title") or "").strip()
    if not vid or not _usable_title(title):
        return None
    duration = entry.get("duration")
    try:
        duration_seconds = int(duration) if duration else None
    except (TypeError, ValueError):
        duration_seconds = None
    thumb = None
    thumbs = entry.get("thumbnails") or []
    if thumbs:
        thumb = thumbs[-1].get("url")
    vid_str = str(vid)
    return PlaylistVideo(
        video_id=vid_str,
        title=title,
        description=(entry.get("description") or "").strip(),
        thumbnail_url=thumb or f"https://i.ytimg.com/vi/{vid_str}/hqdefault.jpg",
        duration_seconds=duration_seconds,
        sort_order=sort_order,
    )


def _playlist_video_from_ytdlp_info(info: dict, sort_order: int = 0) -> Optional[PlaylistVideo]:
    vid = info.get("id")
    title = (info.get("title") or "").strip()
    if not vid or not _usable_title(title):
        return None
    duration = info.get("duration")
    try:
        duration_seconds = int(duration) if duration else None
    except (TypeError, ValueError):
        duration_seconds = None
    vid_str = str(vid)
    return PlaylistVideo(
        video_id=vid_str,
        title=title,
        description=(info.get("description") or "").strip(),
        thumbnail_url=(info.get("thumbnail") or f"https://i.ytimg.com/vi/{vid_str}/hqdefault.jpg"),
        duration_seconds=duration_seconds,
        sort_order=sort_order,
    )


def _fetch_via_ytdlp(url: str, playlist_id: Optional[str], video_id: Optional[str]) -> PlaylistImport:
    try:
        import yt_dlp  # type: ignore
    except ImportError as exc:
        raise YouTubeImportError(
            "YouTube import is not configured. Set YOUTUBE_API_KEY in the backend .env, "
            "or install yt-dlp on the server."
        ) from exc

    ydl_opts: dict = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }
    if playlist_id:
        ydl_opts["extract_flat"] = "in_playlist"
        ydl_opts["noplaylist"] = False
    else:
        ydl_opts["noplaylist"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise YouTubeImportError("Could not read that YouTube link. Check that the playlist is public.")

    entries = info.get("entries")
    videos: list[PlaylistVideo] = []
    if entries:
        for entry in entries:
            if not entry:
                continue
            parsed = _playlist_video_from_ytdlp_entry(entry, len(videos))
            if parsed:
                videos.append(parsed)
            if len(videos) >= MAX_PLAYLIST_ITEMS:
                break

    if not videos:
        single = _playlist_video_from_ytdlp_info(info, sort_order=0)
        if single:
            videos.append(single)

    if not videos and video_id:
        single_url = f"https://www.youtube.com/watch?v={video_id}"
        single_opts = {**ydl_opts, "noplaylist": True}
        with yt_dlp.YoutubeDL(single_opts) as ydl:
            single_info = ydl.extract_info(single_url, download=False)
        if single_info:
            single = _playlist_video_from_ytdlp_info(single_info, sort_order=0)
            if single:
                videos.append(single)

    if not videos:
        raise YouTubeImportError("No public videos found on that YouTube link.")

    is_playlist = info.get("_type") == "playlist" or (entries and len(videos) > 1)
    extracted_playlist_id = info.get("id") if is_playlist and playlist_id else (playlist_id if is_playlist else None)
    title = (info.get("title") or videos[0].title).strip()
    return PlaylistImport(
        title=title,
        description=(info.get("description") or "").strip(),
        playlist_id=extracted_playlist_id if is_playlist else None,
        thumbnail_url=info.get("thumbnail") or videos[0].thumbnail_url,
        channel_title=info.get("channel") or info.get("uploader"),
        source_url=url,
        videos=videos,
    )
