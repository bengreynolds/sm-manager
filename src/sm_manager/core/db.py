from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from sm_manager.core.config import AppConfig


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def bootstrap_database(config: AppConfig) -> None:
    config.ensure_directories()
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                label TEXT NOT NULL,
                username TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'configured',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(platform, label)
            );

            CREATE TABLE IF NOT EXISTS job_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                account_label TEXT NOT NULL,
                action TEXT NOT NULL,
                dry_run INTEGER NOT NULL,
                status TEXT NOT NULL,
                detail_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS publish_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                account_label TEXT NOT NULL,
                media_path TEXT,
                caption TEXT NOT NULL,
                credit TEXT,
                source_username TEXT,
                dry_run INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS account_secrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                account_label TEXT NOT NULL,
                secret_name TEXT NOT NULL,
                secret_key TEXT NOT NULL,
                backend TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(platform, account_label, secret_name)
            );

            CREATE TABLE IF NOT EXISTS platform_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                account_label TEXT NOT NULL,
                token_name TEXT NOT NULL,
                secret_key TEXT NOT NULL,
                backend TEXT NOT NULL,
                expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(platform, account_label, token_name)
            );
            """
        )
        connection.commit()


def upsert_account(config: AppConfig, platform: str, label: str, username: str, status: str = "configured") -> None:
    timestamp = _utc_now()
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO accounts (platform, label, username, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform, label) DO UPDATE SET
                username = excluded.username,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (platform, label, username, status, timestamp, timestamp),
        )
        connection.commit()


def list_accounts(config: AppConfig, platform: str | None = None) -> list[dict[str, str]]:
    query = "SELECT platform, label, username, status, updated_at FROM accounts"
    params: tuple[str, ...] = ()
    if platform:
        query += " WHERE platform = ?"
        params = (platform,)
    query += " ORDER BY platform, label"

    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        rows = cursor.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def count_accounts(config: AppConfig, platform: str | None = None) -> int:
    query = "SELECT COUNT(*) FROM accounts"
    params: tuple[str, ...] = ()
    if platform:
        query += " WHERE platform = ?"
        params = (platform,)
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        return int(cursor.execute(query, params).fetchone()[0])


def record_job_execution(
    config: AppConfig,
    platform: str,
    account_label: str,
    action: str,
    dry_run: bool,
    status: str,
    detail: dict[str, object],
) -> int:
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO job_executions (platform, account_label, action, dry_run, status, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                platform,
                account_label,
                action,
                int(dry_run),
                status,
                json.dumps(detail, sort_keys=True),
                _utc_now(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def record_publish_event(
    config: AppConfig,
    platform: str,
    account_label: str,
    media_path: str | None,
    caption: str,
    credit: str | None,
    source_username: str | None,
    dry_run: bool,
    status: str,
) -> int:
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO publish_events (
                platform, account_label, media_path, caption, credit, source_username, dry_run, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                platform,
                account_label,
                media_path,
                caption,
                credit,
                source_username,
                int(dry_run),
                status,
                _utc_now(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def count_recent_jobs(config: AppConfig) -> int:
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        return int(cursor.execute("SELECT COUNT(*) FROM job_executions").fetchone()[0])


def count_publish_events(config: AppConfig) -> int:
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        return int(cursor.execute("SELECT COUNT(*) FROM publish_events").fetchone()[0])


def upsert_account_secret_reference(
    config: AppConfig,
    platform: str,
    account_label: str,
    secret_name: str,
    secret_key: str,
    backend: str,
) -> None:
    timestamp = _utc_now()
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO account_secrets (platform, account_label, secret_name, secret_key, backend, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform, account_label, secret_name) DO UPDATE SET
                secret_key = excluded.secret_key,
                backend = excluded.backend,
                updated_at = excluded.updated_at
            """,
            (platform, account_label, secret_name, secret_key, backend, timestamp, timestamp),
        )
        connection.commit()


def account_secret_exists(config: AppConfig, platform: str, account_label: str, secret_name: str) -> bool:
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        row = cursor.execute(
            """
            SELECT 1
            FROM account_secrets
            WHERE platform = ? AND account_label = ? AND secret_name = ?
            LIMIT 1
            """,
            (platform, account_label, secret_name),
        ).fetchone()
        return row is not None


def upsert_platform_token_reference(
    config: AppConfig,
    platform: str,
    account_label: str,
    token_name: str,
    secret_key: str,
    backend: str,
    expires_at: str | None,
) -> None:
    timestamp = _utc_now()
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO platform_tokens (platform, account_label, token_name, secret_key, backend, expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform, account_label, token_name) DO UPDATE SET
                secret_key = excluded.secret_key,
                backend = excluded.backend,
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
            """,
            (platform, account_label, token_name, secret_key, backend, expires_at, timestamp, timestamp),
        )
        connection.commit()


def get_platform_token_metadata(config: AppConfig, platform: str, account_label: str) -> list[dict[str, object]]:
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        rows = cursor.execute(
            """
            SELECT token_name, secret_key, backend, expires_at, updated_at
            FROM platform_tokens
            WHERE platform = ? AND account_label = ?
            ORDER BY token_name
            """,
            (platform, account_label),
        ).fetchall()
        return [dict(row) for row in rows]


def list_recent_jobs(config: AppConfig, limit: int = 10) -> list[dict[str, object]]:
    with closing(_connect(str(config.db_path))) as connection:
        cursor = connection.cursor()
        rows = cursor.execute(
            """
            SELECT id, platform, account_label, action, dry_run, status, detail_json, created_at
            FROM job_executions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        payload: list[dict[str, object]] = []
        for row in rows:
            item = dict(row)
            item["detail_json"] = json.loads(str(item["detail_json"]))
            payload.append(item)
        return payload
