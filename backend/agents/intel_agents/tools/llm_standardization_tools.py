from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from langchain_core.prompts import ChatPromptTemplate


# ---------------------------------------------------------------------------
# Prompt version — bump when system message or schema changes meaningfully
# ---------------------------------------------------------------------------
PROMPT_VERSION = "v2.0-llm-primary"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Structured output sub-models (LLM returns these)
# ---------------------------------------------------------------------------


class LlmTaxonomyItem(_StrictModel):
    taxonomy_type: Literal["OWASP_LLM", "CWE", "CAPEC", "ATTACK"]
    taxonomy_code: str = Field(min_length=1)
    taxonomy_name: str = Field(min_length=1)
    confidence_score: float = Field(ge=0.0, le=1.0)
    is_primary: bool = False


class LlmBomMention(_StrictModel):
    """A software component / AI-BOM artifact mentioned in the text.

    IMPORTANT: only include real component names (framework, library, model,
    platform, plugin, runtime).  Do NOT include attack names, vulnerability
    classes, or abstract concepts as BOM mentions.
    """

    mentioned_name: str = Field(min_length=1)
    mentioned_vendor: str | None = None
    mentioned_version: str | None = None
    component_layer: Literal[
        "vendor_platform",
        "model_family",
        "framework",
        "plugin",
        "runtime",
        "vector_stack",
        "unknown",
    ] = "unknown"
    confidence_score: float = Field(ge=0.0, le=1.0)
    reason_code: str = Field(default="llm_inferred")


class LlmCvssHint(_StrictModel):
    cvss_version: str = Field(default="3.1")
    base_score: float = Field(ge=0.0, le=10.0)
    severity_label: Literal["Low", "Medium", "High", "Critical"]
    score_origin: str = Field(default="estimated")
    vector_string: str | None = None


class LlmEvidenceSpan(_StrictModel):
    """An evidence span linking a field value to source text."""

    field_name: str = Field(min_length=1)
    evidence_text: str = Field(min_length=1)
    source_offset: str | None = None


class LlmPerFieldConfidence(_StrictModel):
    """Per-field confidence and reasoning from the LLM."""

    field_name: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class LlmStandardizationResult(_StrictModel):
    """Full structured output schema for LLM primary standardization.

    The LLM MUST populate every required field.  If the source text does not
    contain enough evidence for a field, the LLM should output ``"unknown"``
    and set a low per-field confidence, rather than guessing.
    """

    canonical_name: str = Field(min_length=1)
    attack_family: str = Field(min_length=1)
    severity_level: Literal["info", "low", "medium", "high", "critical"]
    summary: str = Field(min_length=1)
    description: str = Field(min_length=1)
    exploit_preconditions: str | None = None
    impact_scope: str | None = None
    extraction_reason: str = Field(min_length=1)
    taxonomy_items: list[LlmTaxonomyItem] = Field(default_factory=list)
    cvss_hint: LlmCvssHint | None = None
    bom_mentions: list[LlmBomMention] = Field(default_factory=list)
    evidence_spans: list[LlmEvidenceSpan] = Field(default_factory=list)
    field_confidences: list[LlmPerFieldConfidence] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# System prompt — v2.0 LLM-primary
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是 AI/ML 安全情报标准化专家。你是 **主要的信息提取者**，不是可选增强。

## 核心原则
1. **基于文本证据提取**：每一个字段值都必须能在原始文本中找到对应证据，不要猜测。
2. **允许 unknown**：如果文本不包含足够证据，canonical_name/attack_family/summary 等字段可以填 "unknown"，\
但 extraction_reason 必须说明为什么无法提取。
3. **区分攻击对象和 BOM 影响对象**：
   - 攻击对象 = 攻击手法/漏洞本身（对应 canonical_name, attack_family, taxonomy_items）
   - BOM 影响对象 = 受影响的具体软件/模型/框架/平台（对应 bom_mentions）
   - 不要将攻击名称放入 bom_mentions，不要将软件名称放入 attack_family
