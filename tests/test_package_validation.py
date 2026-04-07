from __future__ import annotations

import unittest

from saads_wp12.engines.test_package_generation import RuleBasedTestPackageGenerationEngine
from saads_wp12.nodes.validation import validate_test_package
from tests.test_test_package_generation import _base_state


class PackageValidationTest(unittest.TestCase):
    def test_triage_package_requires_triage_execution_shape(self) -> None:
        state = {
            "test_package": {
                "package_id": "pkg-1",
                "package_kind": "triage",
                "attack_family": "unsupported",
                "target_surface": "unsupported_target",
                "objective": "triage only",
                "attack_hypothesis": "out of scope",
                "payload_plan": [
                    {
                        "payload_id": "payload-triage-1",
                        "payload_type": "triage_probe",
                        "payload_source": "analysis://threat_understanding",
                        "payload_template": "triage_summary",
                        "payload_variables": [],
                        "delivery_channel": "analysis",
                        "risk_level": "none",
                        "use_mode": "analysis_only",
                        "expected_effect": "triage summary",
                    }
                ],
                "execution_plan": {
                    "entry_strategy": "do_not_execute",
                    "runner_type": "analysis_only",
                    "runner_command_template": "python -m saads_wp12.debug.inspect_test_package atk-001",
                    "input_contract": ["threat_understanding_contract"],
                    "expected_outputs": ["triage_decision"],
                    "timeout_seconds": 0,
                    "retry_budget": 0,
                    "parameterization": {},
                    "execution_steps": [{"step_id": "s1", "action": "summarize"}],
                    "cleanup_steps": [],
                    "execution_eligibility": "blocked_out_of_scope",
                },
                "success_criteria": [{"criterion_id": "c1", "signal_type": "triage_summary"}],
                "failure_signals": [{"signal_id": "f1", "signal_type": "contract_violation"}],
                "evidence_hooks": ["triage_notes"],
                "assumptions": ["analysis only"],
                "environment_assumptions": ["no runtime required"],
                "known_gaps": ["missing aibom"],
                "recommended_follow_up": ["wait for enrichment"],
                "evidence_collection_plan": {
                    "collection_mode": "analysis_only",
                    "required_hooks": ["triage_notes"],
                    "artifact_targets": ["triage_summary.json"],
                    "capture_strategy": "record_only_contract_outputs",
                },
                "script_blueprint": {
                    "blueprint_kind": "analysis_only",
                    "file_plan": [{"path": "reports/triage_summary.json"}],
                },
                "target_artifacts": [{"path": "reports/triage_summary.json", "required": True}],
                "family_specific_strategy": {"family": "unsupported"},
                "metadata": {"package_kind": "triage"},
                "generation_mode": "triage",
            }
        }

        result = validate_test_package(state)

        self.assertTrue(result["package_validation"]["valid"])
        self.assertEqual(result["package_validation"]["validation_errors"], [])

    def test_triage_package_fails_when_generation_mode_is_not_triage(self) -> None:
        state = {
            "test_package": {
                "package_id": "pkg-2",
                "package_kind": "triage",
                "attack_family": "unsupported",
                "target_surface": "unsupported_target",
                "objective": "triage only",
                "attack_hypothesis": "out of scope",
                "payload_plan": [
                    {
                        "payload_id": "payload-triage-1",
                        "payload_type": "triage_probe",
                        "payload_source": "analysis://threat_understanding",
                        "payload_template": "triage_summary",
                        "payload_variables": [],
                        "delivery_channel": "analysis",
                        "risk_level": "none",
                        "use_mode": "analysis_only",
                        "expected_effect": "triage summary",
                    }
                ],
                "execution_plan": {
                    "entry_strategy": "do_not_execute",
                    "runner_type": "analysis_only",
                    "runner_command_template": "python -m saads_wp12.debug.inspect_test_package atk-001",
                    "input_contract": ["threat_understanding_contract"],
                    "expected_outputs": ["triage_decision"],
                    "timeout_seconds": 0,
                    "retry_budget": 0,
                    "parameterization": {},
                    "execution_steps": [{"step_id": "s1", "action": "summarize"}],
                    "cleanup_steps": [],
                    "execution_eligibility": "blocked_out_of_scope",
                },
                "success_criteria": [{"criterion_id": "c1", "signal_type": "triage_summary"}],
                "failure_signals": [{"signal_id": "f1", "signal_type": "contract_violation"}],
                "evidence_hooks": ["triage_notes"],
                "assumptions": ["analysis only"],
                "environment_assumptions": ["no runtime required"],
                "known_gaps": ["missing aibom"],
                "recommended_follow_up": ["wait for enrichment"],
                "evidence_collection_plan": {
                    "collection_mode": "analysis_only",
                    "required_hooks": ["triage_notes"],
                    "artifact_targets": ["triage_summary.json"],
                    "capture_strategy": "record_only_contract_outputs",
                },
                "script_blueprint": {
                    "blueprint_kind": "analysis_only",
                    "file_plan": [{"path": "reports/triage_summary.json"}],
                },
                "target_artifacts": [{"path": "reports/triage_summary.json", "required": True}],
                "family_specific_strategy": {"family": "unsupported"},
                "metadata": {"package_kind": "triage"},
                "generation_mode": "conservative",
            }
        }

        result = validate_test_package(state)

        self.assertFalse(result["package_validation"]["valid"])
        self.assertIn(
            "triage package must use generation_mode='triage'.",
            result["package_validation"]["validation_errors"],
        )

    def test_standard_package_requires_full_runtime_profile(self) -> None:
        package = RuleBasedTestPackageGenerationEngine().run(_base_state())["test_package"]
        package["execution_plan"]["parameterization"]["execution_profile"] = "verification_probe"

        result = validate_test_package({"test_package": package})

        self.assertFalse(result["package_validation"]["valid"])
        self.assertIn(
            "standard package must use execution_plan.parameterization.execution_profile='full_runtime_execution'.",
            result["package_validation"]["validation_errors"],
        )

    def test_conservative_package_requires_probe_shape(self) -> None:
        state = _base_state()
        state["execution_assessment"]["execution_eligibility"] = "blocked_no_aibom"
        state["execution_assessment"]["execution_blockers"] = ["missing_aibom_context"]
        state["execution_assessment"]["has_aibom_context"] = False
        state["execution_assessment"]["has_component_context"] = False
        state["execution_assessment"]["has_seed_assets"] = False
        state["execution_assessment"]["test_readiness"] = "low"
        package = RuleBasedTestPackageGenerationEngine().run(state)["test_package"]
        package["execution_plan"]["entry_strategy"] = "single_script_iteration"

        result = validate_test_package({"test_package": package})

        self.assertFalse(result["package_validation"]["valid"])
        self.assertIn(
            "conservative package must use execution_plan.entry_strategy='assumption_gated_probe'.",
            result["package_validation"]["validation_errors"],
        )

    def test_dialogue_package_requires_state_tracker_contract(self) -> None:
        state = _base_state(
            attack_id="attack-dialogue-001",
            generation_route="dialogue_generator",
            attack_family="long_horizon_dialogue",
            target_surface="chat_session",
            component_name="chat-agent",
            asset_type="dialogue_corpus",
            artifact_uri="s3://bucket/dialogue.json",
        )
        package = RuleBasedTestPackageGenerationEngine().run(state)["test_package"]
        package["payload_plan"] = [
            payload for payload in package["payload_plan"] if payload.get("payload_type") != "dialogue_state_tracker"
        ]

        result = validate_test_package({"test_package": package})

        self.assertFalse(result["package_validation"]["valid"])
        self.assertIn(
            "long_horizon_dialogue package must include payload_plan entry with payload_type='dialogue_state_tracker'.",
            result["package_validation"]["validation_errors"],
        )

    def test_tool_hijack_package_requires_trace_expectation_contract(self) -> None:
        state = _base_state(
            attack_id="attack-tool-001",
            generation_route="tool_system_generator",
            attack_family="tool_hijack",
            target_surface="tool_runtime",
            component_name="tool-agent",
            asset_type="tool_rule",
            artifact_uri="s3://bucket/tool.json",
        )
        package = RuleBasedTestPackageGenerationEngine().run(state)["test_package"]
        package["script_blueprint"]["file_plan"] = [
            file_plan
            for file_plan in package["script_blueprint"]["file_plan"]
            if file_plan.get("path") != "configs/tool_trace_expectation.json"
        ]

        result = validate_test_package({"test_package": package})

        self.assertFalse(result["package_validation"]["valid"])
        self.assertIn(
            "tool_hijack package must include script_blueprint file 'configs/tool_trace_expectation.json'.",
            result["package_validation"]["validation_errors"],
        )

    def test_prompt_package_requires_context_binding_contract(self) -> None:
        package = RuleBasedTestPackageGenerationEngine().run(_base_state())["test_package"]
        package["success_criteria"] = [
            criterion
            for criterion in package["success_criteria"]
            if criterion.get("criterion_id") != "context-priority-inversion-confirmed"
        ]

        result = validate_test_package({"test_package": package})

        self.assertFalse(result["package_validation"]["valid"])
        self.assertIn(
            "prompt_injection package must include success criterion 'context-priority-inversion-confirmed'.",
            result["package_validation"]["validation_errors"],
        )


if __name__ == "__main__":
    unittest.main()
