import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.core.logging import logger

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


class GoogleOAuthHandler:
    """
    Official Google OAuth 2.0 authorization-code flow handler.
    Ensures real server-side code exchange, offline refresh tokens,
    identity verification, and honest configuration checks.
    """

    @classmethod
    def is_configured(cls) -> bool:
        cid = settings.GOOGLE_CLIENT_ID
        csec = settings.GOOGLE_CLIENT_SECRET
        return bool(cid and csec and cid.strip() and csec.strip() and not cid.startswith("google-client-id"))

    @classmethod
    def get_authorization_url(cls, state: str, redirect_uri: str, scopes: List[str]) -> str:
        if not cls.is_configured():
            raise ValidationException(
                "Google OAuth credentials are not configured. "
                "Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your backend environment (.env). "
                "Refer to docs/integrations/GOOGLE_SETUP.md for instructions."
            )

        # Always include identity scopes so account email can be displayed
        all_scopes = set(scopes).union({
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        })

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(sorted(all_scopes)),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    @classmethod
    async def exchange_code(cls, code: str, redirect_uri: str) -> Dict[str, Any]:
        if not cls.is_configured():
            raise ValidationException("Google OAuth is not configured in backend environment.")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                err_text = resp.text
                logger.error(f"Google token exchange failed ({resp.status_code}): {err_text}")
                raise RuntimeError(f"Google OAuth token exchange failed (HTTP {resp.status_code}): {err_text}")

            tokens = resp.json()
            return tokens

    @classmethod
    async def refresh_access_token(cls, refresh_token: str) -> Dict[str, Any]:
        if not cls.is_configured():
            raise ValidationException("Google OAuth is not configured in backend environment.")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                },
            )
            if resp.status_code != 200:
                err_text = resp.text
                logger.error(f"Google token refresh failed ({resp.status_code}): {err_text}")
                raise RuntimeError(f"Google token refresh failed (HTTP {resp.status_code}): {err_text}")

            return resp.json()

    @classmethod
    async def fetch_user_profile(cls, access_token: str) -> Dict[str, Any]:
        """Retrieves verified Google user profile and email."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"Failed to fetch Google userinfo: HTTP {resp.status_code} {resp.text}")
            return {}

    @classmethod
    async def revoke_token(cls, token: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    GOOGLE_REVOKE_URL,
                    params={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Google token revocation request failed: {e}")
            return False
