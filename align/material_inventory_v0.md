---
stage: material_fact_ledger
stage_status: confirmed
requires_confirmed: ppt_production_brief
allowed_next_stage: ppt-defense-narrative-stage
confirmed_by: user, 2026-05-31
created_at: 2026-05-31
source_brief: align/ppt_production_brief_v0.md
---

# 答辩 PPT 材料清单 v0

## 1. 本阶段范围

本清单服务 15 分钟本科毕业设计答辩 PPT。当前阶段只做材料盘点与权威等级划分，不生成叙事、storyboard、讲稿或 PPTX。

来源优先级沿用已确认 brief：

1. 最终论文 PDF 与当前 LaTeX 源。
2. 论文最终图目录与模板 PPTX。
3. `gaokaollm-v2` 中的事实入口、图表包、作图代码和实验输出。
4. 历史草稿、旧报告、临时目录和未被终稿引用的素材只作追溯，不直接进入答辩 PPT。

## 2. 核心材料清单

| 材料 | 路径 | 类型 | 权威等级 | 可能用途 | 提取方法 | 风险 |
| --- | --- | --- | --- | --- | --- | --- |
| 已确认生产 brief | `align/ppt_production_brief_v0.md` | workflow contract | 最高 | 限定时长、页数、模板策略、来源优先级 | 已读 YAML 与正文 | 已确认，可作为后续阶段门禁 |
| 最终论文 PDF | `D:\毕设\latex-for-zju-master\latex-for-zju-master\out\zjuthesis.pdf` | compiled PDF | 最高 | PPT 内容、封面字段、最终事实口径、页面视觉核对 | `pdfinfo`、`pdftotext`、后续截图渲染 | 当前只做文本抽取，尚未做页面截图 QA |
| LaTeX 主入口 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\zjuthesis.tex` | LaTeX root | 最高 | 封面元数据、论文类型、英文题名、提交日期 | 直接读取 UTF-8 源码 | 无明显风险 |
| 封面模板 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\page\undergraduate\final\cover.tex` | LaTeX cover | 最高 | 封面字段映射、题名换行、是否公开 | 直接读取 + PDF 首页文本 | 题名在封面分两行，PPT 封面需保持可读 |
| 摘要 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\final\abstract.tex` | LaTeX prose | 最高 | 一句话主张、研究背景、系统核心机制、关键词 | 直接读取 | 不能把摘要整段搬进 PPT，需要压缩成答辩语言 |
| 正文入口 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\final\content.tex` | LaTeX index | 最高 | 章节顺序 | 直接读取 | 当前实际入口为 5 个主要章节，不应沿用旧报告中的 7 章说法 |
| 正文章节 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\final\chapters` | LaTeX chapters | 最高 | 研究问题、方法、系统、实验、结论 | `rg` 关键词与行号抽取 | 后续 narrative 阶段需再聚焦阅读 |
| 论文最终图目录 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures` | PDF/PNG/SVG figures | 高 | 架构图、流程图、实验图、前端图 | 文件盘点 + LaTeX 引用抽取 | 目录中有终稿引用图和历史候选图，后续只优先使用 LaTeX 引用图 |
| PPT 模板候选 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\zjuslides.pptx` | PPTX template/reference | 高 | 学校风格、配色、版式参考、可复用母版 | ZIP 结构读取：9 slides, 9 layouts, 1 master, 8 media | 不强制复刻模板页序，后续 asset/layout 阶段再拆解视觉规则 |
| 项目事实入口 hub | `gaokaollm_bench/outputs/thesis_document_hub.md` | Markdown index | 高 | 历史事实入口、旧三贡献口径、文档地图 | 直接读取 | 与当前终稿 LaTeX 的章节组织存在漂移，不能高于 PDF/LaTeX |
| 机器事实 manifest | `gaokaollm_bench/outputs/thesis_claims_manifest.json` | JSON fact manifest | 高 | 数据层覆盖、旧实验指标、边界约束、术语归一 | 直接读取 | 对旧七组实验口径权威，但当前终稿实验表已经重组为 180 条受控测试画像 |
| 术语映射 | `gaokaollm_bench/outputs/thesis_term_mapping.json` | JSON glossary | 高 | 工程名到论文名转换 | 直接读取 | 只作为术语安全表，不替代终稿正文 |
| 专业树报告 | `gaokaollm_bench/outputs/major_tree_annotation_summary.md` | data report | 高 | 专业层级本体覆盖与验证边界 | 直接读取 | 可写“全量可审计挂载”，不可写“全部语义人工正确” |
| 地域树报告 | `gaokaollm_bench/outputs/region_urban_tier_tree_full_coverage_v2_report.md` | data report | 高 | 地域层级画像覆盖与边界 | 直接读取 | 不可把城市层级直接写成就业/生活收益 |
| 终稿事实一致性报告 | `gaokaollm_bench/outputs/thesis_latex_final_consistency_report.md` | QA report | 中 | 历史验收证据、旧口径残留检查项 | 直接读取 | 该报告与当前 PDF/LaTeX 有明显时间和章节差异，只作为历史风险提示 |
| 项目最终图表包 | `gaokaollm_bench/outputs/thesis_figures` | PNG/SVG figures | 中高 | PPT 可编辑或高清重绘来源 | 文件盘点 | 不含 PDF 版本，且少于 LaTeX 终稿图目录；后续优先使用论文目录 |
| 作图代码 | `app/evaluation/chapter4_c1_figures.py`, `app/evaluation/chapter4_c2_c6_figures.py`, `app/evaluation/chapter6_figures.py`, `app/evaluation/preview_c1_c6_average_figures.py`, `app/evaluation/plotter.py`, `scripts/sync_final_thesis_figures.py` | Python scripts | 中 | 需要重绘实验图或补高清图时使用 | 文件定位，未运行 | 运行前需确认 `gaokao_pg` 环境；不读取 `.env` 或 secret |
| 实验结果目录 | `app/evaluation/results` | CSV/PNG/PDF/JSON/MD outputs | 中 | 复核第 4 章实验图和表 | 文件定位 | 目录含大量新增/未跟踪结果，必须以终稿引用和 fact ledger 为准 |
| 历史 PDF/资料 | `D:\gaokaollm-v2\*.pdf` | references/history | 低 | 背景追溯 | 文件盘点 | 默认不进入 PPT，除非后续明确引用 |
| 临时与旧产物 | `tmp/`, old reports, stale figures | temporary/history | 低 | 排错追溯 | 文件盘点 | 默认不作为答辩素材 |

## 3. 封面与身份字段

从最终论文封面和 `zjuthesis.tex` 读取：

| 字段 | 值 | 来源 |
| --- | --- | --- |
| 论文类型 | 本科生毕业设计，公开论文 | PDF 首页、`cover.tex` |
| 题目 | 大模型驱动的高考志愿推荐系统设计与实现 | PDF 首页、`zjuthesis.tex` |
| 学生 | 潘臻琦 | PDF 首页、`zjuthesis.tex` |
| 学号 | 3210102495 | PDF 首页、`zjuthesis.tex` |
| 指导教师 | 胡天磊 | PDF 首页、`zjuthesis.tex` |
| 年级与专业 | 2021级计算机科学与技术 | PDF 首页、`zjuthesis.tex` |
| 学院 | 计算机学院 | PDF 首页、`zjuthesis.tex` |
| 递交日期 | 2026年5月18日 | PDF 首页、`zjuthesis.tex` |
| 英文题名 | Design and Implementation of an LLM-driven Gaokao College Application Recommendation System | `zjuthesis.tex` |

## 4. 终稿结构与可用图表

当前 `content.tex` 实际输入：

1. `01-introduction`
2. `02-problem-algorithm`
3. `03-system-design`
4. `04-system-test-evaluation`
5. `07-conclusion`

优先考虑进入 PPT 的终稿引用图表：

| 类别 | 代表图表 | PPT 用途 |
| --- | --- | --- |
| 论文结构 | `fig:thesis-structure` | 可转化为答辩路线页，不一定直接使用论文原表 |
| 混合检索基线 | `fig:static-hybrid-rag-flow` | 说明旧式一次性检索链路及其局限 |
| 系统架构 | `fig:system-architecture`, `fig:database-physical-schema` | 展示系统层次和事实来源 |
| 数据证据层 | `fig:major-tree-partial`, `fig:region-hierarchy-partial`, `tab:major-tree-final-stats` | 展示数据可审计覆盖 |
| 偏好澄清机制 | `fig:mas-workflow`, `fig:runtime-state-machine`, `fig:ucb-dispatch`, `alg:preference-loop` | 展示多轮闭环与算法机制 |
| 交互界面 | `fig:frontend-elicitation-console`, `fig:frontend-final-report`, `fig:frontend-admin-trace-dashboard` | 展示系统实现效果 |
| 评测流程 | `fig:benchmark-flow`, `tab:dataset-design`, `fig:data-evidence-mapping`, `tab:probe-evidence-source` | 展示测试设计 |
| 实验结果 | `tab:baseline-results`, `fig:baseline-methods`, `tab:ablation-results`, `fig:ablation-core`, `fig:planner-process`, `fig:negotiator-process`, `fig:tracker-process` | 展示核心结论和消融证据 |

## 5. 缺失或待后续阶段确认

- 还未做 `zjuslides.pptx` 逐页视觉规则拆解；放到 `ppt-asset-layout-plan`。
- 还未渲染 PDF/PPT 截图做视觉 QA；放到 render QA 或资产计划阶段。
- 还未确认是否需要英文副标题页；production brief 默认中文，英文题名可用于封面副标题。
- 还未确认最终 PPT 是否包含完整备份页数量；production brief 默认需要备份页，具体页数在 Q&A/backup 阶段确定。
