from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

from pydantic import SecretStr

from .source_fetch_tools import compute_backoff_delay

LLM_TASK_NAMES = (
    "planning",
    "reflection",
    "standardization",
    "bom_resolution",
    "dedup_merge",
    "dedup_adjudication",
    "coverage",
)

_PROFILE_STATE_LOCK = Lock()
_PROFILE_COOLDOWN_UNTIL: dict[str, float] = {}
_PROFILE_ACTIVE_COUNT: dict[str, int] = {}


@dataclass(frozen=True)
class LlmProfile:
    profile_id: str
    provider: str
    model: str
    base_url: str | None
    api_key: str | None
    enabled: bool
    supports_structured_output: bool
    cost_tier: str
    max_concurrency: int
    cooldown_seconds: float


class LlmInvocationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        error_family: str,
        retry_after_seconds: float = 0.0,
        recommended_tuning_changes: list[str] | None = None,
        attempted_profiles: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_family = error_family
        self.retry_after_seconds = round(max(retry_after_seconds, 0.0), 3)
        self.recommended_tuning_changes = recommended_tuning_changes or []
        self.attempted_profiles = attempted_profiles or []


def _read_bool_env(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _is_dashscope_base_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    lowered = base_url.strip().lower()
    return (
        "dashscope.aliyuncs.com" in lowered
        or "dashscope-intl.aliyuncs.com" in lowered
    )


def _is_qwen_thinking_family(model: str) -> bool:
    lowered = model.strip().lower()
    return lowered.startswith("qwen3") or lowered.startswith("qwen3.5")


def should_disable_thinking_for_structured_output(
    *, model: str, base_url: str | None
) -> bool:
    explicit = _read_bool_env("OPENAI_ENABLE_THINKING")
    if explicit is not None:
        return not explicit
    return _is_dashscope_base_url(base_url) and _is_qwen_thinking_family(model)


def build_structured_chat_openai(
    *,
    model: str,
    temperature: float,
    base_url: str | None,
    api_key: str | None,
) -> Any:
    from langchain_openai import ChatOpenAI

    extra_body: dict[str, Any] | None = None
    explicit_thinking = _read_bool_env("OPENAI_ENABLE_THINKING")

    if explicit_thinking is not None:
        extra_body = {"enable_thinking": explicit_thinking}
    elif should_disable_thinking_for_structured_output(
        model=model,
        base_url=base_url,
    ):
        # DashScope Qwen3/Qwen3.5 mixed-thinking models reject forced
        # `tool_choice` in thinking mode, which LangChain uses for
        # `with_structured_output(..., method="function_calling")`.
        extra_body = {"enable_thinking": False}

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        base_url=base_url,
        api_key=SecretStr(api_key) if api_key else None,
        extra_body=extra_body,
    )


def _read_json_env(name: str) -> Any | None:
    raw = os.getenv(name)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} must be valid JSON.") from exc


def _resolve_value(raw_value: Any, env_key: str | None) -> Any:
    if raw_value is not None:
        return raw_value
    if env_key:
        return os.getenv(env_key)
    return None


def _build_default_profile(
    *,
    default_model: str,
    base_url: str | None,
    api_key: str | None,
) -> LlmProfile:
    return LlmProfile(
        profile_id="default",
        provider="openai_compatible",
        model=default_model,
        base_url=base_url,
        api_key=api_key,
        enabled=True,
        supports_structured_output=True,
        cost_tier="standard",
        max_concurrency=2,
        cooldown_seconds=30.0,
    )


def _load_profiles(
    *,
    default_model: str,
    base_url: str | None,
    api_key: str | None,
) -> dict[str, LlmProfile]:
    payload = _read_json_env("WP11_LLM_PROFILES_JSON")
    if payload is None:
        default_profile = _build_default_profile(
            default_model=default_model,
            base_url=base_url,
            api_key=api_key,
        )
        return {default_profile.profile_id: default_profile}

    rows = payload.get("profiles") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise RuntimeError("WP11_LLM_PROFILES_JSON must be a JSON array or object with profiles.")

    profiles: dict[str, LlmProfile] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError("Each LLM profile must be a JSON object.")
        profile_id = str(row.get("profile_id") or f"profile_{idx + 1}").strip()
        if not profile_id:
            raise RuntimeError("LLM profile_id cannot be empty.")
        profile = LlmProfile(
            profile_id=profile_id,
            provider=str(row.get("provider") or "openai_compatible"),
            model=str(row.get("model") or default_model).strip(),
            base_url=_resolve_value(row.get("base_url"), row.get("base_url_env")),
            api_key=_resolve_value(row.get("api_key"), row.get("api_key_env")),
            enabled=bool(row.get("enabled", True)),
            supports_structured_output=bool(
                row.get("supports_structured_output", True)
            ),
            cost_tier=str(row.get("cost_tier") or "standard"),
            max_concurrency=max(1, int(row.get("max_concurrency", 2))),
            cooldown_seconds=max(1.0, float(row.get("cooldown_seconds", 30.0))),
        )
        profiles[profile.profile_id] = profile

    if not profiles:
        default_profile = _build_default_profile(
            default_model=default_model,
            base_url=base_url,
            api_key=api_key,
        )
        profiles[default_profile.profile_id] = default_profile
    return profiles


