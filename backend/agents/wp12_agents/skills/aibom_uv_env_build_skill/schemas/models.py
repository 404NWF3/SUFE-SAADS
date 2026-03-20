"""Pydantic contracts for the AIBOM uv build skill."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AIBOMComponentInput(BaseModel):
    """Structured component input provided by agent two."""

    id: str = Field(..., description="Component identifier from upstream state")
    name: str = Field(..., min_length=1, description="Raw component name")
    version_constraint: str | None = Field(
        default=None,
        description="Version constraint passed from upstream context",
    )
    vendor: str | None = None
    version: str | None = None
    component_type: str | None = None

    @field_validator("id", "name")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class AIBOMEnvBuildRequest(BaseModel):
    """Contract consumed by the skill bundle."""

    tenant_id: str
    scenario_id: str
    attack_id: str
    target_mode: Literal["blueprint_only", "uv_build", "uv_build_and_seed"] = "uv_build"
    python_version: str = "3.11"
    workspace_root: str
    aibom_components: list[AIBOMComponentInput]
    seed_asset_ids: list[str] = Field(default_factory=list)
    allow_fuzzy_match: bool = True

    @field_validator("tenant_id", "scenario_id", "attack_id", "python_version", "workspace_root")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def _validate_components(self) -> "AIBOMEnvBuildRequest":
        if not self.aibom_components:
            raise ValueError("aibom_components must contain at least one component")
        return self


class ResolvedComponent(BaseModel):
    """Resolution record returned to agent two."""

    input_id: str
    input_name: str
    resolved_name: str | None = None
    resolved_version: str | None = None
    status: Literal["exact", "alias", "fuzzy", "unresolved"]
    confidence: float = 0.0


class EnvArtifact(BaseModel):
    """Concrete file artifact written to the workspace."""

    kind: str
    path: str
    description: str | None = None


class AIBOMEnvBuildResult(BaseModel):
    """Structured result returned by the skill."""

    environment_id: str
    env_version: str = "v1"
    build_mode: str
    status: Literal["ready", "partial", "failed"]
    workspace_path: str
    entry_command: str
    resolved_components: list[ResolvedComponent] = Field(default_factory=list)
    env_artifacts: list[EnvArtifact] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
