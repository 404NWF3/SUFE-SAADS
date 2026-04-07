from __future__ import annotations

import unittest
from unittest.mock import patch

from saads_wp12.llm.client import LlmNotConfiguredError
from saads_wp12.reporting.llm_plan_writer import (
    build_plan_writer_system_prompt,
    build_plan_writer_user_prompt,
    generate_plan_markdown,
)
from tests.test_test_package_generation import _base_state


class LlmPlanWriterTest(unittest.TestCase):
    def test_system_prompt_demands_executable_detail(self) -> None:
        prompt = build_plan_writer_system_prompt()
        self.assertIn("Python", prompt)
        self.assertIn("Markdown", prompt)
        self.assertIn("6", prompt)

    def test_user_prompt_contains_writer_hints_and_new_intermediate_types(self) -> None:
        prompt = build_plan_writer_user_prompt(_base_state())
        self.assertIn("writer_hints", prompt)
        self.assertIn("baseline_examples", prompt)
        self.assertIn("hostile_examples", prompt)
        self.assertIn("target_surface_type", prompt)
        self.assertIn("attack_mechanism_type", prompt)

    @patch("saads_wp12.reporting.llm_plan_writer.get_config")
    @patch("saads_wp12.reporting.llm_plan_writer.generate_text_response")
    def test_generate_plan_markdown_falls_back_when_llm_output_is_not_detailed_enough(
        self,
        mock_generate,
        mock_get_config,
    ) -> None:
        mock_get_config.return_value.llm_enabled = True
        mock_generate.return_value = "# short\n\nnot enough detail"

        result = generate_plan_markdown(_base_state())

        self.assertIn("```python", result)
        self.assertIn("# ", result)

    @patch("saads_wp12.reporting.llm_plan_writer.get_config")
    @patch("saads_wp12.reporting.llm_plan_writer.generate_text_response")
    def test_generate_plan_markdown_falls_back_to_renderer_on_error(self, mock_generate, mock_get_config) -> None:
        mock_get_config.return_value.llm_enabled = True
        mock_generate.side_effect = LlmNotConfiguredError("missing key")

        result = generate_plan_markdown(_base_state())

        self.assertIn("```python", result)
        self.assertIn("# ", result)


if __name__ == "__main__":
    unittest.main()