def _default_route_presets(default_profile_id: str) -> dict[str, dict[str, list[str]]]:
    return {
        "default": {
            task_name: [default_profile_id] for task_name in LLM_TASK_NAMES
        }
    }


def _load_route_presets(default_profile_id: str) -> dict[str, dict[str, list[str]]]:
    payload = _read_json_env("WP11_LLM_ROUTE_PRESETS_JSON")
    if payload is None:
        return _default_route_presets(default_profile_id)
    if not isinstance(payload, dict):
        raise RuntimeError("WP11_LLM_ROUTE_PRESETS_JSON must be a JSON object.")

    route_presets: dict[str, dict[str, list[str]]] = {}
    for preset_name, preset_payload in payload.items():
        if not isinstance(preset_payload, dict):
            raise RuntimeError("Each route preset must be a JSON object.")
        task_routes: dict[str, list[str]] = {}
        for task_name in LLM_TASK_NAMES:
            route = preset_payload.get(task_name) or [default_profile_id]
            if not isinstance(route, list):
                raise RuntimeError("Each route preset entry must be a JSON array.")
            task_routes[task_name] = [
                str(profile_id).strip()
                for profile_id in route
                if str(profile_id).strip()
            ] or [default_profile_id]
        route_presets[str(preset_name)] = task_routes

    if "default" not in route_presets:
        route_presets["default"] = {
            task_name: [default_profile_id] for task_name in LLM_TASK_NAMES
        }
    return route_presets


def resolve_model_pool(
    *,
    task_name: str,
    default_model: str,
    base_url: str | None,
    api_key: str | None,
    runtime_config: dict[str, Any] | None = None,
) -> tuple[list[LlmProfile], dict[str, Any]]:
    profiles = _load_profiles(
        default_model=default_model,
        base_url=base_url,
        api_key=api_key,
    )
    default_profile_id = next(iter(profiles))
    route_presets = _load_route_presets(default_profile_id)

    runtime_config = runtime_config or {}
    preset_name = str(
        runtime_config.get("llm_route_preset")
        or os.getenv("WP11_LLM_DEFAULT_ROUTE_PRESET")
        or "default"
    )
    preset = route_presets.get(preset_name) or route_presets["default"]
    task_routes = runtime_config.get("llm_task_routes") or {}
    if not isinstance(task_routes, dict):
        task_routes = {}
    configured_route = task_routes.get(task_name) or preset.get(task_name) or [
        default_profile_id
    ]
    selected_profiles: list[LlmProfile] = []
    for profile_id in configured_route:
        profile = profiles.get(str(profile_id))
        if profile and profile.enabled:
            selected_profiles.append(profile)

    if not selected_profiles:
        selected_profiles = [
            profile for profile in profiles.values() if profile.enabled
        ] or [profiles[default_profile_id]]

    return selected_profiles, {
        "selected_preset": preset_name,
        "route_presets": route_presets,
        "profiles": profiles,
    }


