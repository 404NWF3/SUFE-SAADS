import subprocess

from backend.agents.wp12_agents.skills.aibom_uv_env_build_skill.executor import (
    AIBOMUvEnvBuildSkill,
    run_aibom_uv_env_build_skill,
)


def test_executor_degrades_seed_mode_and_returns_partial(tmp_path):
    def runner(command, cwd):
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    result = run_aibom_uv_env_build_skill(
        {
            "tenant_id": "tenant-demo",
            "scenario_id": "scenario-001",
            "attack_id": "attack-123",
            "target_mode": "uv_build_and_seed",
            "python_version": "3.11",
            "workspace_root": str(tmp_path),
            "aibom_components": [
                {
                    "id": "comp-1",
                    "name": "langchain",
                    "version_constraint": ">=0.1,<0.2",
                    "component_type": "framework",
                }
            ],
            "seed_asset_ids": [],
            "allow_fuzzy_match": True,
        },
        command_runner=runner,
    )

    assert result["build_mode"] == "uv_build"
    assert result["status"] == "partial"
    assert "degraded" in " ".join(result["warnings"]).lower()
    assert result["entry_command"] == "uv run python run_attack.py"


def test_executor_marks_failed_on_validation_error(tmp_path):
    result = AIBOMUvEnvBuildSkill().run(
        {
            "tenant_id": "tenant-demo",
            "scenario_id": "scenario-001",
            "attack_id": "attack-123",
            "workspace_root": str(tmp_path),
            "aibom_components": [],
        }
    )

    assert result["status"] == "failed"
    assert result["errors"]
