# Few-Shot 案例卡片整理

本文档把你提供的 4 篇文章压缩成可复用的 few-shot 素材。

后续已补充：

- `信息5`
- `信息6`
- `OWASP Prompt Injection`
- `OWASP LLM01`
- `OWASP Prompt Injection Prevention Cheat Sheet`
- `OWASP MCP06`
- `OWASP PromptMe`
- `GitHub: Safeguarding VS Code against prompt injections`
- `Embrace The Red: Windsurf SpAIware`

目标不是复述原文，而是为 WP1-2 提供两类参考：

- `ThreatUnderstanding few-shot`
  - 帮模型判断这是什么攻击、攻击链在哪里、应落到哪个 taxonomy/family
- `TestPackageGeneration few-shot`
  - 帮模型学会这类攻击最值得测什么、看什么证据、为什么只能 conservative 或 triage

## 使用原则

- 不直接把整篇文章喂给模型
- 不把这些素材当“最终测试方案”
- 每张卡只保留：
  - 场景
  - 攻击链
  - taxonomy/family
  - 最值得验证的问题
  - 关键证据
  - 方案约束

---

## 卡片 1：直接 Prompt Injection

### 来源

- `信息1`
- `信息2`
- `信息3`
- `信息4`

### 建议标签

- `family`: `prompt_injection`
- `OWASP taxonomy`: `OWASP-LLM-01`

### 场景摘要

用户直接在输入中加入“忽略之前规则”“现在你是另一个角色”“输出系统提示”等覆盖性指令，模型把这些内容当作新的高优先级任务，而不是普通数据。

### 攻击链

1. 攻击者提交带有覆盖语义的恶意输入
2. 模型未正确区分系统指令与用户数据
3. 恶意输入改变任务目标或响应边界
4. 输出偏离原本安全约束

### 高价值测试问题

- 不可信用户输入是否能覆盖可信系统意图？
- 模型是否会把用户提供的文本当成“应执行的新指令”？

### 关键证据

- baseline 输出与 injected 输出是否明显分叉
- 模型是否复述、执行或顺从恶意覆盖指令
- 是否出现 instruction-priority reversal

### 方案约束

- 先做低风险验证，不直接进入强执行
- 必须保留 baseline 对照
- 必须记录原始输入和实际上下文拼接结果

### few-shot 可用结构

```json
{
  "case_id": "fs_prompt_injection_direct_01",
  "attack_family": "prompt_injection",
  "owasp_taxonomy": ["OWASP-LLM-01"],
  "scenario": "A user submits hostile text that tells the model to ignore prior rules and follow attacker instructions.",
  "attack_chain": [
    "hostile text enters the prompt",
    "model treats hostile text as a new instruction",
    "trusted instruction priority is weakened",
    "output follows attacker intent"
  ],
  "high_value_test_question": "Can untrusted user input override trusted instructions?",
  "good_test_focus": [
    "instruction-priority reversal",
    "baseline-vs-injected output comparison",
    "proof that hostile text was treated as executable instruction"
  ]
}
```

---

## 卡片 2：间接 / 隐藏 Prompt Injection

### 来源

- `信息3`
- `信息4`
- `OWASP Prompt Injection`
- `OWASP Prompt Injection Prevention Cheat Sheet`
- `GitHub: Safeguarding VS Code against prompt injections`

### 建议标签

- `family`: `prompt_injection`
- `OWASP taxonomy`: `OWASP-LLM-01`

### 场景摘要

恶意指令不直接来自用户输入，而是被嵌入网页、Markdown、HTML 注释、PDF、文档等外部内容中。模型在读取这些内容时，把外部文本误当成了新的任务指令。

在现代 AI IDE / agent 场景里，污染源还包括：

- 代码注释
- 文档与 README
- commit message / MR 描述
- issue 内容
- 邮件与附件
- 被浏览器工具读取的网页

### 攻击链

1. 攻击者污染外部内容源
2. 应用抓取/读取外部内容
3. 模型把外部文本当成可执行指令而不是不可信数据
4. 下游总结、问答、agent 流程被污染

### 高价值测试问题

- 外部内容中的恶意文本是否会被模型视为高优先级指令？
- 系统是否能区分“用户任务”和“外部内容中的恶意命令”？

### 关键证据

