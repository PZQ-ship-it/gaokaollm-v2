# 毕业论文最终成稿装配清单

本文档是正式毕业论文写作阶段的执行清单，用于把当前分散在 `gaokaollm_bench/outputs/` 下的正文母版、图表素材、方法论和逐例 evidence 迁入最终论文。本文档不替代 `thesis_document_hub.md` 和 `thesis_claims_manifest.json`；论文事实、实验指标和边界表述仍以后两者为准。

当前论文主线为：

```text
数据 + Agent + Benchmark
```

Agent 架构写作口径为轻量 MAS / 多角色 Agent：

```text
前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器
```

实现层名称 gatekeeper、radar、negotiator 只在括注、附录或复现材料中保留，不作为正文主叙述。

## 1. 成稿前优先阅读顺序

| 顺序 | 文件 | 用途 |
|---|---|---|
| 1 | `CODEX.md` | 项目协作和论文维护约定 |
| 2 | `gaokaollm_bench/outputs/thesis_document_hub.md` | 论文材料总入口与同步清单 |
| 3 | `gaokaollm_bench/outputs/thesis_claims_manifest.json` | 七实验指标、贡献结构和边界事实源 |
| 4 | `gaokaollm_bench/outputs/thesis_method_experiment_chapters.md` | 第 4-6 章核心正文母版 |
| 5 | `gaokaollm_bench/outputs/thesis_diagrams_with_diagrams.md`、`gaokaollm_bench/outputs/thesis_figures/` | 已生成 SVG/PNG 论文插图 |
| 6 | `gaokaollm_bench/outputs/thesis_figures_tables_pack.md` | 图、表、伪代码和 Mermaid 草稿 |

## 2. 最终 7 章装配表

| 章节 | 建议标题 | 主要来源文档 | 装配要点 |
|---|---|---|---|
| 第 1 章 | 绪论 | `thesis_intro_related_work_chapters.md`、`thesis_agent_benchmark_contribution.md` | 写清高风险志愿咨询、显性红线/隐性妥协、数据 + Agent + Benchmark 三贡献 |
| 第 2 章 | 相关技术 | `thesis_intro_related_work_chapters.md`、`thesis_hierarchical_relaxation_methodology.md` | 组织 RAG、Agent、轻量 MAS、Benchmark、LLM-as-a-Judge、专业树/地域树和 Pareto 妥协 |
| 第 3 章 | 第一版 Agentic RAG 原型系统与问题诊断 | `thesis_v1_prototype_chapter.md`、`thesis_v1_v2_integration_plan.md` | v1 `gaokaollmmodel` 写成工程原型与问题发现，不写成最终主贡献 |
| 第 4 章 | 高考志愿偏好妥协 Benchmark 与数据层构建 | `thesis_method_experiment_chapters.md`、`thesis_system_architecture_algorithms.md` | 写 PostgreSQL 快照、专业树、质量/就业/地域树标准化层、冰山画像和沙盒 |
| 第 5 章 | 证据驱动 Pareto 谈判 Agent 设计 | `thesis_method_experiment_chapters.md`、`thesis_system_architecture_algorithms.md` | 写 `前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器`、各类 relax 算法和轻量 MAS 边界 |
| 第 6 章 | 实验结果、逐例证据与分析 | `thesis_method_experiment_chapters.md`、各 summary/evidence | 主实验与扩展实验分层写，补充 `multi_axis_v1` / `multi_axis_v2` Benchmark 压力测试对照，保留失败样本和 evidence 引用 |
| 第 7 章 | 总结与展望 | `thesis_conclusion_future_work_chapter.md`、`dynamic_decision_considerations_roadmap.md` | 总结 v1 到 v2 的演进，保留真实用户校准、城市收益指标、多省份泛化等后续工作 |

## 3. 图表迁移清单

图像类插图优先使用 `gaokaollm_bench/outputs/thesis_figures/` 下已经生成的 SVG/PNG，作图说明见 `thesis_diagrams_with_diagrams.md`。`thesis_figures_tables_pack.md` 中的 Mermaid 图继续作为概念草稿和结构备份，不再作为最终成稿首选来源。