4. **evidence_spans 必须提供**：对 canonical_name, attack_family, severity_level, bom_mentions 中\
每一个关键字段，都要在 evidence_spans 中引用支撑文本片段。
5. **field_confidences 必须提供**：对 canonical_name, attack_family, severity_level, summary, \
bom_mentions 至少给出五个字段的置信度和理由。
6. **overall_confidence**：综合评估你对整体提取结果的置信度（0.0~1.0）。

## 命名规范
- attack_family 使用简洁 snake_case：prompt_injection, model_poisoning, agent_hijack, \
data_exfiltration, adversarial_evasion, supply_chain_compromise, training_data_leak 等
- taxonomy_items 优先识别：OWASP_LLM（OWASP-LLM-01 ~ OWASP-LLM-10）、CWE、CAPEC、ATTACK
- bom_mentions.component_layer 使用以下之一：vendor_platform, model_family, framework, \
plugin, runtime, vector_stack, unknown
- severity_level 使用：info, low, medium, high, critical

## 参考示例
- langchain prompt injection advisory → canonical_name="LangChain Prompt Injection via Agent Tools", \
attack_family="prompt_injection", taxonomy=[OWASP-LLM-01], bom_mentions=[{mentioned_name="langchain", \
component_layer="framework"}]
- agent workflow abuse discussion → canonical_name="Agent Hijack via Tool Misuse", \
attack_family="agent_hijack", taxonomy=[OWASP-LLM-07]

只输出结构化字段，不输出额外解释。"""

_USER_TEMPLATE = """\
source_name: {source_name}
query_text: {query_text}
title: {title}
summary: {summary}

--- 原始内容 (已清洗) ---
{cleaned_payload}
"""


# ---------------------------------------------------------------------------
# LangChain LLM Primary Standardizer
# ---------------------------------------------------------------------------


class LangChainLlmStandardizer:
    """LLM-primary structured extractor for Phase 3 standardization.

    This is the **primary** extraction path.  Rule-based logic serves only as
    a validator / fuser that runs *after* the LLM produces its structured output.

    Callers should check ``is_available()`` and decide whether to degrade to
    ``rules_only_degraded`` mode based on strategy policy.
    """

    PROMPT_VERSION: str = PROMPT_VERSION

    def __init__(
        self,
        *,
        model: str = "gpt-5-mini",
        temperature: float = 0.0,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.base_url = (
            base_url or os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")
        )
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def validate_connectivity(self) -> None:
        if not self.is_available():
            raise RuntimeError(
                "LLM standardization requested but OPENAI_API_KEY is not configured."
            )

    def extract(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run the LLM primary extraction.

        Parameters
        ----------
        payload : dict
            Must contain keys: source_name, query_text, title, summary,
            cleaned_payload.

        Returns
        -------
        dict
            Validated ``LlmStandardizationResult`` dumped as a dict.
        """
        if not self.is_available():
            raise RuntimeError(
                "LLM standardization requested but OPENAI_API_KEY is not configured."
            )

        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            base_url=self.base_url,
            api_key=SecretStr(self.api_key) if self.api_key else None,
        )
        structured_llm = llm.with_structured_output(LlmStandardizationResult)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _SYSTEM_PROMPT),
                ("user", _USER_TEMPLATE),
            ]
        )
        chain = prompt | structured_llm

        # Truncate payload to avoid token overflow while preserving key content
        invoke_payload = {
            "source_name": payload.get("source_name", ""),
            "query_text": payload.get("query_text", ""),
            "title": payload.get("title", ""),
            "summary": payload.get("summary", ""),
            "cleaned_payload": str(payload.get("cleaned_payload", ""))[:6000],
        }
        result = chain.invoke(invoke_payload)
        if isinstance(result, LlmStandardizationResult):
            return result.model_dump(mode="python")
        return LlmStandardizationResult.model_validate(result).model_dump(mode="python")
