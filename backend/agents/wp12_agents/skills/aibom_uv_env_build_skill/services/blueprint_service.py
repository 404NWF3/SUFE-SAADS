"""Workspace blueprint generation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..schemas.models import AIBOMEnvBuildRequest, EnvArtifact, ResolvedComponent


@dataclass(slots=True)
class Blueprint:
    """Provision plan shared across services."""

    environment_id: str
    build_mode: str
    workspace_path: Path
    entry_command: str
    dependencies: list[str]
    artifacts: list[EnvArtifact]
    warnings: list[str] = field(default_factory=list)


class BlueprintService:
    """Transform a request and resolution result into a concrete workspace plan."""

    def build(
        self,
        request: AIBOMEnvBuildRequest,
        *,
        resolved_components: list[ResolvedComponent],
    ) -> Blueprint:
        build_mode = request.target_mode
        warnings: list[str] = []
        if build_mode == "uv_build_and_seed" and not request.seed_asset_ids:
            build_mode = "uv_build"
            warnings.append("seed_asset_ids is empty; degraded target_mode from uv_build_and_seed to uv_build")

        environment_id = self._make_environment_id(request)
        workspace_path = Path(request.workspace_root).expanduser().resolve() / environment_id
        artifacts = [
            EnvArtifact(kind="pyproject", path=str(workspace_path / "pyproject.toml"), description="uv project file"),
            EnvArtifact(kind="script", path=str(workspace_path / "run_attack.py"), description="default runner"),
            EnvArtifact(kind="healthcheck", path=str(workspace_path / "healthcheck.py"), description="basic healthcheck"),
        ]
        if request.seed_asset_ids:
            artifacts.append(
                EnvArtifact(
                    kind="seed_manifest",
                    path=str(workspace_path / "seed_assets.json"),
                    description="seed asset manifest for downstream mounting",
                )
            )

        return Blueprint(
            environment_id=environment_id,
            build_mode=build_mode,
            workspace_path=workspace_path,
            entry_command="" if build_mode == "blueprint_only" else "uv run python run_attack.py",
            dependencies=self._build_dependencies(resolved_components),
            artifacts=artifacts,
            warnings=warnings,
        )

    @staticmethod
    def _make_environment_id(request: AIBOMEnvBuildRequest) -> str:
        base = f"{request.tenant_id}:{request.scenario_id}:{request.attack_id}:{request.python_version}"
        digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
        slug = BlueprintService._slugify(request.attack_id)[:32] or "attack"
        return f"env_{slug}_{digest}"

    @staticmethod
    def _slugify(value: str) -> str:
        lowered = value.strip().lower()
        lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
        return lowered.strip("_")

    @staticmethod
    def _build_dependencies(resolved_components: list[ResolvedComponent]) -> list[str]:
        dependencies: list[str] = []
        seen: set[str] = set()
        for component in resolved_components:
            if component.status == "unresolved" or not component.resolved_name:
                continue
            if component.resolved_version and not any(op in component.resolved_version for op in "<>~=!"):
                dependency = f"{component.resolved_name}=={component.resolved_version}"
            elif component.resolved_version:
                dependency = f"{component.resolved_name}{component.resolved_version}"
            else:
                dependency = component.resolved_name
            if dependency not in seen:
                dependencies.append(dependency)
                seen.add(dependency)
        return dependencies