| 类型 | 建议编号 | 优先来源 / 图像资产 | 迁入位置 |
|---|---|---|---|
| 系统总体架构图 | 图 4-1 | `thesis_figures/fig_4_1_system_architecture.svg` / `.png` | 第 4 章或第 5 章开头 |
| MAS 工作流图 | 图 5-1 | `thesis_figures/fig_5_1_mas_workflow.svg` / `.png` | 第 5 章 Agent 方法 |
| Benchmark 流程图 | 图 4-2 | `thesis_figures/fig_4_2_benchmark_flow.svg` / `.png` | 第 4 章 Benchmark 方法 |
| 数据证据层图 | 图 4-3 | `thesis_figures/fig_4_3_data_evidence_relax_mapping.svg` / `.png` | 第 4 章数据层设计 |
| 七实验结果总表 | 表 6-1 | 主实验 + 五组扩展实验指标 | 第 6 章实验结果 |
| 算法到实验映射表 | 表 5-1 或表 6-2 | relax 算法、数据证据、实验结果、论文意义 | 第 5 章或第 6 章 |
| Benchmark 压力测试表 | 表 6-3 | `multi_axis_v1` / `multi_axis_v2` 指标对照与三类 profile 成功分布 | 第 6 章补充实验或附录 |

## 4. 算法与方法迁移清单

| 方法/算法 | 来源文档 | 建议位置 | 注意事项 |
|---|---|---|---|
| 通用 Pareto opportunity detection | `thesis_figures_tables_pack.md`、`thesis_system_architecture_algorithms.md` | 第 5 章 | 写成显式约束抽取、baseline 查询、机会探测、证据过滤、谈判回复 |
| `major_geo_relax` | `thesis_method_experiment_chapters.md`、`thesis_hierarchical_relaxation_methodology.md` | 第 5 章 | 结合专业树 staged relaxation，不写成简单去掉专业限制 |
| `risk_band_relax` | `thesis_method_experiment_chapters.md` | 第 5 章 | 说明 `score_margin` / `rank_gap` 与 `chong/wen/bao` |
| `tuition_value_relax` | `thesis_method_experiment_chapters.md` | 第 5 章或扩展实验 | 保留 `budget < tuition <= budget + 10000` 窗口 |
| `major_quality_relax` | `thesis_method_experiment_chapters.md` | 第 5 章或扩展实验 | 引用 `school_major_quality_profiles` |
| `employment_outcome_relax` | `thesis_method_experiment_chapters.md` | 第 5 章或扩展实验 | 引用 `major_employment_outcome_profiles` |
| `region_tree_relax` | `thesis_method_experiment_chapters.md`、`thesis_hierarchical_relaxation_methodology.md` | 第 5 章或扩展实验 | 写清 `geo_block_relax` / `urban_tier_relax`，城市层级不直接等价于城市收益 |

## 5. 七实验指标总表

斜杠格式依次为：

```text
elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns
```

