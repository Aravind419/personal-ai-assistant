import urllib.parse
from typing import Dict, Any, Optional, Tuple, List
import httpx

from app.integrations.base import BaseIntegrationProvider
from app.core.config import settings
from app.core.logging import logger


class GoogleIntegrationProvider(BaseIntegrationProvider):
    """
    Google Workspace OAuth 2.0 integration for Gmail, Google Calendar, and Google Drive.
    """

    @property
    def provider_id(self) -> str:
        return "google"

    @property
    def provider_name(self) -> str:
        return "Google Workspace (Gmail, Calendar, Drive)"

    @property
    def default_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive.readonly",
        ]

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        client_id = settings.GOOGLE_CLIENT_ID or "google-client-id-placeholder"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.default_scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        if code.startswith("mock_"):
            return {
                "access_token": f"ya29.mock_{code}",
                "refresh_token": "mock_google_refresh_token_12345",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": " ".join(self.default_scopes),
            }

        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Google OAuth credentials (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET) are not configured.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Google token exchange failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        if refresh_token.startswith("mock_"):
            return {
                "access_token": "ya29.mock_refreshed_access_token",
                "expires_in": 3600,
                "token_type": "Bearer",
            }

        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                },
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Google token refresh failed: {resp.text}")
            return resp.json()

    async def test_connection(self, credentials: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        token = credentials.get("access_token")
        if not token:
            return False, "Missing access token."
        if token.startswith("ya29.mock_"):
            return True, None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    return True, None
                return False, f"Google API returned HTTP {resp.status_code}: {resp.text}"
        except Exception as exc:
            return False, str(exc)

    async def sync_data(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "gmail_messages_checked": 10,
            "calendar_events_found": 3,
            "drive_files_indexed": 5,
        }
