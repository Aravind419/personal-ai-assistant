import json
import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.integrations.base import (
    IntegrationRegistry,
    IntegrationManager,
    IntegrationStatusResponse,
    IntegrationStatus,
    BaseIntegrationService,
)
from app.integrations.google_auth import GoogleOAuthHandler
from app.models.automation import IntegrationConnection, IntegrationSyncLog
from app.core.exceptions import ResourceNotFoundException, ValidationException, SecurityException
from app.core.config import settings
from app.core.logging import logger

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class AuthUrlResponse(BaseModel):
    service_id: str
    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str
    redirect_uri: Optional[str] = None


class SyncResponse(BaseModel):
    service_id: str
    status: str
    items_synced: int
    details: Dict[str, Any]


@router.get("", response_model=List[IntegrationStatusResponse])
async def list_integrations(
    category: Optional[str] = Query(None, description="Filter by category (google, developer, productivity, etc.)"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all supported and planned integration services with their
    granular, verified connection and health status.
    """
    services = IntegrationRegistry.list_all()

    if category:
        services = [s for s in services if s.category.value == category.lower()]

    if search:
        q = search.lower().strip()
        services = [
            s for s in services
            if q in s.service_name.lower() or q in s.description.lower() or q in s.service_id.lower()
        ]

    results: List[IntegrationStatusResponse] = []
    for s in services:
        status_resp = await s.get_status(db)
        results.append(status_resp)

    return results


@router.get("/categories")
async def list_categories():
    """List available integration categories."""
    return [
        {"id": "all", "label": "All Services"},
        {"id": "google", "label": "Google Workspace"},
        {"id": "developer", "label": "Developer Tools"},
        {"id": "communication", "label": "Communication"},
        {"id": "productivity", "label": "Productivity"},
        {"id": "storage", "label": "Storage"},
        {"id": "design", "label": "Design & Media"},
        {"id": "other", "label": "Other Services"},
    ]


@router.get("/{service_id}", response_model=IntegrationStatusResponse)
async def get_integration(
    service_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve verified status for a specific integration service."""
    # Map 'google' to 'google_gmail' as default or inspect directly
    target_id = "google_gmail" if service_id == "google" else service_id
    service = IntegrationRegistry.get(target_id)
    if not service:
        raise ResourceNotFoundException(f"Integration service '{service_id}' is not registered.")

    return await service.get_status(db)


@router.get("/{service_id}/auth-url", response_model=AuthUrlResponse)
async def get_authorization_url(
    service_id: str,
    redirect_uri: Optional[str] = Query(None),
):
    """
    Generates a cryptographically verified OAuth authorization URL
    for the specific integration service. Validates configuration.
    """
    target_id = "google_gmail" if service_id == "google" else service_id
    service = IntegrationRegistry.get(target_id)
    if not service:
        raise ResourceNotFoundException(f"Integration service '{service_id}' is not registered.")

    if not service.is_configured():
        family = service.provider_family.upper()
        raise ValidationException(
            f"OAuth credentials for {service.service_name} ({family}_CLIENT_ID and {family}_CLIENT_SECRET) "
            f"are not configured in the backend environment. Please configure them in backend/.env before connecting."
        )

    provider_family = service.provider_family
    default_redirect = (
        settings.GOOGLE_REDIRECT_URI if provider_family == "google" else settings.GITHUB_REDIRECT_URI
    )
    target_redirect = redirect_uri or default_redirect
    state = IntegrationManager.create_oauth_state(provider_family, target_redirect, service_id=target_id)

    auth_url = service.get_authorization_url(state=state, redirect_uri=target_redirect)
    return AuthUrlResponse(service_id=target_id, authorization_url=auth_url, state=state)


@router.get("/google/callback", response_class=HTMLResponse)
async def handle_google_oauth_browser_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handles Google OAuth redirect in browser, exchanges authorization code,
    verifies user profile, saves encrypted tokens, and communicates success.
    """
    if error:
        logger.warning(f"Google OAuth denied or returned error: {error} - {error_description}")
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Authentication Failed</title></head>
        <body style="font-family:sans-serif;text-align:center;padding:50px;">
            <h2 style="color:#ef4444;">Google Authorization Cancelled</h2>
            <p>{error_description or error}</p>
            <p>You can close this window and try again from the Integrations page.</p>
            <script>setTimeout(() => window.close(), 4000);</script>
        </body>
        </html>
        """, status_code=400)

    if not code or not state:
        raise ValidationException("Missing code or state parameter in OAuth callback.")

    state_data = IntegrationManager.verify_oauth_state(state)
    redirect_uri = state_data.get("redirect_uri", settings.GOOGLE_REDIRECT_URI)

    # Exchange code for tokens
    tokens = await GoogleOAuthHandler.exchange_code(code, redirect_uri)
    access_token = tokens.get("access_token")
    granted_scopes = tokens.get("scope", "").split()

    # Retrieve account email
    profile = await GoogleOAuthHandler.fetch_user_profile(access_token)
    account_email = profile.get("email")

    await IntegrationManager.save_credentials(
        db=db,
        provider_id="google",
        provider_name="Google Workspace",
        credentials=tokens,
        granted_scopes=granted_scopes,
        account_email=account_email,
    )

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head><title>Authentication Succeeded</title></head>
    <body style="font-family:sans-serif;text-align:center;padding:50px;background:#0f172a;color:#f8fafc;">
        <h2 style="color:#10b981;">Google Account Connected!</h2>
        <p>Authorized as: <strong>{account_email or 'Google User'}</strong></p>
        <p>Your encrypted credentials have been securely stored. Redirecting to Assistant...</p>
        <script>
            if (window.opener) {{
                window.opener.postMessage({{ type: 'OAUTH_SUCCESS', provider: 'google', email: '{account_email}' }}, '*');
                setTimeout(() => window.close(), 1500);
            }} else {{
                setTimeout(() => {{ window.location.href = 'http://localhost:5173'; }}, 1500);
            }}
        </script>
    </body>
    </html>
    """)


@router.get("/github/callback", response_class=HTMLResponse)
async def handle_github_oauth_browser_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handles GitHub OAuth redirect in browser."""
    if error:
        return HTMLResponse(content=f"<h2>GitHub Auth Error</h2><p>{error_description or error}</p>", status_code=400)

    if not code or not state:
        raise ValidationException("Missing code or state parameter in GitHub OAuth callback.")

    state_data = IntegrationManager.verify_oauth_state(state)
    redirect_uri = state_data.get("redirect_uri", settings.GITHUB_REDIRECT_URI)

    github_svc = IntegrationRegistry.get("github")
    tokens = await github_svc.exchange_code(code, redirect_uri)
    granted_scopes = tokens.get("scope", "").split(",")

    # Fetch GitHub username
    conn = await IntegrationManager.save_credentials(
        db=db,
        provider_id="github",
        provider_name="GitHub",
        credentials=tokens,
        granted_scopes=granted_scopes,
    )

    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head><title>GitHub Connected</title></head>
    <body style="font-family:sans-serif;text-align:center;padding:50px;background:#0f172a;color:#f8fafc;">
        <h2 style="color:#10b981;">GitHub Connected Successfully!</h2>
        <script>
            if (window.opener) {
                window.opener.postMessage({ type: 'OAUTH_SUCCESS', provider: 'github' }, '*');
                setTimeout(() => window.close(), 1500);
            } else {
                setTimeout(() => { window.location.href = 'http://localhost:5173'; }, 1500);
            }
        </script>
    </body>
    </html>
    """)


@router.post("/{provider_id}/callback", response_model=IntegrationStatusResponse)
async def handle_oauth_callback(
    provider_id: str,
    payload: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Programmatic token exchange endpoint for API callers and tests.
    Validates CSRF state and exchanges code for real tokens.
    """
    state_data = IntegrationManager.verify_oauth_state(payload.state)
    redirect_uri = payload.redirect_uri or state_data.get("redirect_uri", "")

    if provider_id == "google" or provider_id.startswith("google_"):
        tokens = await GoogleOAuthHandler.exchange_code(payload.code, redirect_uri)
        granted_scopes = tokens.get("scope", "").split()
        profile = await GoogleOAuthHandler.fetch_user_profile(tokens.get("access_token", ""))
        account_email = profile.get("email")

        conn = await IntegrationManager.save_credentials(
            db=db,
            provider_id="google",
            provider_name="Google Workspace",
            credentials=tokens,
            granted_scopes=granted_scopes,
            account_email=account_email,
        )
        svc = IntegrationRegistry.get("google_gmail")
        return await svc.get_status(db)

    elif provider_id == "github":
        svc = IntegrationRegistry.get("github")
        tokens = await svc.exchange_code(payload.code, redirect_uri)
        granted_scopes = tokens.get("scope", "").split(",")

        conn = await IntegrationManager.save_credentials(
            db=db,
            provider_id="github",
            provider_name="GitHub",
            credentials=tokens,
            granted_scopes=granted_scopes,
        )
        return await svc.get_status(db)

    else:
        raise ResourceNotFoundException(f"Provider '{provider_id}' is not supported for OAuth exchange.")


@router.post("/{service_id}/disconnect", status_code=status.HTTP_200_OK)
async def disconnect_integration(
    service_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Disconnects the service/provider family and wipes encrypted tokens."""
    target_id = "google_gmail" if service_id == "google" else service_id
    service = IntegrationRegistry.get(target_id)
    provider_family = service.provider_family if service else service_id

    await IntegrationManager.disconnect(db, provider_family)
    return {"disconnected": True, "service_id": service_id, "provider_family": provider_family}


@router.post("/{service_id}/test", status_code=status.HTTP_200_OK)
async def test_integration_connection(
    service_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Tests credentials directly against the service's official API."""
    target_id = "google_gmail" if service_id == "google" else service_id
    service = IntegrationRegistry.get(target_id)
    if not service:
        raise ResourceNotFoundException(f"Integration service '{service_id}' not found.")

    success, error, meta = await service.test_connection(db)
    if not success:
        return {"connected": False, "service_id": service_id, "error": error}

    return {"connected": True, "service_id": service_id, "message": "API verified successfully.", "details": meta}


@router.post("/{service_id}/sync", response_model=SyncResponse)
async def sync_integration_data(
    service_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Runs data sync audit for an integration service."""
    target_id = "google_gmail" if service_id == "google" else service_id
    service = IntegrationRegistry.get(target_id)
    if not service:
        raise ResourceNotFoundException(f"Integration service '{service_id}' not found.")

    conn = await IntegrationManager.get_connection(db, service.provider_family)
    if not conn or conn.status != "connected":
        raise ValidationException("Cannot sync an integration that is not connected.")

    # Probe service to calculate synced count
    success, error, meta = await service.test_connection(db)
    items_count = 1 if success else 0
    if meta:
        for k, v in meta.items():
            if isinstance(v, int):
                items_count += v

    sync_log = IntegrationSyncLog(
        connection_id=conn.id,
        service_name=service_id,
        status="succeeded" if success else "failed",
        items_synced=items_count,
        error_details=error,
    )
    db.add(sync_log)
    await db.commit()

    return SyncResponse(
        service_id=service_id,
        status="succeeded" if success else "failed",
        items_synced=items_count,
        details=meta or {},
    )
