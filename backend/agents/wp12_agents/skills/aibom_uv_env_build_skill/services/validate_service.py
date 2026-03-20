"""Validation and healthcheck helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..schemas.models import AIBOMEnvBuildRequest
from .blueprint_service import Blueprint

CommandRunner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


@dataclass(slots=True)
class ValidationSummary:
    """Validation result consumed by the executor."""

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ValidateService:
    """Run basic health checks without taking over orchestration."""

    def __init__(self, *, command_runner: CommandRunner | None = None) -> None:
        self._command_runner = command_runner or self._default_command_runner

    def validate(self, request: AIBOMEnvBuildRequest, blueprint: Blueprint) -> ValidationSummary:
        warnings: list[str] = []
        errors: list[str] = []

        if blueprint.build_mode == "blueprint_only":
            warnings.append("Blueprint-only mode skipped healthcheck execution")
            return ValidationSummary(warnings=warnings, errors=errors)

        if request.target_mode == "uv_build_and_seed" and not request.seed_asset_ids:
            warnings.append("Seed execution requested but no seed assets were provided")

        result = self._command_runner(["uv", "run", "python", "healthcheck.py"], blueprint.workspace_path)
        if result.returncode != 0:
            warnings.append(
                "Healthcheck failed after environment provisioning: "
                f"{(result.stderr or result.stdout or 'no output').strip()}"
            )
        return ValidationSummary(warnings=warnings, errors=errors)

    @staticmethod
    def _default_command_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
