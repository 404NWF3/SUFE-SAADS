from __future__ import annotations

import re
from typing import Any

from ..models import AiComponent, AiComponentAlias, AttackComponentImpact
from ..sql import bom_queries as q
from .base import BaseRepository

_ALIAS_CLEAN_RE = re.compile(r"[\s_\-]+")


def normalize_component_alias(alias: str, vendor_name: str | None = None) -> str:
    normalized = _ALIAS_CLEAN_RE.sub("", alias.strip().lower())
    if vendor_name:
        vendor_norm = _ALIAS_CLEAN_RE.sub("", vendor_name.strip().lower())
        if vendor_norm and normalized.startswith(vendor_norm):
            normalized = normalized[len(vendor_norm) :]
    return normalized


class ComponentRepository(BaseRepository):
    def get_component_by_code(self, component_code: str) -> AiComponent | None:
        row = self._fetch_one(q.GET_COMPONENT_BY_CODE, {"component_code": component_code})
        return self._row_to_model(AiComponent, row)

    def get_component_by_name(self, component_name: str) -> AiComponent | None:
        row = self._fetch_one(q.GET_COMPONENT_BY_NAME, {"component_name": component_name})
        return self._row_to_model(AiComponent, row)

    def find_component_by_alias(self, normalized_alias: str) -> AiComponent | None:
        row = self._fetch_one(
            q.GET_COMPONENT_BY_NORMALIZED_ALIAS, {"normalized_alias": normalized_alias}
        )
        return self._row_to_model(AiComponent, row)

    def search_component_alias(self, normalized_alias: str, limit: int = 10) -> list[dict[str, Any]]:
        return self._fetch_all(
            q.SEARCH_COMPONENT_ALIAS,
            {"normalized_alias": normalized_alias, "limit": limit},
        )

    def create_component(
        self,
        *,
        component_code: str,
        component_name: str,
        vendor_name: str | None,
        component_type: str,
        modality: str | None = None,
        purl: str | None = None,
        homepage_uri: str | None = None,
        lifecycle_status: str = "active",
    ) -> AiComponent:
        row = self._fetch_one(
            q.CREATE_COMPONENT,
            {
                "component_code": component_code,
                "component_name": component_name,
                "vendor_name": vendor_name,
                "component_type": component_type,
                "modality": modality,
                "purl": purl,
                "homepage_uri": homepage_uri,
                "lifecycle_status": lifecycle_status,
            },
        )
        return self._require_model(AiComponent, row, message="Failed to create ai_component")

    def insert_component_alias(
        self,
        *,
        component_id: str,
        alias_name: str,
        alias_type: str,
        normalized_alias: str | None = None,
        vendor_name: str | None = None,
        is_preferred: bool = False,
    ) -> AiComponentAlias:
        normalized_alias = normalized_alias or normalize_component_alias(alias_name, vendor_name)
        row = self._fetch_one(
            q.INSERT_COMPONENT_ALIAS,
            {
                "component_id": component_id,
                "alias_name": alias_name,
                "alias_type": alias_type,
                "normalized_alias": normalized_alias,
                "is_preferred": is_preferred,
            },
        )
        return self._require_model(AiComponentAlias, row, message="Failed to insert component alias")

    def list_component_aliases(self, component_id: str) -> list[AiComponentAlias]:
        rows = self._fetch_all(q.LIST_COMPONENT_ALIASES, {"component_id": component_id})
        return [AiComponentAlias(**row) for row in rows]

    def upsert_attack_component_impact(
        self,
        *,
        attack_id: str,
        component_id: str,
        version_constraint_raw: str | None = None,
        normalized_constraint: str | None = None,
        match_mode: str,
        impact_scope: str,
        confidence_score: float,
        evidence_uri: str | None = None,
    ) -> AttackComponentImpact:
        row = self._fetch_one(
            q.UPSERT_ATTACK_COMPONENT_IMPACT,
            {
                "attack_id": attack_id,
                "component_id": component_id,
                "version_constraint_raw": version_constraint_raw,
                "normalized_constraint": normalized_constraint,
                "match_mode": match_mode,
                "impact_scope": impact_scope,
                "confidence_score": confidence_score,
                "evidence_uri": evidence_uri,
            },
        )
        return self._require_model(
            AttackComponentImpact, row, message="Failed to upsert attack_component_impact"
        )

    def list_component_impacts_by_attack(self, attack_id: str) -> list[AttackComponentImpact]:
        rows = self._fetch_all(q.LIST_COMPONENT_IMPACTS_BY_ATTACK, {"attack_id": attack_id})
        return [AttackComponentImpact(**row) for row in rows]

    def list_attacks_by_component(self, component_id: str) -> list[AttackComponentImpact]:
        rows = self._fetch_all(q.LIST_ATTACKS_BY_COMPONENT, {"component_id": component_id})
        return [AttackComponentImpact(**row) for row in rows]

