from __future__ import annotations

import os
import secrets as py_secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from sm_manager.core.config import AppConfig
from sm_manager.core.db import (
    account_secret_exists,
    create_oauth_state,
    get_oauth_state,
    get_platform_token_metadata,
    mark_oauth_state_consumed,
    record_job_execution,
    upsert_platform_token_reference,
)
from sm_manager.core.secret_store import get_secret_store


DEFAULT_AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
DEFAULT_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
DEFAULT_PROFILE_URL = "https://graph.instagram.com/me"
DEFAULT_SCOPES = ["instagram_business_basic", "instagram_business_content_publish"]


@dataclass(slots=True)
class InstagramOAuthConfig:
    app_id: str | None
    app_secret: str | None
    redirect_uri: str | None
    authorize_url: str
    token_url: str
    profile_url: str
    scopes: list[str]

    @classmethod
    def from_env(cls) -> "InstagramOAuthConfig":
        scopes_raw = os.getenv("SM_MANAGER_INSTAGRAM_SCOPES", ",".join(DEFAULT_SCOPES))
        scopes = [item.strip() for item in scopes_raw.split(",") if item.strip()]
        return cls(
            app_id=os.getenv("SM_MANAGER_INSTAGRAM_APP_ID"),
            app_secret=os.getenv("SM_MANAGER_INSTAGRAM_APP_SECRET"),
            redirect_uri=os.getenv("SM_MANAGER_INSTAGRAM_REDIRECT_URI"),
            authorize_url=os.getenv("SM_MANAGER_INSTAGRAM_AUTHORIZE_URL", DEFAULT_AUTHORIZE_URL),
            token_url=os.getenv("SM_MANAGER_INSTAGRAM_TOKEN_URL", DEFAULT_TOKEN_URL),
            profile_url=os.getenv("SM_MANAGER_INSTAGRAM_PROFILE_URL", DEFAULT_PROFILE_URL),
            scopes=scopes or DEFAULT_SCOPES,
        )


def get_instagram_auth_status(config: AppConfig, account_label: str) -> dict[str, object]:
    store = get_secret_store(config)
    auth_config = InstagramOAuthConfig.from_env()
    token_metadata = get_platform_token_metadata(config, "instagram", account_label)
    token_names = {str(item["token_name"]) for item in token_metadata}

    return {
        "status": "ok",
        "command": "instagram-auth-status",
        "platform": "instagram",
        "account_label": account_label,
        "secret_backend": store.describe(),
        "app_config": {
            "app_id_present": bool(auth_config.app_id),
            "app_secret_present": bool(auth_config.app_secret),
            "redirect_uri_present": bool(auth_config.redirect_uri),
            "authorize_url": auth_config.authorize_url,
            "token_url": auth_config.token_url,
            "profile_url": auth_config.profile_url,
            "requested_scopes": auth_config.scopes,
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
        "ready_for_oauth_work": bool(auth_config.app_id and auth_config.app_secret and auth_config.redirect_uri),
    }


def build_instagram_authorize_url(config: AppConfig, account_label: str) -> dict[str, object]:
    auth_config = InstagramOAuthConfig.from_env()
    if not auth_config.app_id or not auth_config.redirect_uri:
        raise RuntimeError(
            "Instagram OAuth is not configured. Set SM_MANAGER_INSTAGRAM_APP_ID and "
            "SM_MANAGER_INSTAGRAM_REDIRECT_URI before generating the auth URL."
        )

    state = py_secrets.token_urlsafe(24)
    create_oauth_state(config, "instagram", account_label, state, auth_config.redirect_uri)

    query = urlencode(
        {
            "client_id": auth_config.app_id,
            "redirect_uri": auth_config.redirect_uri,
            "response_type": "code",
            "scope": ",".join(auth_config.scopes),
            "state": state,
        }
    )
    authorize_url = f"{auth_config.authorize_url}?{query}"

    return {
        "status": "ok",
        "command": "instagram-oauth-url",
        "platform": "instagram",
        "account_label": account_label,
        "authorize_url": authorize_url,
        "state": state,
        "redirect_uri": auth_config.redirect_uri,
        "scopes": auth_config.scopes,
        "note": "Open the authorize_url in a browser while the local FastAPI server is running on the configured redirect URI.",
    }


def exchange_instagram_code(
    config: AppConfig,
    code: str,
    state: str,
    client: httpx.Client | None = None,
) -> dict[str, object]:
    auth_config = InstagramOAuthConfig.from_env()
    if not auth_config.app_id or not auth_config.app_secret or not auth_config.redirect_uri:
        raise RuntimeError(
            "Instagram OAuth is not fully configured. Set SM_MANAGER_INSTAGRAM_APP_ID, "
            "SM_MANAGER_INSTAGRAM_APP_SECRET, and SM_MANAGER_INSTAGRAM_REDIRECT_URI."
        )

    oauth_state = get_oauth_state(config, state)
    if oauth_state is None:
        raise RuntimeError("Unknown OAuth state. Start the Instagram OAuth flow again.")
    if oauth_state["consumed_at"] is not None:
        raise RuntimeError("OAuth state has already been used. Start the Instagram OAuth flow again.")

    should_close_client = client is None
    if client is None:
        client = httpx.Client(timeout=30.0)

    try:
        response = client.post(
            auth_config.token_url,
            data={
                "client_id": auth_config.app_id,
                "client_secret": auth_config.app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": auth_config.redirect_uri,
                "code": code,
            },
        )
        response.raise_for_status()
        token_payload = response.json()
        access_token = str(token_payload["access_token"])

        store = get_secret_store(config)
        account_label = str(oauth_state["account_label"])
        secret_key = f"platform:instagram:account:{account_label}:token:access_token"
        store.set_secret(secret_key, access_token)
        upsert_platform_token_reference(
            config=config,
            platform="instagram",
            account_label=account_label,
            token_name="access_token",
            secret_key=secret_key,
            backend=store.backend_name,
            expires_at=str(token_payload.get("expires_in")) if token_payload.get("expires_in") is not None else None,
        )

        profile_payload: dict[str, object] = {}
        try:
            profile_response = client.get(
                auth_config.profile_url,
                params={
                    "fields": "user_id,username",
                    "access_token": access_token,
                },
            )
            profile_response.raise_for_status()
            profile_payload = profile_response.json()
        except httpx.HTTPError:
            profile_payload = {}

        mark_oauth_state_consumed(config, state)
        record_job_execution(
            config=config,
            platform="instagram",
            account_label=account_label,
            action="instagram_oauth_exchange",
            dry_run=False,
            status="completed",
            detail={
                "token_stored": True,
                "profile_fields_returned": sorted(profile_payload.keys()),
            },
        )

        return {
            "status": "ok",
            "command": "instagram-oauth-exchange",
            "platform": "instagram",
            "account_label": account_label,
            "secret_backend": store.describe(),
            "token_state": {
                "stored": True,
                "token_name": "access_token",
            },
            "profile": profile_payload,
            "note": "OAuth code exchanged and access token stored locally.",
        }
    finally:
        if should_close_client and client is not None:
            client.close()
