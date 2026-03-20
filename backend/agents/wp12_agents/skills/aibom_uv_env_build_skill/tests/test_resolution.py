from backend.agents.wp12_agents.skills.aibom_uv_env_build_skill.schemas.models import (
    AIBOMComponentInput,
)
from backend.agents.wp12_agents.skills.aibom_uv_env_build_skill.services.resolution_service import (
    ResolutionService,
)


def test_resolution_service_prefers_alias_match():
    def provider(component):
        return [
            {"name": "langchain", "version": "0.1.20", "aliases": ["lang-chain", "lc"]},
        ]

    service = ResolutionService(component_candidate_provider=provider)
    summary = service.resolve(
        [
            AIBOMComponentInput(
                id="comp-1",
                name="lang-chain",
                version_constraint=">=0.1,<0.2",
            )
        ],
        allow_fuzzy_match=True,
    )

    resolved = summary.resolved_components[0]
    assert resolved.status == "alias"
    assert resolved.resolved_name == "langchain"
    assert summary.warnings


def test_resolution_service_marks_unresolved_without_candidates():
    service = ResolutionService(component_candidate_provider=lambda component: [])
    summary = service.resolve(
        [
            AIBOMComponentInput(
                id="comp-2",
                name="unknown-lib",
                version_constraint=">=1.0",
            )
        ],
        allow_fuzzy_match=False,
    )

    resolved = summary.resolved_components[0]
    assert resolved.status == "unresolved"
    assert summary.warnings
