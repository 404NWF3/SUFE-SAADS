"""LangChain adapter for the AIBOM uv build skill."""

from __future__ import annotations

from typing import Any

from ..executor import AIBOMUvEnvBuildSkill


def make_langchain_tool(**skill_kwargs: Any):
    """Return a StructuredTool when LangChain is available."""

    from langchain_core.tools import StructuredTool

    skill = AIBOMUvEnvBuildSkill(**skill_kwargs)
    return StructuredTool.from_function(
        func=skill.run,
        name="run_aibom_uv_env_build_skill",
        description=(
            "Build or blueprint a local uv-based Python environment from a structured "
            "AIBOMEnvBuildRequest and return an AIBOMEnvBuildResult."
        ),
    )
