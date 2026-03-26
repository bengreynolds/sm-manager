from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from cryptography.fernet import Fernet

from sm_manager.core.config import AppConfig

try:
    import keyring
except ImportError:  # pragma: no cover
    keyring = None


SERVICE_NAME = "sm-manager"


class SecretStore(Protocol):
    backend_name: str

    def get_secret(self, key: str) -> str | None: ...

    def set_secret(self, key: str, value: str) -> None: ...

    def describe(self) -> dict[str, object]: ...


@dataclass(slots=True)
class KeyringSecretStore:
    backend_name: str = "keyring"

    def get_secret(self, key: str) -> str | None:
        assert keyring is not None
        return keyring.get_password(SERVICE_NAME, key)

    def set_secret(self, key: str, value: str) -> None:
        assert keyring is not None
        keyring.set_password(SERVICE_NAME, key, value)

    def describe(self) -> dict[str, object]:
        backend_repr = None
        if keyring is not None:
            backend_repr = str(keyring.get_keyring())
        return {
            "backend_name": self.backend_name,
            "backend": backend_repr,
        }


@dataclass(slots=True)
class EncryptedFileSecretStore:
    key_path: Path
    vault_path: Path
    backend_name: str = "encrypted_file"

    def __post_init__(self) -> None:
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)

    def get_secret(self, key: str) -> str | None:
        payload = self._read_payload()
        value = payload.get(key)
        return str(value) if value is not None else None

    def set_secret(self, key: str, value: str) -> None:
        payload = self._read_payload()
        payload[key] = value
        self._write_payload(payload)

    def describe(self) -> dict[str, object]:
        return {
            "backend_name": self.backend_name,
            "vault_path": str(self.vault_path),
            "key_path": str(self.key_path),
            "vault_exists": self.vault_path.exists(),
            "key_exists": self.key_path.exists(),
        }

    def _get_fernet(self) -> Fernet:
        if not self.key_path.exists():
            self.key_path.write_bytes(Fernet.generate_key())
        return Fernet(self.key_path.read_bytes())

    def _read_payload(self) -> dict[str, str]:
        if not self.vault_path.exists():
            return {}
        decrypted = self._get_fernet().decrypt(self.vault_path.read_bytes())
        payload = json.loads(decrypted.decode("utf-8"))
        return {str(key): str(value) for key, value in payload.items()}

    def _write_payload(self, payload: dict[str, str]) -> None:
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        encrypted = self._get_fernet().encrypt(encoded)
        self.vault_path.write_bytes(encrypted)


def _keyring_available() -> bool:
    if keyring is None:
        return False
    try:
        backend = keyring.get_keyring()
        priority = getattr(backend, "priority", 0)
        return bool(priority and priority > 0)
    except Exception:  # pragma: no cover
        return False


def get_secret_store(config: AppConfig) -> SecretStore:
    if config.secret_backend == "keyring":
        if not _keyring_available():
            raise RuntimeError("SM_MANAGER_SECRET_BACKEND=keyring was requested, but no keyring backend is available.")
        return KeyringSecretStore()

    if config.secret_backend == "file":
        return EncryptedFileSecretStore(config.vault_key_path, config.vault_file_path)

    if _keyring_available():
        return KeyringSecretStore()

    return EncryptedFileSecretStore(config.vault_key_path, config.vault_file_path)
