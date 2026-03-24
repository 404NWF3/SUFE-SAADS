from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from ...schemas.runtime import RuntimeContextDTO
from ...services.stix_graph_service import StixGraphService
from ...tools.llm_stix_graph_tools import (
    LangChainLlmStixExtractor,
    LangChainLlmStixReviewer,
)


class StixSubgraphState(TypedDict, total=False):
    standardized_items: list[dict[str, Any]]
    runtime_context: dict[str, Any]
    trace_id: str | None
    stix_drafts: list[dict[str, Any]]
    stix_bundle_refs: list[dict[str, Any]]


def _extract_graphs(state: StixSubgraphState) -> StixSubgraphState:
    context = RuntimeContextDTO.model_validate(state.get("runtime_context") or {})
    extractor = LangChainLlmStixExtractor(
        model=context.llm_model,
        temperature=context.llm_temperature,
        runtime_config=context.model_dump(mode="python"),
    )
    reviewer = LangChainLlmStixReviewer(
        model=context.llm_model,
        temperature=context.llm_temperature,
        runtime_config=context.model_dump(mode="python"),
    )
    service = StixGraphService()
    drafts: list[dict[str, Any]] = []
    for item in state.get("standardized_items", []):
        payload = service.build_extraction_payload(item)
        attack_code = str(payload.get("attack_code") or "")
        if context.stix_strategy == "rules_only_degraded":
            graph_draft = None
            validation = service.validate_graph_draft(item=item, graph_draft=None)
            review = {
                "decision": "review_queue",
                "confidence": 0.0,
                "reasoning_summary": "STIX extraction skipped because only degraded mode was available.",
                "finding_codes": ["llm_unavailable"],
                "flagged_object_refs": [],
                "flagged_relationship_refs": [],
                "review_trace": [
                    "No LLM STIX extraction was attempted in degraded mode.",
                ],
            }
            materialized = None
        else:
            try:
                graph_draft = extractor.extract(payload)
            except Exception as exc:
                if context.stix_strategy == "llm_required":
                    raise
                graph_draft = None
                validation = service.validate_graph_draft(item=item, graph_draft=None)
                validation["findings"] = [
                    f"llm_extraction_failed:{type(exc).__name__}",
                    *list(validation.get("findings", []) or []),
                ]
                review = {
                    "decision": "review_queue",
                    "confidence": 0.0,
                    "reasoning_summary": f"STIX extraction failed: {type(exc).__name__}",
                    "finding_codes": ["llm_extraction_failed"],
                    "flagged_object_refs": [],
                    "flagged_relationship_refs": [],
                    "review_trace": [
                        "LLM extraction failed before a reviewable graph was produced.",
                    ],
                }
                materialized = None
            else:
                validation = service.validate_graph_draft(
                    item=item,
                    graph_draft=graph_draft,
                )
                try:
                    review = reviewer.review(
                        attack_code=attack_code,
                        graph_draft_json=json.dumps(graph_draft, ensure_ascii=False),
                        graph_validation_json=json.dumps(validation, ensure_ascii=False),
                        evidence_text=str(payload.get("evidence_text", "")),
                    )
                except Exception as exc:
                    if context.stix_strategy == "llm_required":
                        raise
                    review = {
                        "decision": "review_queue",
                        "confidence": 0.0,
                        "reasoning_summary": f"STIX review failed: {type(exc).__name__}",
                        "finding_codes": ["llm_review_failed"],
                        "flagged_object_refs": [],
                        "flagged_relationship_refs": [],
                        "review_trace": [
                            "Graph review failed, so publication was downgraded to review queue.",
                        ],
                    }
                materialized = None
                if not validation.get("fatal"):
                    try:
                        materialized = service.materialize_bundle(
                            item=item,
                            graph_draft=graph_draft,
                            validation=validation,
                        )
                    except Exception as exc:
                        validation = {
                            **validation,
                            "fatal": True,
                            "findings": [
                                *list(validation.get("findings", []) or []),
                                f"materialization_failed:{type(exc).__name__}",
                            ],
                        }
                        review = {
                            **review,
                            "decision": "review_queue",
                            "confidence": 0.0,
                            "reasoning_summary": f"STIX materialization failed: {type(exc).__name__}",
                            "finding_codes": [
                                *list(review.get("finding_codes", []) or []),
                                "materialization_failed",
                            ],
                            "review_trace": [
                                *list(review.get("review_trace", []) or []),
                                "Materialization failed, so the draft was downgraded to review queue.",
                            ],
                        }
        drafts.append(
            {
                "attack_code": attack_code,
                "graph_draft": graph_draft,
                "validation": validation,
                "review": review,
                "materialized": materialized,
                "extractor_model": extractor.last_invocation_meta.get(
                    "llm_model",
                    extractor.model,
                ),
                "reviewer_model": reviewer.last_invocation_meta.get(
                    "llm_model",
                    reviewer.model,
                ),
                "prompt_version": extractor.PROMPT_VERSION,
            }
        )
    return {"stix_drafts": drafts}


def _persist_graphs(state: StixSubgraphState) -> StixSubgraphState:
    service = StixGraphService()
    items = list(state.get("standardized_items", []))
    draft_map = {
        str(row.get("attack_code")): row
        for row in state.get("stix_drafts", [])
        if row.get("attack_code")
    }
    bundle_refs: list[dict[str, Any]] = []
    updated_items: list[dict[str, Any]] = []
    for item in items:
        attack_code = str(item.get("attack_code") or item.get("stable_attack_code") or "")
        draft_row = draft_map.get(attack_code)
        if draft_row is None:
            updated_items.append(item)
            continue
        persisted = service.persist_bundle(
            item=item,
            graph_draft=draft_row["graph_draft"],
            materialized=draft_row["materialized"],
            validation=draft_row["validation"],
            review_decision=draft_row["review"],
            extractor_model=str(draft_row["extractor_model"]),
            reviewer_model=str(draft_row["reviewer_model"]),
            prompt_version=str(draft_row["prompt_version"]),
            trace_id=state.get("trace_id"),
            runtime_context=state.get("runtime_context", {}),
        )
        bundle_refs.append(
            {
                "attack_code": attack_code,
                **persisted,
            }
        )
        updated_items.append(
            {
                **item,
                **persisted,
            }
        )
    return {
        "standardized_items": updated_items,
        "stix_bundle_refs": bundle_refs,
    }


def build_stix_subgraph():
    graph = StateGraph(StixSubgraphState)
    graph.add_node("extract_graphs", _extract_graphs)
    graph.add_node("persist_graphs", _persist_graphs)
    graph.set_entry_point("extract_graphs")
    graph.add_edge("extract_graphs", "persist_graphs")
    graph.add_edge("persist_graphs", END)
    return graph.compile()


_GRAPH = build_stix_subgraph()


def run_stix_subgraph(state: dict[str, Any]) -> dict[str, Any]:
    result = _GRAPH.invoke(
        {
            "standardized_items": state.get("standardized_items", []),
            "runtime_context": state.get("runtime_context", {}),
            "trace_id": state.get("trace_id"),
            "stix_bundle_refs": state.get("stix_bundle_refs", []),
        }
    )
    return {
        "standardized_items": result.get("standardized_items", []),
        "stix_bundle_refs": result.get("stix_bundle_refs", []),
    }
