import html
import re
import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ToolRegistry
from app.tools.schemas import PermissionLevel, ToolCategory
from app.integrations.base import IntegrationManager
from app.integrations.google_client import GoogleApiClient, _sanitize_text
from app.database.session import async_session_factory
from app.core.logging import logger
import httpx


# ============================================================================
#                               GMAIL TOOLS
# ============================================================================

class GmailGetProfileTool(BaseTool):
    @property
    def id(self) -> str:
        return "gmail_get_profile"

    @property
    def name(self) -> str:
        return "Get Gmail Profile"

    @property
    def description(self) -> str:
        return "Retrieves the authenticated Gmail account email address, total messages, and threads."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATION

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def run(self, **arguments) -> Any:
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {
                    "connected": False,
                    "message": "Gmail is not connected. Please connect your Google account in Integrations.",
                }
            try:
                client = GoogleApiClient(token)
                profile = await client.gmail_get_profile()
                return {"connected": True, "profile": profile}
            except Exception as e:
                return {"connected": True, "error": f"Gmail API error: {str(e)}"}


class GmailListMessagesTool(BaseTool):
    @property
    def id(self) -> str:
        return "gmail_list_messages"

    @property
    def name(self) -> str:
        return "List Gmail Messages"

    @property
    def description(self) -> str:
        return "Retrieves recent emails matching a query (e.g. 'is:unread', 'from:google', 'invoice')."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATION

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "default": "is:unread", "description": "Gmail search query expression"},
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 25},
            },
        }

    async def run(self, **arguments) -> Any:
        query = arguments.get("query", "is:unread")
        max_results = min(int(arguments.get("max_results", 5)), 25)

        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {
                    "connected": False,
                    "message": "Gmail is not connected. Connect your Google account in Integrations to search live emails.",
                    "emails": [],
                }
            try:
                client = GoogleApiClient(token)
                res = await client.gmail_list_messages(query=query, max_results=max_results)
                message_ids = [m["id"] for m in res.get("messages", [])]
                if not message_ids:
                    return {"connected": True, "query": query, "count": 0, "emails": [], "message": "No matching emails found."}

                # Fetch full metadata for each message
                emails = []
                for mid in message_ids:
                    try:
                        msg = await client.gmail_get_message(mid, format_="full")
                        emails.append(msg)
                    except Exception as err:
                        logger.warning(f"Failed to fetch details for msg {mid}: {err}")

                return {
                    "connected": True,
                    "query": query,
                    "count": len(emails),
                    "result_size_estimate": res.get("resultSizeEstimate", len(emails)),
                    "emails": emails,
                }
            except Exception as e:
                return {"connected": True, "error": f"Gmail API call failed: {str(e)}", "emails": []}


class GmailReadMessageTool(BaseTool):
    @property
    def id(self) -> str:
        return "gmail_read_message"

    @property
    def name(self) -> str:
        return "Read Gmail Message Content"

    @property
    def description(self) -> str:
        return "Reads full body text, headers, and attachment names of a specific Gmail message by ID."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATION

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["message_id"],
            "properties": {
                "message_id": {"type": "string", "description": "The unique Gmail message ID"},
            },
        }

    async def run(self, **arguments) -> Any:
        msg_id = arguments.get("message_id")
        if not msg_id:
            return {"error": "Missing required parameter 'message_id'"}

        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Gmail is not connected."}
            try:
                client = GoogleApiClient(token)
                msg = await client.gmail_get_message(msg_id)
                return {"connected": True, "message": msg}
            except Exception as e:
                return {"connected": True, "error": f"Failed to retrieve email: {str(e)}"}


class GmailGetThreadTool(BaseTool):
    @property
    def id(self) -> str:
        return "gmail_get_thread"

    @property
    def name(self) -> str:
        return "Get Gmail Thread"

    @property
    def description(self) -> str:
        return "Retrieves all sequential messages and replies in a Gmail conversation thread."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATION

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["thread_id"],
            "properties": {
                "thread_id": {"type": "string", "description": "The Gmail thread ID"},
            },
        }

    async def run(self, **arguments) -> Any:
        thread_id = arguments.get("thread_id")
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Gmail is not connected."}
            try:
                client = GoogleApiClient(token)
                thread = await client.gmail_get_thread(thread_id)
                return {"connected": True, "thread": thread}
            except Exception as e:
                return {"connected": True, "error": f"Failed to retrieve thread: {str(e)}"}


