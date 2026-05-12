# 论文插图资产视觉验收与维护说明

本文档记录当前论文核心插图的生成方式、PDF 版式快照和视觉验收结果。它不新增实验结论，不修改七组 Agent-vs-Baseline 实验指标，也不替代 `thesis_claims_manifest.json` 或 `thesis_document_hub.md`。

## 1. 当前图源口径

当前正式论文和答辩 PPT 优先使用 `gaokaollm_bench/outputs/thesis_figures/` 下的 SVG/PNG 图像资产。这些图由 `gaokaollm_bench/tests/manual/render_thesis_diagrams.py` 生成；脚本采用手工 SVG 论文框图布局，并使用本地 Edge/Chrome headless 导出 PNG。早期 Diagrams / Mermaid 版本仅作为概念草稿和历史探索，不作为当前最终图像事实源。

图内 MAS 主路径采用当前论文口径：

`前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器`

边界说明：

- LLM 只负责查询归一、机会排序、证据编排顺序和澄清提示。
- 学校、专业、最低分、最低位次、学费、专业质量、就业结果和地域层级候选均来自确定性证据探针。
- 业务 Agent 不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`。
- `gatekeeper`、`radar`、`negotiator` 可作为实现层括注保留，但不作为图题和主路径叙述。

## 2. 图像资产清单

| 图号 | 论文图题 | 图像资产 | LaTeX 位置 | PDF 快照 |
| --- | --- | --- | --- | --- |
| 图 4.1 | 数据 + Agent + Benchmark 总体架构图 | `thesis_figures/fig_4_1_system_architecture.svg` / `.png` | 第 4 章 4.1 节 | `thesis_figures_pdf_snapshots/zjuthesis_figures_page-29.png` |
| 图 4.2 | 专业层级本体全量覆盖 v2 的总体结构与典型分支 | `thesis_figures/fig_4_4_major_tree_partial.svg` / `.png` | 第 4 章 4.4 节 | `thesis_latex_pdf_snapshots/page-33.png` |
| 图 4.3 | 经人工审校的地域层级画像局部可视化 | `thesis_figures/fig_4_5_region_hierarchy_partial.svg` / `.png` | 第 4 章 4.5 节 | `thesis_latex_pdf_snapshots/page-34.png` |
| 图 4.4 | Benchmark 多轮评测流程图 | `thesis_figures/fig_4_2_benchmark_flow.svg` / `.png` | 第 4 章 4.6 节 | `thesis_latex_pdf_snapshots/page-35.png` |
| 图 4.5 | 数据证据层与放宽能力映射图 | `thesis_figures/fig_4_3_data_evidence_relax_mapping.svg` / `.png` | 第 4 章 4.7 节 | `thesis_latex_pdf_snapshots/page-36.png` |
| 图 5.1 | 轻量 MAS / 多角色 Agent 工作流图 | `thesis_figures/fig_5_1_mas_workflow.svg` / `.png` | 第 5 章 5.1 节 | `thesis_latex_pdf_snapshots/page-38.png` |

补充快照：`thesis_figures_pdf_snapshots/` 中还保留第 30-33、36 页渲染结果，用于检查图前后正文和浮动体位置。

## 3. PDF 视觉验收结果

本次验收基于 `latexmk -g -xelatex -outdir=out zjuthesis` 重新编译后的 PDF，并用 `pdftoppm -png -f 29 -l 37 -r 150` 渲染页面快照。

| 图号 | 视觉检查 | 术语检查 | 验收结论 |
| --- | --- | --- | --- |
| 图 4.1 | 无裁切，节点和箭头可读，整体居中；A4 页面中图较小但仍可辨识。 | 包含前置语义归一、LLM 规划、确定性证据探针和证据谈判；未把 LLM 写成事实候选来源。 | 通过 |
| 图 4.2 | 无裁切，8 个 Level-0 大类、典型高频分支和论文使用方式均可读。 | 明确全覆盖是可审计挂载覆盖，不宣称全部语义边界人工逐条确认。 | 通过 |
| 图 4.3 | 无裁切，地理邻近层级与城市层级画像并排清晰。 | 明确地域层级只用于偏好显性化，不直接计入客观收益。 | 通过 |
| 图 4.4 | 无裁切，hidden/evaluator-only 虚线边界清楚；页面留白较多但不影响阅读。 | 明确 hidden fields 只进入模拟器/评测器，业务 Agent 不可见。 | 通过 |
| 图 4.5 | 无裁切，证据族和放宽动作分组清楚；图在页面中偏小但主关系可读。 | 明确 LLM 只规划，确定性探针返回事实候选；地域层级只作偏好显性化证据。 | 通过 |
| 图 5.1 | 无裁切，主路径完整；新 MAS 节点命名与当前论文口径一致。 | 采用“前置语义归一层 -> 约束解析器 -> LLM 引导机会规划器 -> 确定性证据探针 -> 证据谈判器”。 | 通过 |

## 4. 周边一致性提醒

本次只验收并同步图像资产，不改七组实验指标、不重跑 benchmark，也不更新 thesis audit。PDF 第 5 章正文已同步为与图 5.1 一致的五阶段 MAS 叙述；后续若再次调整 Agent 架构，应同时维护图像资产、LaTeX 正文和本文档。

## 5. 维护规则

后续若修改 Agent 架构、图号或图题，建议按以下顺序维护：

1. 更新 `render_thesis_diagrams.py` 并重新生成 `thesis_figures/`。
2. 同步 LaTeX 模板 `figure/thesis_figures/` 中的 PNG 文件。
3. 重新编译 LaTeX PDF。
4. 重新渲染 `thesis_figures_pdf_snapshots/`。
5. 更新本文档、`thesis_diagrams_with_diagrams.md`、`thesis_figures_tables_pack.md`、`thesis_document_hub.md` 和 `outputs/README.md`。
