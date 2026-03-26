from __future__ import annotations

import json
from dataclasses import dataclass

from sm_manager.core.config import AppConfig


@dataclass(slots=True)
class PlatformCredential:
    label: str
    username: str
    password: str

    def redacted(self) -> dict[str, str]:
        return {
            "label": self.label,
            "username": self.username,
            "password": "***",
        }


def load_local_credentials(config: AppConfig) -> dict[str, list[PlatformCredential]]:
    if not config.credential_file.exists():
        return {}

    payload = json.loads(config.credential_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Local credential file must contain a JSON object at the top level.")

    result: dict[str, list[PlatformCredential]] = {}
    for platform, entries in payload.items():
        if not isinstance(entries, list):
            raise ValueError(f"Credential block for {platform!r} must be a list.")

        platform_entries: list[PlatformCredential] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"Credential entry for {platform!r} must be an object.")
            platform_entries.append(
                PlatformCredential(
                    label=str(entry.get("label", "")).strip(),
                    username=str(entry.get("username", "")).strip(),
                    password=str(entry.get("password", "")),
                )
            )
        result[platform] = platform_entries

    return result


def find_platform_credential(config: AppConfig, platform: str, label: str) -> PlatformCredential | None:
    credentials = load_local_credentials(config)
    for entry in credentials.get(platform, []):
        if entry.label == label:
            return entry
    return None
