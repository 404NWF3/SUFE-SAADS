from __future__ import annotations

import unittest

from saads_wp12.engines.test_package_generation import (
    TEST_PACKAGE_INPUT_CONTRACT_VERSION,
    build_test_package_generation_input,
)
from saads_wp12.llm.test_package_generation_prompts import (
    build_test_package_few_shot_examples,
    build_test_package_prompt_bundle,
    build_test_package_system_prompt,
    build_test_package_user_prompt,
)
from tests.test_test_package_generation import _base_state


class TestPackageGenerationPromptAssetsTest(unittest.TestCase):
    def test_system_prompt_includes_output_constraints(self) -> None:
        prompt = build_test_package_system_prompt()

        self.assertIn("machine-consumable JSON object", prompt)
        self.assertIn("package_kind", prompt)
        self.assertIn("If execution_assessment.has_aibom_context=false", prompt)
        self.assertIn("high-quality test plan", prompt)
        self.assertIn("plan quality over runtime detail", prompt)
        self.assertIn("common WP1-2 test-plan foundation", prompt)
        self.assertIn("Use the relevant family detail playbook", prompt)
        self.assertIn("taxonomy detail playbook", prompt)
        self.assertIn("validation_question, primary_comparison, and evidence_priority", prompt)
        self.assertIn("secondary taxonomy playbooks", prompt)
        self.assertIn("Use a two-layer route decision", prompt)
        self.assertIn("Route prompt detail aggressively", prompt)
        self.assertIn("Do not flatten all possible OWASP categories", prompt)
        self.assertIn("Write the analyst test procedure first, then map it into the schema", prompt)
        self.assertIn("prefer triage over stretching a generic vulnerability into an LLM-native test plan", prompt)
        self.assertIn("Different families should produce visibly different plan shapes", prompt)
        self.assertIn("family_plan_shape guidance", prompt)
        self.assertIn("execution_plan should include a human-readable 'steps' list", prompt)
        self.assertIn("execution_plan.steps should explain the attack entry", prompt)
        self.assertIn("execution_plan.steps should sound like analyst test procedure", prompt)
        self.assertIn("do not stop at three generic steps", prompt)
        self.assertIn("payload_plan must include concrete payload ideas", prompt)
        self.assertIn("success_criteria must be sample-coupled", prompt)
        self.assertIn("failure_signals must also be sample-coupled", prompt)
        self.assertIn("payload_plan should contain copyable example content", prompt)
        self.assertIn("execution_plan.steps should read like an executable analyst checklist", prompt)
        self.assertIn("evidence_collection_plan should identify where evidence is collected from", prompt)
        self.assertIn("If the target surface is broad, first narrow it", prompt)
        self.assertIn("Prefer target-specific nouns such as Telegram message", prompt)
        self.assertIn("Use scenario-specific hints from the input when available", prompt)
        self.assertIn("use them to anchor the first one or two human-readable steps in a concrete probe", prompt)
        self.assertIn("evidence_collection_plan should include an 'evidence_types' list", prompt)
        self.assertIn("evidence_collection_plan should explicitly reflect at least one secondary taxonomy evidence priority", prompt)
        self.assertIn("evidence_collection_plan.secondary_evidence_focus", prompt)
        self.assertIn("secondary_evidence_focus should name sample-specific artifacts or control points", prompt)
        self.assertIn("When scenario_specific_hints are present", prompt)
        self.assertIn("Family-specific detail should enrich the common plan foundation", prompt)
        self.assertIn("recommended_follow_up should be human-readable and action-oriented", prompt)
        self.assertIn("recommended_follow_up should include at least one action that is specific to a secondary taxonomy risk theme", prompt)
        self.assertIn("recommended_follow_up should prefer concrete control checks", prompt)
        self.assertIn("related_taxonomy field", prompt)

    def test_user_prompt_serializes_fixed_input_contract(self) -> None:
        contract = build_test_package_generation_input(_base_state())
        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"input_contract_version": 2', prompt)
        self.assertIn('"attack_family": "prompt_injection"', prompt)
        self.assertIn('"component_name": "rag-service"', prompt)
        self.assertIn('"common_plan_foundation"', prompt)
        self.assertIn('"scenario_specific_hints"', prompt)
        self.assertIn('"human_step_style_guide"', prompt)
        self.assertIn('"detailed_schema_expectations"', prompt)
        self.assertIn('"prompt_routing"', prompt)
        self.assertIn('"prompt_mode"', prompt)
        self.assertIn('"family_detail_playbook"', prompt)
        self.assertIn('"family_plan_shape"', prompt)
        self.assertIn('"taxonomy_detail_playbook"', prompt)
        self.assertIn('"secondary_taxonomy_playbooks"', prompt)
        self.assertIn('"planning_focus"', prompt)
        self.assertIn('"plan_readiness"', prompt)

    def test_prompt_bundle_exposes_examples_and_schema(self) -> None:
        contract = build_test_package_generation_input(_base_state())
        bundle = build_test_package_prompt_bundle(contract)

        self.assertIn("system_prompt", bundle)
        self.assertIn("user_prompt", bundle)
        self.assertIn("few_shot_examples", bundle)
        self.assertIn("output_schema_required_fields", bundle)
        self.assertGreaterEqual(len(bundle["few_shot_examples"]), 2)
        self.assertLessEqual(len(bundle["few_shot_examples"]), 4)
        self.assertIn("execution_plan", bundle["output_schema_required_fields"])
        labels = {example["label"] for example in bundle["few_shot_examples"]}
        self.assertIn("prompt_injection_standard", labels)
        self.assertIn("prompt_injection_indirect_plan_reference", labels)

    def test_few_shot_examples_cover_standard_conservative_and_triage(self) -> None:
        examples = build_test_package_few_shot_examples()
        labels = {example["label"] for example in examples}

        self.assertTrue(
            {
                "prompt_injection_standard",
                "dialogue_conservative",
                "unsupported_triage",
                "prompt_injection_indirect_plan_reference",
                "ai_ide_agent_plan_reference",
                "tool_hijack_function_call_reference",
                "tool_hijack_mcp_reference",
                "insecure_output_handling_reference",
                "model_dos_reference",
                "supply_chain_risk_reference",
                "vector_embedding_weakness_reference",
                "overreliance_reference",
                "unbounded_consumption_reference",
                "persistent_memory_poisoning_reference",
            }.issubset(labels)
        )
        self.assertEqual(TEST_PACKAGE_INPUT_CONTRACT_VERSION, 2)

    def test_user_prompt_references_case_guidance(self) -> None:
        contract = build_test_package_generation_input(_base_state())
        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"few_shot_usage_guidance"', prompt)
        self.assertIn('"relevant_case_labels"', prompt)
        self.assertIn('"selected_few_shot_labels"', prompt)
        self.assertIn("Use the reference cases as attack-chain and evidence-quality anchors", prompt)
        self.assertIn("the package keeps the shared WP1-2 planning spine", prompt)
        self.assertIn("prompt_mode is respected", prompt)
        self.assertIn("the plan shape follows the selected family_plan_shape workflow_spine", prompt)
        self.assertIn("when scenario_specific_hints are present", prompt)
        self.assertIn("execution_plan.steps are meaningful test actions", prompt)
        self.assertIn("execution_plan.steps mention the attack path, attack entry or trigger when meaningful", prompt)
        self.assertIn("execution_plan.steps use target-specific artifacts and workflows", prompt)
        self.assertIn("payload_plan contains concrete sample-coupled payload ideas", prompt)
        self.assertIn("payload_plan includes at least one copyable prompt, request body, file fragment", prompt)
        self.assertIn("the first human-readable step should usually start from a concrete probe", prompt)
        self.assertIn("execution_plan.steps and evidence_collection_plan reflect the family detail playbook", prompt)
        self.assertIn("execution_plan.steps name the tool, interface, or collection point", prompt)
        self.assertIn("expected results describe the concrete sample-specific delta", prompt)
        self.assertIn("execution_plan.steps follow the family-specific first_step_patterns", prompt)
        self.assertIn("when a taxonomy_detail_playbook is present", prompt)
        self.assertIn("the plan uses its primary_comparison and does_not_default_to guidance", prompt)
        self.assertIn("when secondary_taxonomy_playbooks are present", prompt)
        self.assertIn("evidence_collection_plan names at least one secondary-taxonomy-specific evidence artifact", prompt)
        self.assertIn("evidence_collection_plan prefers a secondary_evidence_focus structure", prompt)
        self.assertIn("evidence_collection_plan names sample-coupled artifacts", prompt)
        self.assertIn("secondary_evidence_focus uses sample-specific artifacts or controls", prompt)
        self.assertIn("secondary_evidence_focus should prefer those observables", prompt)
        self.assertIn("recommended_follow_up includes at least one secondary-taxonomy-specific control or investigation action", prompt)
        self.assertIn("recommended_follow_up prefers structured entries with related_taxonomy", prompt)
        self.assertIn("recommended_follow_up should prioritize those concrete checks", prompt)
        self.assertIn("success_criteria and failure_signals are specific enough", prompt)
        self.assertIn("evidence_collection_plan says where each important artifact is collected from", prompt)
        self.assertIn("success_criteria and failure_signals avoid generic restatements", prompt)
        self.assertIn("recommended_follow_up maps to missing context or blockers and explains upgrade conditions", prompt)
        self.assertIn("the package reads like a concrete analyst workflow first", prompt)
        self.assertIn("each human-readable step should normally include a concrete attacker-controlled artifact", prompt)

    def test_user_prompt_includes_human_step_style_guide_examples(self) -> None:
        contract = build_test_package_generation_input(_base_state())

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"human_step_style_guide"', prompt)
        self.assertIn('"authoring_priority"', prompt)
        self.assertIn('"detailed_schema_expectations"', prompt)
        self.assertIn('"family_plan_shape"', prompt)
        self.assertIn("baseline prompt or task vs poisoned prompt or task", prompt)
        self.assertIn("Send a poisoned Telegram message", prompt)
        self.assertIn("Place a hostile Markdown chunk in retrieval content", prompt)
        self.assertIn("Identify potential entry points.", prompt)
        self.assertIn("include concrete baseline and hostile payload ideas", prompt)
        self.assertIn("copyable payload body, prompt string, Markdown fragment", prompt)
        self.assertIn("narrow to one or two realistic entry artifacts", prompt)
        self.assertIn("Expected phenomena must describe the concrete delta", prompt)
        self.assertIn("say where it is collected from", prompt)
        self.assertIn("Avoid empty criteria such as 'observe behavior change'", prompt)

    def test_user_prompt_includes_scenario_specific_hints_for_realistic_agent_case(self) -> None:
        state = _base_state(target_surface="n8n-claw AI Agent")
        state["threat_understanding"] = {
            "threat_summary": "Prompt injection through Telegram, webhooks, and web pages with HTTP tool abuse.",
            "attack_mechanism": "HTTP tool can reach internal Docker services and metadata APIs.",
            "attack_entry_context": {
                "description": "Telegram, webhooks, HTTP Tool, metadata API, Docker services, and Workflow & MCP builder all appear in the attack path."
            },
            "recommended_test_strategy": "Probe Telegram and webhook entry points, then inspect HTTP tool requests and workflow modifications.",
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"scenario_specific_hints"', prompt)
        self.assertIn("Telegram message", prompt)
        self.assertIn("hostile Markdown chunk", prompt)
        self.assertIn("HTTP tool request target trace", prompt)
        self.assertIn("workflow change approval gate", prompt)

    def test_prompt_bundle_routes_tool_hijack_case_to_relevant_examples(self) -> None:
        state = _base_state(
            attack_family="tool_hijack",
            generation_route="tool_hijack",
            target_surface="mcp_agent",
        )
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-03",
                "name": "Insecure Plugin Design",
            },
            "all_taxonomy_codes": [
                "OWASP-LLM-03",
                "OWASP-LLM-06",
            ],
        }
        contract = build_test_package_generation_input(state)

        bundle = build_test_package_prompt_bundle(contract)

        labels = {example["label"] for example in bundle["few_shot_examples"]}
        self.assertIn("tool_hijack_function_call_reference", labels)
        self.assertIn("tool_hijack_mcp_reference", labels)
        self.assertIn("persistent_memory_poisoning_reference", labels)
        self.assertLessEqual(len(labels), 4)

    def test_user_prompt_uses_composite_prompt_mode_when_secondary_taxonomies_exist(self) -> None:
        state = _base_state(target_surface="agent_workflow")
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-01",
                "name": "Prompt Injection",
            },
            "all_taxonomy_codes": [
                "OWASP-LLM-01",
                "OWASP-LLM-02",
                "OWASP-LLM-05",
            ],
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"prompt_mode": "multi_taxonomy_composite"', prompt)

    def test_user_prompt_uses_family_plus_taxonomy_mode_for_single_primary_taxonomy(self) -> None:
        state = _base_state(target_surface="downstream_renderer")
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-02",
                "name": "Insecure Output Handling",
            },
            "all_taxonomy_codes": [
                "OWASP-LLM-02",
            ],
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"prompt_mode": "family_plus_taxonomy"', prompt)

    def test_user_prompt_includes_secondary_taxonomy_playbooks_when_present(self) -> None:
        state = _base_state(target_surface="agent_workflow")
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-01",
                "name": "Prompt Injection",
            },
            "all_taxonomy_codes": [
                "OWASP-LLM-01",
                "OWASP-LLM-02",
                "OWASP-LLM-05",
                "OWASP-LLM-07",
            ],
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"secondary_taxonomy_playbooks"', prompt)
        self.assertIn('"taxonomy_code": "OWASP-LLM-02"', prompt)
        self.assertIn('"taxonomy_code": "OWASP-LLM-05"', prompt)
        self.assertNotIn('"taxonomy_code": "OWASP-LLM-07"', prompt)

    def test_user_prompt_includes_taxonomy_specific_playbook_when_present(self) -> None:
        state = _base_state()
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-07",
                "name": "System Prompt Leakage",
            }
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"focus_name": "system_prompt_leakage"', prompt)
        self.assertIn("debugging-style disclosure request", prompt)
        self.assertIn("hidden-instruction recall request", prompt)

    def test_user_prompt_includes_llm03_taxonomy_playbook_when_present(self) -> None:
        state = _base_state(attack_family="tool_hijack", generation_route="tool_hijack", target_surface="plugin_runtime")
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-03",
                "name": "Insecure Plugin Design",
            }
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"focus_name": "insecure_plugin_or_tool_integration"', prompt)
        self.assertIn("plugin selection", prompt)
        self.assertIn("connector invocation", prompt)

    def test_user_prompt_includes_llm02_taxonomy_playbook_when_present(self) -> None:
        state = _base_state(target_surface="downstream_renderer")
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-02",
                "name": "Insecure Output Handling",
            }
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"focus_name": "insecure_output_handling"', prompt)
        self.assertIn('"primary_comparison"', prompt)
        self.assertIn("automatic rendering of model output", prompt)
        self.assertIn("copy-paste into a shell or admin console", prompt)

    def test_user_prompt_includes_llm04_taxonomy_playbook_when_present(self) -> None:
        state = _base_state(
            attack_family="long_horizon_dialogue",
            generation_route="long_horizon_dialogue",
            target_surface="chat_session",
        )
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-04",
                "name": "Model Denial of Service",
            }
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"focus_name": "model_denial_of_service"', prompt)
        self.assertIn("context-window exhaustion", prompt)
        self.assertIn("token, latency, or cost amplification", prompt)

    def test_user_prompt_includes_llm05_taxonomy_playbook_when_present(self) -> None:
        state = _base_state(
            attack_family="tool_hijack",
            generation_route="tool_hijack",
            target_surface="dependency_or_plugin_supply_chain",
        )
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-05",
                "name": "Supply Chain Vulnerabilities",
            }
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"focus_name": "supply_chain_or_dependency_risk"', prompt)
        self.assertIn("component update or dependency ingestion", prompt)
        self.assertIn("provenance, review, or integrity checks", prompt)

    def test_user_prompt_includes_llm08_taxonomy_playbook_when_present(self) -> None:
        state = _base_state(target_surface="retrieval_context")
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-08",
                "name": "Vector and Embedding Weaknesses",
            }
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"focus_name": "vector_and_embedding_weakness"', prompt)
        self.assertIn("semantic search or retrieval ranking", prompt)
        self.assertIn("poisoned embedding corpus or retrieval chunk", prompt)

    def test_user_prompt_includes_llm09_taxonomy_playbook_when_present(self) -> None:
        state = _base_state(
            attack_family="long_horizon_dialogue",
            generation_route="long_horizon_dialogue",
            target_surface="decision_support",
        )
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-09",
                "name": "Overreliance",
            }
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"focus_name": "overreliance_and_false_authority"', prompt)
        self.assertIn("properly verified model guidance vs plausible but unverified model guidance", prompt)
        self.assertIn("decision support workflow", prompt)

    def test_user_prompt_includes_llm10_taxonomy_playbook_when_present(self) -> None:
        state = _base_state(
            attack_family="tool_hijack",
            generation_route="tool_hijack",
            target_surface="usage_governance",
        )
        state["evidence_and_context"]["taxonomy_context"] = {
            "primary": {
                "code": "OWASP-LLM-10",
                "name": "Unbounded Consumption",
            }
        }
        contract = build_test_package_generation_input(state)

        prompt = build_test_package_user_prompt(contract)

        self.assertIn('"focus_name": "unbounded_consumption"', prompt)
        self.assertIn("normal bounded usage path vs attacker-driven unbounded consumption path", prompt)
        self.assertIn("quota exhaustion path", prompt)


if __name__ == "__main__":
    unittest.main()
