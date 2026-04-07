from __future__ import annotations

import unittest
from unittest.mock import patch

from saads_wp12.engines.test_package_generation import (
    LlmNotConfiguredError,
    LlmTestPackageGenerationEngine,
)
from tests.test_test_package_generation import _base_state


class LlmTestPackageGenerationEngineTest(unittest.TestCase):
    @patch("saads_wp12.engines.test_package_generation.generate_json_response")
    def test_llm_engine_merges_valid_overrides(self, mock_generate) -> None:
        mock_generate.return_value = {
            "package_kind": "standard",
            "generation_mode": "standard",
            "objective": "LLM-generated prompt injection runtime package.",
            "attack_hypothesis": "Hostile retrieval content overrides intended behavior.",
            "payload_plan": [
                {
                    "payload_id": "payload-attack-001-1",
                    "payload_type": "context_override",
                    "payload_source": "seed://prompt_corpus",
                    "payload_template": "retrieval_context_override_seeded",
                    "payload_variables": [],
                    "delivery_channel": "retrieval_context",
                    "risk_level": "high",
                    "use_mode": "primary_execution_payload",
                    "expected_effect": "Attempt hostile context override.",
                },
                {
                    "payload_id": "payload-attack-001-2",
                    "payload_type": "context_binding_plan",
                    "payload_source": "derived://context_binding_plan",
                    "payload_template": "retrieval_slot_binding_map",
                    "payload_variables": [],
                    "delivery_channel": "retrieval_context",
                    "risk_level": "medium",
                    "use_mode": "supporting_execution_plan",
                    "expected_effect": "Bind hostile payload into context.",
                },
            ],
            "execution_plan": {
                "entry_strategy": "single_script_iteration",
                "runner_type": "prompt_injection_runner",
                "runner_command_template": "python {workspace}/scripts/run_attack.py --payload {workspace}/assets/payloads.json --mode prompt",
                "input_contract": [
                    "payload_plan",
                    "script_blueprint",
                    "success_criteria",
                    "failure_signals",
                    "evidence_collection_plan",
                ],
                "expected_outputs": ["attempt_result", "evidence_bundle", "retrieval_trace", "runtime_trace"],
                "timeout_seconds": 180,
                "retry_budget": 3,
                "parameterization": {
                    "attack_id": "attack-001",
                    "target_surface": "retrieval_context",
                    "component_focus": "rag-service",
                    "execution_profile": "full_runtime_execution",
                },
                "execution_steps": [
                    {"step_id": "s1", "action": "render_payload_inputs"},
                    {"step_id": "s2", "action": "bind_retrieved_context_slot"},
                    {"step_id": "s3", "action": "assemble_retrieval_context_with_hostile_overlay"},
                    {"step_id": "s4", "action": "prompt_injection_runner"},
                    {"step_id": "s5", "action": "evaluate_instruction_priority_inversion"},
                    {"step_id": "s6", "action": "compare_safe_and_injected_outputs"},
                    {"step_id": "s7", "action": "capture_evidence_hooks"},
                    {"step_id": "s8", "action": "score_family_outcome_against_success_criteria"},
                ],
                "cleanup_steps": [],
                "execution_eligibility": "ready",
            },
            "success_criteria": [
                {
                    "criterion_id": "injected-output-differs-from-safe-baseline",
                    "signal_type": "runtime_trace",
                    "match_mode": "contains",
                    "expected_value": "baseline_and_injected_output_diverged",
                },
                {
                    "criterion_id": "context-priority-inversion-confirmed",
                    "signal_type": "context_snapshot",
                    "match_mode": "contains",
                    "expected_value": "hostile overlay ranked above baseline guidance",
                }
            ],
            "failure_signals": [
                {
                    "signal_id": "context-binding-missing",
                    "signal_type": "context_binding_gap",
                    "description": "missing binding plan",
                },
                {
                    "signal_id": "baseline-output-unchanged",
                    "signal_type": "no_behavioral_delta",
                    "description": "no delta",
                },
            ],
            "evidence_collection_plan": {
                "collection_mode": "runtime_execution",
                "required_hooks": ["stdout", "artifact_capture", "retrieval_trace", "context_snapshot"],
                "artifact_targets": ["payloads.json", "context_binding.json", "run_attack.py", "retrieval_trace.json", "execution_trace.json"],
                "capture_strategy": "capture_retrieval_context_before_and_after_payload_injection",
            },
            "script_blueprint": {
                "blueprint_kind": "runtime_execution",
                "workspace_layout": ["assets/", "scripts/", "reports/", "configs/"],
                "file_plan": [
                    {"path": "assets/payloads.json"},
                    {"path": "assets/context_binding.json"},
                    {"path": "scripts/run_attack.py"},
                    {"path": "reports/retrieval_trace.json"},
                ],
            },
            "target_artifacts": [
                {"path": "assets/payloads.json", "required": True},
                {"path": "scripts/run_attack.py", "required": True},
            ],
            "family_specific_strategy": {
                "family": "prompt_injection",
                "generation_route": "prompt_injection",
                "target_surface": "retrieval_context",
                "package_kind": "standard",
                "attack_style": "context_override",
                "primary_goal": "Inject hostile instructions.",
                "delivery_channel": "retrieval_context",
                "runner_hint": "prompt_injection_runner",
            },
            "recommended_follow_up": ["Proceed to runtime execution."],
        }

        result = LlmTestPackageGenerationEngine().run(_base_state())

        self.assertEqual(result["test_package"]["metadata"]["generator_name"], "llm_generator")
        self.assertTrue(result["test_package"]["metadata"]["llm_enabled"])
        self.assertEqual(result["test_package"]["objective"], "LLM-generated prompt injection runtime package.")

    @patch("saads_wp12.engines.test_package_generation.generate_json_response")
    def test_llm_engine_falls_back_when_llm_is_unavailable(self, mock_generate) -> None:
        mock_generate.side_effect = LlmNotConfiguredError("missing key")

        result = LlmTestPackageGenerationEngine().run(_base_state())

        self.assertEqual(result["test_package"]["metadata"]["generator_name"], "prompt_generator")
        self.assertEqual(result["test_package"]["package_kind"], "standard")
        self.assertEqual(result["test_package"]["metadata"]["llm_fallback_reason"], "llm_exception")

    @patch("saads_wp12.nodes.validation.validate_test_package")
    @patch("saads_wp12.engines.test_package_generation.generate_json_response")
    def test_llm_engine_records_validation_failure_reason(self, mock_generate, mock_validate) -> None:
        mock_generate.return_value = {
            "package_kind": "standard",
            "generation_mode": "standard",
            "objective": "Broken package",
            "attack_hypothesis": "Broken hypothesis",
            "payload_plan": [
                {
                    "payload_id": "payload-attack-001-1",
                    "payload_type": "context_override",
                    "payload_source": "seed://prompt_corpus",
                    "payload_template": "retrieval_context_override_seeded",
                    "payload_variables": [],
                    "delivery_channel": "retrieval_context",
                    "risk_level": "high",
                    "use_mode": "primary_execution_payload",
                    "expected_effect": "Attempt hostile context override.",
                }
            ],
        }
        mock_validate.return_value = {
            "package_validation": {
                "valid": False,
                "missing_fields": [],
                "validation_errors": ["forced validation failure"],
            }
        }

        result = LlmTestPackageGenerationEngine().run(_base_state())

        self.assertEqual(result["test_package"]["metadata"]["generator_name"], "prompt_generator")
        self.assertEqual(result["test_package"]["metadata"]["llm_fallback_reason"], "llm_validation_failed")
        self.assertTrue(result["test_package"]["metadata"]["llm_validation_errors"])

    @patch("saads_wp12.engines.test_package_generation.generate_json_response")
    def test_llm_engine_does_not_downgrade_in_scope_package_to_triage(self, mock_generate) -> None:
        mock_generate.return_value = {
            "package_kind": "triage",
            "generation_mode": "triage",
            "objective": "Analysis-only package",
            "attack_hypothesis": "Broken hypothesis",
            "payload_plan": [
                {
                    "payload_id": "payload-attack-001-1",
                    "payload_type": "context_override",
                    "payload_source": "seed://prompt_corpus",
                    "payload_template": "retrieval_context_override_seeded",
                    "payload_variables": [],
                    "delivery_channel": "retrieval_context",
                    "risk_level": "low",
                    "use_mode": "dry_run_reference",
                    "expected_effect": "Attempt hostile context override.",
                }
            ],
        }

        result = LlmTestPackageGenerationEngine().run(_base_state())

        self.assertEqual(result["test_package"]["metadata"]["generator_name"], "llm_generator")
        self.assertNotEqual(result["test_package"]["package_kind"], "triage")
        self.assertNotEqual(result["test_package"]["generation_mode"], "triage")

    @patch("saads_wp12.engines.test_package_generation.generate_json_response")
    def test_llm_engine_merges_partial_execution_plan_with_fallback_shell(self, mock_generate) -> None:
        mock_generate.return_value = {
            "package_kind": "standard",
            "generation_mode": "standard",
            "objective": "Plan-first package",
            "attack_hypothesis": "Hostile retrieval content overrides intended behavior.",
            "payload_plan": [
                {
                    "payload_id": "payload-attack-001-1",
                    "payload_type": "context_override",
                    "payload_source": "seed://prompt_corpus",
                    "payload_template": "retrieval_context_override_seeded",
                    "payload_variables": [],
                    "delivery_channel": "retrieval_context",
                    "risk_level": "high",
                    "use_mode": "primary_execution_payload",
                    "expected_effect": "Attempt hostile context override.",
                },
                {
                    "payload_id": "payload-attack-001-2",
                    "payload_type": "context_binding_plan",
                    "payload_source": "derived://context_binding_plan",
                    "payload_template": "retrieval_slot_binding_map",
                    "payload_variables": [],
                    "delivery_channel": "retrieval_context",
                    "risk_level": "medium",
                    "use_mode": "supporting_execution_plan",
                    "expected_effect": "Bind hostile payload into context.",
                },
            ],
            "execution_plan": {
                "entry_strategy": "single_script_iteration",
                "execution_steps": [
                    {"step_id": "s1", "action": "compare_safe_and_injected_outputs"},
                ],
            },
            "success_criteria": [
                {
                    "criterion_id": "injected-output-differs-from-safe-baseline",
                    "signal_type": "runtime_trace",
                    "match_mode": "contains",
                    "expected_value": "baseline_and_injected_output_diverged",
                },
                {
                    "criterion_id": "context-priority-inversion-confirmed",
                    "signal_type": "context_snapshot",
                    "match_mode": "contains",
                    "expected_value": "hostile overlay ranked above baseline guidance",
                },
            ],
            "failure_signals": [
                {
                    "signal_id": "context-binding-missing",
                    "signal_type": "context_binding_gap",
                    "description": "missing binding plan",
                },
                {
                    "signal_id": "baseline-output-unchanged",
                    "signal_type": "no_behavioral_delta",
                    "description": "no delta",
                },
            ],
            "evidence_collection_plan": {
                "capture_strategy": "plan_first_capture_strategy",
            },
            "script_blueprint": {
                "rendering_notes": ["Prefer test-plan-first output."],
            },
            "target_artifacts": [
                {"path": "assets/payloads.json", "required": True},
                {"path": "scripts/run_attack.py", "required": True},
            ],
            "family_specific_strategy": {
                "family": "prompt_injection",
                "generation_route": "prompt_injection",
                "target_surface": "retrieval_context",
                "package_kind": "standard",
                "attack_style": "context_override",
                "primary_goal": "Inject hostile instructions.",
                "delivery_channel": "retrieval_context",
                "runner_hint": "prompt_injection_runner",
            },
            "recommended_follow_up": ["Proceed to runtime execution."],
        }

        result = LlmTestPackageGenerationEngine().run(_base_state())

        self.assertEqual(result["test_package"]["metadata"]["generator_name"], "llm_generator")
        self.assertEqual(result["test_package"]["execution_plan"]["runner_type"], "prompt_injection_runner")
        self.assertTrue(result["test_package"]["execution_plan"]["runner_command_template"])
        self.assertEqual(
            result["test_package"]["evidence_collection_plan"]["capture_strategy"],
            "plan_first_capture_strategy",
        )
        self.assertTrue(result["test_package"]["script_blueprint"]["file_plan"])

    @patch("saads_wp12.engines.test_package_generation.generate_json_response")
    def test_llm_engine_preserves_non_triage_shell_when_llm_supplies_analysis_only_controls(self, mock_generate) -> None:
        state = _base_state()
        state["execution_assessment"]["execution_eligibility"] = "blocked_no_aibom"
        state["execution_assessment"]["execution_blockers"] = ["missing_aibom_context"]
        state["execution_assessment"]["has_aibom_context"] = False
        state["execution_assessment"]["has_component_context"] = False
        state["execution_assessment"]["has_seed_assets"] = False
        state["execution_assessment"]["test_readiness"] = "medium"

        mock_generate.return_value = {
            "package_kind": "conservative",
            "generation_mode": "conservative",
            "objective": "Plan-first conservative package.",
            "attack_hypothesis": "Hostile retrieval content overrides intended behavior.",
            "execution_plan": {
                "entry_strategy": "do_not_execute",
                "retry_budget": 0,
            },
            "script_blueprint": {
                "blueprint_kind": "analysis_only",
            },
            "payload_plan": [
                {
                    "payload_id": "payload-attack-001-1",
                    "payload_type": "context_override",
                    "payload_source": "seed://prompt_corpus",
                    "payload_template": "retrieval_context_override_seeded",
                    "payload_variables": [],
                    "delivery_channel": "retrieval_context",
                    "risk_level": "low",
                    "use_mode": "dry_run_reference",
                    "expected_effect": "Attempt hostile context override.",
                },
                {
                    "payload_id": "payload-attack-001-2",
                    "payload_type": "context_binding_plan",
                    "payload_source": "derived://context_binding_plan",
                    "payload_template": "retrieval_slot_binding_map",
                    "payload_variables": [],
                    "delivery_channel": "retrieval_context",
                    "risk_level": "none",
                    "use_mode": "supporting_execution_plan",
                    "expected_effect": "Bind hostile payload into context.",
                }
            ],
            "success_criteria": [
                {
                    "criterion_id": "context-priority-inversion-confirmed",
                    "signal_type": "context_snapshot",
                    "match_mode": "contains",
                    "expected_value": "hostile overlay ranked above baseline guidance",
                },
                {
                    "criterion_id": "injected-output-differs-from-safe-baseline",
                    "signal_type": "runtime_trace",
                    "match_mode": "contains",
                    "expected_value": "baseline_and_injected_output_diverged",
                },
            ],
            "failure_signals": [
                {
                    "signal_id": "context-binding-missing",
                    "signal_type": "context_binding_gap",
                    "description": "missing binding plan",
                },
                {
                    "signal_id": "baseline-output-unchanged",
                    "signal_type": "no_behavioral_delta",
                    "description": "no delta",
                },
            ],
            "target_artifacts": [
                {"path": "assets/payloads.json", "required": True},
                {"path": "scripts/run_attack.py", "required": True},
            ],
            "family_specific_strategy": {
                "family": "prompt_injection",
                "generation_route": "prompt_injection",
                "target_surface": "retrieval_context",
                "package_kind": "conservative",
                "attack_style": "context_override",
                "primary_goal": "Inject hostile instructions.",
                "delivery_channel": "retrieval_context",
                "runner_hint": "prompt_injection_runner",
            },
            "recommended_follow_up": ["Wait for BOM enrichment."],
        }

        result = LlmTestPackageGenerationEngine().run(state)

        self.assertEqual(result["test_package"]["metadata"]["generator_name"], "llm_generator")
        self.assertEqual(result["test_package"]["generation_mode"], "conservative")
        self.assertEqual(result["test_package"]["execution_plan"]["entry_strategy"], "assumption_gated_probe")
        self.assertEqual(result["test_package"]["script_blueprint"]["blueprint_kind"], "runtime_execution")


if __name__ == "__main__":
    unittest.main()
