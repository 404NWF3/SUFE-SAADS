from __future__ import annotations

import unittest

from saads_wp12.nodes.intel import normalize_intel


class IntelNormalizationTest(unittest.TestCase):
    def test_normalize_intel_handles_sparse_real_like_feed(self) -> None:
        state = {
            "intel_raw": {
                "attack_id": "real-001",
                "attack_code": "stable_xxx",
                "canonical_name": "Stub GitHub advisory affecting LangChain-like package",
                "attack_family": "",
                "severity_level": "medium",
                "entry_status": "active",
                "summary": "Stub collection result for query 'langchain prompt injection'.",
                "last_seen_at": "",
                "primary_cvss_version": "3.1",
                "primary_cvss_base_score": 6.4,
                "primary_cvss_vector": "",
                "primary_cvss_severity_label": "medium",
                "taxonomy_type": "OWASP_LLM",
                "taxonomy_code": "OWASP-LLM-01",
                "taxonomy_name": "Prompt Injection",
                "component_id": "",
                "component_name": "",
                "version_constraint_raw": "",
                "normalized_constraint": "",
                "component_impact_scope": "",
                "asset_id": "",
                "asset_type": "",
                "asset_name": "",
                "artifact_uri": "",
                "qa_status": "",
                "active": True,
            }
        }

        result = normalize_intel(state)

        self.assertEqual(result["attack_family"], "prompt_injection")
        self.assertIn("missing_component_context", result["risk_flags"])
        self.assertIn("missing_seed_artifact", result["risk_flags"])
        self.assertEqual(
            result["intel_normalized"]["family_inference_signals"],
            ["taxonomy_code:OWASP-LLM-01"],
        )

    def test_normalize_intel_can_infer_tool_hijack_from_text(self) -> None:
        state = {
            "intel_raw": {
                "attack_id": "real-002",
                "attack_code": "text_tool_case",
                "canonical_name": "Unsafe tool invocation chain",
                "attack_family": "",
                "severity_level": "high",
                "entry_status": "active",
                "summary": "The agent may trigger unsafe tool invocation with attacker-controlled arguments.",
                "last_seen_at": "",
                "primary_cvss_version": "3.1",
                "primary_cvss_base_score": "7.2",
                "primary_cvss_vector": "",
                "primary_cvss_severity_label": "high",
                "taxonomy_type": "",
                "taxonomy_code": "",
                "taxonomy_name": "",
                "component_id": "",
                "component_name": "",
                "version_constraint_raw": "",
                "normalized_constraint": "",
                "component_impact_scope": "",
                "asset_id": "",
                "asset_type": "",
                "asset_name": "",
                "artifact_uri": "",
                "qa_status": "reviewed",
                "active": True,
            }
        }

        result = normalize_intel(state)

        self.assertEqual(result["attack_family"], "tool_hijack")
        self.assertIn("text:tool_hijack", result["intel_normalized"]["family_inference_signals"])
        self.assertEqual(result["intel_normalized"]["primary_cvss_base_score"], 7.2)

    def test_normalize_intel_falls_back_safely_when_signals_are_sparse(self) -> None:
        state = {
            "intel_raw": {
                "attack_id": "real-003",
                "attack_code": "",
                "canonical_name": "",
                "attack_family": "",
                "severity_level": "",
                "entry_status": "",
                "summary": "",
                "last_seen_at": "",
                "primary_cvss_version": "",
                "primary_cvss_base_score": None,
                "primary_cvss_vector": None,
                "primary_cvss_severity_label": "",
                "taxonomy_type": "",
                "taxonomy_code": "",
                "taxonomy_name": "",
                "component_id": None,
                "component_name": None,
                "version_constraint_raw": None,
                "normalized_constraint": None,
                "component_impact_scope": None,
                "asset_id": None,
                "asset_type": None,
                "asset_name": None,
                "artifact_uri": None,
                "qa_status": None,
                "active": False,
            }
        }

        result = normalize_intel(state)

        self.assertEqual(result["attack_family"], "prompt_injection")
        self.assertIn("fallback:prompt_injection", result["intel_normalized"]["family_inference_signals"])
        self.assertIn("missing_summary", result["risk_flags"])
        self.assertIn("missing_taxonomy_code", result["risk_flags"])

    def test_normalize_intel_uses_unknown_for_non_llm_taxonomy_without_llm_signals(self) -> None:
        state = {
            "intel_raw": {
                "attack_id": "real-003b",
                "attack_code": "cwe-only-case",
                "canonical_name": "Java deserialization remote code execution",
                "attack_family": "deserialization_vulnerability",
                "severity_level": "critical",
                "entry_status": "active",
                "summary": "A generic Java deserialization vulnerability allows remote code execution.",
                "last_seen_at": "",
                "primary_cvss_version": "3.1",
                "primary_cvss_base_score": 9.8,
                "primary_cvss_vector": "",
                "primary_cvss_severity_label": "critical",
                "taxonomy_type": "CWE",
                "taxonomy_code": "CWE-502",
                "taxonomy_name": "Deserialization of Untrusted Data",
                "component_id": "",
                "component_name": "",
                "version_constraint_raw": "",
                "normalized_constraint": "",
                "component_impact_scope": "",
                "asset_id": "",
                "asset_type": "",
                "asset_name": "",
                "artifact_uri": "",
                "qa_status": "",
                "active": True,
                "all_taxonomies": [
                    {
                        "map_id": 1,
                        "taxonomy_type": "CWE",
                        "taxonomy_code": "CWE-502",
                        "taxonomy_name": "Deserialization of Untrusted Data",
                        "is_primary": True,
                        "confidence_score": 1.0,
                    }
                ],
            }
        }

        result = normalize_intel(state)

        self.assertEqual(result["attack_family"], "unknown")
        self.assertEqual(
            result["intel_normalized"]["family_inference_signals"],
            ["fallback:unknown_non_llm_taxonomy:CWE-502"],
        )

    def test_normalize_intel_prefers_supported_feed_attack_family(self) -> None:
        state = {
            "intel_raw": {
                "attack_id": "real-004",
                "attack_code": "feed-family-case",
                "canonical_name": "Direct family signal",
                "attack_family": "tool_hijack",
                "severity_level": "high",
                "entry_status": "active",
                "summary": "Sparse but explicitly labeled tool hijack record.",
                "last_seen_at": "",
                "primary_cvss_version": "3.1",
                "primary_cvss_base_score": 8.1,
                "primary_cvss_vector": "",
                "primary_cvss_severity_label": "high",
                "taxonomy_type": "OWASP_LLM",
                "taxonomy_code": "",
                "taxonomy_name": "",
                "component_id": "",
                "component_name": "",
                "version_constraint_raw": "",
                "normalized_constraint": "",
                "component_impact_scope": "",
                "asset_id": "",
                "asset_type": "",
                "asset_name": "",
                "artifact_uri": "",
                "qa_status": "",
                "active": True,
            }
        }

        result = normalize_intel(state)

        self.assertEqual(result["attack_family"], "tool_hijack")
        self.assertEqual(
            result["intel_normalized"]["family_inference_signals"],
            ["feed_attack_family:tool_hijack"],
        )

    def test_normalize_intel_can_use_all_taxonomies_when_primary_is_not_enough(self) -> None:
        state = {
            "intel_raw": {
                "attack_id": "real-005",
                "attack_code": "all-taxonomy-case",
                "canonical_name": "Taxonomy-enriched case",
                "attack_family": "out_of_bounds_write",
                "severity_level": "high",
                "entry_status": "active",
                "summary": "Sparse summary with weak direct LLM cues.",
                "last_seen_at": "",
                "primary_cvss_version": "3.1",
                "primary_cvss_base_score": 8.0,
                "primary_cvss_vector": "",
                "primary_cvss_severity_label": "high",
                "taxonomy_type": "CWE",
                "taxonomy_code": "CWE-787",
                "taxonomy_name": "Out-of-bounds Write",
                "component_id": "",
                "component_name": "",
                "version_constraint_raw": "",
                "normalized_constraint": "",
                "component_impact_scope": "",
                "asset_id": "",
                "asset_type": "",
                "asset_name": "",
                "artifact_uri": "",
                "qa_status": "",
                "active": True,
                "all_taxonomies": [
                    {
                        "map_id": 1,
                        "taxonomy_type": "CWE",
                        "taxonomy_code": "CWE-787",
                        "taxonomy_name": "Out-of-bounds Write",
                        "is_primary": True,
                        "confidence_score": 0.9,
                    },
                    {
                        "map_id": 2,
                        "taxonomy_type": "OWASP_LLM",
                        "taxonomy_code": "OWASP-LLM-02",
                        "taxonomy_name": "Tool Hijacking",
                        "is_primary": False,
                        "confidence_score": 0.8,
                    },
                ],
            }
        }

        result = normalize_intel(state)

        self.assertEqual(result["attack_family"], "tool_hijack")
        self.assertEqual(
            result["intel_normalized"]["family_inference_signals"],
            ["all_taxonomy_code:OWASP-LLM-02"],
        )


if __name__ == "__main__":
    unittest.main()