class GmailCreateDraftTool(BaseTool):
    @property
    def id(self) -> str:
        return "gmail_create_draft"

    @property
    def name(self) -> str:
        return "Create Gmail Draft"

    @property
    def description(self) -> str:
        return "Creates a draft email in your Gmail mailbox without sending it."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATION

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SENSITIVE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["to", "subject", "body"],
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Body text of the email"},
                "thread_id": {"type": "string", "description": "Optional thread ID to draft a reply"},
            },
        }

    async def run(self, **arguments) -> Any:
        to = arguments.get("to")
        subject = arguments.get("subject")
        body = arguments.get("body")
        thread_id = arguments.get("thread_id")

        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Gmail is not connected."}
            try:
                client = GoogleApiClient(token)
                draft = await client.gmail_create_draft(to=to, subject=subject, body=body, thread_id=thread_id)
                return {
                    "connected": True,
                    "draft_id": draft.get("id"),
                    "status": "draft_created",
                    "recipient": to,
                    "subject": subject,
                }
            except Exception as e:
                return {"connected": True, "error": f"Failed to create draft: {str(e)}"}


class GmailSendMessageTool(BaseTool):
    @property
    def id(self) -> str:
        return "gmail_send_message"

    @property
    def name(self) -> str:
        return "Send Gmail Message"

    @property
    def description(self) -> str:
        return "Sends an email via Gmail API. Requires explicit user approval before sending."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATION

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SENSITIVE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["to", "subject", "body"],
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Body text of the email"},
                "thread_id": {"type": "string", "description": "Optional thread ID to reply to"},
            },
        }

    async def run(self, **arguments) -> Any:
        to = arguments.get("to")
        subject = arguments.get("subject")
        body = arguments.get("body")
        thread_id = arguments.get("thread_id")

        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Gmail is not connected. Connect Google in Integrations."}
            try:
                client = GoogleApiClient(token)
                resp = await client.gmail_send_message(to=to, subject=subject, body=body, thread_id=thread_id)
                return {
                    "connected": True,
                    "status": "sent",
                    "message_id": resp.get("id"),
                    "thread_id": resp.get("threadId"),
                    "recipient": to,
                    "subject": subject,
                }
            except Exception as e:
                return {"connected": True, "error": f"Failed to send email: {str(e)}"}


class GmailTrashMessageTool(BaseTool):
    @property
    def id(self) -> str:
        return "gmail_trash_message"

    @property
    def name(self) -> str:
        return "Trash Gmail Message"

    @property
    def description(self) -> str:
        return "Moves a message to the Gmail Trash folder. Requires critical approval."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATION

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CRITICAL

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["message_id"],
            "properties": {
                "message_id": {"type": "string"},
            },
        }

    async def run(self, **arguments) -> Any:
        msg_id = arguments.get("message_id")
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Gmail is not connected."}
            try:
                client = GoogleApiClient(token)
                res = await client.gmail_trash_message(msg_id)
                return {"connected": True, "trashed": True, "message_id": msg_id}
            except Exception as e:
                return {"connected": True, "error": f"Failed to trash message: {str(e)}"}


# ============================================================================
#                               GOOGLE DRIVE TOOLS
# ============================================================================

class GoogleDriveListFilesTool(BaseTool):
    @property
    def id(self) -> str:
        return "drive_list_files"

    @property
    def name(self) -> str:
        return "List Google Drive Files"

    @property
    def description(self) -> str:
        return "Searches and lists documents, spreadsheets, PDFs, and folders in your Google Drive."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.STORAGE

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Drive search query or keyword"},
                "page_size": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            },
        }

    async def run(self, **arguments) -> Any:
        query_param = arguments.get("query")
        page_size = min(int(arguments.get("page_size", 10)), 50)

        # Build drive query
        q = "trashed = false"
        if query_param:
            escaped = query_param.replace("'", "\\'")
            q += f" and (name contains '{escaped}' or fullText contains '{escaped}')"

        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {
                    "connected": False,
                    "message": "Google Drive is not connected. Connect Google in Integrations to browse cloud files.",
                    "files": [],
                }
            try:
                client = GoogleApiClient(token)
                res = await client.drive_list_files(query=q, page_size=page_size)
                files = res.get("files", [])
                return {
                    "connected": True,
                    "count": len(files),
                    "files": files,
                }
            except Exception as e:
                return {"connected": True, "error": f"Drive API failed: {str(e)}", "files": []}


