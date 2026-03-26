from __future__ import annotations

from fastapi import FastAPI, Query

from sm_manager.core.accounts import get_synced_accounts, sync_platform_accounts
from sm_manager.core.config import AppConfig
from sm_manager.core.db import bootstrap_database, list_recent_jobs
from sm_manager.platforms.instagram.auth import get_instagram_auth_status


def create_app() -> FastAPI:
    config = AppConfig.load()
    config.ensure_directories()
    bootstrap_database(config)
    sync_platform_accounts(config, "instagram")

    app = FastAPI(title="sm-manager", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "db_path": str(config.db_path),
            "credential_file_exists": config.credential_file.exists(),
        }

    @app.get("/accounts")
    def accounts(platform: str = Query(default="instagram")) -> dict[str, object]:
        return {
            "platform": platform,
            "accounts": get_synced_accounts(config, platform=platform),
        }

    @app.get("/jobs/recent")
    def recent_jobs(limit: int = Query(default=10, ge=1, le=50)) -> dict[str, object]:
        return {
            "jobs": list_recent_jobs(config, limit=limit),
        }

    @app.get("/instagram/auth/status")
    def instagram_auth_status(account: str = Query(...)) -> dict[str, object]:
        return get_instagram_auth_status(config, account)

    return app
