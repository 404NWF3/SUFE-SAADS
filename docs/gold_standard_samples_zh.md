# 第一版金标准样本集（ThreatUnderstanding / TestPlan）

## 目的

当前数据库中的 `attack_taxonomy_map` 适合作为**候选样本池**，但不适合作为“测试方案生成”的直接真值集。

因此，后续 WP1-2 的 ThreatUnderstanding 与 TestPackageGeneration 调优，统一围绕一小批**人工确认的真实样本**推进，而不是继续泛跑全量 taxonomy 命中结果。

这份文档记录：

- 当前认可的第一版金标准样本
- 观察样本
- 明确应排除的噪声样本
- 建议调试方式

---

## 选择原则

一条样本进入金标准集，至少满足以下条件：

1. 摘要中存在明确的 LLM / agent / AI IDE / RAG / tool-using system 语境。
2. 风险描述与对应 OWASP LLM taxonomy 主题一致。
3. 不只是传统 `CWE / RCE / deserialization / code injection` 漏洞被宽泛映射进来。
4. 适合作为“高质量测试方案”的输入，而不是只能做漏洞归档。

---

## 第一版金标准样本

### 样本 1

- `attack_id`: `f0bea6cd-93bf-4dd2-bfe9-1688a0ca285c`
- 候选 taxonomy: `OWASP-LLM-01`
- primary taxonomy: `OWASP-LLM-01 Prompt Injection`
- 保留原因:
  - 摘要明确出现 `AI-powered IDEs`
  - 摘要明确出现 `prompt injection`
  - 摘要明确出现 `data exfiltration`
  - 很适合作为 prompt injection / AI IDE 风险场景的基准样本
- 当前用途:
  - ThreatUnderstanding 金标准样本
  - Test plan generation 首要样本

### 样本 2

- `attack_id`: `e8efae71-8591-48de-93b6-a42314cc88ac`
- 候选 taxonomy: `OWASP-LLM-02`
- primary taxonomy: `OWASP-LLM-01 Prompt Injection`
- all taxonomies:
  - `OWASP-LLM-01`
  - `OWASP-LLM-02`
  - `OWASP-LLM-05`
  - `OWASP-LLM-07`
- 保留原因:
  - 摘要明确出现 `n8n-claw AI Agent`
  - 明确涉及 prompt injection、data leakage、tool exploitation
  - 是非常典型的 agent / tool-using system 语境
- 当前用途:
  - ThreatUnderstanding 边界强化样本
  - 后续可用于 tool / workflow 测试方案验证

### 样本 3

- `attack_id`: `3e05c87a-fa9a-409e-aea0-bc583e4ae7c1`
- 候选 taxonomy: `OWASP-LLM-02`
- primary taxonomy: `OWASP-LLM-01 Prompt Injection`
- 保留原因:
  - 摘要明确出现 `AI-powered IDEs`
  - 明确出现 prompt injection 与 IDE features 组合
  - 尽管 taxonomy 交叉，但仍是高价值 AI-native 样本
- 当前用途:
  - ThreatUnderstanding 第二类 AI IDE 样本
  - 用于检验 taxonomy 冲突下的规划输出是否稳健

---

## 观察样本（先不纳入核心闭环）

### 样本 A

- `attack_id`: `0be6c7a0-5f0d-4033-ba13-e288078be393`
- 原因:
  - 恶意 npm 包 + 开发者工作流 + 供应链属性更强
  - 同时带有 `OWASP-LLM-10`
  - 语义比较复杂，先不作为第一批核心闭环样本

### 样本 B

- `attack_id`: `3ac15803-09ef-4fd0-a0d9-09cf836e5274`
- 原因:
  - `n8n workflow automation` 很值得观察
  - 但当前 taxonomy 为 `OWASP-LLM-04`，同时摘要里仍带较重传统执行漏洞色彩
  - 先保留为观察样本

---

## 直接排除的噪声样本

以下样本目前不适合作为高质量测试方案金标准：

- `82bd808b-16cd-450b-9f0a-fe1fc588a6d1`
  - Cisco FMC/SCC deserialization RCE
- `020c6268-4242-4b8b-87c4-12356ee94784`
  - Cisco FMC/SCC deserialization RCE
- `f9ac99e9-496a-4b1f-9cd6-b2f4f0ee3d71`
  - Laravel Livewire code injection
- `3d833acc-5564-46e0-8c37-7529e8c85888`
  - Laravel Livewire code injection
- `ea514ad0-0d65-4611-8175-71a59b44c471`
  - Apple Safari buffer overflow
- `dc3279ed-83e9-473d-9484-286b86624cd5`
  - SharePoint deserialization
- `913c1b07-24f0-46f6-99ca-c19116be957f`
  - SolarWinds deserialization
- `61fe2f05-e963-4482-a143-762908778133`
  - Craft CMS code injection
- `f4e2714c-ef00-46b2-8c9c-9eaef28e4c64`
  - Laravel Livewire code injection

排除原因统一为：

- 虽然命中了某个 `OWASP-LLM-0X`
- 但摘要主体更像传统漏洞 / RCE / code injection
- 不适合作为“测试方案生成”主样本

---

## 当前工程结论

### 1. 数据库 taxonomy 更适合做“候选池”

数据库 `attack_taxonomy_map` 目前适合：

- 候选检索
- 风险主题线索

不适合直接当作：

- 高质量测试方案的金标准样本集

### 2. ThreatUnderstanding 必须承担 taxonomy 复核责任

ThreatUnderstanding 后续必须继续加强：

- taxonomy consistency
- llm-native evidence
- taxonomy mapping conflict handling

### 3. 后续调优统一围绕金标准样本进行

后续 WP1-2 迭代统一优先围绕：

- `f0bea6cd-93bf-4dd2-bfe9-1688a0ca285c`
- `e8efae71-8591-48de-93b6-a42314cc88ac`
- `3e05c87a-fa9a-409e-aea0-bc583e4ae7c1`

先把这三条的：

- ThreatUnderstanding
- TestPackageGeneration

打磨到稳定，再扩大样本范围。

---

## 推荐调试方式

单条样本看 ThreatUnderstanding：

```powershell
.\.venv\Scripts\python.exe -m saads_wp12.debug.inspect_threat_understanding f0bea6cd-93bf-4dd2-bfe9-1688a0ca285c
```

切换其他样本时，只替换最后的 `attack_id`。

---

## 当前最小成功闭环目标

先只追求这件事：

1. 对金标准样本，ThreatUnderstanding 输出稳定且一致。
2. 对金标准样本，TestPackageGeneration 能输出高质量测试方案。
3. 脚本生成继续作为条件性后续能力，不阻塞方案主线。