class GoogleDriveReadFileTool(BaseTool):
    @property
    def id(self) -> str:
        return "drive_read_file"

    @property
    def name(self) -> str:
        return "Read Google Drive File"

    @property
    def description(self) -> str:
        return "Reads the text contents of a file on Google Drive (plain text or exported Google Doc)."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.STORAGE

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["file_id"],
            "properties": {
                "file_id": {"type": "string", "description": "Google Drive file ID"},
            },
        }

    async def run(self, **arguments) -> Any:
        file_id = arguments.get("file_id")
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Google Drive is not connected."}
            try:
                client = GoogleApiClient(token)
                meta = await client.drive_get_file_metadata(file_id)
                mime = meta.get("mimeType", "")
                name = meta.get("name", "Document")

                if mime == "application/vnd.google-apps.document":
                    text = await client.drive_export_doc(file_id, mime_type="text/plain")
                elif mime == "application/vnd.google-apps.spreadsheet":
                    text = await client.drive_export_doc(file_id, mime_type="text/csv")
                elif mime.startswith("text/"):
                    content_bytes = await client.drive_download_file(file_id)
                    text = content_bytes.decode("UTF-8", errors="replace")
                else:
                    return {
                        "connected": True,
                        "file_id": file_id,
                        "name": name,
                        "mimeType": mime,
                        "webViewLink": meta.get("webViewLink"),
                        "message": f"File is binary type ({mime}). It can be opened at the provided webViewLink.",
                    }

                return {
                    "connected": True,
                    "file_id": file_id,
                    "name": name,
                    "mimeType": mime,
                    "content": _sanitize_text(text),
                    "webViewLink": meta.get("webViewLink"),
                }
            except Exception as e:
                return {"connected": True, "error": f"Failed to read file from Drive: {str(e)}"}


class GoogleDriveUploadFileTool(BaseTool):
    @property
    def id(self) -> str:
        return "drive_upload_file"

    @property
    def name(self) -> str:
        return "Upload File to Google Drive"

    @property
    def description(self) -> str:
        return "Uploads a text or notes file to your Google Drive. Requires sensitive approval."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.STORAGE

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SENSITIVE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["filename", "content"],
            "properties": {
                "filename": {"type": "string", "description": "Target filename in Drive"},
                "content": {"type": "string", "description": "Text content to save"},
                "parent_id": {"type": "string", "description": "Optional parent folder ID"},
            },
        }

    async def run(self, **arguments) -> Any:
        filename = arguments.get("filename")
        content = arguments.get("content")
        parent_id = arguments.get("parent_id")

        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Google Drive is not connected."}
            try:
                client = GoogleApiClient(token)
                res = await client.drive_upload_text_file(name=filename, content=content, parent_id=parent_id)
                return {
                    "connected": True,
                    "file_id": res.get("id"),
                    "name": res.get("name"),
                    "status": "uploaded",
                }
            except Exception as e:
                return {"connected": True, "error": f"Upload failed: {str(e)}"}


# ============================================================================
#                            GOOGLE CALENDAR TOOLS
# ============================================================================

