---
stage: production_brief
stage_status: confirmed
allowed_next_stage: ppt-material-fact-ledger
confirmed_by: user, 2026-05-31
created_at: 2026-05-31
---

# 答辩 PPT 生产 brief v0

## 1. 目标与场景

- 任务目标：基于最终本科毕业论文材料，制作一份可编辑、可答辩、可追溯的毕业设计答辩 PPT。
- 场景预设：`defense`
- 主要受众：本科毕业设计答辩委员会、导师，以及可能旁听的同学。
- 核心叙事：围绕“数据贡献 + Agent 贡献 + Benchmark 贡献”的三贡献结构，说明高风险高考志愿决策场景中，系统如何通过可审计数据、证据驱动的 Pareto 谈判 Agent 和面向隐性偏好的 benchmark 形成完整研究闭环。
- 当前工作目录：`D:\gaokaollm-v2`

## 2. 已知输入材料

### 2.1 最终论文与 LaTeX 材料

- LaTeX 根目录：`D:\毕设\latex-for-zju-master\latex-for-zju-master`
- 最终 PDF：`D:\毕设\latex-for-zju-master\latex-for-zju-master\out\zjuthesis.pdf`
- LaTeX 主入口：`D:\毕设\latex-for-zju-master\latex-for-zju-master\zjuthesis.tex`
- 正文入口：`D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\final\content.tex`
- 章节目录：`D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\final\chapters`
- 论文图目录：`D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures`

### 2.2 PPT 模板

- 模板候选：`D:\毕设\latex-for-zju-master\latex-for-zju-master\zjuslides.pptx`
- 模板政策：不要求严格沿用原模板结构；允许重组成类似风格的 PPT。`zjuslides.pptx` 作为视觉语言、学校风格、配色和版式参考，具体页面可围绕答辩叙事重新组织。

### 2.3 项目与作图材料

- 项目根目录：`D:\gaokaollm-v2`
- 环境名称：`gaokao_pg`
- 项目事实入口：
  - `gaokaollm_bench/outputs/thesis_document_hub.md`
  - `gaokaollm_bench/outputs/thesis_claims_manifest.json`
  - `gaokaollm_bench/outputs/thesis_term_mapping.json`
  - `gaokaollm_bench/outputs/major_tree_annotation_summary.md`
  - `gaokaollm_bench/outputs/region_urban_tier_tree_full_coverage_v2_report.md`
- 项目图表与作图代码候选：
  - `gaokaollm_bench/outputs/thesis_figures`
  - `app/evaluation/results`
  - `app/evaluation/chapter4_c1_figures.py`
  - `app/evaluation/chapter4_c2_c6_figures.py`
  - `app/evaluation/chapter6_figures.py`
  - `app/evaluation/preview_c1_c6_average_figures.py`
  - `app/evaluation/plotter.py`
  - `scripts/sync_final_thesis_figures.py`

## 3. 来源优先级与冲突处理

1. 最高优先级：最终论文 PDF `out/zjuthesis.pdf`，用于答辩内容、章节顺序、术语和最终事实口径。
2. 第二优先级：对应 LaTeX 源文件和 `figure/thesis_figures`，用于抽取可编辑文本、图题、图号、公式、表格和可复用图片。
3. 第三优先级：`gaokaollm-v2` 中的论文事实入口与 claims manifest，用于机器可读事实核验、术语边界、指标一致性和图表再生成。
4. 第四优先级：项目目录下作图代码与结果目录，用于必要时重绘高清图或生成 PPT 友好的图表。
5. 降级材料：项目文件夹下的历史 PDF、旧论文草稿、旧 benchmark 输出、临时目录、旧实验中间物和未被最终论文引用的素材，默认只作为追溯线索，不直接进入答辩 PPT。

若不同文件冲突，答辩 PPT 以最终论文为准；若最终论文与项目事实入口明显不一致，先在 fact ledger 阶段标记为风险，不直接改写成新结论。

## 4. 已知论文口径

- 贡献结构：数据贡献、Agent 贡献、Benchmark 贡献。
- 专业层级本体口径：全量覆盖 v2，`22,759 / 22,759` 个原始去重专业名、`140,995 / 140,995` 条录取记录，`remaining_unassigned = 0`。
- Agent / MAS 主叙述：前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器。
- 事实边界：LLM 不生成学校、专业、分数、位次等事实候选；事实候选来自 PostgreSQL / 标准化证据层。
- Benchmark 边界：Agent 不读取 hidden persona 字段；`implicit_flexibilities`、`volunteer_set`、`axis_flexibilities` 只供 simulator / evaluator 使用。
- 实验边界：`multi_axis_v2` 是压力测试，不进入七组实验主表；`v1_hybrid_rag` 是补充基线 pilot，不进入七组正式实验主表。
- 风险样本：不得把 `major_geo_v1` 写成 100% 成功；`real-db-set-浙江-569-009` 是失败样本。

## 5. 输出目标与质量优先级

- 输出格式：可编辑 `.pptx`。
- 答辩时长：15 分钟纯讲，不含 Q&A。
- 目标页数：内容页先暂定 15 页左右，不含开头、结尾和中间过渡页。
- 优先级顺序：
  1. 事实忠实于最终论文。
  2. 答辩叙事清楚，能在限定时间内讲完。
  3. 尽量复用模板风格，保持正式、克制、清晰。
  4. 图表可读，关键图优先高清重绘或使用论文最终图。
  5. 保留演讲者备注与备份页，方便现场问答。
