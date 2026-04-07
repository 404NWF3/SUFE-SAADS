from __future__ import annotations

import unittest
from unittest.mock import patch

from saads_wp12.engines.threat_understanding import (
    LlmNotConfiguredError,
    RuleBasedThreatUnderstandingEngine,
    SafeLlmThreatUnderstandingEngine,
)


def _build_state_for_threat_understanding(**overrides):
    normalized = {
        "attack_id": "attack-001",
        "attack_code": "case-001",
        "canonical_name": "Generic vulnerability record",
        "summary": "Generic software vulnerability record.",
        "attack_family": "prompt_injection",
        "feed_attack_family": "",
        "family_inference_signals": ["fallback:prompt_injection"],
        "taxonomy": {"type": "CWE", "code": "CWE-787", "name": "Out-of-bounds Write"},
        "all_taxonomies": [
            {
                "map_id": 1,
                "taxonomy_type": "CWE",
                "taxonomy_code": "CWE-787",
                "taxonomy_name": "Out-of-bounds Write",
                "is_primary": True,
                "confidence_score": 0.95,
            }
        ],
        "component": {
            "id": "",
            "name": "",
            "version_constraint": "",
            "normalized_constraint": "",
            "impact_scope": "",
        },
        "seed_asset": {
            "asset_id": "",
            "asset_type": "",
            "asset_name": "",
            "artifact_uri": "",
            "qa_status": "",
        },
        "attack_entry_context": {
            "description": "Generic software vulnerability record.",
            "exploit_preconditions": "",
            "impact_scope": "",
            "confidence_score": 0.9,
        },
        "bom_component_context": {
            "component_id": "",
            "component_code": "",
            "component_name": "",
            "component_layer": "",
            "vendor_name": "",
            "component_type": "",
            "modality": "",
            "purl": "",
            "homepage_uri": "",
            "lifecycle_status": "",
            "aliases": [],
            "impacts": [],
        },
        "published_seed_assets": [],
        "component_risk_overview": {},
        "stix_context": {"stix_type": "", "stix_payload": {}},
    }
    normalized.update(overrides)
    return {
        "intel_normalized": normalized,
        "risk_flags": ["high_severity"],
    }


