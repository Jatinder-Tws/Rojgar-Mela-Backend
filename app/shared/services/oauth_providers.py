from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.core.config import settings

PROVIDERS = ("google", "github", "linkedin")


@dataclass
class ProviderProfile:
    provider: str
    provider_user_id: str
    email: Optional[str]
    email_verified: bool
    name: Optional[str]
    given_name: Optional[str]
    family_name: Optional[str]
    avatar_url: Optional[str]
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


def provider_configured(provider: str) -> bool:
    if provider == "google":
        return settings.google_oauth_configured()
    if provider == "github":
        return settings.github_oauth_configured()
    if provider == "linkedin":
        return settings.linkedin_oauth_configured()
    return False


def callback_url(provider: str) -> str:
    if provider == "google":
        return settings.GOOGLE_CALLBACK_URL
    if provider == "github":
        return settings.GITHUB_CALLBACK_URL
    if provider == "linkedin":
        return settings.LINKEDIN_CALLBACK_URL
    raise ValueError("Unknown provider")


def authorization_url(provider: str, state: str, code_challenge: str) -> str:
    if provider == "google":
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID or settings.google_sign_in_client_id,
            "redirect_uri": callback_url(provider),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "select_account",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    if provider == "github":
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": callback_url(provider),
            "scope": "read:user user:email",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "allow_signup": "true",
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    if provider == "linkedin":
        params = {
            "response_type": "code",
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "redirect_uri": callback_url(provider),
            "scope": "openid profile email",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
    raise ValueError("Unknown provider")


async def exchange_code(provider: str, code: str, code_verifier: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        if provider == "google":
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID or settings.google_sign_in_client_id,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback_url(provider),
                    "code_verifier": code_verifier,
                },
            )
        elif provider == "github":
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": callback_url(provider),
                    "code_verifier": code_verifier,
                },
            )
        elif provider == "linkedin":
            resp = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": callback_url(provider),
                    "client_id": settings.LINKEDIN_CLIENT_ID,
                    "client_secret": settings.LINKEDIN_CLIENT_SECRET,
                    "code_verifier": code_verifier,
                },
            )
        else:
            raise ValueError("Unknown provider")
    if resp.status_code >= 400:
        raise RuntimeError("Could not exchange authorization code")
    data = resp.json()
    if not data.get("access_token"):
        raise RuntimeError("Provider did not return an access token")
    return data


async def fetch_profile(provider: str, token_payload: dict) -> ProviderProfile:
    access_token = token_payload["access_token"]
    refresh_token = token_payload.get("refresh_token")
    async with httpx.AsyncClient(timeout=20.0) as client:
        if provider == "google":
            resp = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            info = resp.json()
            email = (info.get("email") or "").strip().lower() or None
            name = (info.get("name") or "").strip() or None
            return ProviderProfile(
                provider="google",
                provider_user_id=str(info.get("sub") or ""),
                email=email,
                email_verified=bool(info.get("email_verified")),
                name=name,
                given_name=(info.get("given_name") or "").strip() or None,
                family_name=(info.get("family_name") or "").strip() or None,
                avatar_url=info.get("picture"),
                access_token=access_token,
                refresh_token=refresh_token,
            )
        if provider == "github":
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            user_resp.raise_for_status()
            info = user_resp.json()
            email = (info.get("email") or "").strip().lower() or None
            email_verified = False
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            if emails_resp.status_code == 200:
                emails = emails_resp.json() or []
                primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
                verified = next((e for e in emails if e.get("verified")), None)
                chosen = primary or verified or (emails[0] if emails else None)
                if chosen:
                    email = (chosen.get("email") or "").strip().lower() or email
                    email_verified = bool(chosen.get("verified"))
            name = (info.get("name") or info.get("login") or "").strip() or None
            given, family = _split_name(name)
            return ProviderProfile(
                provider="github",
                provider_user_id=str(info.get("id") or ""),
                email=email,
                email_verified=email_verified,
                name=name,
                given_name=given,
                family_name=family,
                avatar_url=info.get("avatar_url"),
                access_token=access_token,
                refresh_token=refresh_token,
            )
        if provider == "linkedin":
            resp = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            info = resp.json()
            email = (info.get("email") or "").strip().lower() or None
            name = (info.get("name") or "").strip() or None
            return ProviderProfile(
                provider="linkedin",
                provider_user_id=str(info.get("sub") or ""),
                email=email,
                email_verified=bool(info.get("email_verified")),
                name=name,
                given_name=(info.get("given_name") or "").strip() or None,
                family_name=(info.get("family_name") or "").strip() or None,
                avatar_url=info.get("picture"),
                access_token=access_token,
                refresh_token=refresh_token,
            )
    raise ValueError("Unknown provider")


def _split_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    parts = [p for p in (full_name or "").split() if p]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])
