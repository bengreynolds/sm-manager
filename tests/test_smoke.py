from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from sm_manager.core.accounts import sync_platform_accounts
from sm_manager.core.config import AppConfig
from sm_manager.core.db import (
    bootstrap_database,
    count_accounts,
    count_publish_events,
    count_recent_jobs,
    get_oauth_state,
    get_platform_token_metadata,
    upsert_platform_token_reference,
)
from sm_manager.core.secret_store import get_secret_store
from sm_manager.platforms.instagram.adapter import InstagramAdapter, InstagramDryRunRequest
from sm_manager.platforms.instagram.auth import (
    build_instagram_authorize_url,
    exchange_instagram_code,
    get_instagram_auth_status,
)


class SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "runtime").mkdir()
        (self.root / "config").mkdir()
        (self.root / "secrets").mkdir()
        (self.root / ".platform_credentials.local.json").write_text(
            json.dumps(
                {
                    "instagram": [
                        {
                            "label": "ig_test_account_1",
                            "username": "example_user",
                            "password": "example_password",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        os.environ["SM_MANAGER_SECRET_BACKEND"] = "file"
        os.environ["SM_MANAGER_INSTAGRAM_APP_ID"] = "test_app_id"
        os.environ["SM_MANAGER_INSTAGRAM_APP_SECRET"] = "test_app_secret"
        os.environ["SM_MANAGER_INSTAGRAM_REDIRECT_URI"] = "http://127.0.0.1:8000/instagram/oauth/callback"
        self.config = AppConfig.load(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_bootstrap_creates_database(self) -> None:
        bootstrap_database(self.config)
        self.assertTrue(self.config.db_path.exists())

    def test_sync_local_accounts_upserts_instagram_account(self) -> None:
        bootstrap_database(self.config)
        synced = sync_platform_accounts(self.config, "instagram")
        self.assertEqual(len(synced), 1)
        self.assertEqual(count_accounts(self.config, "instagram"), 1)

    def test_instagram_dry_run_records_job_and_publish_event(self) -> None:
        bootstrap_database(self.config)
        sync_platform_accounts(self.config, "instagram")

        adapter = InstagramAdapter(self.config)
        result = adapter.dry_run_publish(
            InstagramDryRunRequest(
                account_label="ig_test_account_1",
                caption="test caption",
                source_username="source_creator",
            )
        )

        self.assertEqual(result["status"], "dry_run_validated")
        self.assertEqual(count_recent_jobs(self.config), 1)
        self.assertEqual(count_publish_events(self.config), 1)

    def test_imported_passwords_and_token_metadata_are_tracked(self) -> None:
        bootstrap_database(self.config)
        sync_platform_accounts(self.config, "instagram", import_passwords=True)

        store = get_secret_store(self.config)
        self.assertEqual(
            store.get_secret("platform:instagram:account:ig_test_account_1:password"),
            "example_password",
        )

        store.set_secret("platform:instagram:account:ig_test_account_1:token:access_token", "token_value")
        upsert_platform_token_reference(
            config=self.config,
            platform="instagram",
            account_label="ig_test_account_1",
            token_name="access_token",
            secret_key="platform:instagram:account:ig_test_account_1:token:access_token",
            backend=store.backend_name,
            expires_at="2026-12-31T00:00:00+00:00",
        )
        token_metadata = get_platform_token_metadata(self.config, "instagram", "ig_test_account_1")
        self.assertEqual(len(token_metadata), 1)
        self.assertEqual(token_metadata[0]["token_name"], "access_token")

        auth_status = get_instagram_auth_status(self.config, "ig_test_account_1")
        self.assertTrue(auth_status["account_credentials"]["password_imported"])
        self.assertTrue(auth_status["token_state"]["has_access_token"])

    def test_instagram_oauth_url_generation_and_exchange(self) -> None:
        bootstrap_database(self.config)
        sync_platform_accounts(self.config, "instagram", import_passwords=True)

        payload = build_instagram_authorize_url(self.config, "ig_test_account_1")
        parsed = urlparse(str(payload["authorize_url"]))
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(query["client_id"][0], "test_app_id")
        self.assertEqual(query["redirect_uri"][0], "http://127.0.0.1:8000/instagram/oauth/callback")
        self.assertEqual(query["response_type"][0], "code")
        self.assertIn("instagram_business_basic", query["scope"][0])
        self.assertIsNotNone(get_oauth_state(self.config, str(payload["state"])))

        def mock_send(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/oauth/access_token":
                return httpx.Response(200, json={"access_token": "oauth_access_token", "user_id": "12345"})
            return httpx.Response(200, json={"user_id": "12345", "username": "oauth_user"})

        client = httpx.Client(transport=httpx.MockTransport(mock_send))
        result = exchange_instagram_code(
            self.config,
            code="test_code",
            state=str(payload["state"]),
            client=client,
        )
        client.close()

        self.assertEqual(result["status"], "ok")
        auth_status = get_instagram_auth_status(self.config, "ig_test_account_1")
        self.assertTrue(auth_status["token_state"]["has_access_token"])


if __name__ == "__main__":
    unittest.main()
