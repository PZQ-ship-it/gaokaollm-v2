# CODEX.md

本文件是后续 Codex / Agent 进入本仓库时优先阅读的协作约定。它用于统一论文维护口径，避免每次改动都重新搜索分散材料。

## 项目目标

本项目服务本科毕业设计论文。当前论文主线为：

```text
数据贡献 + Agent 贡献 + Benchmark 贡献
```

也可简称为“数据 + Agent + Benchmark”三贡献结构。

其中：

- 数据贡献：PostgreSQL 招生快照、分数/位次/批次线/招生计划/学费事实、专业层级本体、学校-专业质量画像、专业就业结果画像、经人工审校的地域层级画像。
- Agent 贡献：面向高风险志愿决策的证据驱动 Pareto 谈判 Agent。
- Benchmark 贡献：冰山画像、多轮沙盒、事实/过程联合评价、证据谈判 Agent vs 硬约束基线。

专业层级本体当前采用“全量覆盖 v2”口径：`22,759 / 22,759` 个原始去重专业名和 `140,995 / 140,995` 条录取记录已完成可审计挂载，`remaining_unassigned = 0`。该全覆盖表示所有原始名称均进入可追溯叶子簇，并保留规则、probe、DeepSeek-R1 低置信复核或 fallback 标记；它不等于全部语义边界都已人工逐条确认正确。

## 优先事实源

论文材料和实验口径优先以下列文件为事实源：

- `gaokaollm_bench/outputs/thesis_document_hub.md`
- `gaokaollm_bench/outputs/thesis_claims_manifest.json`
- `gaokaollm_bench/outputs/thesis_term_mapping.json`
- `gaokaollm_bench/outputs/major_tree_annotation_summary.md`

若论文口径、实验指标、MAS 表述、术语映射或地域树边界需要调整，应先更新这些入口，再按 hub 的同步清单更新相关正文母版、贡献母版、路线图、图表包和 evidence。

其中，`major_tree_annotation_summary.md` 是专业树标注实验、DeepSeek-R1 低置信复核、错分聚类分析和全量覆盖 v2 的数据贡献事实源；机器可读事实同步在 `thesis_claims_manifest.json` 中。

## 当前实验口径

当前主实验：

- `major_geo_v1`
- `risk_band_v1`

当前扩展实验：

- `school_strength_v1`
- `tuition_value_v1`
- `major_quality_v1`
- `employment_outcome_v1`
- `region_tree_v1`

扩展实验用于支撑数据贡献和框架可扩展性，不替代主实验。

Benchmark 压力测试：

- `multi_axis_v1`：历史版多轴隐藏妥协压力测试。
- `multi_axis_v2`：轴一致性修正版压力测试。

压力测试不进入七组实验主表，也不改变主实验定位。

## Agent / MAS 口径

论文正文中使用“轻量 MAS / 多角色 Agent”描述业务 Agent。当前正文主叙述应采用：

```text
前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器
```

实现层可追溯为：

```text
semantic_normalizer -> gatekeeper -> llm-guided radar planner -> deterministic probes -> negotiator
```

推荐写法：

- 前置语义归一层：继承 v1 查询重写能力，只规范化用户显式话语，做偏好轴拆解、歧义提示和查询压缩。
- 约束解析器：抽取用户显式约束并形成硬约束基线。
- LLM 引导的机会规划器：判断先探测哪些可谈判偏好轴、先解释哪些证据、是否需要澄清。
- 确定性证据探针：通过 PostgreSQL / 标准化证据层产生候选，是事实候选唯一来源。
- 证据谈判器：组织真实证据并生成可审计的 Pareto 谈判回复。

LLM 不生成学校、专业、分数、位次等事实候选，只输出 `probe_plan`、`opportunity_rankings` 和 `clarification_hint`。

不要把它夸大为完全自治多智能体系统。Simulator 和 evaluator 属于 benchmark 侧 agent-like role，不写成被测业务 Agent 的内部能力。

## Hidden Persona 边界

被测 Agent 不读取 benchmark persona 的 hidden fields：

- `implicit_flexibilities`
- `volunteer_set`
- `axis_flexibilities`

这些字段只作为 simulator / evaluator 的 ground truth。论文和证据附录必须维持该边界：Agent 输入只来自用户显式话语和 PostgreSQL / 标准化证据层查询结果。

## 文档更新规则

开发、数据补充或实验完成后，论文文档更新采用“一次性长更新”的方式：

- 先判断本次变更影响哪些事实、指标、术语和章节。
- 先更新 `thesis_claims_manifest.json`、`thesis_document_hub.md` 与 `thesis_term_mapping.json`。
- 再按 hub 同步所有受影响文档。
- 避免每发现一个文档就单独开一轮短更新。

这样可以减少反复查找、反复修口径和反复验收的时间浪费。

## 审计规则

除非用户明确要求，后续优先完成：

- 论文正文
- 数据补充
- Agent / Benchmark 开发
- 实验结果
- 逐例证据链

不要主动扩展或重跑 thesis audit。已有 audit 可作为历史材料，但不是当前论文维护的优先入口。

## 建议工作顺序

1. 读 `CODEX.md`。
2. 读 `gaokaollm_bench/outputs/thesis_document_hub.md`。
3. 读 `gaokaollm_bench/outputs/thesis_claims_manifest.json`。
4. 读 `gaokaollm_bench/outputs/thesis_term_mapping.json`，确认正文术语和工程标识边界。
5. 如果是代码开发，再读相关模块 README 和实现文件。
6. 如果是论文维护，先定位受影响文档集合，再做一次性长更新。
7. 如果涉及正式论文交付或 LaTeX 终稿，读 `gaokaollm_bench/outputs/thesis_latex_final_consistency_report.md`，确认 `zjuthesis.pdf` 编译状态、事实一致性和剩余版式 warning。
8. 最后做只读关键词、术语映射和指标一致性检查。

## 边界

- 不要把 v1 `gaokaollmmodel` 包装成最终主贡献；它是第一版志愿咨询原型系统和问题发现来源。
- 不要把 `region_tree_v1` 写成主实验；它是扩展实验。
- 不要把城市层级直接等价为就业机会、生活成本或城市生活质量收益。
- 不要把 `major_geo_v1` 写成 100% 成功；`real-db-set-浙江-569-009` 是失败样本。