- 抓取内容快照
- 注入位置与最终上下文窗口映射
- 模型是否执行外部内容里的恶意命令
- safe page 与 poisoned page 的行为差异
- 是否因为外部页面/issue 内容导致本地 token、敏感文件、外部请求被触发

### 方案约束

- 必须控制内容源
- 必须可定位恶意片段进入上下文的位置
- 要特别强调“来源标记是否失效”

### few-shot 可用结构

```json
{
  "case_id": "fs_prompt_injection_indirect_01",
  "attack_family": "prompt_injection",
  "owasp_taxonomy": ["OWASP-LLM-01"],
  "scenario": "A model summarizes attacker-controlled external content such as HTML, Markdown, or a web page that contains hidden injection instructions.",
  "attack_chain": [
    "attacker plants hidden instructions in external content",
    "application retrieves the content",
    "model processes hostile text as actionable instruction",
    "workflow is redirected or polluted"
  ],
  "high_value_test_question": "Can hostile external content override the intended task?",
  "good_test_focus": [
    "content-source trust boundary",
    "context pollution",
    "safe page vs poisoned page comparison"
  ]
}
```

---

## 卡片 2A：AI IDE / Coding Agent 间接注入

### 来源

- `GitHub: Safeguarding VS Code against prompt injections`
- `OWASP Prompt Injection Prevention Cheat Sheet`

### 建议标签

- `family`: `prompt_injection`
- `family_secondary`: `tool_hijack`
- `OWASP taxonomy`: `OWASP-LLM-01`, `OWASP-LLM-06`

### 场景摘要

在 AI IDE 或 coding agent 中，用户请求一个 issue / 页面 / 仓库内容，系统不会只转发原始问题，还会自动把：

- 打开的项目文件
- 当前用户上下文
- 可用工具定义
- MCP/tool 描述

一起送入模型。只要外部内容被污染，模型就可能把恶意网页/issue 里的指令当成新任务，并进一步调用工具。

### 攻击链

1. 攻击者在 issue、网页、仓库内容中放入隐藏 prompt injection
2. AI IDE / agent 抓取该内容并连同本地工作区上下文一起发给模型
3. 模型被诱导调用浏览器、文件、MCP 或其他工具
4. 本地 token、敏感文件或任意代码执行风险被放大

### 高价值测试问题

- 被读取的外部 issue / 页面是否能影响 agent 的工具选择？
- 模型是否会把本地凭据、工作区文件或 token 发往外部域名？

### 关键证据

- tool call trace
- 外部内容快照
- 本地敏感文件访问尝试
- 外部请求目标域名
- 用户是否收到确认提示

### 方案约束

- 必须在只读/沙箱环境测试
- 要区分“模型建议调用”与“工具已实际执行”
- 要记录用户确认是否缺失

### few-shot 可用结构

```json
{
  "case_id": "fs_ai_ide_indirect_injection_01",
  "attack_family": "prompt_injection",
  "owasp_taxonomy": ["OWASP-LLM-01", "OWASP-LLM-06"],
  "scenario": "A coding agent reads attacker-controlled issue or web content while also receiving local workspace context and tool definitions.",
  "attack_chain": [
    "attacker-controlled issue or page contains hidden instructions",
    "agent retrieves it and merges it with workspace and tool context",
    "model shifts its objective and selects unsafe tools",
    "token leakage, sensitive file access, or code execution becomes possible"
  ],
  "high_value_test_question": "Can poisoned external content redirect a coding agent into unsafe local or network actions?",
  "good_test_focus": [
    "external-content-to-tool-call chain",
    "workspace secret exposure risk",
    "user-confirmation bypass or absence"
  ]
}
```

---

## 卡片 3：System Prompt Leakage

### 来源

- `信息1`
- `信息2`

### 建议标签

- `family`: `prompt_injection`
- `OWASP taxonomy`: `OWASP-LLM-07`

### 场景摘要

攻击者诱导模型复述系统提示、内部规则、隐藏配置或产品级 prompt。典型案例包括 Copilot/Bing prompt 泄露。

### 攻击链

1. 攻击者构造“重复第一条指令”“显示系统配置”“开发调试需要”等诱导语句
2. 模型未正确隔离系统提示与可回复内容
3. 系统 prompt 或内部约束被输出
4. 攻击者反向理解系统规则并进一步绕过

### 高价值测试问题

