from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.models.integration.sync_checkpoint import IntegrationSyncCheckpoint
from app.repositories.base import BaseRepository


class SyncCheckpointRepository(BaseRepository[IntegrationSyncCheckpoint]):
    model = IntegrationSyncCheckpoint

    def get(self, integration_name: str, entity_type: str) -> IntegrationSyncCheckpoint | None:
        stmt = select(self.model).where(
            self.model.integration_name == integration_name, self.model.entity_type == entity_type
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_or_create(
        self, integration_name: str, entity_type: str
    ) -> IntegrationSyncCheckpoint:
        existing = self.get(integration_name, entity_type)
        if existing is not None:
            return existing
        checkpoint = self.model(integration_name=integration_name, entity_type=entity_type)
        self.session.add(checkpoint)
        self.session.flush()
        return checkpoint

    def mark_running(self, checkpoint: IntegrationSyncCheckpoint) -> IntegrationSyncCheckpoint:
        return self.update(
            checkpoint, status="RUNNING", last_attempted_run_at=datetime.now(UTC)
        )

    def mark_success(
        self,
        checkpoint: IntegrationSyncCheckpoint,
        *,
        checkpoint_value: str,
        metadata: dict[str, Any] | None = None,
    ) -> IntegrationSyncCheckpoint:
        now = datetime.now(UTC)
        return self.update(
            checkpoint,
            status="SUCCESS",
            checkpoint_value=checkpoint_value,
            last_successful_run_at=now,
            last_attempted_run_at=now,
            metadata_json=metadata,
        )

    def mark_failed(
        self, checkpoint: IntegrationSyncCheckpoint, *, metadata: dict[str, Any] | None = None
    ) -> IntegrationSyncCheckpoint:
        return self.update(
            checkpoint,
            status="FAILED",
            last_attempted_run_at=datetime.now(UTC),
            metadata_json=metadata,
        )
