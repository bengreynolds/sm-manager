# sm-manager

Cross-platform social media automation manager, designed to stay lightweight, run locally, and support both a browser-based control UI and fully headless execution.

This repository is currently planned as:

- Instagram first
- Facebook next, but not implemented until explicitly approved
- TikTok next, but not implemented until explicitly approved
- X next, but not implemented until explicitly approved

## Current Direction

The first build target is an Instagram automation MVP that can:

- manage one or many Instagram professional accounts
- publish on a fixed schedule
- run as a local background process
- expose a lightweight control panel
- keep credentials and tokens out of plain text
- support pause, resume, dry-run, and per-account settings

## Implemented Now

The repository now includes a runnable Instagram-first local skeleton with:

- package entrypoint and CLI
- SQLite bootstrap in `runtime/sm_manager.sqlite3`
- local test credential loader from the hidden local JSON file
- secure secret storage using OS keyring when available, with encrypted file fallback
- account sync for Instagram labels and usernames
- credential import into secure local storage
- token metadata storage and Instagram auth-readiness checks
- OAuth URL generation and callback handling for Instagram app connection
- Instagram dry-run publish validation that records audit history without calling the Instagram API
- minimal FastAPI control-plane endpoints for health, accounts, and recent jobs

What is not implemented yet:

- a live Meta-app-tested OAuth handshake against your own production app credentials
- real Instagram media upload or publish calls
- scheduler execution
- settings UI
- token storage or refresh flow

## Important Constraint

The original idea of scraping trending posts from other creators and automatically reposting them with attribution is not being treated as the default implementation path.

Reasons:

- attribution alone does not solve copyright or reuse rights
- official platform APIs do not generally support unrestricted public-content scraping for this workflow
- account safety and long-term operability are better when the product is built around official APIs and rights-gated content ingestion

The working plan therefore uses a safer ingestion model:

- approved source accounts
- licensed or owned media only
- source metadata captured for every asset
- approval queue before publication

## Repo Contract

Before any task work, read:

- [agent.md](c:/Users/reynoben/Documents/sm-manager/agent.md)
- the relevant platform `planning.md`

Instagram is the only platform allowed for active implementation right now.

## Proposed Architecture

- One local backend service for API, scheduler, and job orchestration
- One lightweight web UI served by that backend
- SQLite for state and job history
- Encrypted local secret storage plus OS keychain integration where available
- Platform adapters isolated by directory
- Shared policy layer for scheduling, approvals, dedupe, and audit logging

## Skeleton

```text
src/
  sm_manager/
    core/
    scheduler/
    ui/
    platforms/
      instagram/
      facebook/
      tiktok/
      x/
config/
runtime/
secrets/
```

## Planning Files

- [agent.md](c:/Users/reynoben/Documents/sm-manager/agent.md)
- [planning.md](c:/Users/reynoben/Documents/sm-manager/src/sm_manager/platforms/instagram/planning.md)
- [planning.md](c:/Users/reynoben/Documents/sm-manager/src/sm_manager/platforms/facebook/planning.md)
- [planning.md](c:/Users/reynoben/Documents/sm-manager/src/sm_manager/platforms/tiktok/planning.md)
- [planning.md](c:/Users/reynoben/Documents/sm-manager/src/sm_manager/platforms/x/planning.md)

## Local Test Credentials

For initial local testing:

- copy or edit [`.platform_credentials.local.json`](c:/Users/reynoben/Documents/sm-manager/.platform_credentials.local.json) locally
- use [`.platform_credentials.example.json`](c:/Users/reynoben/Documents/sm-manager/.platform_credentials.example.json) as the tracked template
- keep real credentials only in the local file, which is git-ignored

This is a temporary local-testing convention. Long term, platform tokens and encrypted secret storage remain the intended implementation path.

## Add Instagram Accounts

To add another Instagram account, edit [`.platform_credentials.local.json`](c:/Users/reynoben/Documents/sm-manager/.platform_credentials.local.json) and add another object under `instagram`.

Example:

```json
{
  "instagram": [
    {
      "label": "ig_test_account_1",
      "username": "instagram_username_here",
      "password": "replace_with_local_test_password"
    },
    {
      "label": "ig_test_account_2",
      "username": "second_instagram_username_here",
      "password": "replace_with_second_local_test_password"
    }
  ]
}
```

