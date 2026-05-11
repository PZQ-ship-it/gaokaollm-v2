# 论文文档总入口与维护索引

本文档是毕业论文材料的查阅入口和维护索引。它不替代任何实验 summary、transcript、evidence 附录或正文母版，也不新增实验结论。后续如果要修改论文口径、实验指标、MAS 表述或地域树边界，建议先查看本文件和 `thesis_claims_manifest.json`，再按同步清单更新相关文档。

## 1. 当前统一口径

| 项目 | 当前口径 |
| --- | --- |
| 论文贡献结构 | 数据贡献 + Agent 贡献 + Benchmark 贡献 |
| 数据贡献 | PostgreSQL 招生快照、专业树、学费字段、专业质量标准化层、就业结果标准化层、经人工审校的地域层级画像 |
| Agent 贡献 | 前置语义归一层、约束解析器、LLM 引导的机会规划器、确定性证据探针和证据谈判器组成的轻量 MAS/多角色 Agent，执行证据驱动 Pareto 谈判 |
| Benchmark 贡献 | 冰山画像、多轮沙盒、事实/过程联合评价、`app_pareto` vs `hard_constraint` |
| 主实验 | `major_geo_v1 + risk_band_v1` |
| 扩展实验 | `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1` |
| Hidden persona 边界 | Agent 不读取 `implicit_flexibilities` 或 `volunteer_set`；这些字段只作为 evaluator ground truth |
| MAS 边界 | 本文采用基于角色分工的轻量 MAS/多角色 Agent，不写成完全自治多智能体系统 |
| 地域树边界 | `region_tree_v1` 是扩展实验；城市层级只作为 经人工审校的地域层级证据，不直接等价于就业机会、生活成本或生活质量收益 |

机器可读事实源：`gaokaollm_bench/outputs/thesis_claims_manifest.json`。术语事实源：`gaokaollm_bench/outputs/thesis_term_mapping.json`。

专业树全量覆盖 v2 已同步到机器事实源的 `data_artifacts.major_tree_full_coverage_v2`，详细说明见 `major_tree_annotation_summary.md`。

### 1.1 当前 MAS 架构事实

当前业务 Agent 的论文主叙述为：`前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器`。实现层可追溯为 `semantic_normalizer -> gatekeeper -> llm-guided radar planner -> deterministic probes -> negotiator`。

前置语义归一层继承 v1 查询重写能力，只对用户显式话语做语义归一、偏好轴拆解和歧义提示。LLM 引导的机会规划器只输出 `probe_plan`、`opportunity_rankings` 和 `clarification_hint`；确定性证据探针仍是学校、专业、分数、位次等事实候选的唯一来源。证据谈判器负责把候选证据组织为可审计的 Pareto 谈判回复。

LLM 不生成事实候选，Agent 不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`。验收说明见 `thesis_mas_architecture_acceptance.md`。


## 2. 七组实验事实表

斜杠格式依次为：`elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns`。

| 实验 | 定位 | 机会类型 | `app_pareto` | `hard_constraint` | Summary | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `major_geo_v1` | 主实验 | `major_geo_relax` | `0.900 / 0.900 / 0.000 / 5.20` | `0.000 / 0.000 / 0.000 / 7.00` | `agent_benchmark_major_geo_v1_summary.md` | `agent_benchmark_major_geo_v1_evidence.md` |
| `risk_band_v1` | 主实验 | `risk_band_relax` | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 15.00` | `agent_benchmark_risk_band_v1_summary.md` | `agent_benchmark_risk_band_v1_evidence.md` |
| `school_strength_v1` | 扩展实验 | `strength_relax` | `1.000 / 15.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | `agent_benchmark_school_strength_v1_summary.md` | `thesis_data_agent_benchmark_extension_evidence.md` |
| `tuition_value_v1` | 扩展实验 | `tuition_value_relax` | `1.000 / 1.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | `agent_benchmark_tuition_value_v1_summary.md` | `thesis_data_agent_benchmark_extension_evidence.md` |
| `major_quality_v1` | 扩展实验 | `major_quality_relax` | `1.000 / 16.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.050 / 11.00` | `agent_benchmark_major_quality_v1_summary.md` | `thesis_data_agent_benchmark_extension_evidence.md` |
| `employment_outcome_v1` | 扩展实验 | `employment_outcome_relax` | `1.000 / 49.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | `agent_benchmark_employment_outcome_v1_summary.md` | `thesis_data_agent_benchmark_extension_evidence.md` |
| `region_tree_v1` | 扩展实验 | `region_tree_relax` | `1.000 / 1.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | `agent_benchmark_region_tree_v1_summary.md` | `agent_benchmark_region_tree_v1_evidence.md` |

注意：`major_geo_v1` 不是 100% 成功，失败样本为 `real-db-set-浙江-569-009`。

## 2.1 Benchmark 压力测试事实表

