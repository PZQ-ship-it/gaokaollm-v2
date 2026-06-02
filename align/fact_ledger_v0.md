---
stage: material_fact_ledger
stage_status: confirmed
requires_confirmed: ppt_production_brief
allowed_next_stage: ppt-defense-narrative-stage
confirmed_by: user, 2026-05-31
created_at: 2026-05-31
source_brief: align/ppt_production_brief_v0.md
material_inventory: align/material_inventory_v0.md
---

# 答辩 PPT 事实 ledger v0

## 1. 一句话主张

本毕业设计将高考志愿推荐从一次性生成答案转化为事实约束下的多轮偏好澄清：系统用 PostgreSQL 和标准化证据层生成可审计候选，用非补偿性价值映射、UCB 主动探测、帕累托候选对和 Bradley-Terry 后验更新识别用户隐藏底线，并在受控测试中验证完整交互链路相对静态检索和消融系统的优势。

安全表述：

- 可以说“事实候选来自确定性数据源，LLM 负责语义归一、探测规划和表达组织”。
- 可以说“完整系统在参考基线横评和主消融实验中呈现更好的头部推荐与偏好对齐趋势”。
- 不应说“系统已经替代真实升学顾问”。
- 不应说“专业树/地域树全部语义人工正确”。
- 不应说“所有指标均达到生产级充分验证”，因为终稿仍将真实用户研究、跨省跨年份泛化列为局限。

## 2. 答辩主线建议事实

| 主题 | 可用事实 | 来源 |
| --- | --- | --- |
| 研究问题 | 高考志愿填报是高风险、多目标、强事实约束任务；用户首轮表达常有防御性和不完整性，不等于完整真实偏好。 | `abstract.tex`; `01-introduction.tex` |
| 核心挑战 | 事实与偏好必须分离；偏好不能线性补偿；系统需要主动探测；交互系统需要记忆。 | `01-introduction.tex:64-68` |
| 系统思想 | 从“一次性生成答案”转为“事实约束下的多轮偏好澄清”。 | `01-introduction.tex:72-78`; `07-conclusion.tex:6-8` |
| 事实边界 | 学校、专业、学费、地域、录取分和位次等事实只能来自确定性数据源，不能由语言模型自由生成。 | `01-introduction.tex:66,74`; `abstract.tex` |
| 系统分工 | 事实由数据给出，表达由模型完成，取舍由用户确认。 | `01-introduction.tex:74` |
| 方法闭环 | 非补偿性 SAVF、UCB 主动探测、帕累托候选对、Bradley-Terry 后验追踪、证据不确定性膨胀机制。 | `abstract.tex`; `02-problem-algorithm.tex`; `03-system-design.tex` |
| 工程闭环 | 数据层、智能体服务层、推荐决策层、交互展示层和受控测试环境组成完整工程闭环。 | `01-introduction.tex:78`; `03-system-design.tex` |
| 评测目标 | 从单轮答案正确性扩展到多轮过程正确性，检查是否发现隐藏底线且不编造事实。 | `01-introduction.tex:68`; `04-system-test-evaluation.tex` |

## 3. 贡献 ledger

| 贡献 | 安全表达 | 主要证据 | PPT 使用建议 |
| --- | --- | --- | --- |
| 问题定义 | 提出“冰山式偏好”问题定义，将高风险志愿推荐的评价重点从回答流畅推进到隐藏底线识别。 | `01-introduction.tex:83-89`; `07-conclusion.tex:12` | 放在开场后的“为什么需要多轮澄清”页 |
| 数据证据层 | 构建招生事实表、专业树、学费字段、培养质量画像和地域树等证据底座，使候选事实可审计。 | `07-conclusion.tex:14`; `03-system-design.tex`; 专业树/地域树报告 | 与系统架构页或数据页合并 |
| 推荐决策模块 | 组合非补偿性 SAVF、UCB、帕累托候选对和 Bradley-Terry 后验追踪，在结构化事实约束下更新偏好状态。 | `07-conclusion.tex:16`; `02-problem-algorithm.tex`; `03-system-design.tex` | 方法核心 2-3 页 |
| 可回放运行时链路 | 用状态机组织语义归一、约束解析、证据探针、澄清问题、用户反馈和终局推荐。 | `07-conclusion.tex:18`; `fig:runtime-state-machine` | 系统实现页 |
| 受控测试集 | 构建带隐藏底线的用户画像、自动对弈日志和定量指标，使隐藏偏好澄清可复查。 | `07-conclusion.tex:20`; `04-system-test-evaluation.tex:101-127` | 实验设计页 |

