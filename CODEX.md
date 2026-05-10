# CODEX.md

本文件是本仓库给后续 Codex / Agent 优先阅读的协作约定。进入项目后，先读本文件，再按需要阅读 README、论文总入口和代码模块。

## 项目目标

本项目服务毕业设计论文。当前论文主线是：

```text
数据 + Agent + Benchmark
```

其中：

- 数据贡献：PostgreSQL 招生快照、专业树、学费字段、专业质量标准化层、就业结果标准化层、地域树 reviewed v1。
- Agent 贡献：证据驱动 Pareto 谈判 Agent。
- Benchmark 贡献：冰山画像、多轮沙盒、事实/过程联合评价、`app_pareto` vs `hard_constraint`。

## 优先事实源

论文材料和实验口径优先以以下两个文件为事实源：

- `gaokaollm_bench/outputs/thesis_document_hub.md`
- `gaokaollm_bench/outputs/thesis_claims_manifest.json`

若论文口径、实验指标、MAS 表述或地域树边界需要调整，应先更新这两个入口，再按 hub 中的同步清单更新相关正文母版、贡献母版、路线图、图表包和 evidence。

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

## Agent / MAS 口径

论文中使用“轻量 MAS / 多角色 Agent”表述业务 Agent 架构：

```text
gatekeeper -> radar -> negotiator
```

推荐写法：

- `gatekeeper`：抽取用户显式约束并形成 hard-constraint baseline。
- `radar`：调用确定性 probe / SQL 查询，探测 Pareto opportunities。
- `negotiator`：组织真实证据并生成可审计的谈判回复。

不要把它夸大为完全自治多智能体系统。simulator 和 evaluator 属于 benchmark 侧 agent-like role，不写成被测业务 Agent 的内部能力。

## Hidden Persona 边界

被测 Agent 不读取 benchmark persona 的 hidden fields：

- `implicit_flexibilities`
- `volunteer_set`

这些字段只作为 simulator / evaluator 的 ground truth。论文和证据附录中必须维持该边界：Agent 输入只来自用户显式话语和 PostgreSQL / 标准化证据层查询结果。

## 文档更新规则

开发、数据补充或实验完成后，论文文档更新采用“一次性长更新”的方式：

- 先判断本次变更影响哪些事实、指标、术语和章节。
- 先更新 `thesis_claims_manifest.json` 与 `thesis_document_hub.md`。
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

## 变更顺序建议

1. 读 `CODEX.md`。
2. 读 `gaokaollm_bench/outputs/thesis_document_hub.md`。
3. 读 `gaokaollm_bench/outputs/thesis_claims_manifest.json`。
4. 如果是代码开发，再读相关模块 README 和实现文件。
5. 如果是论文维护，先定位受影响文档集合，再做一次性长更新。
6. 最后做只读关键词和指标一致性检查。

## 边界

- 不要把 v1 `gaokaollmmodel` 包装成最终主贡献；它是工程原型与问题发现。
- 不要把 `region_tree_v1` 写成主实验；它是扩展实验。
- 不要把城市层级直接等价为就业机会、生活成本或城市生活质量收益。
- 不要把 `major_geo_v1` 写成 100% 成功；`real-db-set-浙江-569-009` 是失败样本。
