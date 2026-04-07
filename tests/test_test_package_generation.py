from __future__ import annotations

import unittest

from saads_wp12.engines.test_package_generation import (
    TEST_PACKAGE_INPUT_CONTRACT_VERSION,
    RuleBasedTestPackageGenerationEngine,
    build_test_package_generation_input,
)


def _base_state(
    *,
    attack_id: str = "attack-001",
    generation_route: str = "prompt_injection",
    attack_family: str = "prompt_injection",
    target_surface: str = "retrieval_context",
    component_name: str = "rag-service",
    asset_type: str = "prompt_corpus",
    artifact_uri: str = "s3://bucket/payload.txt",
) -> dict:
    return {
        "attack_id": attack_id,
        "generation_route": generation_route,
        "attack_family": attack_family,
        "target_surface": target_surface,
        "confidence": 0.9,
        "candidate_families": [{"family": attack_family, "confidence": 0.9}],
        "threat_understanding": {
            "threat_summary": f"{attack_family} case",
            "attack_mechanism": f"{attack_family} mechanism",
            "exploit_preconditions": [f"{target_surface} is available"],
            "test_focus": [f"{attack_family} behavior observed"],
            "expected_failure_modes": [f"{attack_family} did not trigger"],
            "recommended_test_strategy": f"Validate {attack_family} on {target_surface}.",
        },
        "threat_profile": {
            "attack_family": attack_family,
            "candidate_families": [{"family": attack_family, "confidence": 0.9}],
            "confidence": 0.9,
            "target_surface": target_surface,
            "attack_mechanism": f"{attack_family} mechanism",
        },
        "scope_assessment": {
            "in_scope": True,
            "supported_family": attack_family,
            "scope_reason": "Supported family.",
        },
        "execution_assessment": {
            "has_aibom_context": True,
            "has_component_context": True,
            "has_seed_assets": True,
            "execution_eligibility": "ready",
            "execution_blockers": [],
            "test_readiness": "high",
        },
        "evidence_and_context": {
            "classification_rationale": {"top_candidate": attack_family},
            "component_context_summary": {"component_name": component_name},
            "seed_asset_summary": {"seed_asset_count": 1, "published_seed_asset_count": 1, "available_asset_types": [asset_type]},
            "stix_summary": {"stix_type": "", "has_stix_payload": False},
        },
        "uncertainty_report": {
            "missing_knowledge": [],
            "risk_flags": [],
            "known_gaps": [],
        },
        "intel_normalized": {
            "seed_asset": {
                "artifact_uri": artifact_uri,
                "asset_name": "payload.txt",
                "asset_type": asset_type,
            }
        },
    }


