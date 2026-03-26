from __future__ import annotations

import os

from sm_manager.core.config import AppConfig
from sm_manager.core.db import account_secret_exists, get_platform_token_metadata
from sm_manager.core.secret_store import get_secret_store


def get_instagram_auth_status(config: AppConfig, account_label: str) -> dict[str, object]:
    store = get_secret_store(config)
    app_id = os.getenv("SM_MANAGER_INSTAGRAM_APP_ID")
    app_secret = os.getenv("SM_MANAGER_INSTAGRAM_APP_SECRET")
    redirect_uri = os.getenv("SM_MANAGER_INSTAGRAM_REDIRECT_URI")
    token_metadata = get_platform_token_metadata(config, "instagram", account_label)

    token_names = {str(item["token_name"]) for item in token_metadata}

    return {
        "status": "ok",
        "command": "instagram-auth-status",
        "platform": "instagram",
        "account_label": account_label,
        "secret_backend": store.describe(),
        "app_config": {
            "app_id_present": bool(app_id),
            "app_secret_present": bool(app_secret),
            "redirect_uri_present": bool(redirect_uri),
        },
        "account_credentials": {
            "password_imported": account_secret_exists(config, "instagram", account_label, "password"),
            "note": "Stored local passwords are not used for official Instagram API auth.",
        },
        "token_state": {
            "has_access_token": "access_token" in token_names,
            "has_refresh_token": "refresh_token" in token_names,
            "tokens": token_metadata,
        },
        "ready_for_oauth_work": bool(app_id and app_secret and redirect_uri),
    }