## 4. 数据与证据层事实

| 事实 | 数值/边界 | 来源 | 风险提示 |
| --- | --- | --- | --- |
| 专业层级本体全量覆盖 v2 | `22,759 / 22,759` 原始去重专业名，`140,995 / 140,995` 录取记录，`remaining_unassigned = 0` | `major_tree_annotation_summary.md`; `thesis_claims_manifest.json` | 这是可审计挂载覆盖，不代表全部语义边界人工确认正确 |
| 专业树来源分布 | 规则挂载 18,587；probe auto assigned 3,238；DeepSeek-R1 reviewed 881；LLM abstain probe fallback 53 | `major_tree_annotation_summary.md` | LLM 是低置信复核辅助，不是全量自动标注器 |
| 专业树 clean validation | 最优策略 Accuracy 0.7169、Macro-F1 0.7136；Hit@10 0.9819；剩余错分 `47 / 166` | `major_tree_annotation_summary.md` | 验证集结果不可外推为全库正确率 |
| 地域层级画像覆盖 | 414 个省-市对、3,219 所学校、35 个省份映射、remaining unassigned 0 | `region_urban_tier_tree_full_coverage_v2_report.md` | 不编码城市收益或 Pareto gain |
| 地域树来源 | existing_seed 67；packet_suggested 347；review queue 0 | `region_urban_tier_tree_full_coverage_v2_report.md` | `reviewed_v1` 是历史 seed |

## 5. 系统与算法事实

| 模块/机制 | 事实 | 来源 | 答辩安全说法 |
| --- | --- | --- | --- |
| 静态混合检索基线 | 显式约束归一、PostgreSQL 硬过滤、向量相关性打分、Qwen3-Reranker 二阶重排、冲稳保分段和自然语言解释。 | `02-problem-algorithm.tex:81-103` | 它是强工程基线，但仍主要依赖显式话语和一次性候选排序 |
| 非补偿性 SAVF | 用单属性价值函数保护预算、地域、专业等底线，避免严重违约被学校层次线性抵消。 | `02-problem-algorithm.tex:119-152`; `abstract.tex` | 用“保护底线”解释即可，避免过度公式化 |
| UCB 主动探测 | 用 UCB 启发式选择最值得澄清的偏好维度。 | `02-problem-algorithm.tex:171+`; `03-system-design.tex`; `fig:ucb-dispatch` | UCB 是工程近似，不要说成严格最优信息增益 |
| 帕累托候选对 | 系统构造具有边际替代关系的 A/B 候选，让用户看到“放宽什么换来什么”。 | `02-problem-algorithm.tex:64`; `03-system-design.tex:317-339` | 强调证据驱动的取舍呈现 |
| Bradley-Terry 后验 | 将用户接受、拒绝或偏好反馈转为在线偏好状态。 | `abstract.tex`; `02-problem-algorithm.tex`; `03-system-design.tex` | 与“交互系统需要记忆”配套讲 |
| LangGraph interrupt/resume | 隔离探索期和终局推荐期，使系统先澄清关键不确定性，再生成解释方案。 | `abstract.tex`; `fig:runtime-state-machine` | 作为工程可回放机制，不夸大为完全自治多智能体 |

## 6. 实验 ledger

### 6.1 终稿第 4 章主实验

