from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..schemas.intel import BomResolutionReviewDTO
from ..tools import normalize_vendor_name


class BomResolutionReviewerAgent:
    def review_batch(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        reviewed_items: list[dict[str, Any]] = []
        queue_count = 0
        for item in items:
            reviewed = deepcopy(item)
            resolutions: list[dict[str, Any]] = []
            for resolution in reviewed.get("bom_resolutions", []):
                checked = self.review_resolution(resolution)
                if checked.get("resolution_status") != "resolved":
                    queue_count += 1
                resolutions.append(checked)
            reviewed["bom_resolutions"] = resolutions
            reviewed["source_metadata"] = {
                **reviewed.get("source_metadata", {}),
                "bom_review_summary": {
                    "accepted": sum(
                        1
                        for resolution in resolutions
                        if (resolution.get("review") or {}).get("decision") == "accept"
                    ),
                    "revised": sum(
                        1
                        for resolution in resolutions
                        if (resolution.get("review") or {}).get("decision") == "revise"
                    ),
                    "review_queue": sum(
                        1
                        for resolution in resolutions
                        if resolution.get("resolution_status") != "resolved"
                    ),
                },
            }
            reviewed_items.append(reviewed)
        return {
            "standardized_items": reviewed_items,
            "bom_queue_count": queue_count,
        }

    def review_resolution(self, resolution: dict[str, Any]) -> dict[str, Any]:
        checked = deepcopy(resolution)
        reasons: list[str] = []
        ambiguity_notes: list[str] = []
        decision = "accept"
        selected = checked.get("selected_component")
        candidates = list(checked.get("candidate_components", []))

        # Detect whether this resolution came from LLM
        llm_resolved = any(
            "llm_reason:" in rc or "llm_no_match" in rc or "llm_low_confidence" in rc
            for rc in checked.get("reason_codes", [])
        )

        if checked.get("resolution_status") == "unresolved" or selected is None:
            decision = "review_queue"
            reasons.append("no confident component resolution available")
        else:
            mentioned_vendor = normalize_vendor_name(checked.get("mentioned_vendor"))

            # --- LLM-resolved high-confidence accept: skip heuristic downgrades ---
            # When LLM resolved with high confidence and accept decision, the
            # reviewer trusts the LLM's semantic judgment more than retrieval
            # score heuristics.  We still check vendor mismatch and version
            # ambiguity but skip the fuzzy-threshold and candidate-gap rules.
            llm_high_confidence = (
                llm_resolved
                and float(checked.get("match_confidence", 0.0)) >= 0.85
                and checked.get("resolution_status") == "resolved"
            )

            if checked.get("match_mode") == "embedding" and not llm_high_confidence:
                alias_candidate = self._find_mode_candidate(
                    candidates, {"exact", "alias"}
                )
                if alias_candidate is not None and float(
                    alias_candidate.get("final_score", 0.0)
                ) >= max(0.82, float(selected.get("final_score", 0.0)) - 0.08):
                    selected = alias_candidate
                    checked["selected_component"] = alias_candidate
                    checked["match_mode"] = alias_candidate.get("match_mode")
                    checked["match_confidence"] = float(
                        alias_candidate.get("final_score", 0.0)
                    )
                    decision = "revise"
                    reasons.append(
                        "reviewer replaced embedding-first candidate with stronger alias match"
                    )
            selected_vendor = normalize_vendor_name(selected.get("vendor_name"))
            if (
                mentioned_vendor
                and selected_vendor
                and mentioned_vendor != selected_vendor
            ):
                alternate = self._find_vendor_aligned_candidate(
                    candidates, mentioned_vendor
                )
                if alternate is not None:
                    selected = alternate
                    checked["selected_component"] = alternate
                    checked["match_mode"] = alternate.get("match_mode")
                    checked["match_confidence"] = float(
                        alternate.get("final_score", 0.0)
                    )
                    decision = "revise"
                    reasons.append(
                        "reviewer swapped to vendor-aligned component candidate"
                    )
                else:
                    decision = "review_queue"
                    reasons.append(
                        "selected component vendor conflicts with mention vendor"
                    )
            if checked.get("mentioned_version") and not checked.get(
                "normalized_version_constraint"
            ):
                decision = "review_queue"
                reasons.append("version constraint remains ambiguous")

            # --- Heuristic candidate-gap and fuzzy checks (skip for LLM high-confidence) ---
            if not llm_high_confidence:
                if len(candidates) > 1:
                    ranked_candidates = sorted(
                        candidates,
                        key=lambda candidate: float(candidate.get("final_score", 0.0)),
                        reverse=True,
                    )
                    first = float(ranked_candidates[0].get("final_score", 0.0))
                    second = float(ranked_candidates[1].get("final_score", 0.0))
                    if first - second < 0.05 and first < 0.9:
                        decision = "review_queue"
                        ambiguity_notes.append(
                            "multiple component candidates remain too close"
                        )
                if (
                    checked.get("match_mode") in {"trigram", "embedding"}
                    and float(checked.get("match_confidence", 0.0)) < 0.85
                ):
                    decision = "review_queue"
                    ambiguity_notes.append("fuzzy-only match needs manual confirmation")
                if len(str(checked.get("normalized_alias", ""))) < 4 and checked.get(
                    "match_mode"
                ) not in {
                    "exact",
                    "alias",
                }:
                    decision = "review_queue"
                    ambiguity_notes.append("alias normalization may be too coarse")
            elif llm_high_confidence:
                reasons.append("llm high-confidence resolution accepted by reviewer")

        if decision == "review_queue":
            checked["resolution_status"] = "review_queue"
        review = BomResolutionReviewDTO(
            decision=decision,
            reasons=reasons or ["resolution passes reviewer checks"],
            ambiguity_notes=ambiguity_notes,
            component_suggestion=selected,
        ).model_dump(mode="python")
        checked["review"] = review
        return checked

    def _find_vendor_aligned_candidate(
        self,
        candidates: list[dict[str, Any]],
        mentioned_vendor: str,
    ) -> dict[str, Any] | None:
        for candidate in candidates:
            if normalize_vendor_name(candidate.get("vendor_name")) == mentioned_vendor:
                return candidate
        return None

    def _find_mode_candidate(
        self,
        candidates: list[dict[str, Any]],
        target_modes: set[str],
    ) -> dict[str, Any] | None:
        ranked_candidates = sorted(
            candidates,
            key=lambda candidate: float(candidate.get("final_score", 0.0)),
            reverse=True,
        )
        for candidate in ranked_candidates:
            if candidate.get("match_mode") in target_modes:
                return candidate
        return None