class GoogleCalendarListEventsTool(BaseTool):
    @property
    def id(self) -> str:
        return "calendar_list_events"

    @property
    def name(self) -> str:
        return "List Calendar Events"

    @property
    def description(self) -> str:
        return "Retrieves events scheduled on your Google Calendar for today or a specific time window."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.PRODUCTIVITY

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "description": "ISO timestamp for start of window (defaults to start of today)"},
                "time_max": {"type": "string", "description": "ISO timestamp for end of window (defaults to end of today)"},
                "query": {"type": "string", "description": "Optional search term for event title/description"},
                "max_results": {"type": "integer", "default": 10},
            },
        }

    async def run(self, **arguments) -> Any:
        now = datetime.datetime.now(datetime.timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_end = (now + datetime.timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()

        time_min = arguments.get("time_min") or today_start
        time_max = arguments.get("time_max") or today_end
        query = arguments.get("query")
        max_results = int(arguments.get("max_results", 10))

        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {
                    "connected": False,
                    "message": "Google Calendar is not connected. Connect Google in Integrations to view schedule.",
                    "events": [],
                }
            try:
                client = GoogleApiClient(token)
                events = await client.calendar_list_events(
                    calendar_id="primary",
                    time_min=time_min,
                    time_max=time_max,
                    query=query,
                    max_results=max_results,
                )
                return {
                    "connected": True,
                    "count": len(events),
                    "events": events,
                }
            except Exception as e:
                return {"connected": True, "error": f"Calendar API failed: {str(e)}", "events": []}


class GoogleCalendarCreateEventTool(BaseTool):
    @property
    def id(self) -> str:
        return "calendar_create_event"

    @property
    def name(self) -> str:
        return "Create Calendar Event"

    @property
    def description(self) -> str:
        return "Schedules a new meeting or event on Google Calendar. Requires sensitive user approval."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.PRODUCTIVITY

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SENSITIVE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["summary", "start_time", "end_time"],
            "properties": {
                "summary": {"type": "string", "description": "Title or summary of the meeting"},
                "start_time": {"type": "string", "description": "Start ISO datetime (e.g. 2026-11-24T15:00:00Z)"},
                "end_time": {"type": "string", "description": "End ISO datetime (e.g. 2026-11-24T16:00:00Z)"},
                "description": {"type": "string", "description": "Meeting agenda or description"},
                "location": {"type": "string", "description": "Physical location or video link"},
                "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee emails"},
            },
        }

    async def run(self, **arguments) -> Any:
        summary = arguments.get("summary")
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        description = arguments.get("description", "")
        location = arguments.get("location", "")
        attendees = arguments.get("attendees", [])

        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Google Calendar is not connected."}
            try:
                client = GoogleApiClient(token)
                ev = await client.calendar_create_event(
                    calendar_id="primary",
                    summary=summary,
                    start_time=start_time,
                    end_time=end_time,
                    description=description,
                    location=location,
                    attendees=attendees,
                )
                return {
                    "connected": True,
                    "status": "created",
                    "event": ev,
                }
            except Exception as e:
                return {"connected": True, "error": f"Failed to create event: {str(e)}"}


class GoogleCalendarDeleteEventTool(BaseTool):
    @property
    def id(self) -> str:
        return "calendar_delete_event"

    @property
    def name(self) -> str:
        return "Delete Calendar Event"

    @property
    def description(self) -> str:
        return "Cancels or deletes a meeting from Google Calendar. Requires critical confirmation."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.PRODUCTIVITY

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CRITICAL

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["event_id"],
            "properties": {
                "event_id": {"type": "string", "description": "Google Calendar event ID"},
            },
        }

    async def run(self, **arguments) -> Any:
        event_id = arguments.get("event_id")
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Google Calendar is not connected."}
            try:
                client = GoogleApiClient(token)
                await client.calendar_delete_event(calendar_id="primary", event_id=event_id)
                return {"connected": True, "deleted": True, "event_id": event_id}
            except Exception as e:
                return {"connected": True, "error": f"Failed to delete event: {str(e)}"}


# ============================================================================
#                         GOOGLE DOCS, SHEETS, TASKS
# ============================================================================

class GoogleDocsCreateDocumentTool(BaseTool):
    @property
    def id(self) -> str:
        return "docs_create_document"

    @property
    def name(self) -> str:
        return "Create Google Document"

    @property
    def description(self) -> str:
        return "Creates a new Google Doc with the specified title. Requires sensitive approval."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.PRODUCTIVITY

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SENSITIVE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string", "description": "Document title"},
            },
        }

    async def run(self, **arguments) -> Any:
        title = arguments.get("title")
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Google Docs is not connected."}
            try:
                client = GoogleApiClient(token)
                doc = await client.docs_create_document(title=title)
                return {
                    "connected": True,
                    "document_id": doc.get("documentId"),
                    "title": doc.get("title"),
                    "url": f"https://docs.google.com/document/d/{doc.get('documentId')}/edit",
                }
            except Exception as e:
                return {"connected": True, "error": f"Failed to create Google Doc: {str(e)}"}


class GoogleSheetsReadRangeTool(BaseTool):
    @property
    def id(self) -> str:
        return "sheets_read_range"

    @property
    def name(self) -> str:
        return "Read Google Sheet Range"

    @property
    def description(self) -> str:
        return "Reads rows and columns of data from a Google Spreadsheet range (e.g. 'Sheet1!A1:D10')."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.PRODUCTIVITY

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["spreadsheet_id", "range"],
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "Spreadsheet ID"},
                "range": {"type": "string", "description": "A1 notation range (e.g. 'Sheet1!A1:E20')"},
            },
        }

    async def run(self, **arguments) -> Any:
        sheet_id = arguments.get("spreadsheet_id")
        rng = arguments.get("range")
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Google Sheets is not connected."}
            try:
                client = GoogleApiClient(token)
                res = await client.sheets_read_range(sheet_id, rng)
                return {
                    "connected": True,
                    "spreadsheet_id": sheet_id,
                    "range": res.get("range"),
                    "values": res.get("values", []),
                }
            except Exception as e:
                return {"connected": True, "error": f"Failed to read sheet: {str(e)}"}


