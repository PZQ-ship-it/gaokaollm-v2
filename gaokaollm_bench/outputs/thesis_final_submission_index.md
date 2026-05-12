# 毕业论文最终提交包清单与导师审阅索引

本文档是提交前总入口，用于把正式 PDF、LaTeX 源码、论文事实源、验收报告和可复查 evidence 集中到一处。它不替代 `thesis_document_hub.md`、`thesis_claims_manifest.json` 或 LaTeX 正文，只用于提交前快速核对。

## 1. 最终交付物

| 项目 | 路径 / 状态 |
| --- | --- |
| 最终 PDF | `D:\毕设\latex-for-zju-master\latex-for-zju-master\out\zjuthesis.pdf` |
| PDF 大小 | `3,578,125` bytes |
| PDF 最近写入时间 | `2026-05-12 21:17:38` |
| LaTeX 主入口 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\zjuthesis.tex` |
| 正文入口 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\final\content.tex` |
| 正文章节目录 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\final\chapters\` |
| 摘要文件 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\final\abstract.tex` |
| 参考文献 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\body\ref.bib` |
| 图片目录 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\` |

当前 LaTeX 终稿使用浙江大学本科毕业设计模板，正文按第 1-7 章组织，并保留实验材料说明、第一版基准系统工程机制索引和作者简历。

## 2. 事实源与维护入口

| 类型 | 文件 | 用途 |
| --- | --- | --- |
| 总入口 | `thesis_document_hub.md` | 论文材料地图、实验事实表、同步规则 |
| 机器事实源 | `thesis_claims_manifest.json` | 七组实验、压力测试、数据 artifact 的机器可读事实 |
| 术语事实源 | `thesis_term_mapping.json` | 正文术语与工程标识边界 |
| 专业树事实源 | `major_tree_annotation_summary.md` | 专业树标注实验、DeepSeek-R1 低置信复核、全量覆盖 v2 |
| 最终装配清单 | `thesis_final_assembly_checklist.md` | 从 Markdown 母版到正式论文的装配核对 |
| 连续正文母版 | `thesis_full_draft_v1.md` | Markdown 连续草稿，供后续大修参考 |

提交前若发现事实、指标或术语需要修改，应先更新 `thesis_claims_manifest.json`、`thesis_document_hub.md` 和相关事实源，再同步 LaTeX 正文和验收报告。

## 3. 编译与视觉验收入口

| 验收材料 | 结论 |
| --- | --- |
| `thesis_latex_final_consistency_report.md` | `zjuthesis.pdf` 已生成；无 LaTeX fatal error；无 undefined references / citations；无 overfull `\hbox`。 |
| `thesis_latex_pdf_visual_acceptance.md` | 封面、致谢、摘要、目录、核心图、专业树表、七组实验表、`v1_hybrid_rag` pilot 表、多轴压力测试表、附录边界和作者简历页面通过最新 PDF 页面级视觉验收。 |
| `thesis_final_human_review_check.md` | 记录最新 PDF 下递交日期、英文题名、致谢和作者简历已补齐，并保留提交前人工核对建议。 |
| `thesis_latex_pdf_snapshots/` | 关键 PDF 页面快照，可用于快速复查真实版式效果。 |
| `thesis_figure_visual_acceptance.md` | 核心图像资产在论文 PDF 中的视觉验收记录。 |

提交前最后一次修改 LaTeX 后，应重新运行 `latexmk -xelatex -outdir=out zjuthesis`，并更新上述验收报告中的 PDF 时间、编译结果和页面快照。

## 4. 一页式贡献核对

### 数据贡献

- PostgreSQL 招生事实快照支撑分数、位次、选科、招生计划、学费和录取记录查询。
- 专业层级本体完成全量覆盖 v2：`22,759 / 22,759` 个原始去重专业名、`140,995 / 140,995` 条录取记录完成可审计挂载，`remaining_unassigned = 0`。
- 学校-专业质量画像、专业就业结果画像和经人工审校的地域层级画像为扩展偏好轴提供标准化证据。
- “全覆盖”表示所有原始专业名进入可追溯叶子簇，不等于全部语义边界已由人工逐条确认正确。

### Agent 贡献

- 业务 Agent 写作轻量 MAS / 多角色 Agent。
- 正文主叙述为：前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器。
- LLM 只负责语义归一、机会规划、证据排序和澄清提示。
- 学校、专业、分数、位次、学费、就业和地域候选只来自确定性证据探针。

### Benchmark 贡献

- Benchmark 使用冰山用户画像、多轮沙盒、事实/过程联合评价和证据谈判 Agent 对硬约束基线的对照。
- 主实验为 `major_geo_v1 + risk_band_v1`。
- 五组扩展实验为 `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1`。
- `multi_axis_v1` 与 `multi_axis_v2` 是 Benchmark 压力测试；`multi_axis_v2` 是轴一致性修正版，不进入七组实验主表。

## 5. 证据与结果入口

| 类型 | 文件 |
| --- | --- |
| 专业-地域联合放宽逐例证据 | `agent_benchmark_major_geo_v1_evidence.md` |
| 风险组合放宽逐例证据 | `agent_benchmark_risk_band_v1_evidence.md` |
| 四组数据扩展实验逐例证据 | `thesis_data_agent_benchmark_extension_evidence.md` |
| 地域层级放宽逐例证据 | `agent_benchmark_region_tree_v1_evidence.md` |
| 多轴压力测试历史版逐例证据 | `agent_benchmark_multi_axis_v1_evidence.md` |
| 多轴压力测试修正版逐例证据 | `agent_benchmark_multi_axis_v2_evidence.md` |
| 专业树标注与全量覆盖事实 | `major_tree_annotation_summary.md` |
| v1 混合检索基线 pilot 逐例证据 | `agent_benchmark_v1_hybrid_rag_pilot_evidence.md` |

`major_geo_v1` 不是 100% 成功，唯一失败样本为 `real-db-set-浙江-569-009`。论文中应保留这一失败样本，避免把主实验包装成完全成功。

## 6. 提交前人工检查项

| 检查项 | 建议处理 |
| --- | --- |
| 封面提交日期 | 已填 `2026年5月12日`；提交前按学校最终要求核对。 |
| 导师署名与学生信息 | 与学院系统和模板要求逐项核对。 |
| 致谢 | 已补正式致谢文本；提交前可按个人真实情况微调。 |
| 作者简历 | 已补简短作者简历；提交前按学院要求确认。 |
| 参考文献格式 | 检查引用是否满足学院要求，确认 BibTeX 条目完整。 |
| 图片清晰度 | PDF 已通过页面级验收；答辩 PPT 建议使用 `thesis_figures/` 中的原始 SVG/PNG，尤其是架构图、Benchmark 图、专业层级本体局部图和地域层级画像局部图。当前新增树形局部图已进入第 4 章。 |
| 表格与图题 | 确认图表编号、正文引用和目录一致。 |
| 学校模板要求 | 复查 `Degree = undergraduate`、`Type = design`、`Period = final`。 |
| 隐藏字段边界 | 确认正文和附录仍写明 Agent 不读取 `implicit_flexibilities`、`volunteer_set`、`axis_flexibilities`。 |

## 7. 不应在提交前临时改动的内容

- 不临时重跑七组 Agent/Benchmark 实验，除非明确要更新所有 summary、evidence、manifest 和 LaTeX 结果表。
- 不把 `multi_axis_v2` 写入七组实验主表。
- 不把城市层级写成就业机会、生活成本或城市生活质量收益。
- 不把专业树全量覆盖 v2 写成“全部语义边界人工确认正确”。
- 不把 v1 基准系统写成最终主贡献；v1 是问题来源、工程基础和语义归一能力来源，v2 是最终数据 + Agent + Benchmark 闭环。
- 不把 `v1_hybrid_rag` pilot 写入七组正式实验主表；它只是软约束 RAG / 冲稳保推荐的补充系统基线。

## 8. 最终建议

在正式提交前，建议按以下顺序复查：

1. 打开 `zjuthesis.pdf` 做人工通读。
2. 对照 `thesis_latex_final_consistency_report.md` 确认编译状态。
3. 对照 `thesis_latex_pdf_visual_acceptance.md` 查看关键页面快照。
4. 对照 `thesis_final_human_review_check.md` 确认递交日期、英文题名、致谢、作者简历和 `v1_hybrid_rag` pilot 入口等提交信息。
5. 对照本文档第 4-6 节确认贡献、证据和人工待办。
6. 只在确有必要时修改 LaTeX；修改后重新编译并更新验收报告。