| 实验 | 定位 | `app_pareto` | `hard_constraint` | 证据附录 |
|---|---|---:|---:|---|
| `major_geo_v1` | 主实验 | `0.900 / 0.900 / 0.000 / 5.20` | `0.000 / 0.000 / 0.000 / 7.00` | `agent_benchmark_major_geo_v1_evidence.md` |
| `risk_band_v1` | 主实验 | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 15.00` | `agent_benchmark_risk_band_v1_evidence.md` |
| `school_strength_v1` | 扩展实验 | `1.000 / 15.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | `thesis_data_agent_benchmark_extension_evidence.md` |
| `tuition_value_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | `thesis_data_agent_benchmark_extension_evidence.md` |
| `major_quality_v1` | 扩展实验 | `1.000 / 16.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.050 / 11.00` | `thesis_data_agent_benchmark_extension_evidence.md` |
| `employment_outcome_v1` | 扩展实验 | `1.000 / 49.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | `thesis_data_agent_benchmark_extension_evidence.md` |
| `region_tree_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | `agent_benchmark_region_tree_v1_evidence.md` |

注意：`major_geo_v1` 不是 100% 成功，失败样本为 `real-db-set-浙江-569-009`。论文中必须保留该失败样本，避免把 `0.900` 写成完全成功。

`multi_axis_v1` 与 `multi_axis_v2` 不进入上表的七组实验主线，而是作为 Benchmark 压力测试单独报告。`multi_axis_v1` 是历史压力测试版本，结果为 `app_pareto 0.533 / 1.133 / 0.029 / 7.67` vs `hard_constraint 0.000 / 0.000 / 0.000 / 13.00`；三类 profile `major_geo_risk`、`quality_tuition`、`employment_region` 的成功分布分别为 1/10、5/10、10/10。`multi_axis_v2` 是轴一致性修正版，结果为 `app_pareto 0.367 / 1.133 / 0.005 / 9.33` vs `hard_constraint 0.000 / 0.000 / 0.008 / 13.00`；三类 profile 成功分布为 6/10、5/10、0/10。第 6 章建议写成“七实验结果表 + 多轴压力测试对照分析”：v2 修正了无关轴拼接问题，但 `employment_region` 仍暴露就业证据与地域树证据在同一轮谈判中编排不足的瓶颈。

## 6. 证据附录清单

| 附录材料 | 覆盖范围 | 论文用途 |
|---|---|---|
| `agent_benchmark_major_geo_v1_evidence.md` | `major_geo_v1` 10 个 case | 证明主实验 9/10 成功和失败样本 |
| `agent_benchmark_risk_band_v1_evidence.md` | `risk_band_v1` 10 个 case | 证明风险偏好放宽和 `chong/wen/bao` 组合 |
| `thesis_data_agent_benchmark_extension_evidence.md` | `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1` | 证明数据证据维度可扩展 |
| `agent_benchmark_region_tree_v1_evidence.md` | `region_tree_v1` 10 个 case | 证明地域树 reviewed v1 能接入 Agent+Benchmark |
| `agent_benchmark_multi_axis_v1_evidence.md` | `multi_axis_v1` 30 个 case | 证明多轴隐藏妥协压力测试的逐例轴命中与失败原因 |
| `agent_benchmark_multi_axis_v2_evidence.md` | `multi_axis_v2` 30 个 case | 证明轴一致性修正版压力测试的逐例轴命中与失败原因 |

正文中建议只放聚合表和 1-2 个代表 case，完整逐例证据放附录或答辩备查材料。

## 7. LaTeX / BibTeX 待办

- 将 `thesis_intro_related_work_chapters.md` 中的“可替换引用占位”替换为正式 BibTeX 引用。
- 将 Markdown 表格转成浙江大学模板适配的三线表。
- 优先迁入 `thesis_figures/` 下的 SVG/PNG；Mermaid 图保留为可编辑草稿，只有当模板不兼容 SVG/PNG 或需要进一步美化时再重画。
- 统一中文术语：数据贡献、Agent 贡献、Benchmark 贡献、轻量 MAS、多角色 Agent、证据驱动 Pareto 谈判。
- 统一英文术语：`app_pareto`、`hard_constraint`、`elicitation_success_rate`、`mean_pareto_gain`、`mean_hallucination_rate`、`avg_turns`。
- 检查每个实验指标是否仍与 `thesis_claims_manifest.json` 一致。

## 8. 必须保留的边界

- v1 `gaokaollmmodel` 是工程原型与问题发现，不是最终主贡献。
- v2 是最终主贡献，由数据贡献、Agent 贡献和 Benchmark 贡献组成。
- `major_geo_v1 + risk_band_v1` 是主实验。
- `school_strength_v1 + tuition_value_v1 + major_quality_v1 + employment_outcome_v1 + region_tree_v1` 是扩展实验。
- `region_tree_v1` 不替代主实验；城市层级只作为 reviewed region-tree 证据，不直接等价于就业机会、生活成本或城市生活质量收益。
- `multi_axis_v1` 与 `multi_axis_v2` 是 Benchmark 压力测试，不替代主实验，也不改写七组实验主线；它们只组合已有 relax 能力，不新增业务放宽算法。
- `multi_axis_v2` 是轴一致性修正版，不是第八组主实验；三类 profile 仍为 `major_geo_risk`、`quality_tuition`、`employment_region`。
- Agent 不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`；这些字段只作为 simulator / evaluator ground truth。
- 除非用户明确要求，不主动扩展或重跑 thesis audit。

## 9. 最终成稿检查

提交正式论文前，至少做以下检查：

- 七组实验指标与 `thesis_claims_manifest.json` 一致。
- 第 1 章贡献表述和第 7 章总结表述一致。
- 第 3 章不把 v1 写成最终主贡献。
- 第 4 章包含 PostgreSQL、专业树、专业质量、就业结果和地域树 reviewed v1。
- 第 5 章包含轻量 MAS / 多角色 Agent 和各类 relax 算法。
- 第 6 章主实验和扩展实验分层清楚。
- 逐例 evidence 能支撑所有聚合 claim。
- 图表编号、表格编号、附录编号与正文引用一致。
