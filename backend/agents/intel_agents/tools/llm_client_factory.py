from __future__ import annotations

import os
from typing import Any

from pydantic import SecretStr


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
