from __future__ import annotations

import unittest

from saads_wp12.reporting.state_export import (
    build_compact_export_state,
    build_presentation_export_state,
)


class StateExportTest(unittest.TestCase):
    def test_build_compact_export_state_removes_root_mirrors_and_trims_metadata(self) -> None:
        state = {
            "run_id": "run-1",
            "attack_id": "attack-1",
            "intel_raw": {"summary": "raw"},
            "intel_normalized": {"summary": "normalized"},
            "threat_understanding": {"threat_summary": "summary"},
            "threat_profile": {"attack_family": "prompt_injection"},
            "scope_assessment": {"in_scope": True, "supported_family": "prompt_injection"},
            "execution_assessment": {"execution_eligibility": "blocked_no_aibom"},
            "evidence_and_context": {
                "classification_rationale": {"taxonomy_signal": "OWASP-LLM-01"},
                "planning_focus": {"primary_test_question": "question"},
            },
            "uncertainty_report": {"known_gaps": ["gap"], "risk_flags": ["flag"]},
            "attack_family": "prompt_injection",
            "supported_family": "prompt_injection",
            "classification_rationale": {"taxonomy_signal": "OWASP-LLM-01"},
            "test_package": {
                "attack_family": "prompt_injection",
                "target_surface": "surface",
                "known_gaps": ["gap"],
                "payload_plan": [{"payload_id": "p1"}],
                "metadata": {
                    "generator_name": "llm_generator",
                    "llm_enabled": True,
                    "input_contract": {"version": 2},
                    "scope_assessment": {"in_scope": True},
                    "execution_assessment": {"execution_eligibility": "blocked_no_aibom"},
                    "threat_summary": "duplicate summary",
                },
            },
            "package_validation": {"valid": True},
        }

        exported = build_compact_export_state(state)

        self.assertNotIn("attack_family", exported)
        self.assertNotIn("supported_family", exported)
        self.assertNotIn("classification_rationale", exported)
        self.assertNotIn("intel_raw", exported)
        self.assertNotIn("threat_profile", exported)
        self.assertEqual(exported["evidence_and_context"], {"planning_focus": {"primary_test_question": "question"}})
        self.assertEqual(exported["uncertainty_report"], {"known_gaps": ["gap"], "risk_flags": ["flag"]})
        self.assertNotIn("target_surface", exported["test_package"])
        self.assertNotIn("known_gaps", exported["test_package"])
        self.assertEqual(
            exported["test_package"]["metadata"],
            {
                "generator_name": "llm_generator",
                "llm_enabled": True,
                "input_contract": {"version": 2},
            },
        )

    def test_build_presentation_export_state_keeps_only_showcase_fields(self) -> None:
        state = {
            "run_id": "run-1",
            "attack_id": "attack-1",
            "intel_normalized": {"summary": "normalized"},
            "threat_understanding": {
                "threat_summary": "summary",
                "attack_mechanism": "mechanism",
                "attack_mechanism_type": "memory_poisoning",
                "target_surface": "surface",
                "target_surface_type": "memory_channel",
                "taxonomy": [{"code": "OWASP-LLM-01"}],
                "primary_test_question": "question",
                "highest_value_validation_target": "target",
                "recommended_test_strategy": "strategy",
                "planning_constraints": ["noise"],
            },
            "scope_assessment": {"in_scope": True, "supported_family": "prompt_injection"},
            "execution_assessment": {
                "execution_eligibility": "blocked_no_aibom",
                "execution_blockers": ["missing_aibom_context"],
                "test_readiness": "medium",
                "execution_mode": "analysis_only",
                "can_build_env": False,
            },
            "evidence_and_context": {
                "planning_focus": {"primary_test_question": "question"},
                "surface_and_mechanism_summary": {
                    "target_surface_type": "memory_channel",
                    "attack_mechanism_type": "memory_poisoning",
                },
            },
            "uncertainty_report": {
                "known_gaps": ["gap"],
                "missing_knowledge": [{"type": "context"}],
                "risk_flags": ["flag"],
            },
            "test_package": {
                "package_id": "pkg-1",
                "package_kind": "conservative",
                "generation_mode": "conservative",
                "objective": "objective",
                "attack_hypothesis": "hypothesis",
                "family_specific_strategy": {"family": "prompt_injection"},
                "payload_plan": [{"payload_id": "p1"}],
                "execution_plan": {
                    "entry_strategy": "assumption_gated_probe",
                    "runner_type": "prompt_injection_runner",
                    "parameterization": {"target_surface": "surface"},
                    "steps": [{"step": 1, "action": "do something"}],
                    "execution_steps": [{"step_id": "internal"}],
                },
                "evidence_collection_plan": {
                    "collection_mode": "runtime_execution",
                    "capture_strategy": "capture_trace",
                    "evidence_types": [{"type": "trace"}],
                    "secondary_evidence_focus": [{"type": "focus"}],
                    "required_hooks": ["stdout"],
                },
                "success_criteria": [{"criterion_id": "c1"}],
                "failure_signals": [{"signal_id": "f1"}],
                "assumptions": ["a1"],
                "recommended_follow_up": [{"action": "follow"}],
                "target_artifacts": [{"path": "reports/x.json"}],
                "metadata": {"generator_name": "llm_generator"},
            },
            "package_validation": {"valid": True},
        }

        exported = build_presentation_export_state(state)

        self.assertEqual(
            sorted(exported.keys()),
            [
                "attack_id",
                "evidence_and_context",
                "execution_assessment",
                "package_validation",
                "run_id",
                "scope_assessment",
                "test_package",
                "threat_understanding",
                "uncertainty_report",
            ],
        )
        self.assertNotIn("intel_normalized", exported)
        self.assertEqual(
            sorted(exported["threat_understanding"].keys()),
            [
                "attack_mechanism",
                "attack_mechanism_type",
                "highest_value_validation_target",
                "primary_test_question",
                "recommended_test_strategy",
                "target_surface",
                "target_surface_type",
                "taxonomy",
                "threat_summary",
            ],
        )
        self.assertEqual(
            exported["evidence_and_context"]["surface_and_mechanism_summary"],
            {
                "target_surface_type": "memory_channel",
                "attack_mechanism_type": "memory_poisoning",
            },
        )
        self.assertEqual(
            sorted(exported["test_package"]["execution_plan"].keys()),
            ["entry_strategy", "parameterization", "runner_type", "steps"],
        )
        self.assertEqual(
            sorted(exported["test_package"]["evidence_collection_plan"].keys()),
            ["capture_strategy", "collection_mode", "evidence_types", "secondary_evidence_focus"],
        )


if __name__ == "__main__":
    unittest.main()
