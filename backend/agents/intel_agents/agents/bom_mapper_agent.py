from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Literal

from ..schemas.intel import BomResolutionDTO, LlmBomResolutionAuditDTO
from ..services.component_resolution_service import ComponentResolutionService
from ..tools.llm_bom_resolver_tools import LangChainLlmBomResolver


# ---------------------------------------------------------------------------
# Strategy type
# ---------------------------------------------------------------------------
BomResolutionStrategyValue = Literal[
    "rules_only", "llm_optional", "llm_required", "rules_only_degraded"
]


class BomMapperAgent:
    """Phase 5 BOM resolution agent.

    Architecture (LLM-primary, mirrors Phase 3 design):
    1. ``ComponentResolutionService.retrieve_candidates_for_mention()`` does
       candidate recall (seed catalog + DB alias/trigram/embedding).
    2. ``LangChainLlmBomResolver.resolve()`` receives attack context +
       candidates and makes the final accept/review_queue/no_match decision.
    3. ``ComponentResolutionService.persist_llm_resolution()`` builds the
       ``BomResolutionDTO`` and optionally persists to DB.
    4. Fallback: rules-only path uses the original ``resolve_item()`` logic.

    The strategy parameter controls which path is taken:
    - ``llm_required``: LLM must succeed, otherwise the node fails.
    - ``llm_optional``: LLM is attempted; on failure, falls back to rules.
    - ``rules_only``: no LLM, uses existing rule-based resolution.
    - ``rules_only_degraded``: same as rules_only but flagged as degraded.
    """

    def __init__(
        self,
        *,
        resolution_service: ComponentResolutionService | None = None,
        strategy: BomResolutionStrategyValue = "llm_required",
        llm_model: str = "gpt-5-mini",
        llm_temperature: float = 0.0,
        validate_online: bool = False,
        llm_runtime_config: dict[str, Any] | None = None,
    ) -> None:
        self.resolution_service = resolution_service or ComponentResolutionService()
        self.strategy = strategy
        self.llm_model = llm_model
        self.llm_temperature = llm_temperature
        self.validate_online = validate_online
        self.llm_runtime_config = llm_runtime_config or {}

        self._llm: LangChainLlmBomResolver | None = None
        if strategy in ("llm_required", "llm_optional"):
            self._llm = LangChainLlmBomResolver(
                model=llm_model,
                temperature=llm_temperature,
                runtime_config=self.llm_runtime_config,
            )
            if validate_online and strategy == "llm_required":
                self._llm.validate_connectivity()

    def resolve_batch(
        self,
        items: list[dict[str, Any]],
        *,
        trace_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Resolve BOM mentions for a batch of standardized items.

        Returns
        -------
        tuple[list[dict], list[dict]]
            (resolved_items, llm_bom_resolution_audits)
        """
        resolved_items: list[dict[str, Any]] = []
        all_audits: list[dict[str, Any]] = []
        queue_count = 0

        for item in items:
            if self.strategy in ("llm_required", "llm_optional"):
                resolved, item_queue, audits = self._llm_primary_resolve_item(
                    item, trace_id=trace_id
                )
            else:
                resolved, item_queue, audits = self._rules_only_resolve_item(
                    item, trace_id=trace_id
                )
            resolved_items.append(resolved)
            queue_count += item_queue
            all_audits.extend(audits)

        return resolved_items, all_audits

    # ------------------------------------------------------------------
    # LLM-primary path
    # ------------------------------------------------------------------

    def _llm_primary_resolve_item(
        self,
        item: dict[str, Any],
        *,
        trace_id: str | None = None,
    ) -> tuple[dict[str, Any], int, list[dict[str, Any]]]:
        """Resolve all BOM mentions in an item using LLM as primary judge."""
        updated = deepcopy(item)
        resolutions: list[dict[str, Any]] = []
        unresolved_mentions: list[dict[str, Any]] = []
        audits: list[dict[str, Any]] = []
        queue_count = 0

        attack_context = {
            "attack_name": updated.get("canonical_name", ""),
            "attack_family": updated.get("attack_family", ""),
            "attack_summary": updated.get("summary", "")
            or updated.get("description", ""),
        }
        evidence_text = (
            updated.get("evidence_snippet", "") or updated.get("description", "") or ""
        )
        evidence_uri = next(iter(updated.get("evidence_refs", []) or []), None)

        for mention_idx, mention in enumerate(updated.get("bom_mentions", [])):
            resolution, audit = self._llm_resolve_mention(
                mention=mention,
                mention_idx=mention_idx,
                item=updated,
                attack_context=attack_context,
                evidence_text=evidence_text,
                evidence_uri=evidence_uri,
                trace_id=trace_id,
            )
            if resolution["resolution_status"] != "resolved":
                queue_count += 1
                unresolved_mentions.append(
                    {
                        "mentioned_name": resolution["mentioned_name"],
                        "mentioned_vendor": resolution.get("mentioned_vendor"),
                        "reason_codes": resolution.get("reason_codes", []),
                        "queue_ref": resolution.get("queue_ref"),
                        "top_candidate": (
                            resolution.get("selected_component") or {}
                        ).get("component_name"),
                    }
                )
            resolutions.append(resolution)
            if audit:
                audits.append(audit)

        updated["bom_resolutions"] = resolutions
        updated["source_metadata"] = {
            **updated.get("source_metadata", {}),
            "bom_resolution_summary": {
                "resolved": sum(
                    1 for r in resolutions if r["resolution_status"] == "resolved"
                ),
                "queued": queue_count,
                "unresolved_mentions": unresolved_mentions,
                "resolution_strategy": self.strategy,
            },
        }
        return updated, queue_count, audits

    def _llm_resolve_mention(
        self,
        *,
        mention: dict[str, Any],
        mention_idx: int,
        item: dict[str, Any],
        attack_context: dict[str, Any],
        evidence_text: str,
        evidence_uri: str | None,
        trace_id: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Resolve a single mention via retrieval + LLM."""
        raw_id = item.get("raw_id", "unknown")
        mentioned_name = str(mention.get("mentioned_name", "")).strip()

        # Step 1: Candidate retrieval
        retrieval = self.resolution_service.retrieve_candidates_for_mention(
            mention, uow=None
        )
        candidates = retrieval["candidates"]

        # Step 2: LLM resolution
        strategy_executed = self.strategy
        llm_decision: dict[str, Any] | None = None
        fallback_reason: str | None = None

        try:
            if self._llm is None:
                raise RuntimeError("LLM resolver not initialized")
            if not self._llm.is_available():
                raise RuntimeError("OPENAI_API_KEY not configured")

            candidate_text = LangChainLlmBomResolver.format_candidate_list(candidates)
            payload = {
                **attack_context,
                "mentioned_name": mentioned_name,
                "mentioned_vendor": mention.get("mentioned_vendor"),
                "mentioned_version": mention.get("mentioned_version"),
                "component_layer_hint": mention.get("component_layer", "unknown"),
                "candidate_list": candidate_text,
                "evidence_text": evidence_text[:2000],
            }
            llm_decision = self._llm.resolve(payload)
            strategy_executed = "llm_primary"

        except Exception as exc:
            if self.strategy == "llm_required":
                raise RuntimeError(
                    f"LLM BOM resolution required but failed for "
                    f"'{mentioned_name}': {exc}"
                ) from exc
            # llm_optional: fall back to rules
            fallback_reason = f"llm_failed:{type(exc).__name__}:{str(exc)[:200]}"
            strategy_executed = "rules_only_degraded"

        # Step 3: Build resolution
        if llm_decision is not None:
            resolution = self.resolution_service.persist_llm_resolution(
                mention=mention,
                llm_decision=llm_decision,
                candidates=candidates,
                evidence_uri=evidence_uri,
                attack_id=None,  # no UoW in this path
                uow=None,
            )
        else:
            # Rules-only fallback
            resolution = self._rule_based_resolution(
                mention=mention,
                candidates=candidates,
                evidence_uri=evidence_uri,
            )

        # Step 4: Build audit
        llm_meta = (
            dict(getattr(self._llm, "last_invocation_meta", {}) or {})
            if llm_decision is not None
            else {}
        )
        audit = self._build_audit(
            raw_id=raw_id,
            mention_idx=mention_idx,
            mentioned_name=mentioned_name,
            strategy_executed=strategy_executed,
            llm_decision=llm_decision,
            fallback_reason=fallback_reason,
            candidate_count=len(candidates),
            llm_meta=llm_meta,
        )

        return resolution, audit

    def _rule_based_resolution(
        self,
        *,
        mention: dict[str, Any],
        candidates: list[dict[str, Any]],
        evidence_uri: str | None,
    ) -> dict[str, Any]:
        """Build a BomResolutionDTO using rules-only logic from candidates.
        This mirrors the original ComponentResolutionService._resolve_mention
        decision logic but without DB persistence."""
        from ..schemas.intel import BomCandidateDTO

        mentioned_name = str(mention.get("mentioned_name", "")).strip()
        mentioned_vendor = mention.get("mentioned_vendor")
        from ..tools import normalize_vendor_name, normalize_version_constraint
        from backend.db.repositories.component_repository import (
            normalize_component_alias,
        )

        normalized_vendor = normalize_vendor_name(mentioned_vendor)
        normalized_alias = normalize_component_alias(mentioned_name)
        vendor_scoped_alias = (
            normalize_component_alias(mentioned_name, mentioned_vendor)
            if mentioned_vendor
            else normalized_alias
        )
        normalized_version = normalize_version_constraint(
            mention.get("mentioned_version")
        )

        selected = candidates[0] if candidates else None
        second = candidates[1] if len(candidates) > 1 else None
        gap = round(
            float(selected.get("final_score", 0.0))
            - float(second.get("final_score", 0.0))
            if second and selected
            else 1.0,
            4,
        )

        reason_codes: list[str] = []
        resolution_status = "unresolved"

        if selected is None or float(selected.get("final_score", 0.0)) < 0.58:
            reason_codes.append("alias_not_found")
        elif (
            selected.get("match_mode") in {"exact", "alias"}
            and float(selected.get("final_score", 0.0)) >= 0.94
        ):
            resolution_status = "resolved"
        elif float(selected.get("final_score", 0.0)) >= 0.9 and gap >= 0.05:
            resolution_status = "resolved"
        elif (
            float(selected.get("final_score", 0.0)) >= 0.8
            and selected.get("match_mode") in {"exact", "alias"}
            and (
                second is None
                or second.get("match_mode") not in {"exact", "alias"}
                or gap >= 0.01
            )
        ):
            resolution_status = "resolved"
        else:
            resolution_status = "review_queue"
            reason_codes.append("conflict")

        if mention.get("mentioned_version") and normalized_version is None:
            reason_codes.append("version_ambiguous")
            if resolution_status == "resolved":
                resolution_status = "review_queue"

        if selected is not None and selected.get("match_mode") in {
            "trigram",
            "embedding",
        }:
            reason_codes.append(f"fuzzy_match:{selected['match_mode']}")

        return BomResolutionDTO(
            mentioned_name=mentioned_name,
            mentioned_vendor=mentioned_vendor,
            mentioned_version=mention.get("mentioned_version"),
            normalized_alias=vendor_scoped_alias or normalized_alias,
            normalized_vendor=normalized_vendor,
            normalized_version_constraint=normalized_version,
            resolution_status=resolution_status,
            selected_component=selected,
            candidate_components=[
                BomCandidateDTO.model_validate(c) for c in candidates
            ],
            match_mode=selected.get("match_mode") if selected else None,
            match_confidence=float(
                selected.get("final_score", 0.0) if selected else 0.0
            ),
            reason_codes=reason_codes,
            queue_ref=None,
            review=None,
        ).model_dump(mode="python")

    # ------------------------------------------------------------------
    # Rules-only path (backward-compatible)
    # ------------------------------------------------------------------

    def _rules_only_resolve_item(
        self,
        item: dict[str, Any],
        *,
        trace_id: str | None = None,
    ) -> tuple[dict[str, Any], int, list[dict[str, Any]]]:
        """Delegate to the original ComponentResolutionService.resolve_item."""
        resolved, queue_count = self.resolution_service.resolve_item(
            item, trace_id=trace_id
        )
        strategy_label = (
            "rules_only_degraded"
            if self.strategy == "rules_only_degraded"
            else "rules_only"
        )
        # Build minimal audit records for traceability
        audits: list[dict[str, Any]] = []
        raw_id = item.get("raw_id", "unknown")
        for idx, mention in enumerate(item.get("bom_mentions", [])):
            audits.append(
                self._build_audit(
                    raw_id=raw_id,
                    mention_idx=idx,
                    mentioned_name=str(
                        mention.get("mentioned_name", "unknown")
                    ).strip(),
                    strategy_executed=strategy_label,
                    llm_decision=None,
                    fallback_reason=(
                        "rules_only_by_strategy"
                        if self.strategy == "rules_only"
                        else "degraded_fallback"
                    ),
                    candidate_count=0,
                )
            )
        return resolved, queue_count, audits

    # ------------------------------------------------------------------
    # Audit builder
    # ------------------------------------------------------------------

    def _build_audit(
        self,
        *,
        raw_id: str,
        mention_idx: int,
        mentioned_name: str,
        strategy_executed: str,
        llm_decision: dict[str, Any] | None,
        fallback_reason: str | None,
        candidate_count: int,
        llm_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        llm_meta = llm_meta or {}
        if llm_decision:
            llm_confidence = float(llm_decision.get("confidence", 0.0))
            llm_decision_val = llm_decision.get("decision", "review_queue")
            llm_reasoning = llm_decision.get("reasoning_summary", "n/a")
            selected = llm_decision.get("selected_component") or {}
            selected_code = selected.get("component_code")
        else:
            llm_confidence = 0.0
            llm_decision_val = "n/a"
            llm_reasoning = fallback_reason or "rules_only"
            selected_code = None

        return LlmBomResolutionAuditDTO(
            raw_id=raw_id,
            mention_index=mention_idx,
            mentioned_name=mentioned_name,
            strategy_requested=self.strategy,
            strategy_executed=strategy_executed,
            llm_model=str(llm_meta.get("llm_model", self.llm_model)),
            llm_profile_id=llm_meta.get("profile_id"),
            prompt_version=(self._llm.PROMPT_VERSION if self._llm else "n/a"),
            llm_confidence=llm_confidence,
            llm_decision=llm_decision_val,
            llm_reasoning=llm_reasoning,
            fallback_reason=fallback_reason,
            candidate_count=candidate_count,
            selected_component_code=selected_code,
            llm_wait_seconds=llm_meta.get("wait_seconds"),
            attempted_profiles=list(llm_meta.get("attempted_profiles", []) or []),
            invoked_at=datetime.now(timezone.utc).isoformat(),
        ).model_dump(mode="python")
