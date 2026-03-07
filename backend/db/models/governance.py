from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(slots=True)
class DedupAudit:
    audit_id: int
    candidate_raw_id: UUID
    matched_attack_id: UUID | None
    similarity_score: Decimal
    rule_name: str
    decision: str
    reviewer_name: str | None
    created_at: datetime


@dataclass(slots=True)
class BomResolutionQueueItem:
    queue_id: int
    attack_id: UUID | None
    raw_id: UUID | None
    mentioned_name: str
    mentioned_vendor: str | None
    mentioned_version: str | None
    reason_code: str
    queue_status: str
    resolved_component_id: UUID | None
    created_at: datetime
    resolved_at: datetime | None

