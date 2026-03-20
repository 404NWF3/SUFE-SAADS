import subprocess

from backend.agents.wp12_agents.skills.aibom_uv_env_build_skill.schemas.models import (
    AIBOMComponentInput,
    AIBOMEnvBuildRequest,
    ResolvedComponent,
)
from backend.agents.wp12_agents.skills.aibom_uv_env_build_skill.services.blueprint_service import (
    BlueprintService,
)
from backend.agents.wp12_agents.skills.aibom_uv_env_build_skill.services.provision_service import (
    ProvisionService,
)


def test_provision_service_writes_workspace_files(tmp_path):
    commands = []

    def runner(command, cwd):
        commands.append((command, cwd))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    request = AIBOMEnvBuildRequest(
        tenant_id="tenant",
        scenario_id="scenario",
        attack_id="attack-1",
        workspace_root=str(tmp_path),
        aibom_components=[AIBOMComponentInput(id="c1", name="langchain")],
    )
    blueprint = BlueprintService().build(
        request,
        resolved_components=[
            ResolvedComponent(
                input_id="c1",
                input_name="langchain",
                resolved_name="langchain",
                resolved_version="0.1.20",
                status="exact",
                confidence=1.0,
            )
        ],
    )

    artifacts, warnings, errors = ProvisionService(command_runner=runner).provision(
        request,
        blueprint,
        resolved_dependencies=blueprint.dependencies,
    )

    assert not warnings
    assert not errors
    assert (blueprint.workspace_path / "pyproject.toml").exists()
    assert (blueprint.workspace_path / "run_attack.py").exists()
    assert (blueprint.workspace_path / "healthcheck.py").exists()
    assert commands[0][0][:2] == ["uv", "venv"]
    assert len(artifacts) >= 3
