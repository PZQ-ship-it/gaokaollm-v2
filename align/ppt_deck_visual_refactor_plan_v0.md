---
stage: deck_visual_refactor_plan
stage_status: unconfirmed
requires_confirmed:
  - ppt_production_brief
  - fact_ledger
  - defense_narrative
  - storyboard
  - speaker_notes_rehearsal
  - defense_qa_backup
  - asset_layout_plan
  - academic_figure_prompt_when_required
  - content_fidelity_qa
  - deck_build_draft
allowed_next_action: revise_asset_layout_plan
blocked_next_stage: ppt-render-qa-loop
previously_confirmed_by: user, 2026-05-31
reset_by: user, 2026-06-01
reset_reason: User feedback requires replacing AI chart-like visuals, splitting dense method figure, and revising formula-vs-flow storyboard choices before deck revision.
created_at: 2026-05-31
reference_layout_study: exp/ppt_deck_build_v0/reference_layout_study_v0.md
reference_deck: 应雨轩-毕业答辩V1.pptx
current_draft: generated_pptx_test/gaokaollm_defense_deck_v0.pptx
---

# PPT deck visual refactor plan v0

## 0. 2026-06-01 reset note

Status reset to `unconfirmed`. The previous refactor direction made V-AI01 a large Slide 9 visual, but the user rejected the current visual route:

- chart-like overlays/trends are wrong and should be rebuilt from real data or deterministic code/editable objects;
- the all-in-one method figure is too crowded and must be split;
- some storyboard sections may need formulas rather than flow diagrams;
- the split strategy is a focus discussion item before another deck build or render QA.

## 1. 固化结论

下一轮不是继续局部补丁，而是先回到 storyboard，重审公式/流程图取舍和方法图拆分方式。

固化目标：

- 维持答辩 PPT 的学校风格、4:3 比例、可编辑优先原则。
- 借鉴参考稿的版式逻辑：浅色标题带、大水印/学校识别、分节页留白、单主视觉、短旁注。
- 主讲页目标控制在 18-20 页；其中真正内容页约 15 页，适配 15 分钟纯讲述。
- 当前 `align/ppt_deck_build_manifest_v0.md` 仍保持 draft；本方案确认后只能进入 deck draft revision，不能直接进入 render QA。

## 2. 不可改变的事实边界

- 事实源头仍以最终论文、已确认 fact ledger、storyboard 和 speaker notes 为准。
- 不引入真实学校、分数、产品截图、未验证竞品信息或新的实验数字。
- Current V-AI01 不能继续作为已确认主视觉； chart-like 部分应改为代码/真实数据或可编辑确定性图，整体图需要拆分。
- BT posterior / Pareto feedback 不能画成直接改写 SQL、query 或 filter；只能影响下一轮选轴、候选评分、最终解释。
- 结论措辞保持早期支持、初步支持，不夸大为充分验证或真实用户研究结论。
- 不能把 storyboard / 讲稿里的制作者提示直接上屏；所有可见文字必须是观众展示话术。

## 3. 新版页面语法

### 3.1 母版规则

- Slide size: 4:3, `10.0 x 7.5 in`。
- Header: 改为轻量标题带或压薄学校页眉；标题优先深蓝字，不再让深蓝整条页眉占据过多视觉重量。
- Body safe area: 统一留出一个主视觉区域；一页最多一个主图或两个严格对齐的证据区。
- Footer / brand: 保留学校识别，但不与主体内容争抢空间。
- Watermark: 可使用低透明度学校水印或浅蓝几何底纹，作为参考稿式的正式感来源。
- Takeaway: 每页最多一条短结论条或一个旁注框，作为观众能带走的句子。

### 3.2 页面类型

| 类型 | 用途 | 固化布局 |
| --- | --- | --- |
| Cover | 封面 | 题目居中偏上，字段集中，删英文副标题。 |
| Agenda | 目录 | 4 个章节即可，不放长说明。 |
| Section divider | 节奏页 | 大号章节标题 + 淡水印 + 底部学校带，几乎不放正文。 |
| Problem | 问题定义 | 一张抽象问题图或流程图 + 一条底部结论。 |
| System / method | 系统和方法 | 单主视觉占主体 70-85%，旁注解释作用边界。 |
| Module detail | SAVF/UCB/BT 等机制 | 局部机制图放大，公式和定义放到备份或小注。 |
| Result evidence | 实验页 | 大图表 + 一条结论，不再使用右侧竖向批注卡。 |
| Conclusion | 总结与展望 | 上半总结贡献，下半讲边界与未来工作，类似参考稿 Slide 23。 |
| Backup | 备份页 | 暂缓精修；主讲页稳定后再统一附录化。 |

## 4. 主讲页重构映射

目标主讲结构：约 19 页。若内容过满，允许回到 20 页；不再扩回 21+ 页。

