from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    project_root: Path
    config_dir: Path
    runtime_dir: Path
    secrets_dir: Path
    db_path: Path
    credential_file: Path
    secret_backend: str
    vault_key_path: Path
    vault_file_path: Path

    @classmethod
    def load(cls, project_root: Path | None = None) -> "AppConfig":
        env_project_root = os.getenv("SM_MANAGER_PROJECT_ROOT")
        if project_root is not None:
            root = project_root.resolve()
        elif env_project_root:
            root = Path(env_project_root).resolve()
        else:
            root = Path(__file__).resolve().parents[3]

        if not root.exists():
            raise FileNotFoundError(f"Project root does not exist: {root}")

        runtime_dir = root / "runtime"
        config_dir = root / "config"
        secrets_dir = root / "secrets"

        db_path = Path(os.getenv("SM_MANAGER_DB_PATH", runtime_dir / "sm_manager.sqlite3"))
        credential_file = Path(
            os.getenv("SM_MANAGER_CREDENTIAL_FILE", root / ".platform_credentials.local.json")
        )
        secret_backend = os.getenv("SM_MANAGER_SECRET_BACKEND", "auto").strip().lower() or "auto"
        vault_key_path = Path(os.getenv("SM_MANAGER_VAULT_KEY_PATH", secrets_dir / "local_vault.key"))
        vault_file_path = Path(os.getenv("SM_MANAGER_VAULT_FILE_PATH", secrets_dir / "local_vault.enc"))

        return cls(
            project_root=root,
            config_dir=config_dir,
            runtime_dir=runtime_dir,
            secrets_dir=secrets_dir,
            db_path=db_path,
            credential_file=credential_file,
            secret_backend=secret_backend,
            vault_key_path=vault_key_path,
            vault_file_path=vault_file_path,
        )

    def ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

    def to_public_dict(self) -> dict[str, str]:
        return {
            "project_root": str(self.project_root),
            "config_dir": str(self.config_dir),
            "runtime_dir": str(self.runtime_dir),
            "secrets_dir": str(self.secrets_dir),
            "db_path": str(self.db_path),
            "credential_file": str(self.credential_file),
            "secret_backend": self.secret_backend,
            "vault_key_path": str(self.vault_key_path),
            "vault_file_path": str(self.vault_file_path),
        }
