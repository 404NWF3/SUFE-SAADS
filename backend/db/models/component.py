from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(slots=True)
class AiComponent:
    component_id: UUID
    component_code: str
    component_name: str
    component_layer: str | None
    vendor_name: str | None
    component_type: str
    modality: str | None
    purl: str | None
    homepage_uri: str | None
    lifecycle_status: str
    created_at: datetime


@dataclass(slots=True)
class AiComponentAlias:
    alias_id: int
    component_id: UUID
    alias_name: str
    alias_type: str
    normalized_alias: str
    is_preferred: bool


@dataclass(slots=True)
class AttackComponentImpact:
    impact_id: UUID
    attack_id: UUID
    component_id: UUID
    version_constraint_raw: str | None
    normalized_constraint: str | None
    match_mode: str
    impact_scope: str
    confidence_score: Decimal
    evidence_uri: str | None
    created_at: datetime
