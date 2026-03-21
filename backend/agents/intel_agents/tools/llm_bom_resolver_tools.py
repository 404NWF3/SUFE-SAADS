from __future__ import annotations

import os
from typing import Any, Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field

from .llm_client_factory import (
    invoke_structured_with_model_pool,
    list_available_profile_ids,
)


# ---------------------------------------------------------------------------
# Prompt version -- bump when system message or schema changes meaningfully
# ---------------------------------------------------------------------------
PROMPT_VERSION = "v1.0-llm-bom-resolver"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Structured output sub-models (LLM returns these)
# ---------------------------------------------------------------------------


class LlmSelectedComponent(_StrictModel):
    """The component selected by the LLM from the candidate list."""

    component_code: str | None = None
    component_name: str = Field(min_length=1)
    component_layer: Literal[
        "vendor_platform",
        "model_family",
        "framework",
        "plugin",
        "runtime",
        "vector_stack",
        "unknown",
    ] = "unknown"
    vendor_name: str | None = None


class LlmBomResolutionResult(_StrictModel):
    """Full structured output schema for LLM BOM resolution.

    The LLM receives a bom_mention, attack context, and top-k candidates from
    the retrieval layer.  It must select the best candidate, determine the
    version constraint, and provide evidence and reasoning.

    If no candidate is a good match, set ``decision`` to ``"no_match"`` and
    ``selected_component`` to null.  If confidence is low, set ``decision``
    to ``"review_queue"``.
    """

    selected_component: LlmSelectedComponent | None = None
    version_constraint_raw: str | None = None
    normalized_version_constraint: str | None = None
    decision: Literal["accept", "review_queue", "no_match"] = "review_queue"
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_quotes: list[str] = Field(default_factory=list)
    reasoning_summary: str = Field(min_length=1)
    candidate_ranking: list[str] = Field(
        default_factory=list,
        description="Ordered list of candidate component_codes considered, best first.",
    )


# ---------------------------------------------------------------------------
# System prompt -- v1.0 LLM BOM resolver
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是 AI/ML 安全 BOM (Bill of Materials) 解析专家。你的任务是将攻击报告中提到的\
软件/模型/框架/平台名称映射到标准化的组件目录。

## 核心原则
1. **基于证据选择**：从候选列表中选择最匹配的组件，必须基于原文中的证据。
2. **不要猜测**：如果候选列表中没有合适的组件，decision 设为 "no_match"。
3. **版本约束**：如果原文提到了版本信息，提取并标准化版本约束。
4. **component_layer 准确性**：根据候选组件信息和原文上下文，确认 component_layer。
5. **置信度**：
   - >= 0.85: 明确的精确或别名匹配，decision 设为 "accept"
   - 0.60 ~ 0.85: 有合理匹配但需人工确认，decision 设为 "review_queue"
   - < 0.60 或无合适候选: decision 设为 "no_match"
6. **evidence_quotes 必须提供**：引用原文中支持你选择的文本片段。

## 候选选择策略
- 如果 mention 名称和候选名称完全一致或是已知别名 → 高置信度 accept
- 如果 mention 含有厂商信息，优先选择厂商匹配的候选
- 如果多个候选评分接近（差距 < 0.05），选择 review_queue
- 如果 mention 是模糊名称（如 "AI agent", "LLM framework"），选择 review_queue 或 no_match
- trigram/embedding 匹配需要更高阈值才能 accept

## 版本标准化规则
- "before X.Y.Z" / "prior to X.Y.Z" → "<X.Y.Z"
- "up to X.Y.Z" / "through X.Y.Z" → "<=X.Y.Z"
- "after X.Y.Z" / "later than X.Y.Z" → ">X.Y.Z"
- "from X.Y.Z" / "at least X.Y.Z" → ">=X.Y.Z"
- "fixed in X.Y.Z" / "patched in X.Y.Z" → ">=X.Y.Z"
- 纯版本号 → "==X.Y.Z"

只输出 JSON 格式的结构化字段，不输出额外解释。"""

_USER_TEMPLATE = """\
## 攻击上下文
attack_name: {attack_name}
attack_family: {attack_family}
attack_summary: {attack_summary}

## 当前 BOM mention
mentioned_name: {mentioned_name}
mentioned_vendor: {mentioned_vendor}
mentioned_version: {mentioned_version}
component_layer_hint: {component_layer_hint}