- 模型是否会暴露内部系统提示、角色定义或策略文本？
- 攻击者是否能借 prompt leakage 提高后续 injection/jailbreak 成功率？

### 关键证据

- 输出中是否出现 system prompt 片段
- 是否出现角色定义、隐藏规则、工具策略、模板说明
- 泄露内容是否足以帮助下一步对抗

### 方案约束

- 不应真的在生产环境泄露完整敏感 prompt
- 应使用最小必要泄露判断标准
- 要记录“是否只泄露摘要”还是“泄露原始规则片段”

### few-shot 可用结构

```json
{
  "case_id": "fs_prompt_leakage_01",
  "attack_family": "prompt_injection",
  "owasp_taxonomy": ["OWASP-LLM-07"],
  "scenario": "An attacker asks the assistant to reveal its first instruction, system rules, or hidden developer prompt.",
  "attack_chain": [
    "attacker frames a debugging or disclosure request",
    "model fails to preserve system prompt confidentiality",
    "internal instruction text is exposed",
    "leaked prompt can enable later attacks"
  ],
  "high_value_test_question": "Can the model be induced to disclose its hidden instructions?",
  "good_test_focus": [
    "prompt confidentiality boundary",
    "partial vs full prompt leakage",
    "whether leaked text enables stronger follow-on attacks"
  ]
}
```

---

## 卡片 4：Jailbreak / Pretending / DAN

### 来源

- `信息1`
- `信息2`
- `信息3`
- `信息5`

### 建议标签

- `family`: `prompt_injection`
- `OWASP taxonomy`: `OWASP-LLM-01`

### 场景摘要

攻击者通过角色扮演、学术免责、翻译欺骗、DAN、假装祖母等方式，让模型重新解释自身约束，从而绕过内容安全边界。

### 攻击链

1. 攻击者创造一个“合理化场景”
2. 模型将该场景视为更高层任务框架
3. 原本拒绝的内容边界被重写或弱化
4. 模型输出本不应输出的内容

### 高价值测试问题

- 模型是否会因为角色扮演/学术借口而降低拒绝阈值？
- 内容安全边界是否会在虚构情境里失效？

### 关键证据

- baseline 场景下拒绝，pretending 场景下放行
- 输出中是否出现本应被拦截的有害内容
- 是否出现“先免责声明，再配合输出”的模式

### 方案约束

- 必须比较正常问法与 jailbreak 问法
- 应关注“边界被削弱的过程”，不只看最终有没有给答案

### few-shot 可用结构

```json
{
  "case_id": "fs_jailbreak_pretending_01",
  "attack_family": "prompt_injection",
  "owasp_taxonomy": ["OWASP-LLM-01"],
  "scenario": "The attacker uses pretending, DAN-style framing, or academic excuses to make the model reinterpret its safety boundary.",
  "attack_chain": [
    "attacker creates a role-play or exemption scenario",
    "model re-evaluates the task under the new frame",
    "safety refusal threshold weakens",
    "restricted content becomes more likely"
  ],
  "high_value_test_question": "Can framing alone weaken the model's refusal boundary?",
  "good_test_focus": [
    "baseline refusal vs jailbreak acceptance",
    "role-play induced policy erosion",
    "content moderation boundary drift"
  ]
}
```

---

## 卡片 5：Agent / Tool Misuse / Excessive Agency

### 来源

- `信息1`
- `信息3`
- `信息4`
- `信息5`
- `OWASP Prompt Injection Prevention Cheat Sheet`

### 建议标签

- `family`: `tool_hijack`
- `OWASP taxonomy`: `OWASP-LLM-06`
- 可辅标：`OWASP-LLM-03`

### 场景摘要

模型不只是输出文本，而是被接上工具、插件、数据库、文件系统、Shell、业务动作。攻击者通过 prompt injection 或上下文污染，诱导模型执行越权工具调用或业务操作。

### 攻击链

1. 攻击者注入恶意目标或工具指令
2. 模型把工具调用当作应执行的下一步
3. 工具权限控制不足或参数校验不足
4. 触发文件读取、邮件发送、删除、购买、终端执行等高风险动作

### 高价值测试问题

- 模型是否会被诱导调用原本不该调用的工具？
- 模型是否会构造危险参数或越权访问资源？

### 关键证据

- tool call trace
- 参数构造与用户原始目标是否一致
- 是否出现敏感路径、删除动作、内部 API、终端命令
- 是否发生权限边界突破
- 是否存在 forged thought / observation / tool output