| 实验层 | 事实 | 来源 | PPT 用法 |
| --- | --- | --- | --- |
| 参考基线横评 | 五个基座模型：智谱 GLM-5.1、深度求索 V3.2、MiniMax M2.5、Kimi-K2.6、Qwen3.6；每个模型比较完整系统、静态检索-直接提示、静态检索-思维链提示。 | `04-system-test-evaluation.tex:101-115` | 一页讲实验设计 |
| 数据规模 | 围绕 180 条受控测试画像组织自动化运行。 | `04-system-test-evaluation.tex:127` | 放在实验设计页 |
| 参考基线结果 | 完整系统在五个模型上 F1@1 约 0.721-0.743，F1@3 约 0.633-0.644，F1@5 约 0.680-0.707；静态检索直接提示多为 0.700 / 0.600 / 0.673；思维链提示未稳定超过完整系统。 | `04-system-test-evaluation.tex:151-183` | 用图 `fig_4_5_c1_baseline_model_target`，避免逐项念表 |
| 主消融设置 | 固定智谱 GLM-5.1，比较完整系统、去除主动探测、去除后验追踪。 | `04-system-test-evaluation.tex:117-124` | 一页讲模块贡献 |
| 主消融结果 | 完整系统 MAE `0.144±0.045`，F1@1 `0.767±0.430`，F1@3 `0.667±0.371`，F1@5 `0.700±0.277`；去除主动探测 MAE 上升到 `0.178±0.035`；去除后验追踪 F1 系列低于完整系统。 | `04-system-test-evaluation.tex:211-238` | 用 `fig_4_6_c1_ablation_core_metrics`，强调趋势 |
| 过程指标 | 完整系统更能命中有效探测方向、保持权衡张力并更新后验状态。 | `04-system-test-evaluation.tex:266-296` | 可作为备份或方法证明页 |

### 6.2 项目 manifest 中的历史/旧口径实验

`thesis_claims_manifest.json` 与 `thesis_document_hub.md` 仍保存“数据 + Agent + Benchmark”旧组织下的七组实验、压力测试和 pilot 数值。这些内容对理解项目演化有价值，但当前答辩 PPT 应优先服务最终 LaTeX 第 4 章的 180 条受控测试画像实验。

可作为备份事实：

- 旧主实验：`major_geo_v1`、`risk_band_v1`。
- 旧扩展实验：`school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1`。
- `major_geo_v1` 不是 100% 成功，失败样本为 `real-db-set-浙江-569-009`。
- `multi_axis_v2` 是轴一致性多轴隐藏妥协压力测试，不是第八组主实验。
- `v1_hybrid_rag` 是补充基线 pilot，不进入正式七组实验主表。

风险：这些旧口径不应覆盖当前终稿第 4 章的主要实验叙事；若用于备份页，必须标注为项目演化/历史口径。

## 7. 术语 ledger

| 工程名或旧称 | PPT 推荐说法 | 来源 |
| --- | --- | --- |
| `gaokaollmmodel` | 第一版志愿咨询原型系统 | `thesis_term_mapping.json` |
| `app_pareto` | 证据谈判 Agent / 完整系统 | `thesis_term_mapping.json`，但终稿第 4 章多用“完整系统” |
| `hard_constraint` | 硬约束基线 | `thesis_term_mapping.json` |
| `semantic_normalizer` | 前置语义归一层 | `thesis_term_mapping.json` |
| `gatekeeper` | 约束解析器 | `thesis_term_mapping.json` |
| `radar planner` | LLM 引导的机会规划器 | `thesis_term_mapping.json` |
| `deterministic probe` | 确定性证据探针 | `thesis_term_mapping.json` |
| `negotiator` | 证据谈判器 | `thesis_term_mapping.json` |
| `implicit_flexibilities`, `volunteer_set`, `axis_flexibilities` | 评测端隐藏偏好字段 / 隐藏 ground truth | `thesis_term_mapping.json`; `thesis_claims_manifest.json` |

## 8. 高风险问答与安全回答

