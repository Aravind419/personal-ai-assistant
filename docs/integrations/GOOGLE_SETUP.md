# Google Cloud OAuth 2.0 Integration Setup Guide

This guide provides end-to-end instructions for configuring official **Google Cloud OAuth 2.0** credentials for the Personal AI Assistant.

---

## 1. Prerequisites

- A personal or Google Workspace Google Account.
- Access to the [Google Cloud Console](https://console.cloud.google.com/).

---

## 2. Step-by-Step Configuration

### Step 1: Create a Google Cloud Project
1. Navigate to [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown at the top of the page and select **New Project**.
3. Set **Project Name**: `Personal-AI-Assistant` (or your preferred name).
4. Click **Create** and ensure the new project is selected.

---

### Step 2: Enable Required Google APIs
Enable the individual APIs for the services you wish to use:

1. In the left navigation, go to **APIs & Services > Library**.
2. Search for and **Enable** each of the following:
   - **Gmail API**
   - **Google Drive API**
   - **Google Calendar API**
   - **Google Docs API**
   - **Google Sheets API**
   - **Google Slides API**
   - **Google Tasks API**
   - **People API** (for Google Contacts)

---

### Step 3: Configure OAuth Consent Screen
1. In the left navigation, go to **APIs & Services > OAuth consent screen**.
2. Select **External** (standard for personal projects) and click **Create**.
3. Under **App Information**:
   - **App name**: `Personal AI Assistant`
   - **User support email**: Select your Google email.
4. Under **Developer Contact Information**:
   - Enter your email address.
5. Click **Save and Continue**.
6. Under **Scopes**:
   - Click **Add or Remove Scopes**.
   - Add:
     - `.../auth/userinfo.email`
     - `.../auth/userinfo.profile`
     - `openid`
     - `.../auth/gmail.readonly`
     - `.../auth/gmail.send`
     - `.../auth/gmail.modify`
     - `.../auth/gmail.compose`
     - `.../auth/drive.readonly`
     - `.../auth/drive.file`
     - `.../auth/calendar`
     - `.../auth/calendar.events`
     - `.../auth/documents`
     - `.../auth/spreadsheets`
     - `.../auth/presentations`
     - `.../auth/tasks`
     - `.../auth/contacts.readonly`
   - Click **Update** and then **Save and Continue**.
7. Under **Test Users** (Critical while App is in Testing mode):
   - Click **Add Users**.
   - Enter your personal Google email address (the account you will authorize).
   - Click **Add** and **Save and Continue**.

---

### Step 4: Create OAuth 2.0 Web Application Credentials
1. In the left navigation, go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Under **Application type**, select **Web application**.
4. Set **Name**: `Personal AI Assistant Web Client`.
5. Under **Authorized redirect URIs**, click **Add URI** and enter:
   ```
   http://localhost:8000/api/v1/integrations/google/callback
   ```
   *(For production deployment, add your production domain's redirect URI, e.g. `https://your-domain.com/api/v1/integrations/google/callback`)*.
6. Click **Create**.
7. A dialog will display your **Client ID** and **Client Secret**.

---

### Step 5: Configure Backend Environment
Open `backend/.env` (and root `.env`) in your local project and configure the keys:

```env
GOOGLE_CLIENT_ID=1234567890-abcdef.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/integrations/google/callback
```

---

### Step 6: Verify and Connect
1. Restart the backend service so it reads the new `.env` variables:
   ```powershell
   cd backend
   .\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Open the frontend in your browser at `http://localhost:5173/integrations`.
3. Locate the **Gmail** card. The status will transition from *Configuration Required* to *Not Connected* with an active **Connect** button.
4. Click **Connect**. The official Google sign-in and consent screen opens.
5. Select your Google account and grant permissions.
6. The popup window will complete the token exchange, store your AES-256 encrypted tokens, verify your email identity, and automatically update your dashboard to **Connected & Verified**!
7. Click **Test** on any Google service to run a live API health check.
