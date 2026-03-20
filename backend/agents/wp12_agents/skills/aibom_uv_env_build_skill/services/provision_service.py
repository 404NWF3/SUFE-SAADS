"""Filesystem and uv provisioning logic."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from string import Template
from typing import Callable

from ..schemas.models import AIBOMEnvBuildRequest, EnvArtifact
from .blueprint_service import Blueprint

CommandRunner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


class ProvisionService:
    """Create the workspace and execute uv commands when requested."""

    def __init__(self, *, command_runner: CommandRunner | None = None) -> None:
        self._command_runner = command_runner or self._default_command_runner
        self._template_dir = Path(__file__).resolve().parent.parent / "templates"

    def provision(
        self,
        request: AIBOMEnvBuildRequest,
        blueprint: Blueprint,
        *,
        resolved_dependencies: list[str],
    ) -> tuple[list[EnvArtifact], list[str], list[str]]:
        warnings: list[str] = []
        errors: list[str] = []

        blueprint.workspace_path.mkdir(parents=True, exist_ok=True)
        self._write_pyproject(request, blueprint.workspace_path, resolved_dependencies)
        self._write_script(
            "run_attack_template.py.j2",
            blueprint.workspace_path / "run_attack.py",
            environment_id=blueprint.environment_id,
            attack_id=request.attack_id,
            tenant_id=request.tenant_id,
            scenario_id=request.scenario_id,
        )
        self._write_script(
            "healthcheck_template.py.j2",
            blueprint.workspace_path / "healthcheck.py",
            environment_id=blueprint.environment_id,
            python_version=request.python_version,
        )
        if request.seed_asset_ids:
            seed_manifest_path = blueprint.workspace_path / "seed_assets.json"
            seed_manifest_path.write_text(
                json.dumps({"seed_asset_ids": request.seed_asset_ids}, indent=2),
                encoding="utf-8",
            )

        if blueprint.build_mode == "blueprint_only":
            warnings.append("Blueprint generated without executing uv commands")
            return blueprint.artifacts, warnings, errors

        commands = [
            ["uv", "venv", "--python", request.python_version, ".venv"],
            ["uv", "sync"],
        ]
        for command in commands:
            result = self._command_runner(command, blueprint.workspace_path)
            if result.returncode != 0:
                errors.append(self._format_command_error(command, result.stderr))
                return blueprint.artifacts, warnings, errors
        return blueprint.artifacts, warnings, errors

    @staticmethod
    def _default_command_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

    def _write_pyproject(
        self,
        request: AIBOMEnvBuildRequest,
        workspace_path: Path,
        dependencies: list[str],
    ) -> None:
        template = Template((self._template_dir / "pyproject_template.toml.j2").read_text(encoding="utf-8"))
        dependency_lines = ",\n".join(f'    "{dependency}"' for dependency in dependencies)
        content = template.safe_substitute(
            project_name=workspace_path.name.replace("_", "-"),
            python_version=request.python_version,
            dependency_block=dependency_lines,
        )
        (workspace_path / "pyproject.toml").write_text(content, encoding="utf-8")

    def _write_script(self, template_name: str, destination: Path, **kwargs: str) -> None:
        template = Template((self._template_dir / template_name).read_text(encoding="utf-8"))
        destination.write_text(template.safe_substitute(**kwargs), encoding="utf-8")

    @staticmethod
    def _format_command_error(command: list[str], stderr: str) -> str:
        joined_command = " ".join(command)
        stderr = stderr.strip() or "no stderr captured"
        return f"Command '{joined_command}' failed: {stderr}"