def describe_model_pool(
    *,
    default_model: str,
    base_url: str | None,
    api_key: str | None,
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_config = runtime_config or {}
    profiles = _load_profiles(
        default_model=default_model,
        base_url=base_url,
        api_key=api_key,
    )
    default_profile_id = next(iter(profiles))
    route_presets = _load_route_presets(default_profile_id)
    _, route_meta = resolve_model_pool(
        task_name="standardization",
        default_model=default_model,
        base_url=base_url,
        api_key=api_key,
        runtime_config=runtime_config,
    )
    return {
        "selected_preset": route_meta["selected_preset"],
        "profiles": [
            {
                "profile_id": profile.profile_id,
                "provider": profile.provider,
                "model": profile.model,
                "base_url": profile.base_url,
                "enabled": profile.enabled,
                "supports_structured_output": profile.supports_structured_output,
                "cost_tier": profile.cost_tier,
                "max_concurrency": profile.max_concurrency,
                "cooldown_seconds": profile.cooldown_seconds,
                "has_api_key": bool(profile.api_key),
            }
            for profile in profiles.values()
        ],
        "route_presets": route_presets,
    }


def list_available_profile_ids(
    *,
    task_name: str,
    default_model: str,
    base_url: str | None,
    api_key: str | None,
    runtime_config: dict[str, Any] | None = None,
) -> list[str]:
    profiles, _ = resolve_model_pool(
        task_name=task_name,
        default_model=default_model,
        base_url=base_url,
        api_key=api_key,
        runtime_config=runtime_config,
    )
    return [profile.profile_id for profile in profiles if profile.api_key or profile.base_url]


def _extract_status_code(exc: Exception) -> int | None:
    for attr_name in ("status_code", "status"):
        raw = getattr(exc, attr_name, None)
        if isinstance(raw, int):
            return raw
    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int):
            return status_code
    message = str(exc).lower()
    for code in (429, 408, 401, 403, 400, 422, 500, 502, 503, 504):
        if f"{code}" in message:
            return code
    return None


def classify_llm_error(exc: Exception) -> str:
    class_name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    status_code = _extract_status_code(exc)

    if "ratelimit" in class_name or status_code == 429 or "rate limit" in message:
        return "rate_limit"
    if "timeout" in class_name or status_code == 408:
        return "timeout"
    if any(token in class_name for token in ("connection", "apierror", "internalserver")):
        return "transient"
    if status_code in {500, 502, 503, 504}:
        return "transient"
    if status_code in {401, 403} or "api key" in message or "unauthorized" in message:
        return "auth"
    if status_code in {400, 404, 409, 422}:
        return "invalid_request"
    if "tool_choice" in message or "structured output" in message:
        return "invalid_request"
    return "fatal"


def _is_retryable_family(error_family: str) -> bool:
    return error_family in {"rate_limit", "timeout", "transient"}


def _cooldown_remaining_seconds(profile_id: str) -> float:
    with _PROFILE_STATE_LOCK:
        until = _PROFILE_COOLDOWN_UNTIL.get(profile_id, 0.0)
    return max(0.0, until - time.time())


def _mark_profile_cooldown(profile_id: str, cooldown_seconds: float) -> None:
    with _PROFILE_STATE_LOCK:
        _PROFILE_COOLDOWN_UNTIL[profile_id] = max(
            _PROFILE_COOLDOWN_UNTIL.get(profile_id, 0.0),
            time.time() + cooldown_seconds,
        )


def _try_acquire_profile_slot(profile: LlmProfile) -> bool:
    with _PROFILE_STATE_LOCK:
        active = _PROFILE_ACTIVE_COUNT.get(profile.profile_id, 0)
        if active >= max(1, profile.max_concurrency):
            return False
        _PROFILE_ACTIVE_COUNT[profile.profile_id] = active + 1
        return True


def _release_profile_slot(profile_id: str) -> None:
    with _PROFILE_STATE_LOCK:
        active = _PROFILE_ACTIVE_COUNT.get(profile_id, 0)
        if active <= 1:
            _PROFILE_ACTIVE_COUNT.pop(profile_id, None)
            return
        _PROFILE_ACTIVE_COUNT[profile_id] = active - 1


def _acquire_profile_slot_with_wait(
    profile: LlmProfile,
    *,
    max_wait_seconds: float,
    poll_interval_seconds: float = 0.25,
) -> float | None:
    if _try_acquire_profile_slot(profile):
        return 0.0
    if max_wait_seconds <= 0:
        return None

    deadline = time.monotonic() + max_wait_seconds
    waited_seconds = 0.0
    while time.monotonic() < deadline:
        sleep_seconds = min(
            poll_interval_seconds,
            max(0.0, deadline - time.monotonic()),
        )
        if sleep_seconds <= 0:
            break
        time.sleep(sleep_seconds)
        waited_seconds += sleep_seconds
        if _try_acquire_profile_slot(profile):
            return round(waited_seconds, 3)
    return None


