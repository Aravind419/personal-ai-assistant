from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.base import BaseIntegrationService, IntegrationCategory, IntegrationManager
from app.integrations.google_auth import GoogleOAuthHandler
from app.integrations.google_client import GoogleApiClient
from app.core.logging import logger


class GmailIntegrationService(BaseIntegrationService):
    @property
    def service_id(self) -> str:
        return "google_gmail"

    @property
    def service_name(self) -> str:
        return "Gmail"

    @property
    def provider_family(self) -> str:
        return "google"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.GOOGLE

    @property
    def description(self) -> str:
        return "Read, search, draft, and send emails with thread context and attachments via official Gmail API."

    @property
    def icon_name(self) -> str:
        return "mail"

    @property
    def required_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ]

    @property
    def optional_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.compose",
        ]

    @property
    def capabilities(self) -> List[str]:
        return [
            "List recent and unread emails",
            "Search inbox with natural queries",
            "Read full message content and MIME parts",
            "View email threads and reply history",
            "Inspect and download attachments",
            "Draft replies and new messages",
            "Send emails with human-in-the-loop approval",
            "Label and trash messages",
        ]

    def is_configured(self) -> bool:
        return GoogleOAuthHandler.is_configured()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return GoogleOAuthHandler.get_authorization_url(state, redirect_uri, self.required_scopes)

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        token = await IntegrationManager.get_valid_access_token(db, "google")
        if not token:
            return False, "Google account is not connected.", None

        try:
            client = GoogleApiClient(token)
            profile = await client.gmail_get_profile()
            return True, None, {
                "email_address": profile.get("emailAddress"),
                "messages_total": profile.get("messagesTotal"),
                "threads_total": profile.get("threadsTotal"),
            }
        except Exception as e:
            logger.warning(f"Gmail test_connection failed: {e}")
            return False, f"Gmail API probe failed: {str(e)}", None


class GoogleDriveIntegrationService(BaseIntegrationService):
    @property
    def service_id(self) -> str:
        return "google_drive"

    @property
    def service_name(self) -> str:
        return "Google Drive"

    @property
    def provider_family(self) -> str:
        return "google"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.GOOGLE

    @property
    def description(self) -> str:
        return "Browse, search, read, download, and export cloud files, documents, and spreadsheets on Google Drive."

    @property
    def icon_name(self) -> str:
        return "hard-drive"

    @property
    def required_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.file",
        ]

    @property
    def capabilities(self) -> List[str]:
        return [
            "List and search files across folders",
            "Retrieve detailed file metadata",
            "Download binary documents, PDFs, and images",
            "Read and export Google Docs/Sheets to plain text",
            "Create new folders",
            "Upload files and document summaries",
            "Move, rename, and trash files",
        ]

    def is_configured(self) -> bool:
        return GoogleOAuthHandler.is_configured()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return GoogleOAuthHandler.get_authorization_url(state, redirect_uri, self.required_scopes)

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        token = await IntegrationManager.get_valid_access_token(db, "google")
        if not token:
            return False, "Google account is not connected.", None

        try:
            client = GoogleApiClient(token)
            about = await client.drive_get_about()
            quota = about.get("storageQuota", {})
            return True, None, {
                "user_name": about.get("user", {}).get("displayName"),
                "storage_used_bytes": quota.get("usage"),
                "storage_limit_bytes": quota.get("limit"),
            }
        except Exception as e:
            logger.warning(f"Google Drive test_connection failed: {e}")
            return False, f"Google Drive API probe failed: {str(e)}", None


class GoogleCalendarIntegrationService(BaseIntegrationService):
    @property
    def service_id(self) -> str:
        return "google_calendar"

    @property
    def service_name(self) -> str:
        return "Google Calendar"

    @property
    def provider_family(self) -> str:
        return "google"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.GOOGLE

    @property
    def description(self) -> str:
        return "Inspect meetings, find free availability windows, and schedule events with attendees and reminders."

    @property
    def icon_name(self) -> str:
        return "calendar"

    @property
    def required_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
        ]

    @property
    def capabilities(self) -> List[str]:
        return [
            "List today's, upcoming, and past calendar events",
            "Search events by keywords and attendees",
            "Check free/busy availability slots",
            "Schedule meetings with confirmation",
            "Update event times and locations",
            "Delete or cancel events with critical confirmation",
            "Quick add events from natural language expressions",
        ]

    def is_configured(self) -> bool:
        return GoogleOAuthHandler.is_configured()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return GoogleOAuthHandler.get_authorization_url(state, redirect_uri, self.required_scopes)

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        token = await IntegrationManager.get_valid_access_token(db, "google")
        if not token:
            return False, "Google account is not connected.", None

        try:
            client = GoogleApiClient(token)
            cals = await client.calendar_list_calendars()
            return True, None, {"calendar_count": len(cals)}
        except Exception as e:
            logger.warning(f"Google Calendar test_connection failed: {e}")
            return False, f"Google Calendar API probe failed: {str(e)}", None


class GoogleDocsIntegrationService(BaseIntegrationService):
    @property
    def service_id(self) -> str:
        return "google_docs"

    @property
    def service_name(self) -> str:
        return "Google Docs"

    @property
    def provider_family(self) -> str:
        return "google"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.GOOGLE

    @property
    def description(self) -> str:
        return "Create, read, and write Google Docs documents directly through official Google Docs v1 API."

    @property
    def icon_name(self) -> str:
        return "file-text"

    @property
    def required_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive.file",
        ]

    @property
    def capabilities(self) -> List[str]:
        return [
            "Read full Google Doc document structure",
            "Create new documents with title and body",
            "Insert text and append meeting notes",
            "Export document content to Markdown or text",
        ]

    def is_configured(self) -> bool:
        return GoogleOAuthHandler.is_configured()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return GoogleOAuthHandler.get_authorization_url(state, redirect_uri, self.required_scopes)

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        token = await IntegrationManager.get_valid_access_token(db, "google")
        if not token:
            return False, "Google account is not connected.", None

        try:
            # Probe Drive files endpoint for docs
            client = GoogleApiClient(token)
            files = await client.drive_list_files(query="mimeType = 'application/vnd.google-apps.document'", page_size=1)
            return True, None, {"sample_docs_found": len(files.get("files", []))}
        except Exception as e:
            return False, f"Google Docs probe failed: {str(e)}", None