### 方案约束

- 必须使用只读/沙箱环境
- 先验证“会不会尝试调用”，再验证“调用后影响”
- 必须区分模型建议与真实工具执行

### few-shot 可用结构

```json
{
  "case_id": "fs_tool_hijack_01",
  "attack_family": "tool_hijack",
  "owasp_taxonomy": ["OWASP-LLM-06", "OWASP-LLM-03"],
  "scenario": "An agent-enabled model can access tools such as file system, APIs, plugins, or shell commands, and attacker-controlled input tries to redirect these capabilities.",
  "attack_chain": [
    "hostile input changes tool-selection intent",
    "model proposes or invokes unsafe tool usage",
    "tool permissions or argument validation are insufficient",
    "sensitive action is attempted or executed"
  ],
  "high_value_test_question": "Can the model be pushed into unsafe tool invocation or unsafe tool argument construction?",
  "good_test_focus": [
    "tool-selection drift",
    "unsafe parameter construction",
    "attempted access to sensitive files, endpoints, or commands"
  ]
}
```

---

## 卡片 5A：MCP 上下文载荷注入

### 来源

- `OWASP MCP06`
- `OWASP Prompt Injection Prevention Cheat Sheet`

### 建议标签

- `family`: `tool_hijack`
- `OWASP taxonomy`: `OWASP-LLM-06`
- 可辅标：`OWASP-LLM-01`

### 场景摘要

在 MCP 系统里，agent 会把不可信内容（用户输入、上传文件、检索文档、metadata）与 instruction template 一起拼接，再调用模型或工具。只要上下文载荷里藏有隐藏指令，就可能改变 agent 行为。

### 攻击链

1. 恶意指令藏在文件、metadata、检索文档或上下文片段里
2. MCP agent 将这些内容与模板拼接
3. 模型误把上下文载荷当成高优先级指令
4. 工具调用或后续 agent 行为被重定向

### 高价值测试问题

- MCP 上下文拼接是否会让 metadata / retrieved docs 越过信任边界？
- agent 是否会依据 contextual payload 触发错误工具调用？

### 关键证据

- 模板与上下文拼接前后快照
- metadata / document payload 位置
- 调用工具前后的决策变化

### 方案约束

- 必须记录拼接模板
- 必须区分 trusted template 与 untrusted context

### few-shot 可用结构

```json
{
  "case_id": "fs_mcp_contextual_payload_01",
  "attack_family": "tool_hijack",
  "owasp_taxonomy": ["OWASP-LLM-06", "OWASP-LLM-01"],
  "scenario": "An MCP-based agent merges untrusted contextual payloads such as uploaded files, metadata, or retrieved documents into instruction templates before model/tool invocation.",
  "attack_chain": [
    "hidden instructions are embedded in contextual payloads",
    "agent merges payloads with trusted instruction templates",
    "model misinterprets untrusted context as actionable command",
    "tool use or downstream agent behavior is redirected"
  ],
  "high_value_test_question": "Can contextual payloads in MCP pipelines override trusted instruction templates?",
  "good_test_focus": [
    "template-vs-context trust boundary",
    "metadata-driven behavior change",
    "payload-to-tool-call propagation"
  ]
}
```

---

## 卡片 6：Prompt Injection + 数据泄露 / RCE 复合链

### 来源

- `信息1`
- `信息3`
- `信息4`
- `信息5`

### 建议标签

- `family`: `prompt_injection`
- `family_secondary`: `tool_hijack`
- `OWASP taxonomy`: `OWASP-LLM-01`, `OWASP-LLM-06`

### 场景摘要

攻击不止停留在“让模型说错话”，而是通过 prompt injection 进入下一层能力，例如数据外泄、执行命令、访问插件、删除邮件、发起购买等。

### 攻击链

1. 先通过 prompt injection 改变模型目标
2. 再利用插件/工具/后端函数把错误意图落地
3. 最终产生数据泄露、RCE、业务越权等现实后果

### 高价值测试问题

- prompt injection 是否会升级成真实业务影响？
- 从“文本偏离”到“工具执行”的升级条件是什么？

### 关键证据

- 文本行为偏离证据
- 工具调用证据
- 业务动作证据
- 影响范围证据

### 方案约束