def invoke_structured_with_model_pool(
    *,
    task_name: str,
    prompt: Any,
    schema: type[Any],
    payload: dict[str, Any],
    default_model: str,
    temperature: float,
    base_url: str | None,
    api_key: str | None,
    runtime_config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime_config = runtime_config or {}
    retry_attempts = int(runtime_config.get("llm_retry_attempts", 3) or 3)
    backoff_base = float(runtime_config.get("llm_backoff_base_seconds", 2.0) or 2.0)
    backoff_max = float(runtime_config.get("llm_backoff_max_seconds", 30.0) or 30.0)
    short_wait_threshold = float(
        runtime_config.get("llm_short_wait_threshold_seconds", 60.0) or 60.0
    )
    profiles, route_meta = resolve_model_pool(
        task_name=task_name,
        default_model=default_model,
        base_url=base_url,
        api_key=api_key,
        runtime_config=runtime_config,
    )
    errors: list[str] = []
    total_wait_seconds = 0.0
    attempted_profiles: list[str] = []
    suggested_retry_after = 0.0

    for profile in profiles:
        if not profile.supports_structured_output:
            errors.append(f"{profile.profile_id}: structured output not supported")
            continue

        cooldown_remaining = _cooldown_remaining_seconds(profile.profile_id)
        if cooldown_remaining > 0:
            suggested_retry_after = max(suggested_retry_after, cooldown_remaining)
            errors.append(
                f"{profile.profile_id}: cooling down for {cooldown_remaining:.1f}s"
            )
            continue
        slot_waited_seconds = _acquire_profile_slot_with_wait(
            profile,
            max_wait_seconds=short_wait_threshold,
        )
        if slot_waited_seconds is None:
            suggested_retry_after = max(suggested_retry_after, short_wait_threshold)
            errors.append(
                f"{profile.profile_id}: max_concurrency {profile.max_concurrency} reached"
            )
            continue
        total_wait_seconds += slot_waited_seconds

        attempted_profiles.append(profile.profile_id)
        try:
            for attempt in range(1, retry_attempts + 1):
                try:
                    llm = build_structured_chat_openai(
                        model=profile.model,
                        temperature=temperature,
                        base_url=profile.base_url,
                        api_key=profile.api_key,
                    )
                    structured_llm = llm.with_structured_output(
                        schema, method="function_calling"
                    )
                    chain = prompt | structured_llm
                    result = chain.invoke(payload)
                    if isinstance(result, schema):
                        validated = result.model_dump(mode="python")
                    else:
                        validated = schema.model_validate(result).model_dump(
                            mode="python"
                        )
                    return validated, {
                        "profile_id": profile.profile_id,
                        "provider": profile.provider,
                        "llm_model": profile.model,
                        "base_url": profile.base_url,
                        "attempts": attempt,
                        "wait_seconds": round(total_wait_seconds, 3),
                        "selected_preset": route_meta["selected_preset"],
                        "attempted_profiles": attempted_profiles,
                    }
                except Exception as exc:
                    error_family = classify_llm_error(exc)
                    message = (
                        f"{profile.profile_id}:{error_family}:{type(exc).__name__}:"
                        f"{str(exc)[:220]}"
                    )
                    if _is_retryable_family(error_family) and attempt < retry_attempts:
                        wait_seconds = min(
                            backoff_max,
                            compute_backoff_delay(backoff_base, attempt),
                        )
                        if wait_seconds <= short_wait_threshold:
                            total_wait_seconds += wait_seconds
                            time.sleep(wait_seconds)
                            continue
                        _mark_profile_cooldown(
                            profile.profile_id,
                            max(profile.cooldown_seconds, wait_seconds),
                        )
                        suggested_retry_after = max(
                            suggested_retry_after,
                            wait_seconds,
                        )
                        errors.append(
                            f"{message}:deferred_wait={round(wait_seconds, 3)}s"
                        )
                        break

                    if error_family in {"rate_limit", "timeout", "transient"}:
                        cooldown_seconds = max(
                            profile.cooldown_seconds,
                            min(backoff_max, max(backoff_base, short_wait_threshold)),
                        )
                        _mark_profile_cooldown(
                            profile.profile_id,
                            cooldown_seconds,
                        )
                        suggested_retry_after = max(
                            suggested_retry_after,
                            cooldown_seconds,
                        )
                    errors.append(message)
                    break
        finally:
            _release_profile_slot(profile.profile_id)

    recommended_changes = [
        "lower standardization_max_concurrency",
        "reduce source max_results",
        "switch llm_route_preset or llm_task_routes",
    ]
    retry_after = max(
        total_wait_seconds,
        suggested_retry_after,
        max(
            (_cooldown_remaining_seconds(profile.profile_id) for profile in profiles),
            default=0.0,
        ),
    )
    raise LlmInvocationError(
        "All configured LLM profiles were exhausted or unavailable for structured output. "
        + " | ".join(errors[-6:]),
        error_family="pool_exhausted",
        retry_after_seconds=retry_after,
        recommended_tuning_changes=recommended_changes,
        attempted_profiles=attempted_profiles,
    )