压力测试不替代七组实验事实表，也不改变主实验 `major_geo_v1 + risk_band_v1` 的定位。它们用于检查 Benchmark 在更复杂隐藏妥协结构下是否仍能区分“单轴命中”和“多轴同时命中”。

| 压力测试 | 定位 | 画像规模 | `app_pareto` | `hard_constraint` | Profile 结果 | Summary | Evidence |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| `multi_axis_v1` | 多轴隐藏妥协压力测试历史版 | 30 | `0.533 / 1.133 / 0.029 / 7.67` | `0.000 / 0.000 / 0.000 / 13.00` | `major_geo_risk` 1/10；`quality_tuition` 5/10；`employment_region` 10/10 | `agent_benchmark_multi_axis_v1_summary.md` | `agent_benchmark_multi_axis_v1_evidence.md` |
| `multi_axis_v2` | 轴一致性修正版压力测试 | 30 | `0.367 / 1.133 / 0.005 / 9.33` | `0.000 / 0.000 / 0.008 / 13.00` | `major_geo_risk` 6/10；`quality_tuition` 5/10；`employment_region` 0/10 | `agent_benchmark_multi_axis_v2_summary.md` | `agent_benchmark_multi_axis_v2_evidence.md` |

`multi_axis_v2` 的目标不是追求更高聚合成功率，而是修复 v1 中部分交叉画像轴不一致的问题。v2 要求两个隐藏放宽轴围绕一致的显性需求或可解释的正交需求构造；因此它更适合用于论文中的压力测试诊断。当前结果显示：专业-地域与风险组合的联合命中从 v1 的 1/10 改善到 6/10；专业质量与学费组合保持 5/10；就业与地域组合暴露出 Agent 能稳定给出就业证据但未能同步给出地域树证据的问题。

## 3. 文档地图

### 3.1 正文母版

| 文档 | 角色 | 维护建议 |
| --- | --- | --- |
| `thesis_full_draft_v1.md` | 第 1-7 章连续正文总稿 | 修改章节装配、图表占位或最终成稿主线时优先同步 |
| `thesis_term_mapping.json` | 正文术语与工程标识映射 | 修改术语、实验 id 展示方式或去工程化规则时优先同步 |
| `thesis_intro_related_work_chapters.md` | 第 1-2 章绪论与相关技术正文母版 | 修改贡献结构或实验总览时同步 |
| `thesis_v1_prototype_chapter.md` | 第 3 章 v1 原型与问题诊断正文母版 | 修改 v1/v2 关系时同步 |
| `thesis_method_experiment_chapters.md` | 方法与实验章节主文母版 | 修改数据层、Agent 算法、实验指标时优先同步 |
| `thesis_conclusion_future_work_chapter.md` | 第 7 章总结与展望正文母版 | 修改最终贡献总结和后续工作时同步 |

### 3.2 贡献、路线图、架构与图表

| 文档 | 角色 | 维护建议 |
| --- | --- | --- |
| `thesis_agent_benchmark_contribution.md` | 摘要、绪论、答辩 PPT 可复用的贡献母版 | 修改贡献列表或结果表时优先同步 |
| `thesis_v1_v2_integration_plan.md` | v1/v2 论文组织方案 | 修改 v1 定位或 v2 主线时同步 |
| `thesis_system_architecture_algorithms.md` | MAS、系统架构和算法设计正文母版 | 修改 Agent 架构或算法清单时同步 |
| `thesis_figures_tables_pack.md` | 图、表、伪代码和答辩素材包 | 修改实验数量、图表标题或算法映射时同步 |
| `thesis_diagrams_with_diagrams.md` | 手工 SVG/PNG 论文框图生成说明与渲染命令 | 修改论文图像生成方式或图号时同步 |
| `thesis_figure_visual_acceptance.md` | 当前论文插图在 PDF 中的视觉验收报告 | 重绘插图、替换图号或调整 LaTeX 图位置后同步 |
| `thesis_latex_final_consistency_report.md` | 正式 LaTeX 终稿事实一致性与编译验收记录 | 提交前复查 `zjuthesis.pdf`、事实口径、编译结果和剩余版式 warning |
| `thesis_figures/` | 当前可迁入论文/PPT 的 SVG/PNG 图像资产 | 重新渲染图像或替换正式插图时同步 |
| `thesis_figures_pdf_snapshots/` | LaTeX PDF 页面快照 | 检查图像是否裁切、重叠或与正文口径不一致 |
| `dynamic_decision_considerations_roadmap.md` | 动态决策路线图 | 修改后续开发优先级和能力矩阵时同步 |
| `gaokaollm_bench/放宽与跃迁.md` | 动态放宽与 Pareto 跃迁总览 | 修改放宽能力清单和实验总览时同步 |

说明：`thesis_figures_tables_pack.md` 中的 Mermaid 图保留为概念草稿和可编辑结构说明；当前正式写论文或做答辩 PPT 时，优先使用 `thesis_figures/` 中由手工 SVG/PNG 论文框图生成器生成的图像资产。Diagrams 仅作为早期探索和概念草稿来源保留。