class GoogleSheetsIntegrationService(BaseIntegrationService):
    @property
    def service_id(self) -> str:
        return "google_sheets"

    @property
    def service_name(self) -> str:
        return "Google Sheets"

    @property
    def provider_family(self) -> str:
        return "google"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.GOOGLE

    @property
    def description(self) -> str:
        return "Read table ranges, query tabular data, append rows, and update spreadsheet cells via Google Sheets v4 API."

    @property
    def icon_name(self) -> str:
        return "table"

    @property
    def required_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ]

    @property
    def capabilities(self) -> List[str]:
        return [
            "Read cell ranges and sheet metadata",
            "Query and filter spreadsheet tables",
            "Append new rows to tracking sheets",
            "Update cells and headers",
            "Generate structured expense or metric reports",
        ]

    def is_configured(self) -> bool:
        return GoogleOAuthHandler.is_configured()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return GoogleOAuthHandler.get_authorization_url(state, redirect_uri, self.required_scopes)

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        token = await IntegrationManager.get_valid_access_token(db, "google")
        if not token:
            return False, "Google account is not connected.", None

        try:
            client = GoogleApiClient(token)
            files = await client.drive_list_files(query="mimeType = 'application/vnd.google-apps.spreadsheet'", page_size=1)
            return True, None, {"sample_sheets_found": len(files.get("files", []))}
        except Exception as e:
            return False, f"Google Sheets probe failed: {str(e)}", None


class GoogleSlidesIntegrationService(BaseIntegrationService):
    @property
    def service_id(self) -> str:
        return "google_slides"

    @property
    def service_name(self) -> str:
        return "Google Slides"

    @property
    def provider_family(self) -> str:
        return "google"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.GOOGLE

    @property
    def description(self) -> str:
        return "Read slide presentations, extract deck text, and inspect presentation structure via Slides v1 API."

    @property
    def icon_name(self) -> str:
        return "presentation"

    @property
    def required_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/drive.file",
        ]

    @property
    def capabilities(self) -> List[str]:
        return [
            "Read slide titles and text shapes",
            "Inspect presentation slide count",
            "Create new presentations",
        ]

    def is_configured(self) -> bool:
        return GoogleOAuthHandler.is_configured()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return GoogleOAuthHandler.get_authorization_url(state, redirect_uri, self.required_scopes)

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        token = await IntegrationManager.get_valid_access_token(db, "google")
        if not token:
            return False, "Google account is not connected.", None

        try:
            client = GoogleApiClient(token)
            files = await client.drive_list_files(query="mimeType = 'application/vnd.google-apps.presentation'", page_size=1)
            return True, None, {"sample_slides_found": len(files.get("files", []))}
        except Exception as e:
            return False, f"Google Slides probe failed: {str(e)}", None


class GoogleTasksIntegrationService(BaseIntegrationService):
    @property
    def service_id(self) -> str:
        return "google_tasks"

    @property
    def service_name(self) -> str:
        return "Google Tasks"

    @property
    def provider_family(self) -> str:
        return "google"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.GOOGLE

    @property
    def description(self) -> str:
        return "Sync and manage your personal to-do lists, task items, due dates, and completed tasks."

    @property
    def icon_name(self) -> str:
        return "check-square"

    @property
    def required_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/tasks",
        ]

    @property
    def capabilities(self) -> List[str]:
        return [
            "List task lists",
            "List pending and completed tasks",
            "Create new tasks with due date",
            "Mark tasks complete",
            "Delete tasks",
        ]

    def is_configured(self) -> bool:
        return GoogleOAuthHandler.is_configured()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return GoogleOAuthHandler.get_authorization_url(state, redirect_uri, self.required_scopes)

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        token = await IntegrationManager.get_valid_access_token(db, "google")
        if not token:
            return False, "Google account is not connected.", None

        try:
            client = GoogleApiClient(token)
            lists = await client.tasks_list_tasklists()
            return True, None, {"tasklists_count": len(lists)}
        except Exception as e:
            return False, f"Google Tasks probe failed: {str(e)}", None


class GoogleContactsIntegrationService(BaseIntegrationService):
    @property
    def service_id(self) -> str:
        return "google_contacts"

    @property
    def service_name(self) -> str:
        return "Google Contacts"

    @property
    def provider_family(self) -> str:
        return "google"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.GOOGLE

    @property
    def description(self) -> str:
        return "Look up contact email addresses and names to assist with sending emails and calendar invitations."

    @property
    def icon_name(self) -> str:
        return "users"

    @property
    def required_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/contacts.readonly",
        ]

    @property
    def capabilities(self) -> List[str]:
        return [
            "Search contacts by name",
            "Retrieve verified contact emails",
        ]

    def is_configured(self) -> bool:
        return GoogleOAuthHandler.is_configured()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return GoogleOAuthHandler.get_authorization_url(state, redirect_uri, self.required_scopes)

    async def test_connection(self, db: AsyncSession) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        token = await IntegrationManager.get_valid_access_token(db, "google")
        if not token:
            return False, "Google account is not connected.", None

        # Return status based on token presence
        return True, None, {"status": "authorized"}
