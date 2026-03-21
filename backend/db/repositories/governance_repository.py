from __future__ import annotations

from ..models import BomResolutionQueueItem, DedupAudit, QueryFeedbackLog
from ..sql import governance_queries as q
from .base import BaseRepository


class GovernanceRepository(BaseRepository):
    def insert_dedup_audit(
        self,
        *,
        candidate_raw_id: str,
        matched_attack_id: str | None,
        similarity_score: float,
        rule_name: str,
        decision: str,
        reviewer_name: str | None = None,
    ) -> DedupAudit:
        row = self._fetch_one(
            q.INSERT_DEDUP_AUDIT,
            {
                "candidate_raw_id": candidate_raw_id,
                "matched_attack_id": matched_attack_id,
                "similarity_score": similarity_score,
                "rule_name": rule_name,
                "decision": decision,
                "reviewer_name": reviewer_name,
            },
        )
        return self._require_model(DedupAudit, row, message="Failed to insert dedup_audit")

    def list_dedup_candidates_for_review(self, limit: int = 100) -> list[DedupAudit]:
        rows = self._fetch_all(q.LIST_DEDUP_REVIEW_ITEMS, {"limit": limit})
        return [DedupAudit(**row) for row in rows]

    def enqueue_bom_resolution(
        self,
        *,
        attack_id: str | None,
        raw_id: str | None,
        mentioned_name: str,
        mentioned_vendor: str | None,
        mentioned_version: str | None,
        reason_code: str,
    ) -> BomResolutionQueueItem:
        row = self._fetch_one(
            q.ENQUEUE_BOM_RESOLUTION,
            {
                "attack_id": attack_id,
                "raw_id": raw_id,
                "mentioned_name": mentioned_name,
                "mentioned_vendor": mentioned_vendor,
                "mentioned_version": mentioned_version,
                "reason_code": reason_code,
            },
        )
        return self._require_model(
            BomResolutionQueueItem, row, message="Failed to enqueue bom_resolution_queue"
        )

    def list_open_bom_queue(self, limit: int = 100) -> list[BomResolutionQueueItem]:
        rows = self._fetch_all(q.LIST_OPEN_BOM_QUEUE, {"limit": limit})
        return [BomResolutionQueueItem(**row) for row in rows]

    def resolve_bom_queue_item(
        self, *, queue_id: int, resolved_component_id: str
    ) -> BomResolutionQueueItem | None:
        row = self._fetch_one(
            q.RESOLVE_BOM_QUEUE_ITEM,
            {"queue_id": queue_id, "resolved_component_id": resolved_component_id},
        )
        return self._row_to_model(BomResolutionQueueItem, row)

    def reject_bom_queue_item(self, *, queue_id: int) -> BomResolutionQueueItem | None:
        row = self._fetch_one(q.REJECT_BOM_QUEUE_ITEM, {"queue_id": queue_id})
        return self._row_to_model(BomResolutionQueueItem, row)

    def insert_query_feedback(self, row: dict) -> QueryFeedbackLog | None:
        result = self._fetch_one(q.INSERT_QUERY_FEEDBACK_BATCH, row)
        return self._row_to_model(QueryFeedbackLog, result)

    def load_recent_query_feedback(self, limit: int = 100) -> list[QueryFeedbackLog]:
        rows = self._fetch_all(q.LOAD_RECENT_QUERY_FEEDBACK, {"limit": limit})
        return [QueryFeedbackLog(**row) for row in rows]

