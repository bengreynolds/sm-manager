from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sm_manager.core.accounts import sync_platform_accounts
from sm_manager.core.config import AppConfig
from sm_manager.core.db import (
    bootstrap_database,
    count_accounts,
    count_publish_events,
    count_recent_jobs,
    upsert_platform_token_reference,
)
from sm_manager.core.log_config import configure_logging, get_logger
from sm_manager.core.secret_store import get_secret_store
from sm_manager.platforms.instagram.adapter import InstagramAdapter, InstagramDryRunRequest
from sm_manager.platforms.instagram.auth import (
    build_instagram_authorize_url,
    exchange_instagram_code,
    get_instagram_auth_status,
)


LOGGER = get_logger(__name__)


def _json_dump(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sm-manager",
        description="Local-first social media automation manager",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Override the repository root. Defaults to the current repo.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level. Defaults to INFO.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap", help="Create runtime directories and bootstrap SQLite.")

    sync_parser = subparsers.add_parser(
        "sync-local-accounts",
        help="Import local test account labels and usernames into SQLite.",
    )
    sync_parser.add_argument(
        "--platform",
        default="instagram",
        choices=["instagram"],
        help="Platform to import. Only Instagram is active.",
    )

    import_parser = subparsers.add_parser(
        "import-local-credentials",
        help="Import local test account passwords into the secure local secret store.",
    )
    import_parser.add_argument(
        "--platform",
        default="instagram",
        choices=["instagram"],
        help="Platform to import. Only Instagram is active.",
    )

    secret_status_parser = subparsers.add_parser(
        "secret-store-status",
        help="Show which secret backend is active.",
    )
    secret_status_parser.add_argument(
        "--platform",
        default="instagram",
        choices=["instagram"],
        help="Platform to inspect. Only Instagram is active.",
    )

    token_parser = subparsers.add_parser(
        "store-platform-token",
        help="Store a platform token in the secure local secret store.",
    )
    token_parser.add_argument("--platform", required=True, choices=["instagram"])
    token_parser.add_argument("--account", required=True, help="Account label.")
    token_parser.add_argument("--name", required=True, help="Token name, for example access_token.")
    token_parser.add_argument("--value", required=True, help="Token value.")
    token_parser.add_argument(
        "--expires-at",
        default=None,
        help="Optional ISO-8601 expiry timestamp stored as metadata only.",
    )

    auth_status_parser = subparsers.add_parser(
        "instagram-auth-status",
        help="Show Instagram auth readiness for a local account.",
    )
    auth_status_parser.add_argument("--account", required=True, help="Account label.")

    oauth_url_parser = subparsers.add_parser(
        "instagram-oauth-url",
        help="Generate the Instagram OAuth URL for a configured account.",
    )
    oauth_url_parser.add_argument("--account", required=True, help="Account label.")

    oauth_exchange_parser = subparsers.add_parser(
        "instagram-oauth-exchange",
        help="Exchange an Instagram OAuth code for a stored access token.",
    )
    oauth_exchange_parser.add_argument("--code", required=True, help="Authorization code returned by Instagram.")
    oauth_exchange_parser.add_argument("--state", required=True, help="State value created during auth URL generation.")

    dry_run_parser = subparsers.add_parser(
        "instagram-dry-run",
        help="Validate an Instagram account and record a dry-run publish event.",
    )
    dry_run_parser.add_argument("--account", required=True, help="Account label from the local credential file.")
    dry_run_parser.add_argument(
        "--media-path",
        default=None,
        help="Optional path to a local media file. If omitted, the dry-run only validates account state.",
    )
    dry_run_parser.add_argument(
        "--caption",
        default="Dry-run caption",
        help="Caption to validate for the dry-run request.",
    )
    dry_run_parser.add_argument(
        "--credit",
        default=None,
        help="Optional credit line to append to the caption preview.",
    )
    dry_run_parser.add_argument(
        "--source-username",
        default=None,
        help="Optional source creator handle for metadata only.",
    )

    subparsers.add_parser("status", help="Show local runtime status.")

    serve_parser = subparsers.add_parser("serve", help="Run the local FastAPI control plane.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    return parser


def handle_bootstrap(config: AppConfig) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    _json_dump(
        {
            "status": "ok",
            "command": "bootstrap",
            "runtime_dir": str(config.runtime_dir),
            "db_path": str(config.db_path),
            "credential_file_exists": config.credential_file.exists(),
        }
    )
    return 0


def handle_sync_local_accounts(config: AppConfig, platform: str) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    synced = sync_platform_accounts(config, platform)
    _json_dump(
        {
            "status": "ok",
            "command": "sync-local-accounts",
            "platform": platform,
            "synced_count": len(synced),
            "accounts": synced,
        }
    )
    return 0


def handle_import_local_credentials(config: AppConfig, platform: str) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    synced = sync_platform_accounts(config, platform, import_passwords=True)
    store = get_secret_store(config)
    _json_dump(
        {
            "status": "ok",
            "command": "import-local-credentials",
            "platform": platform,
            "secret_backend": store.describe(),
            "stored_count": len(synced),
            "accounts": synced,
        }
    )
    return 0


def handle_secret_store_status(config: AppConfig, platform: str) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    store = get_secret_store(config)
    _json_dump(
        {
            "status": "ok",
            "command": "secret-store-status",
            "platform": platform,
            "secret_backend": store.describe(),
        }
    )
    return 0


def handle_store_platform_token(
    config: AppConfig,
    platform: str,
    account: str,
    name: str,
    value: str,
    expires_at: str | None,
) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    store = get_secret_store(config)
    secret_key = f"platform:{platform}:account:{account}:token:{name}"
    store.set_secret(secret_key, value)
    upsert_platform_token_reference(
        config=config,
        platform=platform,
        account_label=account,
        token_name=name,
        secret_key=secret_key,
        backend=store.backend_name,
        expires_at=expires_at,
    )
    _json_dump(
        {
            "status": "ok",
            "command": "store-platform-token",
            "platform": platform,
            "account_label": account,
            "token_name": name,
            "expires_at": expires_at,
            "secret_backend": store.describe(),
        }
    )
    return 0


def handle_instagram_auth_status(config: AppConfig, account: str) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    _json_dump(get_instagram_auth_status(config, account))
    return 0


def handle_instagram_oauth_url(config: AppConfig, account: str) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    _json_dump(build_instagram_authorize_url(config, account))
    return 0


def handle_instagram_oauth_exchange(config: AppConfig, code: str, state: str) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    _json_dump(exchange_instagram_code(config, code=code, state=state))
    return 0


def handle_instagram_dry_run(
    config: AppConfig,
    account: str,
    media_path: str | None,
    caption: str,
    credit: str | None,
    source_username: str | None,
) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    sync_platform_accounts(config, "instagram")

    adapter = InstagramAdapter(config)
    result = adapter.dry_run_publish(
        InstagramDryRunRequest(
            account_label=account,
            media_path=Path(media_path) if media_path else None,
            caption=caption,
            credit=credit,
            source_username=source_username,
        )
    )
    _json_dump(result)
    return 0 if result["status"] == "dry_run_validated" else 1


def handle_status(config: AppConfig) -> int:
    config.ensure_directories()
    bootstrap_database(config)
    _json_dump(
        {
            "status": "ok",
            "command": "status",
            "paths": config.to_public_dict(),
            "credential_file_exists": config.credential_file.exists(),
            "instagram_account_count": count_accounts(config, "instagram"),
            "recent_job_count": count_recent_jobs(config),
            "publish_event_count": count_publish_events(config),
        }
    )
    return 0


def handle_serve(config: AppConfig, host: str, port: int) -> int:
    import uvicorn
    from sm_manager.ui.app import create_app

    config.ensure_directories()
    bootstrap_database(config)

    LOGGER.info("Starting control plane on %s:%s", host, port)
    uvicorn.run(create_app, host=host, port=port, factory=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.log_level)
    config = AppConfig.load(args.project_root)

    if args.command == "bootstrap":
        return handle_bootstrap(config)
    if args.command == "sync-local-accounts":
        return handle_sync_local_accounts(config, args.platform)
    if args.command == "import-local-credentials":
        return handle_import_local_credentials(config, args.platform)
    if args.command == "secret-store-status":
        return handle_secret_store_status(config, args.platform)
    if args.command == "store-platform-token":
        return handle_store_platform_token(
            config=config,
            platform=args.platform,
            account=args.account,
            name=args.name,
            value=args.value,
            expires_at=args.expires_at,
        )
    if args.command == "instagram-auth-status":
        return handle_instagram_auth_status(config, args.account)
    if args.command == "instagram-oauth-url":
        return handle_instagram_oauth_url(config, args.account)
    if args.command == "instagram-oauth-exchange":
        return handle_instagram_oauth_exchange(config, args.code, args.state)
    if args.command == "instagram-dry-run":
        return handle_instagram_dry_run(
            config=config,
            account=args.account,
            media_path=args.media_path,
            caption=args.caption,
            credit=args.credit,
            source_username=args.source_username,
        )
    if args.command == "status":
        return handle_status(config)
    if args.command == "serve":
        return handle_serve(config, args.host, args.port)

    parser.error(f"Unknown command: {args.command}")
    return 2