### 3.3 方法论与数据层说明

| 文档 | 角色 | 维护建议 |
| --- | --- | --- |
| `benchmark_methodology.md` | Benchmark 方法学说明 | Benchmark schema 或评测原则变化时同步 |
| `major_tree_methodology.md` | 专业树构建方法说明 | 专业树统计或审校流程变化时同步 |
| `major_tree_annotation_summary.md` | 专业树标注实验与全量覆盖 v2 汇总 | 专业树覆盖、模型候选、LLM 复核或错分聚类变化时同步 |
| `thesis_hierarchical_relaxation_methodology.md` | 专业树与地域树层级放宽方法论 | 层级放宽、HITL、地域树边界变化时同步 |

### 3.4 逐例证据与实验产物

| 文档 | 覆盖范围 | 维护建议 |
| --- | --- | --- |
| `agent_benchmark_major_geo_v1_evidence.md` | `major_geo_v1` 逐例 evidence | 主实验重跑或 case 解释变化时同步 |
| `agent_benchmark_risk_band_v1_evidence.md` | `risk_band_v1` 逐例 evidence | 主实验重跑或风险证据变化时同步 |
| `thesis_data_agent_benchmark_extension_evidence.md` | `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1` | 四组数据扩展实验重跑时同步 |
| `agent_benchmark_region_tree_v1_evidence.md` | `region_tree_v1` 逐例 evidence | 地域树实验重跑或地域树解释变化时同步 |
| `agent_benchmark_multi_axis_v1_evidence.md` | `multi_axis_v1` 历史压力测试逐例 evidence | 只在说明历史压力测试时引用 |
| `agent_benchmark_multi_axis_v2_evidence.md` | `multi_axis_v2` 轴一致性压力测试逐例 evidence | 压力测试修正版重跑或解释变化时同步 |

### 3.5 历史报告与数据质量报告

| 文档 | 角色 | 维护建议 |
| --- | --- | --- |
| `region_tree_coverage_report.md` | 地域树 v0 覆盖报告 | 历史/数据质量报告，不作为当前论文主口径事实源 |
| `region_tree_v1_coverage_report.md` | 地域树 v1 覆盖报告 | 历史/数据质量报告，不作为当前七实验主结果表 |
| `thesis_artifact_audit.md` | 早期论文产物审计报告 | 当前用户已暂停审计；不要为了普通正文维护而更新 |

## 4. 常见修改场景同步清单

| 场景 | 先改 | 再同步 |
| --- | --- | --- |
| 新增或删除实验 | `thesis_claims_manifest.json`、本 hub | 方法实验正文、贡献母版、路线图、放宽总览、系统架构、图表包、总结章 |
| 修改实验指标 | `thesis_claims_manifest.json`、对应 summary/evidence | 结果表所在正文母版和 PPT/图表素材 |
| 修改 MAS 表述 | 本 hub、系统架构算法母版、术语映射 | 方法正文、贡献母版、绪论、图表包 |
| 修改图像资产或图号 | `thesis_diagrams_with_diagrams.md`、`thesis_figures/`、`thesis_figure_visual_acceptance.md` | 图表包、最终成稿装配清单、README 入口 |
| 修改 hidden persona 边界 | `thesis_claims_manifest.json`、本 hub | 方法正文、证据附录、Benchmark 方法学 |
| 修改地域树边界 | 本 hub、术语映射、层级放宽方法论 | 放宽总览、路线图、系统架构、region evidence |
| 修改 v1/v2 关系 | v1/v2 整合方案 | 第 3 章、绪论、总结章 |
| 修改后续工作 | 路线图、总结章 | 绪论和放宽总览中的展望段落 |

## 5. 使用建议

1. 写论文正文时，先查 `thesis_full_draft_v1.md`；需要展开局部章节时，再查 `thesis_method_experiment_chapters.md` 和 `thesis_system_architecture_algorithms.md`。
2. 写摘要、创新点、答辩 PPT 时，先查 `thesis_agent_benchmark_contribution.md`、`thesis_figures_tables_pack.md`、`thesis_diagrams_with_diagrams.md`、`thesis_figure_visual_acceptance.md` 和 `thesis_figures/`。
3. 查逐例证据时，按主实验 evidence、扩展 evidence、region evidence 三类入口进入。
4. 做全局口径变更时，先更新 `thesis_claims_manifest.json`、`thesis_term_mapping.json` 与本 hub，再按第 4 节同步相关母版。
5. coverage report、artifact audit 等历史报告只用于追溯，不建议为了当前论文口径反复改写。
6. 提交正式论文或同步 LaTeX 终稿后，查看 `thesis_latex_final_consistency_report.md`；若重编译、改图或改实验口径，应重新生成该报告。

- `thesis_mas_architecture_acceptance.md`：新 MAS 架构接入、LLM 参与边界和 smoke/regression 验收说明。
