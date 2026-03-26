from __future__ import annotations

from sm_manager.core.config import AppConfig
from sm_manager.core.db import (
    bootstrap_database,
    list_accounts,
    record_job_execution,
    upsert_account,
    upsert_account_secret_reference,
)
from sm_manager.core.secret_store import get_secret_store
from sm_manager.core.secrets import load_local_credentials


def sync_platform_accounts(
    config: AppConfig,
    platform: str,
    import_passwords: bool = False,
) -> list[dict[str, str]]:
    bootstrap_database(config)
    credentials = load_local_credentials(config)
    platform_credentials = credentials.get(platform, [])
    store = get_secret_store(config) if import_passwords else None

    synced: list[dict[str, str]] = []
    for credential in platform_credentials:
        upsert_account(
            config=config,
            platform=platform,
            label=credential.label,
            username=credential.username,
        )
        if import_passwords and store is not None:
            secret_key = f"platform:{platform}:account:{credential.label}:password"
            store.set_secret(secret_key, credential.password)
            upsert_account_secret_reference(
                config=config,
                platform=platform,
                account_label=credential.label,
                secret_name="password",
                secret_key=secret_key,
                backend=store.backend_name,
            )
        synced.append(
            {
                "label": credential.label,
                "username": credential.username,
                "platform": platform,
            }
        )

    if import_passwords and synced:
        record_job_execution(
            config=config,
            platform=platform,
            account_label="*",
            action="import_local_credentials",
            dry_run=False,
            status="completed",
            detail={"imported_count": len(synced), "secret_backend": store.describe() if store else {}},
        )

    return synced


def get_synced_accounts(config: AppConfig, platform: str | None = None) -> list[dict[str, str]]:
    return list_accounts(config=config, platform=platform)
