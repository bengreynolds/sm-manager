from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, RedirectResponse

from sm_manager.core.accounts import get_synced_accounts, sync_platform_accounts
from sm_manager.core.config import AppConfig
from sm_manager.core.db import bootstrap_database, list_recent_jobs
from sm_manager.platforms.instagram.auth import (
    build_instagram_authorize_url,
    exchange_instagram_code,
    get_instagram_auth_status,
)


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

    @app.get("/instagram/oauth/start")
    def instagram_oauth_start(
        account: str = Query(...),
        redirect: bool = Query(default=False),
    ):
        payload = build_instagram_authorize_url(config, account)
        if redirect:
            return RedirectResponse(payload["authorize_url"])
        return JSONResponse(payload)

    @app.get("/instagram/oauth/callback")
    def instagram_oauth_callback(
        code: str | None = Query(default=None),
        state: str | None = Query(default=None),
        error: str | None = Query(default=None),
        error_description: str | None = Query(default=None),
    ) -> JSONResponse:
        if error:
            return JSONResponse(
                {
                    "status": "error",
                    "platform": "instagram",
                    "error": error,
                    "error_description": error_description,
                },
                status_code=400,
            )
        if not code or not state:
            return JSONResponse(
                {
                    "status": "error",
                    "platform": "instagram",
                    "error": "missing_code_or_state",
                },
                status_code=400,
            )
        try:
            payload = exchange_instagram_code(config, code=code, state=state)
        except Exception as exc:
            return JSONResponse(
                {
                    "status": "error",
                    "platform": "instagram",
                    "error": "oauth_exchange_failed",
                    "detail": str(exc),
                },
                status_code=400,
            )
        return JSONResponse(payload)

    return app
