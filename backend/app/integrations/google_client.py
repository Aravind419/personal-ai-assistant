import base64
import email
from email.message import EmailMessage
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List, Tuple
import httpx

from app.core.logging import logger
from app.integrations.base import IntegrationManager
from sqlalchemy.ext.asyncio import AsyncSession


def _sanitize_text(text: Optional[str], max_len: int = 8000) -> str:
    if not text:
        return ""
    clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(text))
    clean = clean.replace("</tool_output>", "&lt;/tool_output&gt;")
    clean = clean.replace("<tool_output>", "&lt;tool_output&gt;")
    clean = clean.replace("<system>", "&lt;system&gt;")
    clean = clean.replace("</system>", "&lt;/system&gt;")
    if len(clean) > max_len:
        clean = clean[:max_len] + f"... [truncated {len(clean) - max_len} chars]"
    return clean


class GoogleApiClient:
    """
    Central HTTP client executing real Google REST API requests
    with bearer token authorization and error mapping.
    """

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    # ==================== Gmail Operations ====================

    async def gmail_get_profile(self) -> Dict[str, Any]:
        url = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail get_profile failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def gmail_list_messages(self, query: str = "is:unread", max_results: int = 10, page_token: Optional[str] = None) -> Dict[str, Any]:
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        params: Dict[str, Any] = {
            "q": query,
            "maxResults": min(max(max_results, 1), 50),
        }
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail list_messages failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def gmail_get_message(self, message_id: str, format_: str = "full") -> Dict[str, Any]:
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers, params={"format": format_})
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail get_message failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            return self._parse_gmail_payload(data)

    def _parse_gmail_payload(self, msg_data: Dict[str, Any]) -> Dict[str, Any]:
        headers = {h.get("name", "").lower(): h.get("value", "") for h in msg_data.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "No Subject")
        sender = headers.get("from", "Unknown")
        to = headers.get("to", "")
        date = headers.get("date", "")
        snippet = msg_data.get("snippet", "")

        # Extract body text from parts or body
        body_text = self._extract_body_text(msg_data.get("payload", {}))
        attachments = self._extract_attachment_meta(msg_data.get("payload", {}))

        return {
            "id": msg_data.get("id"),
            "threadId": msg_data.get("threadId"),
            "labelIds": msg_data.get("labelIds", []),
            "subject": _sanitize_text(subject),
            "from": _sanitize_text(sender),
            "to": _sanitize_text(to),
            "date": date,
            "snippet": _sanitize_text(snippet),
            "body": _sanitize_text(body_text),
            "attachments": attachments,
        }

    def _extract_body_text(self, payload: Dict[str, Any]) -> str:
        body = payload.get("body", {})
        data = body.get("data")
        if data:
            try:
                decoded = base64.urlsafe_b64decode(data.encode("UTF-8")).decode("UTF-8", errors="replace")
                return decoded
            except Exception:
                pass

        parts = payload.get("parts", [])
        text_parts = []
        for part in parts:
            mime = part.get("mimeType", "")
            if mime == "text/plain":
                p_data = part.get("body", {}).get("data")
                if p_data:
                    try:
                        decoded = base64.urlsafe_b64decode(p_data.encode("UTF-8")).decode("UTF-8", errors="replace")
                        text_parts.append(decoded)
                    except Exception:
                        pass
            elif mime.startswith("multipart/"):
                sub_text = self._extract_body_text(part)
                if sub_text:
                    text_parts.append(sub_text)

        return "\n\n".join(text_parts) if text_parts else payload.get("snippet", "")

    def _extract_attachment_meta(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        attachments = []
        for part in payload.get("parts", []):
            filename = part.get("filename")
            body = part.get("body", {})
            attachment_id = body.get("attachmentId")
            if filename and attachment_id:
                attachments.append({
                    "filename": filename,
                    "mimeType": part.get("mimeType"),
                    "size": body.get("size", 0),
                    "attachmentId": attachment_id,
                })
        return attachments

    async def gmail_get_thread(self, thread_id: str) -> Dict[str, Any]:
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers, params={"format": "full"})
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail get_thread failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            parsed_messages = [self._parse_gmail_payload(m) for m in data.get("messages", [])]
            return {
                "id": data.get("id"),
                "historyId": data.get("historyId"),
                "messages_count": len(parsed_messages),
                "messages": parsed_messages,
            }

    async def gmail_list_labels(self) -> List[Dict[str, Any]]:
        url = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail list_labels failed ({resp.status_code}): {resp.text}")
            return resp.json().get("labels", [])

    async def gmail_create_draft(
        self,
        to: str,
        subject: str,
        body: Optional[str] = None,
        body_text: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        content = body_text if body_text is not None else (body or "")
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(content)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("UTF-8")
        payload: Dict[str, Any] = {"message": {"raw": raw}}
        if thread_id:
            payload["message"]["threadId"] = thread_id

        url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail create_draft failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def gmail_send_message(
        self,
        to: str,
        subject: str,
        body: Optional[str] = None,
        body_text: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        content = body_text if body_text is not None else (body or "")
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(content)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("UTF-8")
        payload: Dict[str, Any] = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id

        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail send_message failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def gmail_trash_message(self, message_id: str) -> Dict[str, Any]:
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/trash"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail trash_message failed ({resp.status_code}): {resp.text}")
            return resp.json()

    # ==================== Google Drive Operations ====================

    async def drive_get_about(self) -> Dict[str, Any]:
        url = "https://www.googleapis.com/drive/v3/about?fields=user,storageQuota"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Drive get_about failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def drive_list_files(self, query: Optional[str] = None, page_size: int = 15, page_token: Optional[str] = None) -> Dict[str, Any]:
        url = "https://www.googleapis.com/drive/v3/files"
        fields = "nextPageToken,files(id,name,mimeType,size,modifiedTime,webViewLink,trashed)"
        params: Dict[str, Any] = {
            "pageSize": min(max(page_size, 1), 50),
            "fields": fields,
            "q": query or "trashed = false",
        }
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Drive list_files failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def drive_get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        fields = "id,name,mimeType,size,modifiedTime,webViewLink,parents,trashed,description"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers, params={"fields": fields})
            if resp.status_code != 200:
                raise RuntimeError(f"Drive get_file_metadata failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def drive_download_file(self, file_id: str) -> bytes:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Drive download_file failed ({resp.status_code}): {resp.text}")
            return resp.content

    async def drive_export_doc(self, file_id: str, mime_type: str = "text/plain") -> str:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.headers, params={"mimeType": mime_type})
            if resp.status_code != 200:
                raise RuntimeError(f"Drive export_doc failed ({resp.status_code}): {resp.text}")
            return resp.text

    async def drive_create_folder(self, name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        url = "https://www.googleapis.com/drive/v3/files"
        body: Dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            body["parents"] = [parent_id]
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self.headers, json=body)
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Drive create_folder failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def drive_upload_text_file(self, name: str, content: str, mime_type: str = "text/plain", parent_id: Optional[str] = None) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"name": name, "mimeType": mime_type}
        if parent_id:
            metadata["parents"] = [parent_id]

        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        boundary = "===GOOGLE_DRIVE_UPLOAD_BOUNDARY==="
        body_parts = [
            f"--{boundary}",
            "Content-Type: application/json; charset=UTF-8",
            "",
            json.dumps(metadata),
            f"--{boundary}",
            f"Content-Type: {mime_type}",
            "",
            content,
            f"--{boundary}--",
            "",
        ]
        body = "\r\n".join(body_parts).encode("UTF-8")
        headers = dict(self.headers)
        headers["Content-Type"] = f"multipart/related; boundary={boundary}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, content=body)
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Drive upload failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def drive_trash_file(self, file_id: str) -> Dict[str, Any]:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(url, headers=self.headers, json={"trashed": True})
            if resp.status_code != 200:
                raise RuntimeError(f"Drive trash_file failed ({resp.status_code}): {resp.text}")
            return resp.json()

    # ==================== Google Calendar Operations ====================

    async def calendar_list_calendars(self) -> List[Dict[str, Any]]:
        url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Calendar list_calendars failed ({resp.status_code}): {resp.text}")
            return resp.json().get("items", [])

    async def calendar_list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 25,
    ) -> List[Dict[str, Any]]:
        enc_id = urllib.parse.quote(calendar_id)
        url = f"https://www.googleapis.com/calendar/v3/calendars/{enc_id}/events"
        params: Dict[str, Any] = {
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": min(max(max_results, 1), 100),
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        if query:
            params["q"] = query

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Calendar list_events failed ({resp.status_code}): {resp.text}")
            items = resp.json().get("items", [])
            return [self._format_calendar_event(ev) for ev in items]

    def _format_calendar_event(self, ev: Dict[str, Any]) -> Dict[str, Any]:
        start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
        end = ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date")
        return {
            "id": ev.get("id"),
            "summary": _sanitize_text(ev.get("summary", "Untitled Event")),
            "description": _sanitize_text(ev.get("description", "")),
            "start": start,
            "end": end,
            "location": _sanitize_text(ev.get("location", "")),
            "status": ev.get("status"),
            "htmlLink": ev.get("htmlLink"),
            "attendees": [a.get("email") for a in ev.get("attendees", []) if a.get("email")],
        }

    async def calendar_create_event(
        self,
        calendar_id: str = "primary",
        summary: str = "New Meeting",
        start_time: str = "",
        end_time: str = "",
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        enc_id = urllib.parse.quote(calendar_id)
        url = f"https://www.googleapis.com/calendar/v3/calendars/{enc_id}/events"
        body: Dict[str, Any] = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start_time} if "T" in start_time else {"date": start_time},
            "end": {"dateTime": end_time} if "T" in end_time else {"date": end_time},
        }
        if attendees:
            body["attendees"] = [{"email": a} for a in attendees]

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self.headers, json=body)
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Calendar create_event failed ({resp.status_code}): {resp.text}")
            return self._format_calendar_event(resp.json())

    async def calendar_delete_event(self, calendar_id: str, event_id: str) -> bool:
        enc_id = urllib.parse.quote(calendar_id)
        url = f"https://www.googleapis.com/calendar/v3/calendars/{enc_id}/events/{event_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(url, headers=self.headers)
            if resp.status_code not in (200, 204):
                raise RuntimeError(f"Calendar delete_event failed ({resp.status_code}): {resp.text}")
            return True

    # ==================== Google Docs, Sheets, Slides, Tasks ====================

    async def docs_get_document(self, document_id: str) -> Dict[str, Any]:
        url = f"https://docs.googleapis.com/v1/documents/{document_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Docs get_document failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def docs_create_document(self, title: str) -> Dict[str, Any]:
        url = "https://docs.googleapis.com/v1/documents"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self.headers, json={"title": title})
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Docs create_document failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def sheets_get_spreadsheet(self, spreadsheet_id: str) -> Dict[str, Any]:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Sheets get_spreadsheet failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def sheets_read_range(self, spreadsheet_id: str, range_name: str) -> Dict[str, Any]:
        enc_range = urllib.parse.quote(range_name)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{enc_range}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Sheets read_range failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def tasks_list_tasklists(self) -> List[Dict[str, Any]]:
        url = "https://tasks.googleapis.com/tasks/v1/users/@me/lists"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Tasks list_tasklists failed ({resp.status_code}): {resp.text}")
            return resp.json().get("items", [])

    async def tasks_list_tasks(self, tasklist_id: str = "@default") -> List[Dict[str, Any]]:
        url = f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist_id}/tasks"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Tasks list_tasks failed ({resp.status_code}): {resp.text}")
            return resp.json().get("items", [])