| 新页 | 来源 | 处理 |
| --- | --- | --- |
| N01 封面 | 当前 S01 | 沿用封面字段，强化题目层级，删多余口号式小字。 |
| N02 目录 | 新增/改造 | 参考稿目录逻辑：研究背景、系统方法、实验验证、总结展望。 |
| N03 分节：研究背景与问题 | 新增 | 留白分节页，给 15 分钟讲述建立节奏。 |
| N04 问题定义 | 当前 S02-S03 合并 | 用一个问题图解释“事实可召回但偏好不可直接判断”；产品现状只保留一句背景。 |
| N05 总体解法 | 当前 S04 | 论文工作流图放大为主视觉，底部一句“事实候选 -> A/B 取舍 -> 状态更新 -> 解释输出”。 |
| N06 分节：系统与方法 | 新增 | 留白分节页。 |
| N07 系统架构 | 当前 S05 | 改成单主图：Data / Agent / Decision / Benchmark 四层架构，减少横向散框。 |
| N08 事实边界 | 当前 S06-S07 压缩 | 只讲“LLM 不生成事实，证据层给候选”；覆盖率细表移备份。 |
| N09 静态基线缺口 | 当前 S08 | 放大论文静态基线图，旁注只说明缺口：不主动问隐藏底线、不更新偏好状态。 |
| N10 决策闭环总览 | 当前 S09 | 先重审拆分方案；不再默认使用 V-AI01 作为单张大图。可保留一个高层闭环图，SAVF/UCB/Pareto-BT/后验状态拆成独立视觉。 |
| N11 SAVF 底线保护 | 当前 S10 | 机制图放大，英文流程短语改成中文展示话术或移到图注。 |
| N12 UCB 主动探测 | 当前 S11 | 论文 UCB 图/机制图放大，右侧只保留“收益 + 不确定性 -> 下一轮探测轴”。 |
| N13 A/B 取舍与后验状态 | 当前 S12-S13 合并 | 把 Pareto/BT 与状态机合成一页：反馈改变偏好状态，不改写底层事实查询。 |
| N14 分节：实验验证 | 新增 | 留白分节页。 |
| N15 评测设置 | 当前 S14-S15 合并 | 基准流程图或 UI 证据二选一主视觉；180 条、显式话语、F1/MAE 做小标签。 |
| N16 基线对比结果 | 当前 S16 | 图表大幅放大；右侧竖框改成底部结论条。 |
| N17 消融与过程指标 | 当前 S17-S18 合并/取舍 | 优先保留最能支撑机制的图；修复 S18 右侧出界问题，放不下的过程指标进备份。 |
| N18 分节：总结与展望 | 新增或短页 | 如页数紧张，可并入 N19 前半。 |
| N19 总结与边界 | 当前 S19-S20 合并 | 参考稿总结页：上半贡献，下面边界/未来工作；弱化成“初步支持”。 |
| N20 Q&A | 当前 S21 | 极简感谢页；如果需要 19 页版本，可与 N19 后接 Q&A，不单独计内容页。 |

## 5. 优先修复清单

第一优先级：

- S16-S18 实验页：重排为“大图表 + 一条结论”，删除竖向批注卡，修复 S18 出界。
- S09-S13：先讨论方法图拆分。chart-like 曲线/趋势图用代码或可编辑对象重做，不使用 AI 生成图。
- S02-S03：合并并删除指示性、铺垫性文字，只保留给老师看的问题定义。

第二优先级：

- 增加/替换目录与分节页，建立参考稿式节奏。
- 调整母版页眉：减少深蓝横幅压迫感，保留学校识别。
- 将细表、公式、覆盖率细节和长解释迁移到备份页。

第三优先级：

- 备份页 B01-B16 统一附录样式，但先不追求和主讲页同等精修。

## 6. 下一轮构建验收标准

下一版 deck draft 生成后，先做视觉抽查，不进入正式 render QA。最小验收：

- 主讲页 contact sheet 看起来是同一套版式系统。
- 80% 以上主讲内容页满足“单主视觉 + 一条短结论/旁注”。
- 无可见制作痕迹：`fallback`、`deferred`、`Source:`、`image not generated`、prompt 说明、讲稿提示。
- S18 不再有任何对象越界或右侧裁切。
- 实验页图表字号在 4:3 放映下可读。
- 主讲页数控制在 18-20 页；内容页约 15 页。
- 备份页仍保留 B01-B16 的问答支撑，但不阻塞主讲页版式确认。

## 7. 执行顺序

1. 修改 `exp/ppt_deck_build_v0/build_deck_v0.py` 的版式系统与主讲结构。
2. 必要时补充局部可编辑图，但不新增证据图或实验图。
3. 重新生成 `generated_pptx_test/gaokaollm_defense_deck_v0.pptx`。
4. 导出主讲页 contact sheet，先做人工视觉确认。
5. 用户认可后，再确认 deck build manifest；随后才能进入 `ppt-render-qa-loop`。