class GoogleTasksListTool(BaseTool):
    @property
    def id(self) -> str:
        return "tasks_list_tasks"

    @property
    def name(self) -> str:
        return "List Google Tasks"

    @property
    def description(self) -> str:
        return "Lists pending and completed to-do items from your Google Tasks."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.PRODUCTIVITY

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tasklist_id": {"type": "string", "default": "@default"},
            },
        }

    async def run(self, **arguments) -> Any:
        tl_id = arguments.get("tasklist_id", "@default")
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "google")
            if not token:
                return {"connected": False, "message": "Google Tasks is not connected."}
            try:
                client = GoogleApiClient(token)
                tasks = await client.tasks_list_tasks(tl_id)
                clean_tasks = [
                    {
                        "id": t.get("id"),
                        "title": _sanitize_text(t.get("title")),
                        "notes": _sanitize_text(t.get("notes")),
                        "status": t.get("status"),
                        "due": t.get("due"),
                    }
                    for t in tasks
                ]
                return {"connected": True, "count": len(clean_tasks), "tasks": clean_tasks}
            except Exception as e:
                return {"connected": True, "error": f"Failed to list tasks: {str(e)}"}


# ============================================================================
#                               GITHUB TOOLS
# ============================================================================

class GitHubListReposTool(BaseTool):
    @property
    def id(self) -> str:
        return "github_list_repos"

    @property
    def name(self) -> str:
        return "List GitHub Repositories"

    @property
    def description(self) -> str:
        return "Lists repositories owned or accessible by the connected GitHub user."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DEVELOPER

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "default": 10},
            },
        }

    async def run(self, **arguments) -> Any:
        max_results = min(int(arguments.get("max_results", 10)), 30)
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "github")
            if not token:
                return {
                    "connected": False,
                    "message": "GitHub is not connected. Connect in Integrations to view repositories.",
                    "repositories": [],
                }
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        "https://api.github.com/user/repos",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github.v3+json",
                            "User-Agent": "Personal-AI-Assistant",
                        },
                        params={"sort": "updated", "per_page": max_results},
                    )
                    if resp.status_code != 200:
                        return {"connected": True, "error": f"GitHub API error: {resp.text}", "repositories": []}
                    repos = resp.json()
                    clean_repos = [
                        {
                            "name": _sanitize_text(r.get("name")),
                            "full_name": _sanitize_text(r.get("full_name")),
                            "private": r.get("private"),
                            "description": _sanitize_text(r.get("description")),
                            "html_url": r.get("html_url"),
                            "open_issues_count": r.get("open_issues_count"),
                        }
                        for r in repos
                    ]
                    return {"connected": True, "count": len(clean_repos), "repositories": clean_repos}
            except Exception as e:
                return {"connected": True, "error": f"Failed to list GitHub repos: {str(e)}"}


class GitHubListIssuesTool(BaseTool):
    @property
    def id(self) -> str:
        return "github_list_issues"

    @property
    def name(self) -> str:
        return "List GitHub Issues"

    @property
    def description(self) -> str:
        return "Lists open or closed issues for a specified GitHub repository ('owner/repo')."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DEVELOPER

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string", "description": "Repository in 'owner/repo' format"},
                "state": {"type": "string", "default": "open", "enum": ["open", "closed", "all"]},
            },
        }

    async def run(self, **arguments) -> Any:
        repo = arguments.get("repo")
        state = arguments.get("state", "open")
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "github")
            if not token:
                return {"connected": False, "message": "GitHub is not connected."}
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        f"https://api.github.com/repos/{repo}/issues",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github.v3+json",
                            "User-Agent": "Personal-AI-Assistant",
                        },
                        params={"state": state, "per_page": 15},
                    )
                    if resp.status_code != 200:
                        return {"connected": True, "error": f"GitHub API error: {resp.text}"}
                    issues = resp.json()
                    clean = [
                        {
                            "number": i.get("number"),
                            "title": _sanitize_text(i.get("title")),
                            "state": i.get("state"),
                            "html_url": i.get("html_url"),
                            "user": i.get("user", {}).get("login"),
                        }
                        for i in issues
                    ]
                    return {"connected": True, "repo": repo, "count": len(clean), "issues": clean}
            except Exception as e:
                return {"connected": True, "error": f"Failed to list GitHub issues: {str(e)}"}


