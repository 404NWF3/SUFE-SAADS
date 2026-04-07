from __future__ import annotations

import unittest

from saads_wp12.agent import graph


class MinimalFlowSmokeTest(unittest.TestCase):
    def test_minimal_flow_smoke(self) -> None:
        result = graph.invoke(
            {
                "attack_id": "atk-001",
                "tenant_id": "test-tenant",
                "scenario_id": "smoke-scenario",
            }
        )

        self.assertTrue(result["package_validation"]["valid"])
        self.assertEqual(result["env_status"], "not_applicable_plan_generation")
        self.assertEqual(result["verdict"], "planned")
        self.assertTrue(result["persistence_path"])
        self.assertTrue(result["audit_log"])

    def test_low_confidence_uses_conservative_test_package(self) -> None:
        result = graph.invoke(
            {
                "attack_id": "atk-005",
                "tenant_id": "test-tenant",
                "scenario_id": "conservative-package-scenario",
            }
        )

        self.assertEqual(result["test_package"]["generation_mode"], "conservative")
        self.assertGreaterEqual(len(result["test_package"]["success_criteria"]), 3)
        self.assertIn(
            "classification_rationale",
            result["test_package"]["metadata"],
        )
        self.assertTrue(result["test_package"]["safety_constraints"])

    def test_tool_hijack_uses_family_generator(self) -> None:
        result = graph.invoke(
            {
                "attack_id": "atk-003",
                "tenant_id": "test-tenant",
                "scenario_id": "tool-generator-scenario",
            }
        )

        self.assertEqual(result["test_package"]["metadata"]["generator_name"], "tool_system_generator")
        self.assertIn("tool_call_trace", result["test_package"]["evidence_hooks"])

    def test_missing_aibom_stays_in_plan_generation_mode(self) -> None:
        result = graph.invoke(
            {
                "attack_id": "atk-007",
                "tenant_id": "test-tenant",
                "scenario_id": "missing-aibom-scenario",
            }
        )

        self.assertEqual(result["execution_eligibility"], "blocked_no_aibom")
        self.assertFalse(result["can_build_env"])
        self.assertFalse(result["should_execute"])
        self.assertEqual(result["execution_mode"], "analysis_only")
        self.assertEqual(result["env_status"], "not_applicable_plan_generation")
        self.assertIn(result["verdict"], {"planned", "triaged"})
        self.assertTrue(result["persistence_path"])


if __name__ == "__main__":
    unittest.main()