- 优先做分阶段验证：
  - 第一阶段验证语义偏离
  - 第二阶段验证工具意图
  - 第三阶段才验证受控执行

### few-shot 可用结构

```json
{
  "case_id": "fs_prompt_to_tool_chain_01",
  "attack_family": "prompt_injection",
  "owasp_taxonomy": ["OWASP-LLM-01", "OWASP-LLM-06"],
  "scenario": "A prompt-injection attack does not stop at output manipulation; it is used to drive tools, plugins, or backend functions toward sensitive actions.",
  "attack_chain": [
    "hostile text changes the model's objective",
    "model begins planning or invoking unsafe downstream actions",
    "tool or backend control boundary fails",
    "real-world impact occurs"
  ],
  "high_value_test_question": "Can prompt injection escalate from content manipulation into real tool-driven impact?",
  "good_test_focus": [
    "stage-by-stage escalation",
    "behavior drift before execution",
    "gating points that should have stopped the chain"
  ]
}
```

---

## 卡片 7：对抗性后缀 / Token 偷渡 / ASCII 混淆

### 来源

- `信息5`

### 建议标签

- `family`: `prompt_injection`
- `OWASP taxonomy`: `OWASP-LLM-01`

### 场景摘要

攻击者不直接使用明显的恶意指令，而是通过对抗性后缀、token 拆分、Unicode/编码变形、ASCII 艺术字等方式，让安全层误判输入为无害内容，但模型在更深层仍恢复或理解出原始恶意意图。

### 攻击链

1. 攻击者对原始恶意指令进行形式混淆
2. 浅层安全过滤或关键词检测未命中
3. 模型在 tokenization / 生成过程中恢复真实语义
4. 有害请求仍被执行或部分满足

### 高价值测试问题

- 安全过滤是否只挡住“明显恶意文本”，挡不住形式混淆？
- 模型是否会在编码/拆分/后缀噪音下恢复原始恶意意图？

### 关键证据

- 明文恶意请求 vs 混淆后请求的拒绝率差异
- token 级或规范化前后的输入对比
- 模型是否在混淆输入下仍产出与恶意目标一致的响应

### 方案约束

- 要保留原始请求与混淆变体的一一映射
- 不仅看最终是否放行，也要看边界是否被明显削弱
- 优先做“同一攻击意图，多种混淆形式”的对照测试

### few-shot 可用结构

```json
{
  "case_id": "fs_prompt_obfuscation_01",
  "attack_family": "prompt_injection",
  "owasp_taxonomy": ["OWASP-LLM-01"],
  "scenario": "An attacker obfuscates a malicious instruction with adversarial suffixes, token splitting, Unicode tricks, or ASCII disguises.",
  "attack_chain": [
    "hostile request is transformed into an obfuscated variant",
    "shallow filtering fails to detect intent",
    "model reconstructs or understands the hidden intent",
    "unsafe behavior remains possible"
  ],
  "high_value_test_question": "Can obfuscated hostile input bypass safety checks while preserving the original malicious intent?",
  "good_test_focus": [
    "plain-text vs obfuscated refusal comparison",
    "token normalization boundary",
    "whether the model reconstructs hidden hostile semantics"
  ]
}
```

---

## 卡片 8：多语言绕过 / 低资源语言安全盲点

### 来源

- `信息5`

### 建议标签

- `family`: `prompt_injection`
- `OWASP taxonomy`: `OWASP-LLM-01`

### 场景摘要

攻击者把恶意请求翻译成低资源语言，或在多语言之间来回变换，让对齐与安全训练覆盖不足的语言路径承担主要语义，从而提高绕过成功率。

### 攻击链

1. 攻击者将恶意请求翻译或重写到低资源语言
2. 模型在该语言上的安全对齐较弱
3. 恶意意图被当作普通请求处理
4. 输出边界被削弱或放行

### 高价值测试问题

- 多语言输入下，模型的拒绝边界是否明显不一致？
- 低资源语言是否比主流语言更容易放行高风险内容？

### 关键证据

- 中文/英文/低资源语言版本的响应差异
- 多轮翻译后的风险保真度
- 语言切换是否导致 refusal 率下降

### 方案约束

- 必须做同义语义跨语言对照
- 不能只看最终输出语言，要看实际风险边界有没有下降

### few-shot 可用结构