class TestPackageGenerationContractTest(unittest.TestCase):
    def test_builds_stable_input_contract_from_orchestration_state(self) -> None:
        state = _base_state()
        contract = build_test_package_generation_input(state)

        self.assertEqual(contract.attack_id, "attack-001")
        self.assertEqual(contract.attack_family, "prompt_injection")
        self.assertEqual(contract.component_context_summary["component_name"], "rag-service")
        self.assertEqual(contract.seed_asset_summary["available_asset_types"], ["prompt_corpus"])
        self.assertEqual(contract.stix_summary["has_stix_payload"], False)
        self.assertEqual(contract.to_state()["known_gaps"], [])

    def test_generates_standard_package_when_ready(self) -> None:
        result = RuleBasedTestPackageGenerationEngine().run(_base_state())
        package = result["test_package"]

        self.assertEqual(package["package_kind"], "standard")
        self.assertEqual(package["generation_mode"], "standard")
        self.assertEqual(package["execution_plan"]["execution_eligibility"], "ready")
        self.assertEqual(result["package_version"], 2)
        self.assertTrue(package["script_blueprint"]["file_plan"])
        self.assertTrue(package["execution_plan"]["execution_steps"])
        self.assertEqual(package["script_blueprint"]["blueprint_kind"], "runtime_execution")
        self.assertEqual(package["payload_plan"][0]["payload_type"], "context_override")
        self.assertEqual(package["payload_plan"][1]["payload_type"], "context_binding_plan")
        self.assertEqual(package["payload_plan"][1]["payload_template"], "retrieval_slot_binding_map")
        self.assertIn("retrieval_trace.json", str(package["script_blueprint"]["file_plan"]))
        self.assertIn("context_binding.json", str(package["script_blueprint"]["file_plan"]))
        self.assertIn("context_snapshot", package["evidence_collection_plan"]["required_hooks"])
        self.assertEqual(package["execution_plan"]["entry_strategy"], "single_script_iteration")
        self.assertEqual(package["execution_plan"]["parameterization"]["execution_profile"], "full_runtime_execution")
        self.assertEqual(package["payload_plan"][0]["risk_level"], "high")
        self.assertEqual(package["payload_plan"][1]["risk_level"], "medium")
        self.assertIn(
            "score_family_outcome_against_success_criteria",
            [step["action"] for step in package["execution_plan"]["execution_steps"]],
        )
        self.assertIn(
            "assemble_retrieval_context_with_hostile_overlay",
            [step["action"] for step in package["execution_plan"]["execution_steps"]],
        )
        self.assertIn(
            "compare_safe_and_injected_outputs",
            [step["action"] for step in package["execution_plan"]["execution_steps"]],
        )
        self.assertGreaterEqual(len(package["success_criteria"]), 6)
        self.assertIn(
            "context-binding-missing",
            [signal["signal_id"] for signal in package["failure_signals"]],
        )
        self.assertEqual(
            package["execution_plan"]["parameterization"]["component_focus"],
            "rag-service",
        )
        self.assertEqual(
            package["metadata"]["context_design_basis"]["component_focus"],
            "rag-service",
        )
        self.assertEqual(package["metadata"]["input_contract"]["version"], TEST_PACKAGE_INPUT_CONTRACT_VERSION)
        self.assertIn("execution_assessment", package["metadata"]["input_contract"]["fields"])
        self.assertIn("rag-service", package["objective"])

    def test_generates_conservative_package_when_execution_is_blocked(self) -> None:
        state = _base_state()
        state["execution_assessment"]["execution_eligibility"] = "blocked_no_aibom"
        state["execution_assessment"]["execution_blockers"] = ["missing_aibom_context"]
        state["execution_assessment"]["has_aibom_context"] = False
        state["execution_assessment"]["has_component_context"] = False
        state["execution_assessment"]["has_seed_assets"] = False
        state["execution_assessment"]["test_readiness"] = "low"
        state["uncertainty_report"]["known_gaps"] = ["AI BOM context is missing."]

        result = RuleBasedTestPackageGenerationEngine().run(state)
        package = result["test_package"]

        self.assertEqual(package["package_kind"], "conservative")
        self.assertEqual(package["generation_mode"], "conservative")
        self.assertEqual(package["execution_plan"]["execution_eligibility"], "blocked_no_aibom")
        self.assertIn("AI BOM context is missing.", package["known_gaps"])
        self.assertEqual(package["payload_plan"][0]["use_mode"], "dry_run_reference")
        self.assertEqual(package["payload_plan"][0]["risk_level"], "low")
        self.assertEqual(package["payload_plan"][1]["risk_level"], "none")
        self.assertEqual(package["execution_plan"]["retry_budget"], 1)
        self.assertGreaterEqual(len(package["execution_plan"]["execution_steps"]), 4)
        self.assertEqual(package["execution_plan"]["entry_strategy"], "assumption_gated_probe")
        self.assertEqual(package["execution_plan"]["parameterization"]["execution_profile"], "verification_probe")
        self.assertEqual(package["execution_plan"]["parameterization"]["prompt_variant"], "override_then_probe")
        self.assertIn(
            "verify_target_and_asset_readiness",
            [step["action"] for step in package["execution_plan"]["execution_steps"]],
        )
        self.assertIn(
            "decide_whether_to_escalate",
            [step["action"] for step in package["execution_plan"]["execution_steps"]],
        )
        self.assertIn(
            "assemble_retrieval_context_with_hostile_overlay",
            [step["action"] for step in package["execution_plan"]["execution_steps"]],
        )
        self.assertIn("AI BOM context is missing.", package["payload_plan"][0]["notes"])
        self.assertIn(
            "verification-first runtime",
            " ".join(package["script_blueprint"]["rendering_notes"]),
        )

    def test_generates_triage_package_when_out_of_scope(self) -> None:
        state = _base_state()
        state["attack_family"] = "unsupported"
        state["target_surface"] = "unsupported_target"
        state["scope_assessment"] = {
            "in_scope": False,
            "supported_family": "unsupported",
            "scope_reason": "Out of current scope.",
        }
        state["execution_assessment"] = {
            "has_aibom_context": False,
            "has_component_context": False,
            "has_seed_assets": False,
            "execution_eligibility": "blocked_out_of_scope",
            "execution_blockers": ["out_of_scope"],
            "test_readiness": "low",
        }
        state["uncertainty_report"]["known_gaps"] = ["Out of current WP1-2 scope."]

        result = RuleBasedTestPackageGenerationEngine().run(state)
        package = result["test_package"]

        self.assertEqual(package["package_kind"], "triage")
        self.assertEqual(package["generation_mode"], "triage")
        self.assertEqual(package["execution_plan"]["runner_type"], "analysis_only")
        self.assertIn("must not be treated as an executable attack script", " ".join(package["assumptions"]))
        self.assertEqual(package["script_blueprint"]["blueprint_kind"], "analysis_only")
        self.assertEqual(package["payload_plan"][0]["use_mode"], "analysis_only")
        self.assertEqual(package["execution_plan"]["retry_budget"], 0)

    def test_long_horizon_dialogue_package_uses_multi_turn_blueprint(self) -> None:
        state = _base_state(
            attack_id="attack-dialogue-001",
            generation_route="dialogue_generator",
            attack_family="long_horizon_dialogue",
            target_surface="chat_session",
            component_name="chat-agent",
            asset_type="dialogue_corpus",
            artifact_uri="s3://bucket/dialogue.json",
        )

        result = RuleBasedTestPackageGenerationEngine().run(state)
        package = result["test_package"]

        self.assertEqual(package["family_specific_strategy"]["runner_hint"], "dialogue_runner")
        self.assertEqual(package["payload_plan"][0]["payload_template"], "multi_turn_dialogue_plan")
        self.assertEqual(package["payload_plan"][1]["payload_type"], "dialogue_turn_schedule")
        self.assertEqual(package["payload_plan"][2]["payload_type"], "dialogue_state_tracker")
        self.assertEqual(package["execution_plan"]["parameterization"]["dialogue_shape"], "progressive_escalation")
        self.assertEqual(package["execution_plan"]["parameterization"]["turn_budget"], 6)
        self.assertIn(
            "bind_dialogue_state_checkpoints",
            str(package["execution_plan"]["execution_steps"]),
        )
        self.assertIn(
            "compare_turn_by_turn_safety_delta",
            str(package["execution_plan"]["execution_steps"]),
        )
        self.assertIn("dialogue_plan.json", str(package["script_blueprint"]["file_plan"]))
        self.assertIn("dialogue_state_tracker.json", str(package["script_blueprint"]["file_plan"]))
        self.assertIn("dialogue_transcript", package["evidence_collection_plan"]["required_hooks"])
        self.assertIn("dialogue-checkpoints-covered", str(package["success_criteria"]))
        self.assertIn("dialogue-output-static", str(package["failure_signals"]))
        self.assertEqual(
            package["execution_plan"]["parameterization"]["component_focus"],
            "chat-agent",
        )
        self.assertIn("chat-agent", package["objective"])

    def test_tool_hijack_package_uses_tool_specific_blueprint(self) -> None:
        state = _base_state(
            attack_id="attack-tool-001",
            generation_route="tool_system_generator",
            attack_family="tool_hijack",
            target_surface="tool_runtime",
            component_name="tool-agent",
            asset_type="tool_rule",
            artifact_uri="s3://bucket/tool.json",
        )

        result = RuleBasedTestPackageGenerationEngine().run(state)
        package = result["test_package"]

        self.assertEqual(package["family_specific_strategy"]["runner_hint"], "tool_hijack_runner")
        self.assertEqual(package["payload_plan"][0]["payload_template"], "tool_argument_hijack_component_bound")
        self.assertEqual(package["payload_plan"][1]["payload_type"], "tool_argument_map")
        self.assertEqual(package["payload_plan"][2]["payload_type"], "tool_trace_expectation")
        self.assertEqual(package["execution_plan"]["parameterization"]["target_tool_name"], "web_search")
        self.assertIn(
            "bind_expected_tool_trace_markers",
            str(package["execution_plan"]["execution_steps"]),
        )
        self.assertIn(
            "compare_planned_and_observed_tool_usage",
            str(package["execution_plan"]["execution_steps"]),
        )
        self.assertIn("configs/tool_plan.json", str(package["script_blueprint"]["file_plan"]))
        self.assertIn("tool_trace_expectation.json", str(package["script_blueprint"]["file_plan"]))
        self.assertIn("tool_call_trace", package["evidence_collection_plan"]["required_hooks"])
        self.assertIn("planned-tool-path-matched", str(package["success_criteria"]))
        self.assertIn("tool-usage-static", str(package["failure_signals"]))
        self.assertIn("tool-agent", package["script_blueprint"]["rendering_notes"][2])


if __name__ == "__main__":
    unittest.main()