class ThreatUnderstandingContractTest(unittest.TestCase):
    def test_out_of_scope_record_uses_unsupported_profile(self) -> None:
        state = _build_state_for_threat_understanding(
            summary="WatchGuard Fireware OS 的 iked 进程存在越界写入漏洞。",
            feed_attack_family="out_of_bounds_write",
            all_taxonomies=[
                {
                    "map_id": 1,
                    "taxonomy_type": "CWE",
                    "taxonomy_code": "CWE-787",
                    "taxonomy_name": "Out-of-bounds Write",
                    "is_primary": True,
                    "confidence_score": 0.95,
                },
                {
                    "map_id": 2,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-unknown",
                    "taxonomy_name": "unknown",
                    "is_primary": False,
                    "confidence_score": 0.1,
                },
            ],
        )

        result = RuleBasedThreatUnderstandingEngine().run(state)

        self.assertFalse(result["in_scope"])
        self.assertEqual(result["attack_family"], "unsupported")
        self.assertEqual(result["supported_family"], "unsupported")
        self.assertEqual(result["target_surface"], "unsupported_target")
        self.assertIn("generic software", result["threat_understanding"]["attack_mechanism"].lower())
        self.assertIn("out-of-scope", result["threat_understanding"]["recommended_test_strategy"].lower())
        self.assertEqual(result["candidate_families"], [{"family": "unsupported", "confidence": result["confidence"]}])
        self.assertEqual(result["classification_rationale"]["top_candidate"], "unsupported")

    def test_missing_seed_asset_is_not_reported_as_asset_quality_problem(self) -> None:
        state = _build_state_for_threat_understanding()

        result = RuleBasedThreatUnderstandingEngine().run(state)
        missing_types = {item["type"] for item in result["missing_knowledge"]}

        self.assertIn("seed_asset_detail", missing_types)
        self.assertNotIn("asset_quality", missing_types)
        self.assertEqual(result["threat_understanding"]["usable_seed_assets"], [])

    def test_generic_owasp_llm06_record_without_llm_native_mechanism_stays_out_of_scope(self) -> None:
        state = _build_state_for_threat_understanding(
            canonical_name="React Native Community CLI OS Command Injection via Metro Development Server",
            summary="React Native Community CLI contains an OS command injection vulnerability that may let unauthenticated attackers send POST requests to the Metro Development Server and execute arbitrary executables.",
            attack_family="tool_hijack",
            feed_attack_family="os_command_injection",
            family_inference_signals=["text:tool_hijack"],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-06", "name": "Command and Control / OS Command Injection"},
            all_taxonomies=[
                {
                    "map_id": 1,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-06",
                    "taxonomy_name": "Command and Control / OS Command Injection",
                    "is_primary": True,
                    "confidence_score": 0.35,
                },
                {
                    "map_id": 2,
                    "taxonomy_type": "CWE",
                    "taxonomy_code": "CWE-78",
                    "taxonomy_name": "OS Command Injection",
                    "is_primary": False,
                    "confidence_score": 0.9,
                },
            ],
        )

        result = RuleBasedThreatUnderstandingEngine().run(state)

        self.assertFalse(result["in_scope"])
        self.assertEqual(result["attack_family"], "unsupported")
        self.assertEqual(result["supported_family"], "unsupported")
        self.assertIn("generic software", result["scope_reason"].lower())

    def test_text_signal_requires_explicit_llm_native_mechanism_to_enter_scope(self) -> None:
        state = _build_state_for_threat_understanding(
            canonical_name="Memory poisoning through unauthenticated local API",
            summary="An unauthenticated local API lets a local process write memory entries and inject hostile instructions into future Claude sessions.",
            attack_family="prompt_injection",
            feed_attack_family="",
            family_inference_signals=["text:prompt_injection"],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-01", "name": "Prompt Injection"},
            all_taxonomies=[
                {
                    "map_id": 1,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-01",
                    "taxonomy_name": "Prompt Injection",
                    "is_primary": True,
                    "confidence_score": 0.95,
                }
            ],
        )

        result = RuleBasedThreatUnderstandingEngine().run(state)

        self.assertTrue(result["in_scope"])
        self.assertEqual(result["supported_family"], "prompt_injection")
        self.assertTrue(
            any(item.startswith("llm_mechanism:") for item in result["scope_assessment"]["scope_evidence"])
        )
        self.assertEqual(
            result["threat_understanding"]["attack_mechanism_type"],
            "memory_poisoning",
        )
        self.assertEqual(
            result["threat_understanding"]["target_surface_type"],
            "memory_channel",
        )

    def test_tool_hijack_text_signal_requires_explicit_tool_invocation_mechanism(self) -> None:
        state = _build_state_for_threat_understanding(
            canonical_name="Kimwolf Botnet Operation via Vulnerability Supply Chain Compromise",
            summary="A botnet operator assembled infrastructure for DDoS, doxing, SIM swapping, CAPTCHA bypass tools, and disposable email services.",
            attack_family="tool_hijack",
            feed_attack_family="botnet_operation",
            family_inference_signals=["text:tool_hijack"],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-10", "name": "Model Theft"},
            all_taxonomies=[
                {
                    "map_id": 1,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-10",
                    "taxonomy_name": "Model Theft",
                    "is_primary": True,
                    "confidence_score": 0.5,
                },
                {
                    "map_id": 2,
                    "taxonomy_type": "ATTACK",
                    "taxonomy_code": "T1584",
                    "taxonomy_name": "Compromise Infrastructure",
                    "is_primary": False,
                    "confidence_score": 0.7,
                },
            ],
        )

        result = RuleBasedThreatUnderstandingEngine().run(state)

        self.assertFalse(result["in_scope"])
        self.assertEqual(result["supported_family"], "unsupported")
        self.assertIn("generic software", result["scope_reason"].lower())

    def test_true_tool_hijack_text_signal_with_tool_invocation_language_stays_in_scope(self) -> None:
        state = _build_state_for_threat_understanding(
            canonical_name="Unsafe tool invocation through memory write and function call steering",
            summary="An attacker can use a memory write plus function call steering to alter tool selection, change parameter construction, and trigger unsafe tool invocation inside an agent workflow.",
            attack_family="tool_hijack",
            feed_attack_family="",
            family_inference_signals=["text:tool_hijack"],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-06", "name": "Excessive Agency"},
            all_taxonomies=[
                {
                    "map_id": 1,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-06",
                    "taxonomy_name": "Excessive Agency",
                    "is_primary": True,
                    "confidence_score": 0.82,
                }
            ],
        )

        result = RuleBasedThreatUnderstandingEngine().run(state)

        self.assertTrue(result["in_scope"])
        self.assertEqual(result["supported_family"], "tool_hijack")
        self.assertTrue(
            any(item.startswith("llm_mechanism:") for item in result["scope_assessment"]["scope_evidence"])
        )
        self.assertEqual(
            result["threat_understanding"]["attack_mechanism_type"],
            "tool_parameter_steering",
        )
        self.assertEqual(
            result["threat_understanding"]["target_surface_type"],
            "tool_runtime",
        )

    def test_tool_mechanism_can_override_broad_prompt_surface_bias(self) -> None:
        state = _build_state_for_threat_understanding(
            canonical_name="AI IDE workflow abuse through function-call steering",
            summary=(
                "An AI-powered IDE workflow can be abused through function call steering, "
                "tool selection changes, and unsafe parameter construction inside an agent runtime."
            ),
            attack_family="prompt_injection",
            feed_attack_family="",
            family_inference_signals=["text:tool_hijack", "text:prompt_injection"],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-01", "name": "Prompt Injection"},
            all_taxonomies=[
                {
                    "map_id": 1,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-01",
                    "taxonomy_name": "Prompt Injection",
                    "is_primary": True,
                    "confidence_score": 0.8,
                },
                {
                    "map_id": 2,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-02",
                    "taxonomy_name": "Insecure Output Handling",
                    "is_primary": False,
                    "confidence_score": 0.4,
                },
            ],
        )

        result = RuleBasedThreatUnderstandingEngine().run(state)

        self.assertTrue(result["in_scope"])
        self.assertEqual(result["attack_family"], "tool_hijack")
        self.assertEqual(result["supported_family"], "tool_hijack")
        self.assertEqual(result["candidate_families"][0]["family"], "tool_hijack")

    def test_unreviewed_existing_seed_asset_reports_asset_quality_problem(self) -> None:
        state = _build_state_for_threat_understanding(
            feed_attack_family="prompt_injection",
            all_taxonomies=[
                {
                    "map_id": 10,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-01",
                    "taxonomy_name": "Prompt Injection",
                    "is_primary": True,
                    "confidence_score": 0.95,
                }
            ],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-01", "name": "Prompt Injection"},
            seed_asset={
                "asset_id": "seed-1",
                "asset_type": "prompt_corpus",
                "asset_name": "seed asset",
                "artifact_uri": "s3://bucket/seed.txt",
                "qa_status": "draft",
            },
        )

        result = RuleBasedThreatUnderstandingEngine().run(state)
        missing_types = {item["type"] for item in result["missing_knowledge"]}

        self.assertIn("asset_quality", missing_types)
        self.assertEqual(len(result["threat_understanding"]["usable_seed_assets"]), 1)

    def test_missing_aibom_context_blocks_environment_build_and_execution(self) -> None:
        state = _build_state_for_threat_understanding(
            feed_attack_family="prompt_injection",
            all_taxonomies=[
                {
                    "map_id": 10,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-01",
                    "taxonomy_name": "Prompt Injection",
                    "is_primary": True,
                    "confidence_score": 0.95,
                }
            ],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-01", "name": "Prompt Injection"},
            seed_asset={
                "asset_id": "seed-2",
                "asset_type": "prompt_corpus",
                "asset_name": "seed asset",
                "artifact_uri": "s3://bucket/seed.txt",
                "qa_status": "published",
            },
        )

        result = RuleBasedThreatUnderstandingEngine().run(state)
        execution_assessment = result["execution_assessment"]

        self.assertFalse(execution_assessment["has_aibom_context"])
        self.assertEqual(execution_assessment["execution_eligibility"], "blocked_no_aibom")
        self.assertFalse(execution_assessment["can_build_env"])
        self.assertFalse(execution_assessment["should_execute"])
        self.assertEqual(execution_assessment["execution_mode"], "analysis_only")
        self.assertEqual(result["plan_readiness"]["plan_mode"], "conservative")
        self.assertFalse(result["plan_readiness"]["can_generate_script"])
        self.assertIn("Enrich AIBOM context", " ".join(result["recommended_follow_up"]))

    def test_taxonomy_and_planning_fields_are_present_for_supported_prompt_case(self) -> None:
        state = _build_state_for_threat_understanding(
            summary="Retrieved untrusted content injects hostile instructions into the model context window.",
            feed_attack_family="prompt_injection",
            family_inference_signals=["taxonomy_code:OWASP-LLM-01"],
            all_taxonomies=[
                {
                    "map_id": 10,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-01",
                    "taxonomy_name": "Prompt Injection",
                    "is_primary": True,
                    "confidence_score": 0.95,
                }
            ],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-01", "name": "Prompt Injection"},
            seed_asset={
                "asset_id": "seed-4",
                "asset_type": "prompt_corpus",
                "asset_name": "prompt seed",
                "artifact_uri": "s3://bucket/seed.txt",
                "qa_status": "published",
            },
        )

        result = RuleBasedThreatUnderstandingEngine().run(state)

        self.assertEqual(result["taxonomy_context"]["selected_taxonomy_code"], "OWASP-LLM-01")
        self.assertIn("OWASP-LLM-01", result["taxonomy_context"]["all_taxonomy_codes"])
        self.assertIn("Prompt Injection", result["taxonomy_context"]["selected_taxonomy_name"])
        self.assertIn("override", result["planning_focus"]["primary_test_question"].lower())
        self.assertTrue(result["planning_focus"]["planning_constraints"])
        self.assertEqual(result["plan_readiness"]["plan_mode"], "conservative")
        self.assertTrue(result["plan_readiness"]["can_build_test_plan"])
        self.assertEqual(
            result["threat_understanding"]["taxonomy_test_focus"],
            result["taxonomy_context"]["taxonomy_test_focus"],
        )
        self.assertEqual(
            result["threat_profile"]["primary_test_question"],
            result["planning_focus"]["primary_test_question"],
        )

    @patch("saads_wp12.engines.threat_understanding.generate_json_response")
    def test_safe_llm_engine_falls_back_to_rule_engine_when_llm_fails(self, mock_generate) -> None:
        state = _build_state_for_threat_understanding(
            feed_attack_family="prompt_injection",
            all_taxonomies=[
                {
                    "map_id": 10,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-01",
                    "taxonomy_name": "Prompt Injection",
                    "is_primary": True,
                    "confidence_score": 0.95,
                }
            ],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-01", "name": "Prompt Injection"},
        )
        mock_generate.side_effect = LlmNotConfiguredError("missing key")

        result = SafeLlmThreatUnderstandingEngine().run(state)

        self.assertEqual(result["attack_family"], "prompt_injection")
        self.assertIn(result["execution_eligibility"], {"blocked_no_aibom", "ready", "blocked_no_seed_asset"})
        self.assertIn("plan_mode", result["plan_readiness"])
        self.assertIn("taxonomy_context", result)

    @patch("saads_wp12.engines.threat_understanding.generate_json_response")
    def test_safe_llm_engine_sanitizes_model_output(self, mock_generate) -> None:
        state = _build_state_for_threat_understanding(
            feed_attack_family="prompt_injection",
            all_taxonomies=[
                {
                    "map_id": 10,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-01",
                    "taxonomy_name": "Prompt Injection",
                    "is_primary": True,
                    "confidence_score": 0.95,
                }
            ],
            taxonomy={"type": "OWASP_LLM", "code": "OWASP-LLM-01", "name": "Prompt Injection"},
            seed_asset={
                "asset_id": "seed-3",
                "asset_type": "prompt_corpus",
                "asset_name": "seed asset",
                "artifact_uri": "s3://bucket/seed.txt",
                "qa_status": "published",
            },
        )
        mock_generate.return_value = {
            "attack_family": "prompt_injection",
            "target_surface": "retrieval_context",
            "confidence": 0.91,
            "candidate_families": [
                {"family": "prompt_injection", "confidence": 0.91},
                {"family": "tool_hijack", "confidence": 0.22},
                {"family": "made_up_family", "confidence": 0.99},
            ],
            "classification_rationale": {"top_candidate": "prompt_injection"},
            "missing_knowledge": [
                {"type": "component_context", "description": "Need tighter component scoping."},
                {"type": "", "description": "bad row"},
            ],
            "threat_understanding": {
                "threat_summary": "Injected hostile retrieval content overrides the target.",
                "attack_mechanism": "Hostile context override",
                "taxonomy": {"type": "OWASP_LLM", "code": "OWASP-LLM-01", "name": "Prompt Injection"},
                "target_surface": "retrieval_context",
                "exploit_preconditions": ["retrieval content available"],
                "test_focus": ["override success"],
                "expected_failure_modes": ["unsafe response"],
                "recommended_test_strategy": "Run prompt injection validation",
                "usable_seed_assets": [],
            },
        }

        result = SafeLlmThreatUnderstandingEngine().run(state)

        self.assertEqual(result["attack_family"], "prompt_injection")
        self.assertEqual(len(result["candidate_families"]), 2)
        self.assertEqual(result["candidate_families"][0]["family"], "prompt_injection")
        self.assertEqual(result["missing_knowledge"][0]["type"], "component_context")
        self.assertEqual(result["taxonomy_context"]["selected_taxonomy_code"], "OWASP-LLM-01")
        self.assertTrue(result["planning_focus"]["evidence_priority"])

    @patch("saads_wp12.engines.threat_understanding.generate_json_response")
    def test_safe_llm_engine_reconciles_unsupported_prediction_with_supported_taxonomy(self, mock_generate) -> None:
        state = _build_state_for_threat_understanding(
            summary="Retrieved untrusted content injects hostile instructions into the model context window.",
            feed_attack_family="",
            family_inference_signals=["taxonomy_code:OWASP-LLM-01"],
            all_taxonomies=[
                {
                    "map_id": 10,
                    "taxonomy_type": "OWASP_LLM",
                    "taxonomy_code": "OWASP-LLM-01",
                    "taxonomy_name": "LLM08:SoftwareIntegrity",
                    "is_primary": False,
                    "confidence_score": 0.95,
                },
                {
                    "map_id": 11,
                    "taxonomy_type": "CWE",
                    "taxonomy_code": "CWE-502",
                    "taxonomy_name": "Deserialization of Untrusted Data",
                    "is_primary": True,
                    "confidence_score": 0.91,
                },
            ],
            taxonomy={"type": "CWE", "code": "CWE-502", "name": "Deserialization of Untrusted Data"},
            seed_asset={
                "asset_id": "seed-5",
                "asset_type": "prompt_corpus",
                "asset_name": "seed asset",
                "artifact_uri": "s3://bucket/seed.txt",
                "qa_status": "published",
            },
        )
        mock_generate.return_value = {
            "attack_family": "unsupported",
            "target_surface": "unsupported_target",
            "confidence": 0.87,
            "candidate_families": [
                {"family": "unsupported", "confidence": 0.87},
                {"family": "prompt_injection", "confidence": 0.64},
            ],
            "classification_rationale": {"top_candidate": "unsupported"},
            "missing_knowledge": [
                {"type": "component_context", "description": "Missing version constraint or target component scope."},
            ],
            "threat_understanding": {
                "threat_summary": "The record may describe a generic vulnerability.",
                "attack_mechanism": "The model output is uncertain.",
                "taxonomy": {"type": "OWASP_LLM", "code": "OWASP-LLM-01", "name": "LLM08:SoftwareIntegrity"},
                "target_surface": "unsupported_target",
                "exploit_preconditions": ["more evidence needed"],
                "test_focus": ["taxonomy consistency"],
                "expected_failure_modes": ["wrongly treated as LLM-native"],
                "recommended_test_strategy": "Stay in triage mode.",
                "usable_seed_assets": [],
            },
        }

        result = SafeLlmThreatUnderstandingEngine().run(state)

        self.assertEqual(result["attack_family"], "prompt_injection")
        self.assertEqual(result["supported_family"], "prompt_injection")
        self.assertTrue(result["in_scope"])
        self.assertEqual(result["candidate_families"][0]["family"], "prompt_injection")
        self.assertEqual(result["taxonomy_context"]["selected_taxonomy_code"], "OWASP-LLM-01")
        self.assertEqual(result["taxonomy_context"]["selected_taxonomy_name"], "Prompt Injection")
        self.assertEqual(result["threat_understanding"]["target_surface"], "retrieval_context")
        self.assertIn("override", result["planning_focus"]["primary_test_question"].lower())


if __name__ == "__main__":
    unittest.main()