- 整页截图政策：默认禁用整页图片化。只有复杂 PDF 图、模板背景或不可可靠重建的版式可作为局部图片使用。
- 可编辑性政策：标题、正文、流程框、表格、备注应尽量可编辑；来源图、实验图和架构图可使用高分辨率图片或从 SVG/PDF 转换。

## 6. Assertion-Evidence 与视觉政策

- Assertion-evidence policy：`strict`
- 每页原则：标题尽量写成可答辩的判断句或结论句；正文只放支撑证据，不做大段论文搬运。
- 视觉生产路由：
  - 论文已有图：优先使用最终论文图目录中的版本，必要时从 PDF/SVG 重新导出。
  - 数据图表：优先使用项目作图代码和最终论文图表包；若重绘，必须在 fact ledger 里绑定数据源。
  - 系统/Agent/Benchmark 流程图：优先复用论文图；若为 PPT 可读性重排，不能改变模块语义。
  - 概念性学术图：需要先走 `academic-figure-prompt` 并由用户确认 prompt，再进入生成。
  - 装饰图：默认不使用，避免稀释答辩重点。
- OpenRouter ICU Image 权限：默认未授权。除非用户在后续阶段明确批准，不生成 AI 图片。

## 7. 工具与 QA 政策

- `python_pptx_policy`：允许用于生成和编辑 PPTX；应保持文本、形状、图片和备注尽量可编辑。
- `powerpoint_com_qa_policy`：在 Windows + PowerPoint 可用时，优先用 PowerPoint COM 渲染导出截图做 QA。
- 渲染 fallback：若 PowerPoint COM 不可用，可用 LibreOffice、python-pptx 结构检查、PDF 导出或截图检查作为降级验证，并在 QA 报告中注明。
- 环境政策：需要运行项目作图代码时，优先使用 `gaokao_pg` 环境；运行前不得读取或输出 `.env`、API key、token 等秘密。
- Workflow state：后续在阶段确认后维护 `align/ppt_workflow_state.json`，记录最新 artifact、状态、hash 和下一阶段。

## 8. 非目标

- 本阶段不重写论文、不新增实验、不重跑 benchmark。
- 不把项目目录中的过期素材、历史草稿或未进入终稿的图表直接放入答辩 PPT。
- 不把 v1 `gaokaollmmodel` 包装为最终主贡献。
- 不把 `region_tree_v1` 写成主实验。
- 不把城市层级直接等价为就业机会、生活成本或城市生活质量收益。
- 不生成最终 PPT、不生成 AI 图片、不进入事实抽取或 storyboard。

## 9. 待用户确认的高影响决策

- 答辩时长：15 分钟纯讲，不含 Q&A。
- 目标页数：内容页先暂定 15 页左右，不含开头、结尾和中间过渡页。
- 语言：默认中文；是否需要英文标题、英文摘要页或英文关键词页待确认。
- 身份字段：姓名、学号、学院、专业、导师、答辩日期等封面字段直接从论文封面读取；后续在 fact ledger 或 asset/layout 阶段列出供用户核对。
- 模板绑定程度：不严格沿用模板，可重组成类似风格的 PPT；`zjuslides.pptx` 作为风格参考。
- 是否需要完整 speaker notes：默认需要。
- 是否需要备份页：默认需要，尤其覆盖失败样本、hidden persona 边界、事实候选来源、七组实验与压力测试边界。

## 10. 验收标准

- 每个核心结论可追溯到最终论文 PDF、LaTeX 源或 confirmed fact ledger。
- 不出现旧口径残留：六组实验、八组主实验、地域树 reviewed v1 主叙述、`v1_hybrid_rag` 被写成正式实验等。
- PPT 能以模板视觉风格打开并编辑。
- 关键图表在投影尺寸下可读；不出现文字遮挡、裁剪或明显糊图。
- Render QA 至少覆盖封面、目录/路线页、三贡献页、方法页、实验结果页、结论页和代表性备份页。
- 最终构建前必须通过 content fidelity QA；若 QA 阻塞，不生成 deck。

## 11. 计划阶段顺序

1. `ppt-production-brief`：当前草案，等待用户确认。
2. `ppt-material-fact-ledger`：确认材料清单、事实源、claim-source map。
3. `ppt-defense-narrative-stage`：形成答辩故事线和 action-title spine。
4. `ppt-storyboard-stage`：逐页 storyboard。
5. `ppt-speaker-notes-rehearsal-stage`：逐页讲稿、过渡和时长控制。
6. `ppt-defense-qa-backup-stage`：问答策略和备份页。
7. `ppt-asset-layout-plan`：模板盘点、资产审计、版式计划。
8. `academic-figure-prompt`：仅在确认需要 AI 生成学术视觉时使用。
9. `ppt-content-fidelity-qa-stage`：生成前事实忠实度检查。
10. `ppt-deck-build`：生成可编辑 PPTX 草案。
11. `ppt-render-qa-loop`：渲染截图、检查版式并输出 QA 报告。

## 12. Native agent lanes

- 主线程负责生产 brief、事实 ledger、叙事、Q&A/backup、content fidelity QA 和最终判断。
- `ppt_storyboard`：仅在 storyboard 阶段作为 bounded worker。
- `ppt_template_automation`：仅在 deck build 阶段处理模板自动化。
- `ppt_render_qa`：仅在 render QA 阶段处理截图/版式验收。
- 默认不启用 Figma；除非用户单独提供 Figma context 或要求 Figma 实验。