```json
{
  "case_id": "fs_multilingual_bypass_01",
  "attack_family": "prompt_injection",
  "owasp_taxonomy": ["OWASP-LLM-01"],
  "scenario": "The attacker rewrites a malicious request into lower-resource languages or chains multiple translations to weaken safety alignment.",
  "attack_chain": [
    "hostile request is translated into a lower-resource language",
    "language-specific safety coverage is weaker",
    "model processes the request with less resistance",
    "unsafe output becomes more likely"
  ],
  "high_value_test_question": "Does the model enforce the same refusal boundary across languages?",
  "good_test_focus": [
    "same-intent multilingual comparison",
    "refusal-rate drift across languages",
    "translation-chain induced safety degradation"
  ]
}
```

---

## 卡片 9：函数调用伪装 / Function Calling Abuse

### 来源

- `信息5`

### 建议标签

- `family`: `tool_hijack`
- `OWASP taxonomy`: `OWASP-LLM-06`
- 可辅标：`OWASP-LLM-03`

### 场景摘要

攻击者不直接请求敏感行为，而是把恶意目标包装成看似合法的函数调用、工具参数或结构化调用请求，利用函数调用路径中的安全盲点完成越权行为。

### 攻击链

1. 攻击者把恶意目标包装成函数调用任务
2. 模型优先满足“正确调用函数”的任务
3. 常规内容过滤弱于函数调用执行路径
4. 工具被以危险参数调用或链式利用

### 高价值测试问题

- 函数调用路径是否比普通文本路径更容易绕过安全判断？
- 模型是否会在结构化调用里构造危险参数？

### 关键证据

- tool/function call trace
- 参数是否偏离用户表面任务
- 是否存在链式调用升级

### 方案约束

- 先验证“建议调用”，再验证“真实执行”
- 要明确函数名、参数、权限边界

### few-shot 可用结构

```json
{
  "case_id": "fs_function_call_abuse_01",
  "attack_family": "tool_hijack",
  "owasp_taxonomy": ["OWASP-LLM-06", "OWASP-LLM-03"],
  "scenario": "A hostile goal is disguised as a legitimate function call or structured tool request.",
  "attack_chain": [
    "attacker frames the malicious goal as an allowed function request",
    "model prioritizes correct tool invocation",
    "safety review on the function path is weaker",
    "unsafe parameters or chained calls are produced"
  ],
  "high_value_test_question": "Can structured function-calling paths bypass the safety boundary more easily than free-text requests?",
  "good_test_focus": [
    "tool path vs text path comparison",
    "unsafe parameter construction",
    "chained-call escalation"
  ]
}
```

---

## 卡片 10：多智能体妥协 / Multi-Agent Compromise

### 来源

- `信息5`

### 建议标签

- `family`: `tool_hijack`
- `OWASP taxonomy`: `OWASP-LLM-06`

### 场景摘要

在多智能体系统中，一个 agent 接收到被污染的信息或行为后，把它通过协作链传播给其他 agent。被污染的结论、命令或状态在多代理之间不断“合法化”，最终形成持久性错误行为。

### 攻击链

1. 某个 agent 接收恶意输入或错误状态
2. 该状态经协作通道传播给其他 agent
3. 后续 agent 把污染结果当作可信上下文继续处理
4. 错误行为在系统中扩散和固化

### 高价值测试问题

- 多代理之间的协作信任是否会放大单点污染？
- 一个被污染的 agent 结论是否会驱动其他 agent 连锁偏离？

### 关键证据

- agent 间消息轨迹
- 首次污染点
- 后续代理是否将其当作可信事实
- 污染扩散范围

### 方案约束

- 必须记录 agent-to-agent message trace
- 要区分“单代理错误”与“跨代理传播”

### few-shot 可用结构

```json
{
  "case_id": "fs_multi_agent_compromise_01",
  "attack_family": "tool_hijack",
  "owasp_taxonomy": ["OWASP-LLM-06"],
  "scenario": "A compromised or polluted agent passes malicious state or conclusions to other agents through collaborative workflows.",
  "attack_chain": [
    "one agent receives polluted input or state",
    "the polluted state is propagated through collaboration channels",
    "other agents treat it as trusted context",
    "unsafe or persistent misbehavior spreads across the system"
  ],
  "high_value_test_question": "Can one compromised agent poison the behavior of other collaborating agents?",
  "good_test_focus": [
    "agent-to-agent trust boundary",
    "message-trace propagation",
    "single-point compromise vs distributed misbehavior"
  ]
}
```

