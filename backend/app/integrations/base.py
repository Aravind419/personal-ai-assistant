import abc
import enum
import json
import uuid
import datetime
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.automation import IntegrationConnection, IntegrationSyncLog
from app.core.security import encrypt_secret, decrypt_secret, mask_secret
from app.core.exceptions import ResourceNotFoundException, ValidationException, SecurityException
from app.core.logging import logger
from app.core.config import settings


class IntegrationCategory(str, enum.Enum):
    GOOGLE = "google"
    DEVELOPER = "developer"
    MICROSOFT = "microsoft"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    STORAGE = "storage"
    DESIGN = "design"
    OTHER = "other"


class IntegrationStatus(str, enum.Enum):
    NOT_CONNECTED = "not_connected"
    CONFIGURATION_REQUIRED = "configuration_required"
    AUTHORIZATION_PENDING = "authorization_pending"
    CONNECTED = "connected"
    CONNECTED_WITH_LIMITED_SCOPES = "connected_with_limited_scopes"
    TOKEN_EXPIRED = "token_expired"
    REAUTHORIZATION_REQUIRED = "reauthorization_required"
    CONNECTION_ERROR = "connection_error"
    DISCONNECTED = "disconnected"
    PLANNED = "planned"


class IntegrationStatusResponse(BaseModel):
    service_id: str
    service_name: str
    provider_family: str
    category: str
    description: str
    icon_name: str
    status: str
    is_configured: bool
    account_identity: Optional[str] = None
    required_scopes: List[str] = []
    granted_scopes: List[str] = []
    capabilities: List[str] = []
    token_expires_at: Optional[datetime.datetime] = None
    last_successful_connection: Optional[datetime.datetime] = None
    last_error: Optional[str] = None


