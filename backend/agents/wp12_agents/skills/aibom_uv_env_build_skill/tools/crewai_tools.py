"""CrewAI adapter for the AIBOM uv build skill."""

from __future__ import annotations

from typing import Any

from ..executor import AIBOMUvEnvBuildSkill


class CrewAIAIBOMUvEnvBuildTool:
    """Minimal CrewAI-compatible tool wrapper."""

    name = "run_aibom_uv_env_build_skill"
    description = (
        "Build or blueprint a uv Python workspace from a structured AIBOMEnvBuildRequest."
    )

    def __init__(self, **skill_kwargs: Any) -> None:
        self._skill = AIBOMUvEnvBuildSkill(**skill_kwargs)

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        return self._skill.run(request)