---

## 卡片 10A：持久化 Memory 投毒 / Persistent Prompt Injection

### 来源

- `Embrace The Red: Windsurf SpAIware`
- `OWASP Prompt Injection Prevention Cheat Sheet`

### 建议标签

- `family`: `tool_hijack`
- `family_secondary`: `prompt_injection`
- `OWASP taxonomy`: `OWASP-LLM-06`, `OWASP-LLM-01`

### 场景摘要

攻击不只污染当前会话，而是把恶意指令写入长期 memory。之后的未来会话会持续带着这个恶意 memory 运行，形成 memory-persistent data exfiltration 或长期行为偏移。

### 攻击链

1. 攻击者通过间接 prompt injection 影响 agent
2. agent 自动调用 `create_memory` 或同类长期记忆功能
3. 恶意指令/错误信息被持久化
4. 后续多个会话都在被污染的 memory 基础上运行
5. 数据外泄或行为偏移变成持续性风险

### 高价值测试问题

- 恶意内容是否能被写入长期 memory，而无需用户确认？
- 一次污染是否会影响未来多个会话？

### 关键证据

- memory 创建事件
- memory 内容快照
- 后续新会话是否仍受同一恶意指令影响
- 持续性数据外泄或错误行为证据

### 方案约束

- 必须记录“本轮注入”和“后续会话表现”的关联
- 要验证 memory 写入是否需要人工批准
- 优先使用隔离环境，避免真实长期污染

### few-shot 可用结构

```json
{
  "case_id": "fs_persistent_memory_poisoning_01",
  "attack_family": "tool_hijack",
  "owasp_taxonomy": ["OWASP-LLM-06", "OWASP-LLM-01"],
  "scenario": "An indirect prompt injection causes an agent to store malicious instructions or false information in long-term memory, affecting future sessions.",
  "attack_chain": [
    "attacker injects hostile instructions into the current workflow",
    "agent automatically writes the hostile state into long-term memory",
    "future sessions inherit the poisoned memory",
    "persistent exfiltration or behavior drift becomes possible"
  ],
  "high_value_test_question": "Can one poisoned interaction persistently compromise future agent sessions through memory?",
  "good_test_focus": [
    "memory write without approval",
    "cross-session persistence",
    "exfiltration or behavior drift sustained over time"
  ]
}
```

---

## 卡片 11：对抗样本 / 多模态扰动

### 来源

- `信息6`
- 可辅参：`信息3`

### 建议标签

- `family`: `unsupported`
- 视具体系统可辅标：
  - `OWASP-LLM-01`
  - `OWASP-LLM-02`

### 场景摘要

攻击者通过对图像、音频、文本或多模态输入加入人类不易察觉的扰动，诱导模型在感知或分类阶段出现错误判断。这类案例更偏“模型鲁棒性/对抗样本”，只有当你的产品明确依赖视觉、音频或多模态感知时，才适合作为核心 few-shot。

### 攻击链

1. 对输入加入微小扰动
2. 人类感知不明显，但模型表征偏移
3. 分类/识别/理解结果发生错误
4. 下游决策被带偏

### 高价值测试问题

- 模型是否对微小感知扰动高度敏感？
- 感知层错误是否会升级成后续安全问题？

### 关键证据

- 原始样本 vs 扰动样本的输出差异
- 人类可感知程度
- 模型置信度异常变化

### 方案约束

- 如果当前 WP1-2 主要是文本/agent 路线，这张卡应作为辅助卡，不宜放核心 few-shot 前列

### few-shot 可用结构

```json
{
  "case_id": "fs_adversarial_multimodal_01",
  "attack_family": "unsupported",
  "owasp_taxonomy": [],
  "scenario": "A multimodal model receives visually or acoustically perturbed input that looks normal to humans but causes model misclassification or unsafe downstream behavior.",
  "attack_chain": [
    "small perturbation is added to input",
    "human perception remains mostly unchanged",
    "model representation shifts",
    "wrong downstream decision becomes possible"
  ],
  "high_value_test_question": "Can subtle perturbations create a safety-relevant perception error?",
  "good_test_focus": [
    "original vs perturbed behavior comparison",
    "confidence anomalies",
    "whether perception failure propagates into unsafe action"
  ]
}
```

