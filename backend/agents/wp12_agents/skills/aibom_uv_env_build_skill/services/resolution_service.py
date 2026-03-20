"""Component normalization and resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable, Iterable, Sequence

from ..schemas.models import AIBOMComponentInput, ResolvedComponent

CandidateProvider = Callable[[AIBOMComponentInput], Sequence[dict[str, Any]]]
ExternalResolver = Callable[[AIBOMComponentInput], ResolvedComponent | dict[str, Any] | None]


@dataclass(slots=True)
class ResolutionSummary:
    """Aggregated resolution output for the executor."""

    resolved_components: list[ResolvedComponent]
    warnings: list[str] = field(default_factory=list)


class ResolutionService:
    """Resolve components without owning task-level input discovery."""

    def __init__(
        self,
        *,
        component_candidate_provider: CandidateProvider | None = None,
        bom_resolution_resolver: ExternalResolver | None = None,
    ) -> None:
        self._component_candidate_provider = component_candidate_provider
        self._bom_resolution_resolver = bom_resolution_resolver

    def resolve(
        self,
        components: Iterable[AIBOMComponentInput],
        *,
        allow_fuzzy_match: bool,
    ) -> ResolutionSummary:
        resolved_components: list[ResolvedComponent] = []
        warnings: list[str] = []
        for component in components:
            resolved = self._resolve_component(component, allow_fuzzy_match=allow_fuzzy_match)
            resolved_components.append(resolved)
            if resolved.status == "unresolved":
                warnings.append(f"Component '{component.name}' could not be resolved")
            elif resolved.status in {"alias", "fuzzy"}:
                warnings.append(
                    f"Component '{component.name}' resolved via {resolved.status} match to "
                    f"'{resolved.resolved_name or component.name}'"
                )
        return ResolutionSummary(resolved_components=resolved_components, warnings=warnings)

    def _resolve_component(
        self,
        component: AIBOMComponentInput,
        *,
        allow_fuzzy_match: bool,
    ) -> ResolvedComponent:
        externally_resolved = self._resolve_external(component)
        if externally_resolved is not None:
            return externally_resolved

        candidates = list(self._component_candidate_provider(component)) if self._component_candidate_provider else []
        if not candidates:
            return ResolvedComponent(
                input_id=component.id,
                input_name=component.name,
                status="unresolved",
                confidence=0.0,
            )

        normalized_input = self._normalize(component.name)
        exact = next(
            (
                candidate
                for candidate in candidates
                if self._normalize(str(candidate.get("name", ""))) == normalized_input
            ),
            None,
        )
        if exact is not None:
            return self._build_resolved(component, exact, "exact", 1.0)

        alias = next(
            (
                candidate
                for candidate in candidates
                if normalized_input in {self._normalize(alias) for alias in candidate.get("aliases", [])}
            ),
            None,
        )
        if alias is not None:
            return self._build_resolved(component, alias, "alias", 0.92)

        if allow_fuzzy_match:
            fuzzy_match = self._find_best_fuzzy_match(normalized_input, candidates)
            if fuzzy_match is not None:
                return self._build_resolved(component, fuzzy_match, "fuzzy", 0.75)

        return ResolvedComponent(
            input_id=component.id,
            input_name=component.name,
            status="unresolved",
            confidence=0.0,
        )

    def _resolve_external(self, component: AIBOMComponentInput) -> ResolvedComponent | None:
        if self._bom_resolution_resolver is None:
            return None
        raw = self._bom_resolution_resolver(component)
        if raw is None:
            return None
        if isinstance(raw, ResolvedComponent):
            return raw
        return ResolvedComponent.model_validate(raw)

    @staticmethod
    def _build_resolved(
        component: AIBOMComponentInput,
        candidate: dict[str, Any],
        status: str,
        confidence: float,
    ) -> ResolvedComponent:
        return ResolvedComponent(
            input_id=component.id,
            input_name=component.name,
            resolved_name=str(candidate.get("name") or component.name),
            resolved_version=candidate.get("version") or component.version or component.version_constraint,
            status=status,
            confidence=confidence,
        )

    @staticmethod
    def _find_best_fuzzy_match(
        normalized_input: str,
        candidates: Sequence[dict[str, Any]],
    ) -> dict[str, Any] | None:
        best_candidate: dict[str, Any] | None = None
        best_score = 0.0
        for candidate in candidates:
            candidate_name = ResolutionService._normalize(str(candidate.get("name", "")))
            score = SequenceMatcher(a=normalized_input, b=candidate_name).ratio()
            if score > best_score:
                best_candidate = candidate
                best_score = score
        if best_candidate is None or best_score < 0.72:
            return None
        return best_candidate

    @staticmethod
    def _normalize(name: str) -> str:
        return " ".join(name.lower().replace("-", " ").replace("_", " ").split())
