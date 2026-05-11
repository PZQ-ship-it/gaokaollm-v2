# 新 MAS 架构验收说明

本文档记录“v1 语义归一能力融合进 v2 机会规划”的当前验收状态。它不新增实验结论，不改变七组 Agent/Benchmark 指标，只用于统一论文事实源与实现边界。

## 1. 当前论文口径

业务 Agent 在论文正文中写作：

```text
前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器
```

实现层可追溯为：

```text
semantic_normalizer -> gatekeeper -> llm-guided radar planner -> deterministic probes -> negotiator
```

当前业务 Agent 采用基于角色分工的轻量 MAS：前置语义归一层继承 v1 的查询重写能力，只对用户显式话语做语义归一、偏好轴拆解、歧义提示和查询压缩；约束解析器形成硬约束基线；LLM 引导的机会规划器只决定优先探测哪些可谈判偏好轴、先解释哪些证据以及是否需要澄清；事实候选仍由确定性证据探针通过 PostgreSQL 与标准化证据层产生；证据谈判器负责组织候选证据并生成可审计回复。

## 2. LLM 参与边界

LLM 不生成学校、专业、分数、位次等事实候选，只输出 `probe_plan`、`opportunity_rankings` 和 `clarification_hint`；Agent 不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`。

LLM 的合理职责包括：

- 对用户显式话语进行查询重写、偏好轴拆解、歧义提示和查询压缩。
- 基于显式约束、baseline 和意图轴输出机会探测计划。
- 对已有候选证据进行解释顺序规划和澄清策略建议。

LLM 的禁止职责包括：

- 直接生成学校、专业、最低分、最低位次、学费、就业排名或地域节点等事实候选。
- 读取 benchmark hidden fields。
- 覆盖确定性 SQL probes 的事实判断。

## 3. 数据流验收

| 阶段 | 输入 | 输出 | 验收边界 |
| --- | --- | --- | --- |
| 前置语义归一层 | 用户显式话语 | `rewritten_query`、`intent_axes`、`clarification_hint` | 只归一显式话语，不读取 hidden fields |
| 约束解析器 | 原始话语与归一化表达 | 硬约束字典与 baseline | 硬约束仍由结构化抽取和数据库查询锁定 |
| LLM 引导的机会规划器 | 显式约束、baseline、意图轴 | `probe_plan`、`opportunity_rankings`、`clarification_hint` | 只规划探针和解释顺序，不生成候选 |
| 确定性证据探针 | 结构化约束与证据层 | Pareto opportunities 与候选证据 | 唯一事实候选来源 |
| 证据谈判器 | baseline、opportunities、规划顺序 | 可审计谈判回复与状态 | 回复必须落到真实候选证据 |

## 4. 已完成检查

本轮验收应运行：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m pytest tests/test_llm_guided_planning.py tests/test_missing_constraints.py tests/test_phase3.py gaokaollm_bench/tests/test_agent_benchmark_targets.py -q
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m ruff check app/schemas/state.py app/graphs/nodes/semantic_normalizer.py app/graphs/workflow.py app/graphs/nodes/gatekeeper.py app/graphs/nodes/radar.py app/graphs/nodes/negotiator.py app/api/chat_api.py gaokaollm_bench/sandbox/target_agents.py tests/test_llm_guided_planning.py
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m ruff format --check app/schemas/state.py app/graphs/nodes/semantic_normalizer.py app/graphs/workflow.py app/graphs/nodes/gatekeeper.py app/graphs/nodes/radar.py app/graphs/nodes/negotiator.py app/api/chat_api.py gaokaollm_bench/sandbox/target_agents.py tests/test_llm_guided_planning.py
```

LaTeX 侧应至少验证摘要、第 3/5/7 章与本文档口径一致，并能编译生成 `zjuthesis.pdf` 或备用 PDF。若默认 PDF 被占用，可由已生成的 XDV 输出备用 PDF。

## 5. 论文写作提醒

- 主实验仍为 `major_geo_v1 + risk_band_v1`。
- 五组扩展实验仍用于支撑数据贡献与框架可扩展性。
- `multi_axis_v2` 是 Benchmark 压力测试修正版，不写入七实验主表。
- 后续若要证明 LLM 规划层带来指标提升，应另起小规模对照实验；本验收只证明架构接入和边界一致。