## 候选组件列表 (按检索评分降序)
{candidate_list}

## 原文片段 (截取)
{evidence_text}
"""


# ---------------------------------------------------------------------------
# LangChain LLM BOM Resolver
# ---------------------------------------------------------------------------


class LangChainLlmBomResolver:
    """LLM-primary BOM resolver for Phase 5.

    This receives retrieval candidates from ``ComponentResolutionService`` and
    uses the LLM to make the final selection/rejection decision.  The LLM sees
    the attack context, bom_mention details, and the top-k candidate list with
    scores, aliases, and layers.

    Callers should check ``is_available()`` and decide whether to fall back
    to rule-based resolution.
    """

    PROMPT_VERSION: str = PROMPT_VERSION

    def __init__(
        self,
        *,
        model: str = "gpt-5-mini",
        temperature: float = 0.0,
        base_url: str | None = None,
        api_key: str | None = None,
        runtime_config: dict[str, Any] | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.base_url = (
            base_url or os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")
        )
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.runtime_config = runtime_config or {}
        self.last_invocation_meta: dict[str, Any] = {}

    def is_available(self) -> bool:
        return bool(
            list_available_profile_ids(
                task_name="bom_resolution",
                default_model=self.model,
                base_url=self.base_url,
                api_key=self.api_key,
                runtime_config=self.runtime_config,
            )
        )

    def validate_connectivity(self) -> None:
        if not self.is_available():
            raise RuntimeError(
                "LLM BOM resolution requested but OPENAI_API_KEY is not configured."
            )

    def resolve(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run the LLM BOM resolution.

        Parameters
        ----------
        payload : dict
            Must contain keys: attack_name, attack_family, attack_summary,
            mentioned_name, mentioned_vendor, mentioned_version,
            component_layer_hint, candidate_list (formatted string),
            evidence_text.

        Returns
        -------
        dict
            Validated ``LlmBomResolutionResult`` dumped as a dict.
        """
        if not self.is_available():
            raise RuntimeError(
                "LLM BOM resolution requested but OPENAI_API_KEY is not configured."
            )
        self.last_invocation_meta = {}

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _SYSTEM_PROMPT),
                ("user", _USER_TEMPLATE),
            ]
        )

        invoke_payload = {
            "attack_name": str(payload.get("attack_name", ""))[:200],
            "attack_family": str(payload.get("attack_family", ""))[:100],
            "attack_summary": str(payload.get("attack_summary", ""))[:500],
            "mentioned_name": str(payload.get("mentioned_name", "")),
            "mentioned_vendor": str(payload.get("mentioned_vendor", "") or "unknown"),
            "mentioned_version": str(
                payload.get("mentioned_version", "") or "unspecified"
            ),
            "component_layer_hint": str(
                payload.get("component_layer_hint", "") or "unknown"
            ),
            "candidate_list": str(payload.get("candidate_list", ""))[:3000],
            "evidence_text": str(payload.get("evidence_text", ""))[:2000],
        }
        result, meta = invoke_structured_with_model_pool(
            task_name="bom_resolution",
            prompt=prompt,
            schema=LlmBomResolutionResult,
            payload=invoke_payload,
            default_model=self.model,
            temperature=self.temperature,
            base_url=self.base_url,
            api_key=self.api_key,
            runtime_config=self.runtime_config,
        )
        self.last_invocation_meta = meta
        return result

    @staticmethod
    def format_candidate_list(candidates: list[dict[str, Any]]) -> str:
        """Format a list of BomCandidateDTO dicts into a readable string for
        the LLM prompt."""
        if not candidates:
            return "(no candidates retrieved)"
        lines: list[str] = []
        for idx, candidate in enumerate(candidates, 1):
            code = candidate.get("component_code") or "N/A"
            name = candidate.get("component_name", "?")
            vendor = candidate.get("vendor_name") or "unknown"
            layer = candidate.get("component_type") or "unknown"
            mode = candidate.get("match_mode", "?")
            score = candidate.get("final_score", 0.0)
            aliases = ", ".join(candidate.get("aliases", [])[:5]) or "none"
            modality = candidate.get("component_modality") or "unknown"
            lines.append(
                f"{idx}. [{code}] {name} (vendor={vendor}, layer={layer}, "
                f"modality={modality}, match={mode}, score={score:.3f}, "
                f"aliases=[{aliases}])"
            )
        return "\n".join(lines)