The tracked reference file is [`.platform_credentials.example.json`](c:/Users/reynoben/Documents/sm-manager/.platform_credentials.example.json).

After editing the local file, run:

```powershell
.\.venv\Scripts\python.exe -m sm_manager sync-local-accounts --platform instagram
.\.venv\Scripts\python.exe -m sm_manager import-local-credentials --platform instagram
```

## Instagram OAuth Setup

Use [instagram_oauth.example.env](c:/Users/reynoben/Documents/sm-manager/config/instagram_oauth.example.env) as the environment template.

Minimum variables:

```powershell
$env:SM_MANAGER_INSTAGRAM_APP_ID='your_meta_app_id'
$env:SM_MANAGER_INSTAGRAM_APP_SECRET='your_meta_app_secret'
$env:SM_MANAGER_INSTAGRAM_REDIRECT_URI='http://127.0.0.1:8000/instagram/oauth/callback'
```

Then start the local control plane:

```powershell
.\.venv\Scripts\python.exe -m sm_manager serve
```

Generate the auth URL for an account:

```powershell
.\.venv\Scripts\python.exe -m sm_manager instagram-oauth-url --account ig_test_account_1
```

Or open the local route directly:

```text
http://127.0.0.1:8000/instagram/oauth/start?account=ig_test_account_1&redirect=true
```

The callback route is:

```text
http://127.0.0.1:8000/instagram/oauth/callback
```

## Recommended MVP Stack

- Python
- FastAPI for local API and web control surface
- SQLite for local persistence
- APScheduler for timed jobs
- httpx for platform API calls
- keyring plus encrypted fallback vault for secrets

This stack is small enough for local machines, supports headless mode well, and avoids introducing unnecessary infrastructure in the first release.

## Next Build Order

1. lock the Instagram MVP spec from its planning file
2. scaffold the backend package and config model
3. implement secret storage and account registration
4. implement Instagram auth and publishing flow
5. add scheduler, approval queue, and UI controls
6. test headless and UI modes on a clean machine

## Local Run Commands

Create the local environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Bootstrap the app:

```powershell
.\.venv\Scripts\python.exe -m sm_manager bootstrap
```

Sync Instagram test accounts from the hidden local credential file:

```powershell
.\.venv\Scripts\python.exe -m sm_manager sync-local-accounts --platform instagram
```

Import local test passwords into the secure local secret store:

```powershell
.\.venv\Scripts\python.exe -m sm_manager import-local-credentials --platform instagram
```

Inspect the active secret backend:

```powershell
.\.venv\Scripts\python.exe -m sm_manager secret-store-status --platform instagram
```

Inspect Instagram auth readiness:

```powershell
.\.venv\Scripts\python.exe -m sm_manager instagram-auth-status --account ig_test_account_1
```

Generate an Instagram OAuth URL:

```powershell
.\.venv\Scripts\python.exe -m sm_manager instagram-oauth-url --account ig_test_account_1
```

Exchange an Instagram OAuth code manually if needed:

```powershell
.\.venv\Scripts\python.exe -m sm_manager instagram-oauth-exchange --code YOUR_CODE --state YOUR_STATE
```

Store a local platform token for testing metadata flow:

```powershell
.\.venv\Scripts\python.exe -m sm_manager store-platform-token --platform instagram --account ig_test_account_1 --name access_token --value test_access_token_value --expires-at 2026-12-31T00:00:00+00:00
```

Run an Instagram dry-run:

```powershell
.\.venv\Scripts\python.exe -m sm_manager instagram-dry-run --account ig_test_account_1 --caption "Initial dry-run post" --source-username source_creator
```

Inspect local status:

```powershell
.\.venv\Scripts\python.exe -m sm_manager status
```

Start the control-plane API:

```powershell
.\.venv\Scripts\python.exe -m sm_manager serve
```

Available endpoints:

- `GET /health`
- `GET /accounts`
- `GET /jobs/recent`
- `GET /instagram/auth/status?account=...`
- `GET /instagram/oauth/start?account=...`
- `GET /instagram/oauth/callback`
