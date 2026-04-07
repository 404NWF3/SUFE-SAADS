from __future__ import annotations

import unittest

from saads_wp12.engines.test_package_generation import RuleBasedTestPackageGenerationEngine
from saads_wp12.reporting.test_plan_renderer import render_test_plan_markdown
from tests.test_test_package_generation import _base_state


class TestPlanRendererTest(unittest.TestCase):
    def test_render_test_plan_markdown_for_supported_case(self) -> None:
        state = _base_state()
        result = RuleBasedTestPackageGenerationEngine().run(state)
        result.update(
            {
                "attack_id": state["attack_id"],
                "attack_family": state["attack_family"],
                "supported_family": state["scope_assessment"]["supported_family"],
                "target_surface": state["target_surface"],
                "scope_reason": state["scope_assessment"]["scope_reason"],
                "execution_eligibility": result["test_package"]["execution_plan"]["execution_eligibility"],
                "test_readiness": state["execution_assessment"]["test_readiness"],
                "threat_understanding": state["threat_understanding"],
                "known_gaps": state["uncertainty_report"]["known_gaps"],
            }
        )

        rendered = render_test_plan_markdown(result)

        self.assertIn("## 二、中文测试方案", rendered)
        self.assertIn("### 5. 示例输入与攻击载荷", rendered)
        self.assertIn("文言文越狱片段", rendered)
        self.assertIn("角色扮演与修辞增强片段", rendered)
        self.assertIn("验证脚本：自动写入基线 README、恶意 README", rendered)
        self.assertIn("```python", rendered)
        self.assertIn("### 6. 详细操作步骤", rendered)
        self.assertIn("步骤 1：准备隔离环境与观测点", rendered)
        self.assertIn("`.env`", rendered)
        self.assertNotIn("English Reference", rendered)

    def test_render_test_plan_markdown_for_triage_case(self) -> None:
        state = _base_state(
            attack_id="attack-triage-001",
            attack_family="unsupported",
            target_surface="unsupported_target",
        )
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
        result.update(
            {
                "attack_id": state["attack_id"],
                "attack_family": "unsupported",
                "supported_family": "unsupported",
                "target_surface": "unsupported_target",
                "scope_reason": "Out of current scope.",
                "execution_eligibility": "blocked_out_of_scope",
                "test_readiness": "low",
                "threat_understanding": {
                    "threat_summary": "Generic vulnerability, triage only.",
                },
                "known_gaps": ["Out of current WP1-2 scope."],
            }
        )

        rendered = render_test_plan_markdown(result)

        self.assertIn("当前样本不建议直接生成攻击载荷", rendered)
        self.assertIn("### 6. 详细操作步骤", rendered)
        self.assertIn("阶段 1：确认该漏洞与 LLM 系统是否存在资产或依赖关系", rendered)
        self.assertIn("一旦发现与提示词、记忆、检索、工具调用或代理工作流相关的证据", rendered)


if __name__ == "__main__":
    unittest.main()