| 可能问题 | 安全回答锚点 |
| --- | --- |
| 大模型会不会编造学校和分数？ | 系统把事实候选限定在 PostgreSQL 和标准化证据层，LLM 不直接生成学校、专业、分数、位次或学费；它负责语义归一、探测规划和表达组织。 |
| 为什么不用一次性 RAG 就够了？ | 一次性 RAG 能找事实，但不能自然发现隐藏底线；本文把 RAG 证据层和多轮偏好澄清结合起来，让用户通过具体 A/B 取舍确认真实边界。 |
| UCB 是不是理论最优？ | 不是严格最优信息增益推导，而是用于工程系统的启发式选轴策略；论文也把进一步比较随机选轴、最大方差、最大均值与 UCB 列为后续工作。 |
| 实验是不是只在模拟用户上做？ | 是，当前受控测试集适合验证机制差异，但不能替代真实用户研究；论文结论中明确将真实用户或专家小规模评估列为后续工作。 |
| 专业树全量覆盖是不是都人工检查正确？ | 不是。全量覆盖指所有原始专业名都有可审计挂载路径；语义边界仍有验证集错分和后续 HITL 优化空间。 |
| 地域层级能否代表就业机会和生活质量？ | 不能直接等价。地域树是地理/城市层级证据，不编码城市收益、生活成本或就业机会。 |
| 为什么完整系统提升不大但还值得做？ | 志愿推荐更关注头部候选和偏好边界是否可信；完整系统的贡献在于把事实、取舍、反馈和后验状态连成可复查机制，而不是单轮模型能力堆叠。 |

## 9. 图表使用决策

优先进入主线的图表：

1. `fig_4_1_system_architecture`：系统四层架构。
2. `fig_4_6_database_physical_schema` 或数据证据层简化图：事实来源。
3. `fig_5_1_mas_workflow`：交互式偏好澄清工作流。
4. `fig_5_3_ucb_dispatch`：主动探测调度链路。
5. `fig_3_5_elicitation_console` / `fig_3_6_final_decision_report`：系统界面证据。
6. `fig_4_2_benchmark_flow`：多轮评测流程。
7. `fig_4_5_c1_baseline_model_target`：参考基线横评。
8. `fig_4_6_c1_ablation_core_metrics`：主消融实验。

适合作备份或视时间取舍：

- `fig_4_4_major_tree_partial`
- `fig_4_5_region_hierarchy_partial`
- `fig_5_2_runtime_state_machine`
- `fig_4_8_1_c1_planner_process`
- `fig_4_8_2_c1_negotiator_process`
- `fig_4_8_3_c1_tracker_process`

## 10. 已发现冲突与风险

| 风险 | 说明 | 后续处理 |
| --- | --- | --- |
| 旧三贡献口径与当前终稿叙事不完全一致 | `CODEX.md`、hub、manifest 强调“数据 + Agent + Benchmark”；当前最终 LaTeX 更突出“冰山式偏好 + 事实约束多轮澄清 + 受控测试”。 | defense narrative 阶段以当前 PDF/LaTeX 为主，把数据/Agent/Benchmark 作为支撑结构而不是硬塞成唯一主线 |
| 终稿一致性报告疑似滞后 | 报告描述 7 章结构和旧 PDF 大小/时间；当前 `content.tex` 是 5 个主要章节，PDF 写入时间为 2026-05-18 17:44:45。 | 不把该报告作为当前章节结构事实源，只保留旧口径残留检查项 |
| 图目录含未引用或历史图 | LaTeX 终稿图目录包含多个旧 robust/pressure 图和候选图。 | storyboard 和 asset/layout 阶段优先使用 LaTeX 引用图，不按文件夹全量纳入 |
| 项目工作区有大量未跟踪/修改结果 | `git status` 显示不少实验输出、图和代码改动。 | 当前不清理、不覆盖；后续只按终稿和 confirmed ledger 引用 |
| Python 默认版本为 3.7 | 运行新脚本可能受版本影响。 | 若后续需要作图，先激活/验证 `gaokao_pg`，再运行最小命令 |

## 11. 本阶段不确认的内容

- 不确认最终 slide 顺序。
- 不确认最终图表数量。
- 不确认 speaker notes。
- 不确认备份页数量。
- 不确认是否需要重新作图。
- 不确认 AI 生成学术图；production brief 仍默认未授权 OpenRouter ICU Image。
