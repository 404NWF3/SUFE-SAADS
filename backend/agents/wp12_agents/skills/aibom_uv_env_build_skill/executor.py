"""Unified entrypoint for the AIBOM uv environment build skill."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schemas.models import AIBOMEnvBuildRequest, AIBOMEnvBuildResult
from .services import BlueprintService, ProvisionService, ResolutionService, ValidateService


class AIBOMUvEnvBuildSkill:
    """Coordinate resolution, blueprinting, provisioning, and validation."""

    def __init__(
        self,
        *,
        component_candidate_provider=None,
        bom_resolution_resolver=None,
        seed_asset_loader=None,
        command_runner=None,
    ) -> None:
        self._seed_asset_loader = seed_asset_loader
        self._resolution_service = ResolutionService(
            component_candidate_provider=component_candidate_provider,
            bom_resolution_resolver=bom_resolution_resolver,
        )
        self._blueprint_service = BlueprintService()
        self._provision_service = ProvisionService(command_runner=command_runner)
        self._validate_service = ValidateService(command_runner=command_runner)

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            build_request = AIBOMEnvBuildRequest.model_validate(request)
        except ValidationError as exc:
            fallback_workspace = str(Path(request.get("workspace_root", ".")))
            return AIBOMEnvBuildResult(
                environment_id="",
                build_mode=str(request.get("target_mode", "uv_build")),
                status="failed",
                workspace_path=fallback_workspace,
                entry_command="",
                errors=[str(exc)],
            ).model_dump()

        warnings: list[str] = []
        errors: list[str] = []

        if self._seed_asset_loader and build_request.seed_asset_ids:
            warnings.extend(self._validate_seed_assets(build_request.seed_asset_ids))

        resolution_summary = self._resolution_service.resolve(
            build_request.aibom_components,
            allow_fuzzy_match=build_request.allow_fuzzy_match,
        )
        warnings.extend(resolution_summary.warnings)

        blueprint = self._blueprint_service.build(
            build_request,
            resolved_components=resolution_summary.resolved_components,
        )
        warnings.extend(blueprint.warnings)

        artifacts, provision_warnings, provision_errors = self._provision_service.provision(
            build_request,
            blueprint,
            resolved_dependencies=blueprint.dependencies,
        )
        warnings.extend(provision_warnings)
        errors.extend(provision_errors)

        if not errors:
            validation_summary = self._validate_service.validate(build_request, blueprint)
            warnings.extend(validation_summary.warnings)
            errors.extend(validation_summary.errors)

        status = self._derive_status(
            build_mode=blueprint.build_mode,
            warnings=warnings,
            errors=errors,
            resolved_statuses=[component.status for component in resolution_summary.resolved_components],
        )

        result = AIBOMEnvBuildResult(
            environment_id=blueprint.environment_id,
            build_mode=blueprint.build_mode,
            status=status,
            workspace_path=str(blueprint.workspace_path),
            entry_command="" if status == "failed" else blueprint.entry_command,
            resolved_components=resolution_summary.resolved_components,
            env_artifacts=artifacts,
            warnings=warnings,
            errors=errors,
        )
        return result.model_dump()

    def _validate_seed_assets(self, seed_asset_ids: list[str]) -> list[str]:
        loaded_assets = self._seed_asset_loader(seed_asset_ids)
        loaded_ids = {str(item.get("id")) for item in loaded_assets}
        missing = [seed_id for seed_id in seed_asset_ids if seed_id not in loaded_ids]
        if not missing:
            return []
        return [f"Seed assets missing from auxiliary loader: {', '.join(missing)}"]

    @staticmethod
    def _derive_status(
        *,
        build_mode: str,
        warnings: list[str],
        errors: list[str],
        resolved_statuses: list[str],
    ) -> str:
        if errors:
            return "failed"
        if build_mode == "blueprint_only":
            return "partial"
        if "unresolved" in resolved_statuses:
            return "partial"
        if warnings:
            return "partial"
        return "ready"


def run_aibom_uv_env_build_skill(
    request: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Stable function entrypoint used by agent two."""

    return AIBOMUvEnvBuildSkill(**kwargs).run(request)
