from __future__ import annotations

from typing import Any


class QueryFeedbackMemoryService:
    """Lightweight in-memory/DB-adjacent facade for query feedback rows.

    Current Phase 6 implementation uses runtime-context rows as the primary
    source of historical feedback. This service exists so later DB-backed or
    learned-policy upgrades do not require changing agent/node contracts.
    """

    def load_recent_feedback(
        self,
        rows: list[dict[str, Any]] | None,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = list(rows or [])
        return rows[-limit:]

    def append_feedback(
        self,
        existing_rows: list[dict[str, Any]] | None,
        new_rows: list[dict[str, Any]],
        *,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        merged = [*(existing_rows or []), *new_rows]
        return merged[-limit:]
