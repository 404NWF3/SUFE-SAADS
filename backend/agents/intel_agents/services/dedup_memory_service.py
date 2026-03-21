from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.db.services.attack_merge_service import AttackMergeService
from backend.db.services.cvss_service import CvssService
from backend.db.services.taxonomy_service import TaxonomyService
from backend.db.typing import SqlContext
from backend.db.unit_of_work import UnitOfWork


class DedupMemoryService:
    """DB/read-model aligned stable attack memory service.

    This service loads prior stable attack units from DB read models when available and
    persists post-dedup merge results back into DB attack tables and governance audit
    records. If the DB is unavailable, it degrades to an in-memory empty baseline for
    the current run, instead of using local file persistence.
    """

    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir

    def load_records(self, *, trace_id: str | None = None) -> list[dict[str, Any]]:
        try:
            with UnitOfWork(
                context=SqlContext(trace_id=trace_id, agent_name="dedup_memory_load"),
                read_only=True,
            ) as uow:
                rows = uow.read_models.list_wp12_attack_feed(limit=500)
                grouped: dict[str, list[Any]] = defaultdict(list)
                for row in rows:
                    grouped[str(row.attack_id)].append(row)

                records: list[dict[str, Any]] = []
                for attack_id, group_rows in grouped.items():
                    first = group_rows[0]
                    taxonomy_items = [
                        {
                            "taxonomy_type": item.taxonomy_type,
                            "taxonomy_code": item.taxonomy_code,
                            "taxonomy_name": item.taxonomy_name,
                            "is_primary": item.is_primary,
                            "confidence_score": float(item.confidence_score),
                        }
                        for item in uow.attacks.list_taxonomy_maps(attack_id)
                    ]
                    evidence = uow.attacks.list_attack_evidence(attack_id)
                    component_impacts = uow.components.list_component_impacts_by_attack(
                        attack_id
                    )

                    bom_mentions: list[dict[str, Any]] = []
                    source_coverage: set[str] = set()
                    evidence_refs: set[str] = set()
                    member_attack_codes: set[str] = set()
                    related_raw_ids: set[str] = set()
                    for row in group_rows:
                        member_attack_codes.add(row.attack_code)
                        if row.artifact_uri:
                            evidence_refs.add(row.artifact_uri)
                        if row.component_name:
                            bom_mentions.append(
                                {
                                    "mentioned_name": row.component_name,
                                    "mentioned_vendor": None,
                                    "mentioned_version": row.normalized_constraint,
                                    "confidence_score": 0.85,
                                    "reason_code": "db_read_model_component",
                                }
                            )
                        if row.taxonomy_code:
                            source_coverage.add(f"taxonomy:{row.taxonomy_code}")
                    for evidence_row in evidence:
                        related_raw_ids.add(str(evidence_row.raw_id))
                        evidence_refs.add(f"raw://{evidence_row.raw_id}")
                    for impact in component_impacts:
                        bom_mentions.append(
                            {
                                "mentioned_name": str(impact.component_id),
                                "mentioned_vendor": None,
                                "mentioned_version": impact.normalized_constraint,
                                "confidence_score": float(impact.confidence_score),
                                "reason_code": f"db_component_impact:{impact.match_mode}",
                            }
                        )

                    dedup_bom = _dedupe_bom_mentions(bom_mentions)
                    records.append(
                        {
                            "stable_attack_id": attack_id,
                            "stable_attack_code": first.attack_code,
                            "canonical_name": first.canonical_name,
                            "attack_family": first.attack_family,
                            "severity_level": first.severity_level,
                            "summary": first.summary,
                            "description": first.summary or first.canonical_name,
                            "taxonomy_items": taxonomy_items,
                            "cvss_hint": {
                                "cvss_version": first.primary_cvss_version,
                                "base_score": float(first.primary_cvss_base_score)
                                if first.primary_cvss_base_score is not None
                                else None,
                                "severity_label": first.primary_cvss_severity_label,
                                "score_origin": "db_primary",
                                "vector_string": first.primary_cvss_vector,
                            }
                            if first.primary_cvss_version
                            else None,
                            "bom_mentions": dedup_bom,
                            "evidence_refs": sorted(evidence_refs),
                            "source_coverage": sorted(source_coverage)
                            or [first.attack_code],
                            "related_raw_ids": sorted(related_raw_ids),
                            "member_attack_codes": sorted(member_attack_codes),
                            "last_decision": "merge",
                            "confidence_score": float(
                                first.primary_cvss_base_score or 0.0
                            )
                            / 10.0
                            if first.primary_cvss_base_score is not None
                            else 0.0,
                        }
                    )
                return records
        except Exception:
            return []
        return []

    def save_records(
        self, records: list[dict[str, Any]], *, trace_id: str | None = None
    ) -> None:
        self.persist_records(records, trace_id=trace_id)

    def persist_records(
        self, records: list[dict[str, Any]], *, trace_id: str | None = None
    ) -> None:
        if not records:
            return
        try:
            with UnitOfWork(
                context=SqlContext(trace_id=trace_id, agent_name="dedup_memory_persist")
            ) as uow:
                attack_merge = AttackMergeService(uow)
                taxonomy_service = TaxonomyService(uow)
                cvss_service = CvssService(uow)
                for record in records:
                    raw_id = next(
                        iter(
                            record.get("related_raw_ids", [])
                            or [f"db_synth_{record['stable_attack_id']}"]
                        )
                    )
                    merge_result = attack_merge.merge_parsed_attack(
                        raw_id=raw_id,
                        attack_code=record.get("stable_attack_code")
                        or record["stable_attack_id"],
                        canonical_name=record["canonical_name"],
                        attack_family=record["attack_family"],
                        severity_level=record["severity_level"],
                        summary=record.get("summary") or record["canonical_name"],
                        description=record.get("description")
                        or record["canonical_name"],
                        exploit_preconditions=None,
                        impact_scope=None,
                        confidence_score=float(record.get("confidence_score", 0.0)),
                        first_seen_at=None,
                        last_seen_at=None,
                        stix_type=None,
                        stix_payload=None,
                        evidence_role="supporting",
                        extractor_name="dedup_memory_service",
                        evidence_snippet=record.get("summary"),
                        dedup_similarity_score=1.0,
                        dedup_rule_name="stable_attack_memory_sync",
                        dedup_decision="merge",
                        dedup_matched_attack_id=None,
                    )
                    if record.get("taxonomy_items"):
                        taxonomy_service.replace_taxonomy_set(
                            attack_id=merge_result.attack_id,
                            taxonomy_items=record["taxonomy_items"],
                        )
                    for bom in record.get("bom_mentions", []):
                        if not bom.get("mentioned_name"):
                            continue
                        bom_resolution = uow.components.find_component_by_alias(
                            str(bom["mentioned_name"]).lower().replace(" ", "")
                        ) or uow.components.get_component_by_name(
                            str(bom["mentioned_name"])
                        )
                        if bom_resolution is not None:
                            uow.components.upsert_attack_component_impact(
                                attack_id=merge_result.attack_id,
                                component_id=str(bom_resolution.component_id),
                                version_constraint_raw=bom.get("mentioned_version"),
                                normalized_constraint=bom.get("mentioned_version"),
                                match_mode="dedup_memory_sync",
                                impact_scope="direct",
                                confidence_score=float(
                                    bom.get("confidence_score", 0.7)
                                ),
                                evidence_uri=next(
                                    iter(record.get("evidence_refs", []) or []), None
                                ),
                            )
                    cvss_hint = record.get("cvss_hint")
                    if cvss_hint and cvss_hint.get("base_score") is not None:
                        cvss_service.add_cvss_assessment(
                            attack_id=merge_result.attack_id,
                            source_raw_id=raw_id,
                            cvss_version=cvss_hint.get("cvss_version") or "3.1",
                            vector_string=cvss_hint.get("vector_string"),
                            base_score=float(cvss_hint.get("base_score")),
                            temporal_score=None,
                            environmental_score=None,
                            severity_label=cvss_hint.get("severity_label") or "Medium",
                            exploitability_subscore=None,
                            impact_subscore=None,
                            score_origin=cvss_hint.get("score_origin") or "estimated",
                            score_provider="dedup_memory_service",
                            confidence_score=0.8,
                            is_primary=True,
                        )
        except Exception:
            return

    def append_audits(
        self, audits: list[dict[str, Any]], *, trace_id: str | None = None
    ) -> None:
        if not audits:
            return
        try:
            with UnitOfWork(
                context=SqlContext(trace_id=trace_id, agent_name="dedup_memory_audit")
            ) as uow:
                for audit in audits:
                    uow.governance.insert_dedup_audit(
                        candidate_raw_id=str(
                            audit.get("candidate_raw_id", "audit-only")
                        ),
                        matched_attack_id=audit.get("matched_attack_id"),
                        similarity_score=float(audit.get("similarity_score", 0.0)),
                        rule_name="phase4_multi_stage_dedup",
                        decision=audit.get("decision", "review"),
                        reviewer_name=None,
                    )
        except Exception:
            return


def _dedupe_bom_mentions(mentions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for mention in mentions:
        key = str(mention.get("mentioned_name", "")).lower()
        if not key:
            continue
        existing = deduped.get(key)
        if existing is None or float(mention.get("confidence_score", 0.0)) >= float(
            existing.get("confidence_score", 0.0)
        ):
            deduped[key] = mention
    return list(deduped.values())