class GitHubCreateIssueTool(BaseTool):
    @property
    def id(self) -> str:
        return "github_create_issue"

    @property
    def name(self) -> str:
        return "Create GitHub Issue"

    @property
    def description(self) -> str:
        return "Creates a new issue in a GitHub repository. Requires sensitive user approval."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DEVELOPER

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SENSITIVE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["repo", "title"],
            "properties": {
                "repo": {"type": "string", "description": "Target repo in 'owner/repo' format"},
                "title": {"type": "string", "description": "Issue title"},
                "body": {"type": "string", "description": "Issue description / body"},
            },
        }

    async def run(self, **arguments) -> Any:
        repo = arguments.get("repo")
        title = arguments.get("title")
        body = arguments.get("body", "")
        async with async_session_factory() as db:
            token = await IntegrationManager.get_valid_access_token(db, "github")
            if not token:
                return {"connected": False, "message": "GitHub is not connected."}
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"https://api.github.com/repos/{repo}/issues",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github.v3+json",
                            "User-Agent": "Personal-AI-Assistant",
                        },
                        json={"title": title, "body": body},
                    )
                    if resp.status_code not in (200, 201):
                        return {"connected": True, "error": f"GitHub API error: {resp.text}"}
                    issue = resp.json()
                    return {
                        "connected": True,
                        "status": "created",
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "html_url": issue.get("html_url"),
                    }
            except Exception as e:
                return {"connected": True, "error": f"Failed to create GitHub issue: {str(e)}"}


# ============================================================================
#                         REGISTRATION ENTRYPOINT
# ============================================================================

def register_integration_tools():
    """Registers all live integration tools with the ToolRegistry."""
    # Gmail
    ToolRegistry.register(GmailGetProfileTool())
    ToolRegistry.register(GmailListMessagesTool())
    ToolRegistry.register(GmailReadMessageTool())
    ToolRegistry.register(GmailGetThreadTool())
    ToolRegistry.register(GmailCreateDraftTool())
    ToolRegistry.register(GmailSendMessageTool())
    ToolRegistry.register(GmailTrashMessageTool())

    # Drive
    ToolRegistry.register(GoogleDriveListFilesTool())
    ToolRegistry.register(GoogleDriveReadFileTool())
    ToolRegistry.register(GoogleDriveUploadFileTool())

    # Calendar
    ToolRegistry.register(GoogleCalendarListEventsTool())
    ToolRegistry.register(GoogleCalendarCreateEventTool())
    ToolRegistry.register(GoogleCalendarDeleteEventTool())

    # Docs, Sheets, Tasks
    ToolRegistry.register(GoogleDocsCreateDocumentTool())
    ToolRegistry.register(GoogleSheetsReadRangeTool())
    ToolRegistry.register(GoogleTasksListTool())

    # GitHub
    ToolRegistry.register(GitHubListReposTool())
    ToolRegistry.register(GitHubListIssuesTool())
    ToolRegistry.register(GitHubCreateIssueTool())

    # Backward compatibility aliases for existing automations
    class LegacyMailList(GmailListMessagesTool):
        @property
        def id(self) -> str: return "google_mail_list"
    class LegacyMailRead(GmailReadMessageTool):
        @property
        def id(self) -> str: return "google_mail_read"
    class LegacyMailSend(GmailSendMessageTool):
        @property
        def id(self) -> str: return "google_mail_send"
    class LegacyDriveList(GoogleDriveListFilesTool):
        @property
        def id(self) -> str: return "google_drive_list"
    class LegacyCalList(GoogleCalendarListEventsTool):
        @property
        def id(self) -> str: return "google_calendar_list"
    class LegacyCalCreate(GoogleCalendarCreateEventTool):
        @property
        def id(self) -> str: return "google_calendar_create"
    class LegacyCalDelete(GoogleCalendarDeleteEventTool):
        @property
        def id(self) -> str: return "google_calendar_delete"

    ToolRegistry.register(LegacyMailList())
    ToolRegistry.register(LegacyMailRead())
    ToolRegistry.register(LegacyMailSend())
    ToolRegistry.register(LegacyDriveList())
    ToolRegistry.register(LegacyCalList())
    ToolRegistry.register(LegacyCalCreate())
    ToolRegistry.register(LegacyCalDelete())

    # Aliases for backwards compatibility
GoogleCalendarListTool = GoogleCalendarListEventsTool
GoogleMailListTool = GmailListMessagesTool
GoogleDriveListTool = GoogleDriveListFilesTool
