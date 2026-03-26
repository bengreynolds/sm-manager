# Instagram Planning

Status: active implementation track

## Objective

Build the first production path for this repository on Instagram only.

The Instagram MVP must support:

- one or many Instagram professional accounts
- scheduled publishing
- local-first execution
- headless mode
- lightweight browser UI
- pause, resume, and dry-run controls
- per-account configuration
- secure local credential and token handling

## Critical Constraint

Generic public scraping of trending Instagram creator content is not treated as an MVP requirement because it is high-risk from both platform-policy and content-rights perspectives.

The first safe implementation path is:

- approved source list
- owned or licensed content only
- optional manual approval queue
- persistent credit metadata stored with each asset

If later automation of third-party content sourcing is still desired, it should be designed as a separate ingestion module with explicit rights validation and source allowlists.

## Working Assumptions

- target accounts are Instagram professional accounts, not personal accounts
- official Instagram APIs are used for auth, publishing, and metrics
- the system supports three scheduler windows per day
- default posting budget is one approved media item per account per scheduler window
- all posting schedules remain configurable per account

## Non-Goals For The Instagram MVP

- bypassing official auth flows
- storing raw account credentials in repo files
- scraping private or protected content
- implementing Facebook, TikTok, or X adapters
- advanced AI caption rewriting

## Product Shape

### 1. Local Control Plane

One local service should own:

- account registry
- settings
- schedule management
- job execution
- audit history
- UI API

### 2. Instagram Adapter

Owns:

- auth and token lifecycle
- media validation
- upload and publish flow
- rate-limit aware retries
- publish result capture

### 3. Content Intake Pipeline

Owns:

- source registry
- media import
- source attribution metadata
- content rights state
- dedupe hashes
- approval queue

### 4. Scheduler

Owns:

- three daily windows by default
- per-account enable or disable
- pause switch
- dry-run mode
- retry policy
- missed-run handling

### 5. UI

Must expose:

- account list
- account status
- next scheduled runs
- queue depth
- recent job results
- enable or disable toggles
- per-account settings editor

## Technical Direction

Recommended first implementation stack:

- Python
- FastAPI
- SQLite
- APScheduler
- httpx
- keyring plus encrypted fallback vault

Rationale:

- runs on low-spec local machines
- easy headless service mode
- simple distribution path
- small operational footprint

## Data Model To Introduce

Minimum entities:

- `accounts`
- `platform_tokens`
- `posting_profiles`
- `sources`
- `media_assets`
- `approvals`
- `scheduled_runs`
- `job_executions`
- `publish_events`

Each `media_asset` should include at least:

- source platform
- source creator handle
- source permalink
- rights status
- local file path or managed remote URL
- content hash
- caption template
- credit text
- approval state

## Security Plan

- use OAuth and platform tokens where supported
- do not accept plain-text credential CSV files as the long-term storage format
- if bulk onboarding is required later, import into encrypted storage and immediately discard the plaintext input
- keep runtime secrets outside git-tracked paths
- redact secrets from logs and UI

## Implementation Phases

### Phase 0. Repository framing

- completed in this pass
- create agent contract
- create per-platform plans
- create package skeleton

### Phase 1. Local app skeleton

Status: completed

- create package layout
- add config model
- add SQLite storage bootstrap
- add logging and audit primitives
- add CLI entrypoints for headless mode

### Phase 2. Secret storage and account onboarding

Status: partial

- add account registration sync from hidden local credential file
- add OS keychain integration
- add encrypted fallback vault
- add secure local credential import
- token refresh strategy pending

### Phase 3. Instagram publishing path

Status: partial

- auth connection pending
- auth readiness inspection implemented
- token metadata storage implemented
- media upload and publish flow pending
- store publish events
- add dry-run validation

### Phase 4. Safe content intake

- add source allowlist model
- add content import pipeline
- add source metadata capture
- add approval queue
- add dedupe checks

### Phase 5. Scheduler and controls

- add per-account schedule windows
- add enable or disable controls
- add pause and resume
- add concurrency guards
- add retry rules

### Phase 6. Control UI

Status: partial

- basic FastAPI control-plane endpoints implemented
- account dashboard pending
- queue dashboard pending
- run history UI pending
- settings editor pending
- manual approve or reject actions pending

### Phase 7. Packaging and local deployment

- local install guide
- Windows Task Scheduler or background service mode
- Linux systemd example
- backup and restore plan

## Best-Practice Gaps Filled In

- use tokens, not raw passwords, wherever APIs support it
- keep a full audit trail for every publish action
- add idempotency so retries cannot double-post
- treat approval as part of the ingestion pipeline, not an afterthought
- isolate platform code so policy or API breakage on one platform does not stall the others
- support both browser UI and headless operation from day one

## Open Decisions To Confirm Later

- exact packaging format for local installs
- whether the UI should be server-rendered or API plus minimal frontend
- whether media should be stored only locally or optionally mirrored to object storage
- whether approval is mandatory for all imported content or only third-party content

## Implemented Commands

Verified local commands at the current stage:

- `python -m sm_manager bootstrap`
- `python -m sm_manager sync-local-accounts --platform instagram`
- `python -m sm_manager import-local-credentials --platform instagram`
- `python -m sm_manager secret-store-status --platform instagram`
- `python -m sm_manager instagram-auth-status --account ig_test_account_1`
- `python -m sm_manager store-platform-token --platform instagram --account ig_test_account_1 --name access_token --value test_access_token_value --expires-at 2026-12-31T00:00:00+00:00`
- `python -m sm_manager instagram-dry-run --account ig_test_account_1 --caption "Initial dry-run post" --source-username source_creator`
- `python -m sm_manager status`
- `python -m sm_manager serve`

Current behavior of the dry-run path:

- validates the account label against the hidden local credential file
- syncs account metadata into SQLite
- records job execution history
- records a publish event
- does not send any request to Instagram yet

Current behavior of the auth-readiness path:

- imports local passwords into the secure secret backend for operator-side storage only
- prefers Windows keyring or another OS keychain backend when available
- falls back to an encrypted local vault file when keyring is unavailable
- tracks token metadata in SQLite without storing raw token values there
- reports whether Meta app configuration env vars are present
- does not start OAuth or exchange tokens yet

## References

- Meta Instagram API with Instagram Login: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/
- Meta Instagram API with Facebook Login: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/
- Meta Instagram Content Publishing: https://developers.facebook.com/docs/instagram-platform/content-publishing/