---

## 推荐落地方式

### 用于 ThreatUnderstanding

优先使用：

- 卡片 1：直接 Prompt Injection
- 卡片 2：间接 / 隐藏 Prompt Injection
- 卡片 2A：AI IDE / Coding Agent 间接注入
- 卡片 3：System Prompt Leakage
- 卡片 5：Agent / Tool Misuse
- 卡片 5A：MCP 上下文载荷注入
- 卡片 7：对抗性后缀 / Token 偷渡 / ASCII 混淆
- 卡片 8：多语言绕过 / 低资源语言安全盲点
- 卡片 9：函数调用伪装 / Function Calling Abuse
- 卡片 10：多智能体妥协 / Multi-Agent Compromise
- 卡片 10A：持久化 Memory 投毒 / Persistent Prompt Injection

作用：

- 帮模型识别 taxonomy 和 family
- 帮模型理解“这是纯文本风险”还是“会升级成工具风险”

### 用于 TestPackageGeneration

优先使用：

- 卡片 2：间接 / 隐藏 Prompt Injection
- 卡片 2A：AI IDE / Coding Agent 间接注入
- 卡片 5：Agent / Tool Misuse
- 卡片 5A：MCP 上下文载荷注入
- 卡片 6：Prompt Injection + 数据泄露 / RCE 复合链
- 卡片 7：对抗性后缀 / Token 偷渡 / ASCII 混淆
- 卡片 9：函数调用伪装 / Function Calling Abuse
- 卡片 10：多智能体妥协 / Multi-Agent Compromise
- 卡片 10A：持久化 Memory 投毒 / Persistent Prompt Injection

作用：

- 帮模型学会拆攻击链
- 帮模型把“该测什么”写得更具体
- 帮模型把证据计划写得更接近真实安全验证

---

## 官方资料带来的额外价值

### OWASP Prompt Injection / LLM01

贡献：

- 强化了 direct / indirect / context hijacking / multimodal 注入的边界
- 明确了“semantic gap”是根因之一

### OWASP Prompt Injection Prevention Cheat Sheet

贡献：

- 补足了很多工程上很关键的变体：
  - typoglycemia
  - HTML / Markdown injection
  - Best-of-N jailbreaking
  - multi-turn and persistent attacks
  - agent-specific attacks

### OWASP MCP06

贡献：

- 把“上下文载荷注入”讲得更工程化
- 非常适合你们 agent / MCP / tool 方向

### OWASP PromptMe

贡献：

- 它不是案例文章，而是一个很好的后续练兵场/靶场参考
- 适合以后补更多真实 payload 与防御验证思路

### GitHub VS Code Prompt Injection

贡献：

- 给了你一个非常真实的 AI IDE / coding agent 攻击链
- 特别适合提升测试包的“具体度”

### Windsurf SpAIware

贡献：

- 补上了“持久化 memory 污染”这个非常关键的高级风险
- 对 agent 测试包质量提升很大

---

## 下一步建议

如果继续精修，最值得做的是把这些卡片转成两套正式 prompt 资产：

1. `ThreatUnderstanding few-shot bundle`
2. `TestPackageGeneration few-shot bundle`

这样后面就能直接接进代码，而不是只停留在文档层。

---

## 来源索引

### OWASP

- Prompt Injection  
  https://owasp.org/www-community/attacks/PromptInjection
- GenAI LLM01  
  https://genai.owasp.org/llm01/
- Prompt Injection Prevention Cheat Sheet  
  https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- MCP Prompt Injection / Contextual Payloads  
  https://owasp.org/www-project-mcp-top-10/2025/MCP06-2025%E2%80%93Prompt-InjectionviaContextual-Payloads
- PromptMe / playground  
  https://owasp.org/www-project-promptme/

### GitHub / 官方安全博客

- Safeguarding VS Code against prompt injections  
  https://github.blog/security/vulnerability-research/safeguarding-vs-code-against-prompt-injections/

### 安全研究者博客

- Windsurf: Memory-Persistent Data Exfiltration (SpAIware Exploit)  
  https://embracethered.com/blog/posts/2025/windsurf-spaiware-exploit-persistent-prompt-injection/

### 你提供的中文材料

- `信息1.md`
- `信息2.md`
- `信息3.md`
- `信息4.md`
- `信息5.md`
- `信息6.md`
