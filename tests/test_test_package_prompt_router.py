from __future__ import annotations

import unittest

from saads_wp12.engines.test_package_generation import build_test_package_generation_input
from saads_wp12.llm.test_package_generation_prompts import (
    FAMILY_FEW_SHOT_LABELS,
    PRIMARY_TAXONOMY_FEW_SHOT_LABELS,
    SECONDARY_TAXONOMY_FEW_SHOT_LABELS,
    TAXONOMY_DETAIL_PLAYBOOKS,
)
from saads_wp12.llm.test_package_prompt_router import (
    build_prompt_route_decision,
    extract_taxonomy_context,
    extract_route_signal_snapshot,
    infer_prompt_mode,
    select_secondary_taxonomy_codes,
)
from tests.test_test_package_generation import _base_state


class TestPackagePromptRouter(unittest.TestCase):
    def test_extract_taxonomy_context_returns_primary_and_all_codes(self) -> None:
        state = _base_state()
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {"code": "OWASP-LLM-02", "name": "Insecure Output Handling"},
            "all_taxonomy_codes": ["OWASP-LLM-02", "OWASP-LLM-05"],
        }
        contract = build_test_package_generation_input(state)

        primary_code, all_codes = extract_taxonomy_context(contract)

        self.assertEqual(primary_code, "OWASP-LLM-02")
        self.assertEqual(all_codes, ["OWASP-LLM-02", "OWASP-LLM-05"])

    def test_extract_taxonomy_context_supports_selected_taxonomy_code_shape(self) -> None:
        state = _base_state()
        state["evidence_and_context"]["taxonomy_context"] = {
            "selected_taxonomy_code": "OWASP-LLM-01",
            "selected_taxonomy_name": "Prompt Injection",
            "all_taxonomy_codes": ["OWASP-LLM-01", "OWASP-LLM-02"],
        }
        contract = build_test_package_generation_input(state)

        primary_code, all_codes = extract_taxonomy_context(contract)

        self.assertEqual(primary_code, "OWASP-LLM-01")
        self.assertEqual(all_codes, ["OWASP-LLM-01", "OWASP-LLM-02"])

    def test_extract_taxonomy_context_prefers_ranked_classification_signals(self) -> None:
        state = _base_state()
        state["evidence_and_context"]["taxonomy_context"] = {
            "selected_taxonomy_code": "OWASP-LLM-01",
            "all_taxonomy_codes": ["OWASP-LLM-01", "OWASP-LLM-02", "OWASP-LLM-05"],
        }
        state["evidence_and_context"]["classification_rationale"] = {
            "taxonomy_signal": "OWASP-LLM-01",
            "all_taxonomy_signals": [
                {
                    "taxonomy_code": "OWASP-LLM-01",
                    "is_primary": True,
                    "confidence_score": 0.95,
                },
                {
                    "taxonomy_code": "OWASP-LLM-05",
                    "is_primary": False,
                    "confidence_score": 0.8,
                },
                {
                    "taxonomy_code": "OWASP-LLM-02",
                    "is_primary": False,
                    "confidence_score": 0.6,
                },
            ],
        }
        contract = build_test_package_generation_input(state)

        primary_code, all_codes = extract_taxonomy_context(contract)

        self.assertEqual(primary_code, "OWASP-LLM-01")
        self.assertEqual(all_codes, ["OWASP-LLM-01", "OWASP-LLM-05", "OWASP-LLM-02"])

    def test_select_secondary_taxonomy_codes_limits_to_two_available_codes(self) -> None:
        snapshot = extract_route_signal_snapshot(
            build_test_package_generation_input(_base_state())
        )
        selected = select_secondary_taxonomy_codes(
            snapshot,
            ["OWASP-LLM-01", "OWASP-LLM-02", "OWASP-LLM-05", "OWASP-LLM-07"],
            set(TAXONOMY_DETAIL_PLAYBOOKS),
            max_secondary=2,
        )

        self.assertCountEqual(selected, ["OWASP-LLM-02", "OWASP-LLM-05"])
        self.assertNotIn("OWASP-LLM-07", selected)

    def test_select_secondary_taxonomy_codes_prefers_test_value_for_agent_case(self) -> None:
        state = _base_state(target_surface="n8n-claw AI Agent")
        state["threat_understanding"]["threat_summary"] = (
            "Prompt injection through Telegram and webhooks can drive HTTP tool access "
            "to internal services and workflow builder changes."
        )
        state["threat_understanding"]["attack_mechanism"] = (
            "The HTTP tool can scan metadata API and Docker services while workflow "
            "builder self-modification may persist unsafe behavior."
        )
        state["evidence_and_context"]["classification_rationale"] = {
            "taxonomy_signal": "OWASP-LLM-01",
            "all_taxonomy_signals": [
                {
                    "taxonomy_code": "OWASP-LLM-01",
                    "is_primary": True,
                    "confidence_score": 0.95,
                },
                {
                    "taxonomy_code": "OWASP-LLM-02",
                    "is_primary": False,
                    "confidence_score": 0.7,
                },
                {
                    "taxonomy_code": "OWASP-LLM-07",
                    "is_primary": False,
                    "confidence_score": 0.6,
                },
                {
                    "taxonomy_code": "OWASP-LLM-05",
                    "is_primary": False,
                    "confidence_score": 0.5,
                },
            ],
        }
        contract = build_test_package_generation_input(state)
        snapshot = extract_route_signal_snapshot(contract)

        selected = select_secondary_taxonomy_codes(
            snapshot,
            list(snapshot.ranked_taxonomy_codes),
            set(TAXONOMY_DETAIL_PLAYBOOKS),
            family_few_shot_labels=FAMILY_FEW_SHOT_LABELS,
            primary_taxonomy_few_shot_labels=PRIMARY_TAXONOMY_FEW_SHOT_LABELS,
            secondary_taxonomy_few_shot_labels=SECONDARY_TAXONOMY_FEW_SHOT_LABELS,
            max_secondary=2,
        )

        self.assertCountEqual(selected, ["OWASP-LLM-02", "OWASP-LLM-05"])
        self.assertNotIn("OWASP-LLM-07", selected)

    def test_infer_prompt_mode_returns_composite_for_multi_taxonomy_case(self) -> None:
        snapshot = extract_route_signal_snapshot(
            build_test_package_generation_input(_base_state())
        )

        mode = infer_prompt_mode(
            snapshot,
            secondary_taxonomy_codes=["OWASP-LLM-02", "OWASP-LLM-05"],
        )

        self.assertEqual(mode, "multi_taxonomy_composite")

    def test_extract_route_signal_snapshot_uses_fallback_sources(self) -> None:
        state = _base_state(attack_family="", generation_route="")
        state["threat_profile"] = {"attack_family": "tool_hijack"}
        state["classification_rationale"] = {
            "top_candidate": "tool_hijack",
            "taxonomy_signal": "OWASP-LLM-03",
        }
        state["evidence_and_context"]["taxonomy_context"] = {
            "selected_taxonomy_code": "OWASP-LLM-03",
            "all_taxonomy_codes": ["OWASP-LLM-03"],
        }
        contract = build_test_package_generation_input(state)

        snapshot = extract_route_signal_snapshot(contract)

        self.assertEqual(snapshot.attack_family, "tool_hijack")
        self.assertEqual(snapshot.generation_route, "tool_hijack")
        self.assertEqual(snapshot.primary_taxonomy_code, "OWASP-LLM-03")
        self.assertEqual(list(snapshot.ranked_taxonomy_codes), ["OWASP-LLM-03"])

    def test_extract_route_signal_snapshot_prefers_classification_rationale_ranking(self) -> None:
        state = _base_state()
        state["evidence_and_context"]["taxonomy_context"] = {
            "selected_taxonomy_code": "OWASP-LLM-01",
            "all_taxonomy_codes": ["OWASP-LLM-01", "OWASP-LLM-02", "OWASP-LLM-05"],
        }
        state["evidence_and_context"]["classification_rationale"] = {
            "taxonomy_signal": "OWASP-LLM-01",
            "all_taxonomy_signals": [
                {
                    "taxonomy_code": "OWASP-LLM-01",
                    "is_primary": True,
                    "confidence_score": 0.95,
                },
                {
                    "taxonomy_code": "OWASP-LLM-07",
                    "is_primary": False,
                    "confidence_score": 0.7,
                },
                {
                    "taxonomy_code": "OWASP-LLM-02",
                    "is_primary": False,
                    "confidence_score": 0.6,
                },
            ],
        }
        contract = build_test_package_generation_input(state)

        snapshot = extract_route_signal_snapshot(contract)

        self.assertEqual(snapshot.classification_basis, "classification_rationale")
        self.assertEqual(
            list(snapshot.ranked_taxonomy_codes),
            ["OWASP-LLM-01", "OWASP-LLM-07", "OWASP-LLM-02"],
        )

    def test_build_prompt_route_decision_returns_analysis_only_for_unsupported(self) -> None:
        state = _base_state(attack_family="unsupported", generation_route="unsupported")
        contract = build_test_package_generation_input(state)

        decision = build_prompt_route_decision(
            contract,
            available_taxonomy_codes=set(TAXONOMY_DETAIL_PLAYBOOKS),
            family_few_shot_labels=FAMILY_FEW_SHOT_LABELS,
            primary_taxonomy_few_shot_labels=PRIMARY_TAXONOMY_FEW_SHOT_LABELS,
            secondary_taxonomy_few_shot_labels=SECONDARY_TAXONOMY_FEW_SHOT_LABELS,
        )

        self.assertEqual(decision.prompt_mode, "analysis_only")
        self.assertEqual(list(decision.selected_few_shot_labels), ["unsupported_triage"])

    def test_build_prompt_route_decision_returns_composite_route_with_rationale(self) -> None:
        state = _base_state(target_surface="agent_workflow")
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {"code": "OWASP-LLM-01", "name": "Prompt Injection"},
            "all_taxonomy_codes": ["OWASP-LLM-01", "OWASP-LLM-02", "OWASP-LLM-05"],
        }
        contract = build_test_package_generation_input(state)

        decision = build_prompt_route_decision(
            contract,
            available_taxonomy_codes=set(TAXONOMY_DETAIL_PLAYBOOKS),
            family_few_shot_labels=FAMILY_FEW_SHOT_LABELS,
            primary_taxonomy_few_shot_labels=PRIMARY_TAXONOMY_FEW_SHOT_LABELS,
            secondary_taxonomy_few_shot_labels=SECONDARY_TAXONOMY_FEW_SHOT_LABELS,
        )

        self.assertEqual(decision.prompt_mode, "multi_taxonomy_composite")
        self.assertEqual(decision.selected_primary_taxonomy, "OWASP-LLM-01")
        self.assertEqual(
            list(decision.selected_secondary_taxonomies),
            ["OWASP-LLM-02", "OWASP-LLM-05"],
        )
        self.assertIn(
            "Composite route selected because the sample carries multiple meaningful taxonomy risk themes.",
            decision.routing_rationale,
        )
        self.assertLessEqual(len(decision.selected_few_shot_labels), 4)


if __name__ == "__main__":
    unittest.main()