class BaseIntegrationService(abc.ABC):
    """
    Abstract contract for an independent external service integration
    (e.g., Gmail, Google Drive, Google Calendar, GitHub, etc.).
    """

    @property
    @abc.abstractmethod
    def service_id(self) -> str:
        """Unique identifier (e.g. 'google_gmail', 'google_drive', 'github')."""
        pass

    @property
    @abc.abstractmethod
    def service_name(self) -> str:
        """Human-readable service title."""
        pass

    @property
    @abc.abstractmethod
    def provider_family(self) -> str:
        """Parent provider family ('google', 'github', 'microsoft', etc.)."""
        pass

    @property
    @abc.abstractmethod
    def category(self) -> IntegrationCategory:
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def icon_name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def required_scopes(self) -> List[str]:
        pass

    @property
    def optional_scopes(self) -> List[str]:
        return []

    @property
    @abc.abstractmethod
    def capabilities(self) -> List[str]:
        pass

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Checks if developer credentials (e.g. Client ID & Secret) are present in environment."""
        pass

    @abc.abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Generates the official OAuth authorization URL."""
        pass

    @abc.abstractmethod
    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Runs a real probe against the service's official API."""
        pass

    async def get_status(self, db: AsyncSession) -> IntegrationStatusResponse:
        """
        Calculates the real, granular status of this specific service.
        Never pretends a service is connected without valid credentials,
        granted scopes, and successful API verification.
        """
        configured = self.is_configured()
        if not configured:
            return IntegrationStatusResponse(
                service_id=self.service_id,
                service_name=self.service_name,
                provider_family=self.provider_family,
                category=self.category.value,
                description=self.description,
                icon_name=self.icon_name,
                status=IntegrationStatus.CONFIGURATION_REQUIRED.value,
                is_configured=False,
                required_scopes=self.required_scopes,
                capabilities=self.capabilities,
                last_error="API client credentials (Client ID and Client Secret) are not configured in environment.",
            )

        conn = await IntegrationManager.get_connection(db, self.provider_family)
        if not conn or conn.status == "disconnected" or not conn.encrypted_credentials:
            return IntegrationStatusResponse(
                service_id=self.service_id,
                service_name=self.service_name,
                provider_family=self.provider_family,
                category=self.category.value,
                description=self.description,
                icon_name=self.icon_name,
                status=IntegrationStatus.NOT_CONNECTED.value,
                is_configured=True,
                required_scopes=self.required_scopes,
                capabilities=self.capabilities,
            )

        # Inspect granted scopes
        granted = json.loads(conn.granted_scopes) if conn.granted_scopes else []
        has_required_scopes = all(scope in granted for scope in self.required_scopes)

        account_email = conn.user_identity if conn.user_identity != "personal_user" else None
        creds = await IntegrationManager.get_decrypted_credentials(conn)
        if not account_email and "account_email" in creds:
            account_email = creds["account_email"]

        if not has_required_scopes:
            return IntegrationStatusResponse(
                service_id=self.service_id,
                service_name=self.service_name,
                provider_family=self.provider_family,
                category=self.category.value,
                description=self.description,
                icon_name=self.icon_name,
                status=IntegrationStatus.CONNECTED_WITH_LIMITED_SCOPES.value,
                is_configured=True,
                account_identity=account_email,
                required_scopes=self.required_scopes,
                granted_scopes=granted,
                capabilities=self.capabilities,
                token_expires_at=conn.token_expires_at,
                last_successful_connection=conn.last_successful_connection,
                last_error=f"Google account is connected, but required scopes for {self.service_name} were not granted.",
            )

        # Proactively check token health / expiration
        now = datetime.datetime.now(datetime.timezone.utc)
        if conn.token_expires_at and conn.token_expires_at < now:
            # Attempt token refresh
            refresh_success = await IntegrationManager.refresh_provider_token(db, self.provider_family)
            if not refresh_success:
                return IntegrationStatusResponse(
                    service_id=self.service_id,
                    service_name=self.service_name,
                    provider_family=self.provider_family,
                    category=self.category.value,
                    description=self.description,
                    icon_name=self.icon_name,
                    status=IntegrationStatus.REAUTHORIZATION_REQUIRED.value,
                    is_configured=True,
                    account_identity=account_email,
                    required_scopes=self.required_scopes,
                    granted_scopes=granted,
                    capabilities=self.capabilities,
                    token_expires_at=conn.token_expires_at,
                    last_error="Access token expired and automatic refresh failed. Please reconnect.",
                )

        # Run connection test
        success, error, meta = await self.test_connection(db)
        status_val = IntegrationStatus.CONNECTED.value if success else IntegrationStatus.CONNECTION_ERROR.value

        return IntegrationStatusResponse(
            service_id=self.service_id,
            service_name=self.service_name,
            provider_family=self.provider_family,
            category=self.category.value,
            description=self.description,
            icon_name=self.icon_name,
            status=status_val,
            is_configured=True,
            account_identity=account_email,
            required_scopes=self.required_scopes,
            granted_scopes=granted,
            capabilities=self.capabilities,
            token_expires_at=conn.token_expires_at,
            last_successful_connection=conn.last_successful_connection if success else None,
            last_error=error,
        )


