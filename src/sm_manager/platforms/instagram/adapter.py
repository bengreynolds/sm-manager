from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sm_manager.core.config import AppConfig
from sm_manager.core.db import record_job_execution, record_publish_event
from sm_manager.core.secrets import find_platform_credential


@dataclass(slots=True)
class InstagramDryRunRequest:
    account_label: str
    caption: str
    media_path: Path | None = None
    credit: str | None = None
    source_username: str | None = None


class InstagramAdapter:
    platform = "instagram"

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def dry_run_publish(self, request: InstagramDryRunRequest) -> dict[str, object]:
        credential = find_platform_credential(self.config, self.platform, request.account_label)
        if credential is None:
            status = "missing_account"
            detail = {
                "reason": "Account label was not found in the local credential file.",
                "account_label": request.account_label,
            }
            job_id = record_job_execution(
                config=self.config,
                platform=self.platform,
                account_label=request.account_label,
                action="instagram_dry_run_publish",
                dry_run=True,
                status=status,
                detail=detail,
            )
            return {
                "status": status,
                "job_id": job_id,
                "platform": self.platform,
                "account_label": request.account_label,
                "detail": detail,
            }

        media_validation = self._validate_media_path(request.media_path)
        status = "dry_run_validated" if media_validation["ok"] else "invalid_media"

        credit_suffix = f"\n\nCredit: @{request.source_username}" if request.source_username else ""
        explicit_credit = f"\n{request.credit}" if request.credit else ""
        composed_caption = f"{request.caption}{explicit_credit}{credit_suffix}".strip()

        detail = {
            "account_label": request.account_label,
            "username": credential.username,
            "media_validation": media_validation,
            "caption_preview": composed_caption,
            "api_call_performed": False,
        }

        job_id = record_job_execution(
            config=self.config,
            platform=self.platform,
            account_label=request.account_label,
            action="instagram_dry_run_publish",
            dry_run=True,
            status=status,
            detail=detail,
        )
        publish_event_id = record_publish_event(
            config=self.config,
            platform=self.platform,
            account_label=request.account_label,
            media_path=str(request.media_path) if request.media_path else None,
            caption=request.caption,
            credit=request.credit,
            source_username=request.source_username,
            dry_run=True,
            status=status,
        )

        return {
            "status": status,
            "job_id": job_id,
            "publish_event_id": publish_event_id,
            "platform": self.platform,
            "account_label": request.account_label,
            "username": credential.username,
            "media_validation": media_validation,
            "caption_preview": composed_caption,
            "detail": {
                "note": "Dry-run only. No Instagram API request was sent.",
            },
        }

    def _validate_media_path(self, media_path: Path | None) -> dict[str, object]:
        if media_path is None:
            return {
                "ok": True,
                "checked": False,
                "message": "No media path provided. Account-only dry-run completed.",
            }

        if not media_path.exists():
            return {
                "ok": False,
                "checked": True,
                "message": f"Media file does not exist: {media_path}",
            }

        if not media_path.is_file():
            return {
                "ok": False,
                "checked": True,
                "message": f"Media path is not a file: {media_path}",
            }

        return {
            "ok": True,
            "checked": True,
            "message": f"Media file found: {media_path}",
        }
