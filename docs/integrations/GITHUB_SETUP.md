# GitHub OAuth Integration Setup Guide

This guide describes how to configure official **GitHub OAuth App** credentials for the Personal AI Assistant.

---

## 1. Prerequisites
- A GitHub personal account.
- Access to [GitHub Developer Settings](https://github.com/settings/developers).

---

## 2. Step-by-Step Configuration

1. Log into your GitHub account and go to **Settings > Developer Settings > OAuth Apps**.
2. Click **New OAuth App**.
3. Enter Application Details:
   - **Application name**: `Personal AI Assistant`
   - **Homepage URL**: `http://localhost:5173`
   - **Authorization callback URL**:
     ```
     http://localhost:8000/api/v1/integrations/github/callback
     ```
4. Click **Register application**.
5. Copy your **Client ID**.
6. Under **Client secrets**, click **Generate a new client secret** and copy the secret.
7. Open `backend/.env` and add:
   ```env
   GITHUB_CLIENT_ID=your_github_client_id
   GITHUB_CLIENT_SECRET=your_github_client_secret
   GITHUB_REDIRECT_URI=http://localhost:8000/api/v1/integrations/github/callback
   ```
8. In the Assistant web app, navigate to **Integrations**, find **GitHub**, and click **Connect**.