class PlannedIntegrationService(BaseIntegrationService):
    """Placeholder service for upcoming roadmap integrations."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        provider_family: str,
        category: IntegrationCategory,
        description: str,
        icon_name: str,
        capabilities: List[str],
    ):
        self._id = service_id
        self._name = service_name
        self._family = provider_family
        self._category = category
        self._desc = description
        self._icon = icon_name
        self._caps = capabilities

    @property
    def service_id(self) -> str:
        return self._id

    @property
    def service_name(self) -> str:
        return self._name

    @property
    def provider_family(self) -> str:
        return self._family

    @property
    def category(self) -> IntegrationCategory:
        return self._category

    @property
    def description(self) -> str:
        return self._desc

    @property
    def icon_name(self) -> str:
        return self._icon

    @property
    def required_scopes(self) -> List[str]:
        return []

    @property
    def capabilities(self) -> List[str]:
        return self._caps

    def is_configured(self) -> bool:
        return False

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        raise NotImplementedError(f"{self.service_name} integration is planned.")

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        return False, "Integration is planned on roadmap.", None

    async def get_status(self, db: AsyncSession) -> IntegrationStatusResponse:
        return IntegrationStatusResponse(
            service_id=self.service_id,
            service_name=self.service_name,
            provider_family=self.provider_family,
            category=self.category.value,
            description=self.description,
            icon_name=self.icon_name,
            status=IntegrationStatus.PLANNED.value,
            is_configured=False,
            required_scopes=[],
            granted_scopes=[],
            capabilities=self.capabilities,
            last_error="Planned for upcoming roadmap release.",
        )


class IntegrationRegistry:
    """Central registry of supported and planned integration services."""
    _services: Dict[str, BaseIntegrationService] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, service: BaseIntegrationService):
        cls._services[service.service_id] = service
        logger.info(f"Registered integration service: {service.service_id} ({service.service_name})")

    @classmethod
    def _ensure_defaults(cls):
        if not cls._initialized:
            try:
                from app.integrations.google_services import (
                    GmailIntegrationService,
                    GoogleDriveIntegrationService,
                    GoogleCalendarIntegrationService,
                    GoogleDocsIntegrationService,
                    GoogleSheetsIntegrationService,
                    GoogleSlidesIntegrationService,
                    GoogleTasksIntegrationService,
                    GoogleContactsIntegrationService,
                )
                from app.integrations.github import GitHubIntegrationService

                # Register Google Independent Services
                cls.register(GmailIntegrationService())
                cls.register(GoogleDriveIntegrationService())
                cls.register(GoogleCalendarIntegrationService())
                cls.register(GoogleDocsIntegrationService())
                cls.register(GoogleSheetsIntegrationService())
                cls.register(GoogleSlidesIntegrationService())
                cls.register(GoogleTasksIntegrationService())
                cls.register(GoogleContactsIntegrationService())

                # Register GitHub
                cls.register(GitHubIntegrationService())

                # Register Planned Integrations
                cls.register(PlannedIntegrationService(
                    "microsoft_outlook", "Microsoft Outlook", "microsoft", IntegrationCategory.COMMUNICATION,
                    "Read, draft, and send emails via Microsoft Graph API.", "outlook",
                    ["List emails", "Search inbox", "Send email", "Manage calendar invites"]
                ))
                cls.register(PlannedIntegrationService(
                    "microsoft_onedrive", "Microsoft OneDrive", "microsoft", IntegrationCategory.STORAGE,
                    "Access documents, files, and folders across Microsoft OneDrive cloud.", "onedrive",
                    ["Search files", "Read documents", "Upload files", "Folder management"]
                ))
                cls.register(PlannedIntegrationService(
                    "microsoft_calendar", "Microsoft Calendar", "microsoft", IntegrationCategory.PRODUCTIVITY,
                    "Schedule meetings, check free/busy availability on Outlook Calendar.", "calendar",
                    ["List events", "Create meetings", "Availability check", "Reschedule events"]
                ))
                cls.register(PlannedIntegrationService(
                    "slack", "Slack", "slack", IntegrationCategory.COMMUNICATION,
                    "Read channel messages, send notifications, and collaborate in Slack workspaces.", "slack",
                    ["Read channels", "Post messages", "Search chat history", "Direct messages"]
                ))
                cls.register(PlannedIntegrationService(
                    "notion", "Notion", "notion", IntegrationCategory.PRODUCTIVITY,
                    "Query Notion databases, read and create pages, manage personal knowledgebase.", "notion",
                    ["Query databases", "Read pages", "Create notes", "Update blocks"]
                ))
                cls.register(PlannedIntegrationService(
                    "canva", "Canva", "canva", IntegrationCategory.DESIGN,
                    "Create and manage visual designs, assets, and branding via Canva Connect API.", "canva",
                    ["List designs", "Create design asset", "Export artwork"]
                ))
                cls.register(PlannedIntegrationService(
                    "dropbox", "Dropbox", "dropbox", IntegrationCategory.STORAGE,
                    "Sync, browse, and manage files in Dropbox cloud storage.", "dropbox",
                    ["List files", "Read documents", "Upload content"]
                ))
                cls.register(PlannedIntegrationService(
                    "trello", "Trello", "trello", IntegrationCategory.PRODUCTIVITY,
                    "Manage Kanban boards, lists, and task cards.", "trello",
                    ["List boards", "Create cards", "Move cards"]
                ))
                cls.register(PlannedIntegrationService(
                    "linear", "Linear", "linear", IntegrationCategory.DEVELOPER,
                    "Track software issues, cycles, and team project roadmaps.", "linear",
                    ["List issues", "Create bug report", "Assign issue"]
                ))
                cls.register(PlannedIntegrationService(
                    "discord", "Discord", "discord", IntegrationCategory.COMMUNICATION,
                    "Send server webhooks and interact with community Discord servers.", "discord",
                    ["Post to channel", "Read announcements"]
                ))

                cls._initialized = True
            except Exception as e:
                logger.warning(f"Error loading integration services: {e}", exc_info=True)

    @classmethod
    def get(cls, service_id: str) -> Optional[BaseIntegrationService]:
        cls._ensure_defaults()
        return cls._services.get(service_id)

    @classmethod
    def list_all(cls) -> List[BaseIntegrationService]:
        cls._ensure_defaults()
        return list(cls._services.values())

    @classmethod
    def list_by_category(cls, category: IntegrationCategory) -> List[BaseIntegrationService]:
        cls._ensure_defaults()
        return [s for s in cls._services.values() if s.category == category]


class IntegrationManager:
    """
    Manages encrypted credential storage, OAuth state verification,
    token lifecycle, automatic refresh, and connection states.
    """
    _oauth_states: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create_oauth_state(cls, provider_id: str, redirect_uri: str, service_id: Optional[str] = None) -> str:
        state = str(uuid.uuid4())
        cls._oauth_states[state] = {
            "provider_id": provider_id,
            "service_id": service_id or provider_id,
            "redirect_uri": redirect_uri,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        }
        return state

    @classmethod
    def verify_oauth_state(cls, state: str) -> Dict[str, Any]:
        data = cls._oauth_states.pop(state, None)
        if not data:
            raise SecurityException("Invalid or expired OAuth state parameter (CSRF protection failed).")
        now = datetime.datetime.now(datetime.timezone.utc)
        if (now - data["created_at"]).total_seconds() > 900:
            raise SecurityException("OAuth state has expired. Please re-initiate connection.")
        return data

    @classmethod
    async def get_connection(cls, db: AsyncSession, provider_id: str) -> Optional[IntegrationConnection]:
        stmt = select(IntegrationConnection).where(IntegrationConnection.provider_id == provider_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def get_decrypted_credentials(cls, connection: IntegrationConnection) -> Dict[str, Any]:
        if not connection.encrypted_credentials:
            return {}
        decrypted_json = decrypt_secret(connection.encrypted_credentials)
        if not decrypted_json:
            return {}
        try:
            return json.loads(decrypted_json)
        except Exception:
            return {}

    @classmethod
    async def get_valid_access_token(cls, db: AsyncSession, provider_family: str) -> Optional[str]:
        """
        Retrieves a valid access token for the provider family.
        Automatically triggers token refresh if expired and saves updated tokens.
        """
        conn = await cls.get_connection(db, provider_family)
        if not conn or conn.status == "disconnected" or not conn.encrypted_credentials:
            return None

        now = datetime.datetime.now(datetime.timezone.utc)
        creds = await cls.get_decrypted_credentials(conn)
        access_token = creds.get("access_token")

        # If token expires in less than 60 seconds, attempt proactive refresh
        if conn.token_expires_at and (conn.token_expires_at - now).total_seconds() < 60:
            logger.info(f"Access token for {provider_family} expiring soon; attempting refresh.")
            refreshed = await cls.refresh_provider_token(db, provider_family)
            if refreshed:
                # Reload refreshed credentials
                await db.refresh(conn)
                creds = await cls.get_decrypted_credentials(conn)
                access_token = creds.get("access_token")

        return access_token

    @classmethod
    async def refresh_provider_token(cls, db: AsyncSession, provider_family: str) -> bool:
        """
        Calls provider token endpoint with refresh_token to obtain a fresh access_token.
        """
        conn = await cls.get_connection(db, provider_family)
        if not conn or not conn.encrypted_credentials:
            return False

        creds = await cls.get_decrypted_credentials(conn)
        refresh_token = creds.get("refresh_token")
        if not refresh_token:
            logger.warning(f"Cannot refresh token for {provider_family}: missing refresh_token.")
            return False

        if provider_family == "google":
            from app.integrations.google_auth import GoogleOAuthHandler
            try:
                new_tokens = await GoogleOAuthHandler.refresh_access_token(refresh_token)
                creds["access_token"] = new_tokens["access_token"]
                if "refresh_token" in new_tokens and new_tokens["refresh_token"]:
                    creds["refresh_token"] = new_tokens["refresh_token"]

                now = datetime.datetime.now(datetime.timezone.utc)
                expires_in = int(new_tokens.get("expires_in", 3600))
                conn.token_expires_at = now + datetime.timedelta(seconds=expires_in)
                conn.encrypted_credentials = encrypt_secret(json.dumps(creds))
                conn.last_successful_connection = now
                conn.status = "connected"
                await db.commit()
                logger.info("Successfully refreshed Google access token.")
                return True
            except Exception as e:
                logger.error(f"Failed to refresh Google token: {e}")
                conn.status = "token_expired"
                conn.last_error = f"Token refresh failed: {str(e)}"
                await db.commit()
                return False

        return False

    @classmethod
    async def save_credentials(
        cls,
        db: AsyncSession,
        provider_id: str,
        provider_name: str,
        credentials: Dict[str, Any],
        granted_scopes: List[str],
        requested_scopes: Optional[List[str]] = None,
        account_email: Optional[str] = None,
    ) -> IntegrationConnection:
        conn = await cls.get_connection(db, provider_id)
        now = datetime.datetime.now(datetime.timezone.utc)

        # Preserve existing refresh_token if new one was omitted
        if conn and conn.encrypted_credentials:
            old_creds = await cls.get_decrypted_credentials(conn)
            if not credentials.get("refresh_token") and old_creds.get("refresh_token"):
                credentials["refresh_token"] = old_creds["refresh_token"]
            # Merge granted scopes
            if old_creds.get("granted_scopes"):
                all_scopes = set(granted_scopes).union(set(old_creds["granted_scopes"]))
                granted_scopes = list(all_scopes)

        if account_email:
            credentials["account_email"] = account_email

        enc_creds = encrypt_secret(json.dumps(credentials))

        # Parse token expiration
        expires_at = None
        if "expires_at" in credentials:
            try:
                expires_at = datetime.datetime.fromisoformat(credentials["expires_at"])
            except Exception:
                pass
        elif "expires_in" in credentials:
            expires_at = now + datetime.timedelta(seconds=int(credentials["expires_in"]))

        if not conn:
            conn = IntegrationConnection(
                id=str(uuid.uuid4()),
                provider_id=provider_id,
                provider_name=provider_name,
                status="connected",
                requested_scopes=json.dumps(requested_scopes or granted_scopes),
                granted_scopes=json.dumps(granted_scopes),
                encrypted_credentials=enc_creds,
                token_expires_at=expires_at,
                last_successful_connection=now,
                user_identity=account_email or "personal_user",
            )
            db.add(conn)
        else:
            conn.status = "connected"
            conn.granted_scopes = json.dumps(granted_scopes)
            if requested_scopes:
                conn.requested_scopes = json.dumps(requested_scopes)
            conn.encrypted_credentials = enc_creds
            conn.token_expires_at = expires_at
            conn.last_successful_connection = now
            conn.last_error = None
            if account_email:
                conn.user_identity = account_email

        await db.commit()
        await db.refresh(conn)
        logger.info(f"Saved encrypted credentials for provider '{provider_id}' ({account_email or 'unknown user'})")
        return conn

    @classmethod
    async def disconnect(cls, db: AsyncSession, provider_id: str) -> bool:
        conn = await cls.get_connection(db, provider_id)
        if not conn:
            raise ResourceNotFoundException(f"Integration '{provider_id}' not found.")

        conn.status = "disconnected"
        conn.encrypted_credentials = None
        conn.token_expires_at = None
        conn.last_error = None
        await db.commit()
        logger.info(f"Disconnected integration '{provider_id}' and wiped encrypted credentials.")
        return True
