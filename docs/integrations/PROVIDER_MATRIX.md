# External Integrations Provider Matrix

Comprehensive technical matrix of all supported and planned third-party integrations, authentication methods, required scopes, security tiers, and API capabilities.

---

## 1. Active & Implemented Providers

| Service ID | Service Name | Provider Family | Category | Auth Method | Required Scopes | Permission Tier | Implementation Status |
|---|---|---|---|---|---|---|---|
| `google_gmail` | Gmail | Google | Communication | OAuth 2.0 Auth Code (Offline) | `gmail.readonly`, `gmail.send`, `gmail.modify`, `gmail.compose` | Safe (Read), Sensitive (Send, Draft), Critical (Trash) | **REAL_AND_VERIFIED** |
| `google_drive` | Google Drive | Google | Storage | OAuth 2.0 Auth Code (Offline) | `drive.readonly`, `drive.file` | Safe (Read/Search), Sensitive (Upload), Critical (Trash) | **REAL_AND_VERIFIED** |
| `google_calendar` | Google Calendar | Google | Productivity | OAuth 2.0 Auth Code (Offline) | `calendar`, `calendar.events` | Safe (List/Search), Sensitive (Create/Edit), Critical (Delete) | **REAL_AND_VERIFIED** |
| `google_docs` | Google Docs | Google | Productivity | OAuth 2.0 Auth Code (Offline) | `documents`, `drive.file` | Safe (Read), Sensitive (Create/Edit) | **REAL_AND_VERIFIED** |
| `google_sheets` | Google Sheets | Google | Productivity | OAuth 2.0 Auth Code (Offline) | `spreadsheets`, `drive.file` | Safe (Read), Sensitive (Append/Edit) | **REAL_AND_VERIFIED** |
| `google_slides` | Google Slides | Google | Productivity | OAuth 2.0 Auth Code (Offline) | `presentations`, `drive.file` | Safe (Read), Sensitive (Create) | **REAL_AND_VERIFIED** |
| `google_tasks` | Google Tasks | Google | Productivity | OAuth 2.0 Auth Code (Offline) | `tasks` | Safe (List), Sensitive (Create/Complete) | **REAL_AND_VERIFIED** |
| `google_contacts` | Google Contacts | Google | Productivity | OAuth 2.0 Auth Code (Offline) | `contacts.readonly` | Safe (Search/Read) | **REAL_AND_VERIFIED** |
| `github` | GitHub | GitHub | Developer | OAuth 2.0 Auth Code | `repo`, `read:user` | Safe (List/Search), Sensitive (Create Issue) | **REAL_AND_VERIFIED** |

---

## 2. Planned Roadmap Providers

| Service ID | Service Name | Provider Family | Category | Auth Method | Target Scopes | Status |
|---|---|---|---|---|---|---|
| `microsoft_outlook` | Microsoft Outlook | Microsoft | Communication | OAuth 2.0 (Azure AD) | `Mail.Read`, `Mail.Send` | Roadmap Planned |
| `microsoft_onedrive`| Microsoft OneDrive| Microsoft | Storage | OAuth 2.0 (Azure AD) | `Files.ReadWrite` | Roadmap Planned |
| `microsoft_calendar`| Microsoft Calendar| Microsoft | Productivity | OAuth 2.0 (Azure AD) | `Calendars.ReadWrite` | Roadmap Planned |
| `slack` | Slack | Slack | Communication | OAuth 2.0 (Bot/User) | `channels:read`, `chat:write` | Roadmap Planned |
| `notion` | Notion | Notion | Productivity | OAuth 2.0 / Internal Key | `read_content`, `insert_content` | Roadmap Planned |
| `canva` | Canva | Canva | Design | OAuth 2.0 PKCE | `asset:read`, `design:meta:read` | Roadmap Planned |
| `dropbox` | Dropbox | Dropbox | Storage | OAuth 2.0 (PKCE) | `files.content.read` | Roadmap Planned |
| `trello` | Trello | Atlassian | Productivity | OAuth 1.0a / API Key | `read`, `write` | Roadmap Planned |
| `linear` | Linear | Linear | Developer | OAuth 2.0 (Actor) | `read`, `write` | Roadmap Planned |
| `discord` | Discord | Discord | Communication | OAuth 2.0 Bot | `bot`, `messages.read` | Roadmap Planned |

---

## 3. Security Architecture & Credential Isolation

1. **AES-256 Symmetric Encryption**: All OAuth refresh and access tokens are encrypted with Fernet symmetric keys derived from backend `SECRET_KEY` before being written to PostgreSQL `integration_connections`.
2. **Zero Client Secret Exposure**: Client secrets and refresh tokens are strictly quarantined within the backend environment and never serialized in JSON responses to the frontend.
3. **Automated Token Refresh**: If an access token is expired or within 60 seconds of expiration, `IntegrationManager` transparently negotiates a refreshed token with the provider prior to executing tool calls.
4. **Delimiter Breakout Sanitization**: External text payloads (email contents, file bodies, issue descriptions) are sanitized via `_sanitize_text` to escape `</tool_output>` breakout tags and neutralize prompt injection attempts.
