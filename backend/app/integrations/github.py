import urllib.parse
from typing import Dict, Any, Optional, Tuple, List
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.base import BaseIntegrationService, IntegrationCategory, IntegrationManager
from app.core.config import settings
from app.core.exceptions import ValidationException
from app.core.logging import logger


class GitHubIntegrationService(BaseIntegrationService):
    """
    GitHub OAuth integration for repository, issue, and pull request tracking.
    """

    @property
    def service_id(self) -> str:
        return "github"

    @property
    def service_name(self) -> str:
        return "GitHub"

    @property
    def provider_family(self) -> str:
        return "github"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.DEVELOPER

    @property
    def description(self) -> str:
        return "Inspect repositories, search issues, track pull requests, and create issues with approval."

    @property
    def icon_name(self) -> str:
        return "git-branch"

    @property
    def required_scopes(self) -> List[str]:
        return ["repo", "read:user"]

    @property
    def capabilities(self) -> List[str]:
        return [
            "List user and organization repositories",
            "Search and inspect issues and comments",
            "List pull requests and review statuses",
            "Create new repository issues with approval",
            "Inspect repository recent activity",
        ]

    def is_configured(self) -> bool:
        cid = settings.GITHUB_CLIENT_ID
        csec = settings.GITHUB_CLIENT_SECRET
        return bool(cid and csec and cid.strip() and csec.strip() and not cid.startswith("github-client-id"))

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        if not self.is_configured():
            raise ValidationException(
                "GitHub OAuth credentials are not configured. "
                "Please configure GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in backend/.env. "
                "Refer to docs/integrations/GITHUB_SETUP.md for instructions."
            )

        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.required_scopes),
            "state": state,
        }
        return f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValidationException("GitHub OAuth credentials are not configured.")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
            if resp.status_code != 200:
                raise RuntimeError(f"GitHub token exchange failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"GitHub OAuth error: {data.get('error_description') or data['error']}")
            return data

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        token = await IntegrationManager.get_valid_access_token(db, "github")
        if not token:
            return False, "GitHub account is not connected.", None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Personal-AI-Assistant",
                    },
                )
                if resp.status_code == 200:
                    user_data = resp.json()
                    return True, None, {
                        "login": user_data.get("login"),
                        "name": user_data.get("name"),
                        "public_repos": user_data.get("public_repos"),
                    }
                return False, f"GitHub API returned HTTP {resp.status_code}: {resp.text}", None
        except Exception as exc:
            return False, str(exc), None
