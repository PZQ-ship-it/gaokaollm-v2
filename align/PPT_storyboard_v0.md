---
stage: storyboard
stage_status: unconfirmed
requires_confirmed:
  - ppt_production_brief
  - fact_ledger
  - defense_narrative
blocked_next_stage: ppt-speaker-notes-rehearsal-stage
previously_confirmed_by: user, 2026-05-31
reset_by: user, 2026-06-01
reset_reason: User says some storyboard sections should use formulas instead of mostly flow diagrams; detailed feedback pending.
created_at: 2026-05-31
source_brief: align/ppt_production_brief_v0.md
source_fact_ledger: align/fact_ledger_v0.md
source_defense_narrative: align/ppt_defense_narrative_v0.md
---

# 答辩 PPT storyboard v0

## 0.1 2026-06-01 reset note

Status reset to `unconfirmed`. The current storyboard over-relies on flow diagrams for some sections. User will provide more detailed guidance on where formulas should replace or complement flow diagrams.

Do not continue to speaker notes, Q&A/backup planning, asset/layout planning, content fidelity QA, deck build, or render QA until the revised storyboard exhibit-form decisions are confirmed.

## 0. Storyboard contract

- 目标时长：15 分钟纯讲，不含 Q&A。
- 页数策略：约 20 页总量；其中核心内容页约 15 页，封面、过渡、收束页不计入核心内容。
- 叙事策略：按“现有方案入口 -> 问题定义 -> 数据/Agent/Benchmark 总览 -> 方法闭环 -> 系统实现 -> 实验证据 -> 贡献与边界”推进，不机械压缩论文章节。
- 证据策略：按 `assertion-evidence policy: strict` 处理；每个证据页尽量只有一个主展品和一个明确 `so_what_annotation`。
- 讨论约束：这是故事线草案，后续需要和用户逐页讨论；不进入 speaker notes、Q&A/backup、asset/layout 或 PPTX 生成。

## 1. Slide-by-slide storyboard

### Slide 1. 封面

- Action title: 大模型驱动的高考志愿推荐系统需要同时守住事实可信和偏好真实两条线。
- Core point: 交代题目、学生、导师、学院和答辩场景。
- Source facts: `material_inventory_v0.md` 封面字段；最终论文封面。
- Exhibit type: none.
- Exhibit claim: not applicable.
- so_what_annotation: 本设计面向高风险志愿决策，不是普通聊天问答。
- Citation need: not applicable.
- Recommended visual form: 类似 `zjuslides.pptx` 风格的正式封面；不放英文副标题。
- Asset needs: 浙江大学/学院风格元素、论文封面字段。
- Speaking points: 用一句话说研究主题；不展开方法。
- Estimated time: 0:20.
- QA risk: 题目过长导致封面拥挤。
- Backup/merge/split notes: 封面不计入内容页。

### Slide 2. 现有志愿填报方案能提供信息和建议，但隐藏底线仍需要被证据化澄清

- Action title: 现有志愿填报方案能提供信息和建议，但隐藏底线仍需要被证据化澄清。
- Core point: 用阳光高考、夸克高考等现有方案作为 20-30 秒场景入口，引出“信息可得”不等于“偏好已澄清”。
- Source facts: `ppt_defense_narrative_v0.md` 已定开场策略；具体产品事实待后续核验。
- Exhibit type: comparison.
- Exhibit claim: 现有方案可作为场景入口，但本论文问题聚焦隐藏偏好澄清。
- so_what_annotation: 我的研究切入点不是再做一个信息入口，而是让系统在真实证据下问清用户没有说出口的底线。
- Citation need: user-confirmed source now; storyboard/asset 阶段需核验公开页面或本地截图来源。
- Recommended visual form: 三栏对比：阳光高考 / 夸克高考 / 本设计关注点；前两栏只放“信息入口、条件查询、建议展示”等概括占位，待核验后定稿。
- Asset needs: 后续获取或截图公开页面；避免使用未经许可或过时截图。
- Speaking points: 现有产品能帮助查信息和生成建议；论文进一步问“如果用户第一句话不完整，系统怎么问出底线”。
- Estimated time: 0:35.
- QA risk: 若写具体功能未核验，可能引入事实错误；本页不能变成产品评测。
- Backup/merge/split notes: 如果时间紧，可并入 Slide 3 的问题定义页。

### Slide 3. 高考志愿填报的难点不是回答问题，而是从不完整表达中发现真实底线

- Action title: 高考志愿填报的难点不是回答问题，而是从不完整表达中发现真实底线。
- Core point: 说明任务的高风险、多目标、强事实约束和隐藏偏好特点。
- Source facts: `fact_ledger_v0.md` §2；`01-introduction.tex:64-68`。
- Exhibit type: diagram.
- Exhibit claim: 用户首轮显式话语只覆盖部分约束，真实偏好还包含隐藏底线。
- so_what_annotation: 只按第一句话推荐，容易把表面愿望误当成完整目标。
- Citation need: references slide only.
- Recommended visual form: “显式话语 -> 事实约束 -> 隐藏底线 -> 推荐解释”的漏斗图。
- Asset needs: 可编辑流程图，无需外部图片。
- Speaking points: 用“想留江浙沪、不要太贵、别太冒险”这类抽象例子说明显式话语不完整；不要引入具体未确认 case。
- Estimated time: 0:45.
- QA risk: 例子不能写成真实用户数据。
- Backup/merge/split notes: 与 Slide 4 可合并为一个问题页，但会削弱开场节奏。

### Slide 4. 本设计把一次性推荐改造成事实约束下的多轮偏好澄清系统

- Action title: 本设计把一次性推荐改造成事实约束下的多轮偏好澄清系统。
- Core point: 给出全场 defense thesis 和三段节奏：先锁事实、再问取舍、后给推荐。
- Source facts: `fact_ledger_v0.md` §1, §2；`ppt_defense_narrative_v0.md` §1。
- Exhibit type: process.
- Exhibit claim: 系统主线是从 one-shot answer 到 sequential decision loop。
- so_what_annotation: 系统主动性被限制在“帮助用户看见取舍”，不是替用户做价值判断。
- Citation need: references slide only.
- Recommended visual form: 三步水平流程：事实可行域 -> A/B 取舍澄清 -> 冲稳保推荐解释。
- Asset needs: 可编辑流程图。
- Speaking points: 这是整场答辩的中心句，后面的数据、算法、实验都服务这句话。
- Estimated time: 0:40.
- QA risk: “主动澄清”不要被听成强行引导，后面要预留用户控制和局限。
- Backup/merge/split notes: 可作为过渡页，内容简洁。

### Slide 5. 系统架构把 Data、Agent 和 Benchmark 串成可复查闭环

- Action title: 系统架构把 Data、Agent 和 Benchmark 串成可复查的推荐闭环。
- Core point: 保留“数据 + Agent + Benchmark”作为显式总览页，但用系统架构图来解释支撑结构，而不是重画一个粗略三栏图。
- Source facts: `ppt_defense_narrative_v0.md` §2, §9；`fact_ledger_v0.md` §3。
- Exhibit type: diagram.
- Exhibit claim: 四层系统架构中，Data 提供事实边界，Agent 完成偏好澄清，Benchmark 检验机制有效性。
- so_what_annotation: 这不是三块孤立工作，而是事实、交互和验证三条防线。
- Citation need: references slide only.
- Recommended visual form: 以横版系统架构图为主视觉：从 `gaokaollm_bench/tests/manual/render_thesis_diagrams.py` 的 `render_system_architecture()` 派生 PPT 宽屏版 `fig_4_1_system_architecture_wide`，保留四层架构与关键箭头；在图上用标注层点出 Data / Agent / Benchmark 的支撑关系。
- Asset needs: 后续 asset/layout 阶段基于原作图脚本重排横版 SVG/PNG/PDF，不覆盖论文竖版 `fig_4_1_system_architecture`；当前论文版脚本为 `SvgCanvas(width=1400, height=1800)` 的竖版适配。
- Speaking points: 明确“总览页不是旧主线回退，而是支撑结构”。
- Estimated time: 0:45.
- QA risk: 不能直接硬塞论文竖版图；横版重排时不得改变层次语义、LLM 边界和数据证据流向。
- Backup/merge/split notes: 必留，因为用户已确认保留显式总览页；横版架构图是后续 PPT 资产阶段优先制作对象。

### Slide 6. 事实候选由结构化证据层给出，LLM 不生成学校、专业、分数或学费

- Action title: 事实候选由结构化证据层给出，LLM 不生成学校、专业、分数或学费。
- Core point: 证明系统的事实安全边界。
- Source facts: `fact_ledger_v0.md` §2, §5, §8；`01-introduction.tex:66,74`。
- Exhibit type: diagram.
- Exhibit claim: LLM 与确定性证据层分工清晰。
- so_what_annotation: 高风险事实交给数据库和标准化证据层，模型只做语义归一、规划和表达。
- Citation need: references slide only.
- Recommended visual form: 左侧用户输入/LLM 语义归一，右侧 PostgreSQL/专业树/质量画像/地域树，输出事实可行候选。
- Asset needs: 可复用 `fig_4_6_database_physical_schema` 或重画简化版。
- Speaking points: 这是回答“会不会幻觉”的核心页。
- Estimated time: 0:55.
- QA risk: 不要把所有证据表展开，避免拖慢节奏。
- Backup/merge/split notes: 细节放备份页。

### Slide 7. 专业树和地域树提供可审计覆盖，但不被夸大为全部语义人工正确

- Action title: 专业树和地域树提供可审计覆盖，但不被夸大为全部语义人工正确。
- Core point: 展示数据贡献，同时主动说明边界。
- Source facts: `fact_ledger_v0.md` §4；`major_tree_annotation_summary.md`; `region_urban_tier_tree_full_coverage_v2_report.md`。
- Exhibit type: table.
- Exhibit claim: 证据层覆盖完整，但语义正确性仍有边界。
- so_what_annotation: 数据层让系统“有据可查”，而不是让模型自由想象。
- Citation need: references slide only.
- Recommended visual form: 小表格：专业名 22,759/22,759；录取记录 140,995/140,995；省-市对 414；学校 3,219；旁边放“不是全人工正确”的边界标注。
- Asset needs: 可编辑表格；可选 `fig_4_4_major_tree_partial` / `fig_4_5_region_hierarchy_partial` 小缩略图。
- Speaking points: 这页只讲“可审计挂载覆盖”，不要讲 clean validation 全细节。
- Estimated time: 0:50.
- QA risk: 容易被问“那准确率多少”，备份页准备 clean validation 和错分边界。
- Backup/merge/split notes: 如果时间紧，可与 Slide 6 合并；建议保留以显示工作量。

### Slide 8. 静态检索能找到事实，却难以判断用户愿意为哪类收益放宽哪条约束

- Action title: 静态检索能找到事实，却难以判断用户愿意为哪类收益放宽哪条约束。
- Core point: 解释为什么仅有 RAG/检索基线不够。
- Source facts: `fact_ledger_v0.md` §5；`02-problem-algorithm.tex:81-103`。
- Exhibit type: process.
- Exhibit claim: 静态混合检索是强工程基线，但主要依赖显式话语和一次性排序。
- so_what_annotation: 事实召回解决“有哪些候选”，但不能自动解决“用户真实愿意怎么取舍”。
- Citation need: references slide only.
- Recommended visual form: `fig:static-hybrid-rag-flow` 简化为五步链路，右侧标注“缺少多轮偏好更新”。
- Asset needs: `figure/agent_workflow_2.pdf` 或可编辑重绘。
- Speaking points: 先肯定基线工程合理性，再说研究推进点。
- Estimated time: 0:45.
- QA risk: 不要贬低现有方案或产品；只讲论文系统中的技术缺口。
- Backup/merge/split notes: 可与 Slide 9 形成“旧链路 -> 新闭环”对照。

### Slide 9. 推荐决策闭环把事实候选转化为可回答的偏好取舍

- Action title: 推荐决策闭环把事实候选转化为可回答的偏好取舍。
- Core point: 总览 SAVF、UCB、Pareto 候选对、BT 后验如何串成闭环。
- Source facts: `fact_ledger_v0.md` §5；`02-problem-algorithm.tex`; `03-system-design.tex`。
- Exhibit type: process.
- Exhibit claim: 四个机制分别解决底线保护、问什么、怎么问、如何记住反馈。
- so_what_annotation: 系统不是一次排序，而是在真实证据附近连续缩小偏好不确定性。
- Citation need: references slide only.
- Recommended visual form: 循环图：候选特征 -> SAVF -> UCB 选轴 -> Pareto A/B -> 用户反馈 -> BT 后验 -> 下一轮。
- Asset needs: 可编辑流程图；可参考 `fig_5_1_mas_workflow`。
- Speaking points: 这页是方法总览，后面三页只展开最关键机制。
- Estimated time: 0:55.
- QA risk: 机制太多，需保持“每个模块一句作用”。
- Backup/merge/split notes: 如果后续 storyboard 需要压缩，Slide 10-12 可合并为两页。

### Slide 10. 非补偿性价值映射防止预算、专业等底线被线性总分掩盖

- Action title: 非补偿性价值映射防止预算、专业等底线被线性总分掩盖。
- Core point: 解释为什么高风险志愿推荐不能只用线性加权。
- Source facts: `fact_ledger_v0.md` §5；`02-problem-algorithm.tex:119-152`。
- Exhibit type: diagram.
- Exhibit claim: 严重违反底线的候选不应被其他高分维度抵消。
- so_what_annotation: 底线约束先被保护，后续澄清才有意义。
- Citation need: references slide only.
- Recommended visual form: “线性补偿陷阱”对比图：高学校层次不能抵消超预算/严重专业偏离；右侧为 SAVF 截断/惩罚。
- Asset needs: 可编辑示意图，不需要真实学校案例。
- Speaking points: 用预算和专业底线作直观解释，避免陷入公式。
- Estimated time: 0:50.
- QA risk: 公式细节可能被问，备份页放定义。
- Backup/merge/split notes: 公式不放主线。

### Slide 11. UCB 主动探测让系统优先询问最有诊断价值的偏好维度

- Action title: UCB 主动探测让系统优先询问最有诊断价值的偏好维度。
- Core point: 解释“问什么”的策略。
- Source facts: `fact_ledger_v0.md` §5；`ppt_defense_narrative_v0.md` 风险图；`fig:ucb-dispatch`。
- Exhibit type: process.
- Exhibit claim: 系统根据偏好不确定性和收益线索选择下一轮探测维度。
- so_what_annotation: 有限轮次不能随便问，必须把问题问到最可能暴露底线的地方。
- Citation need: references slide only.
- Recommended visual form: `fig_5_3_ucb_dispatch` 或简化版：候选特征 -> 维度评分 -> 选轴 -> 构造问题。
- Asset needs: `fig_5_3_ucb_dispatch.pdf` 或可编辑重绘。
- Speaking points: 明确 UCB 是工程启发式，不说严格最优。
- Estimated time: 0:50.
- QA risk: 理论最优性追问；答复见备份。
- Backup/merge/split notes: 可与 Slide 12 合并为“问什么/怎么问”。

### Slide 12. 帕累托 A/B 候选把抽象偏好变成用户能够回答的具体取舍

- Action title: 帕累托 A/B 候选把抽象偏好变成用户能够回答的具体取舍。
- Core point: 解释“怎么问”和“如何记住反馈”。
- Source facts: `fact_ledger_v0.md` §5；`03-system-design.tex:317-339`。
- Exhibit type: process.
- Exhibit claim: A/B 候选展示边际替代，BT 后验将反馈写入偏好状态。
- so_what_annotation: 用户不需要说出完整效用函数，只需要在真实候选取舍中表达接受、拒绝或犹豫。
- Citation need: references slide only.
- Recommended visual form: 一个抽象 A/B 卡片对比 + 反馈箭头进入后验权重条；不使用未确认真实学校名。
- Asset needs: 可编辑 mockup；可参考 `fig_3_5_elicitation_console`。
- Speaking points: 用“放宽地域换学校层次”“增加学费换质量证据”等抽象例子，不写具体学校。
- Estimated time: 1:00.
- QA risk: 如果展示具体学校需事实核验；主线先用抽象卡片。
- Backup/merge/split notes: 具体贯穿案例可作为备份或后续讲稿讨论。

### Slide 13. 运行时状态机把澄清、反馈和终局推荐串成可回放链路

- Action title: 运行时状态机把澄清、反馈和终局推荐串成可回放链路。
- Core point: 证明系统不是概念图，而是有工程实现和状态管理。
- Source facts: `fact_ledger_v0.md` §3, §5；`fig:runtime-state-machine`。
- Exhibit type: process.
- Exhibit claim: 系统用状态机组织探索期和终局推荐期。
- so_what_annotation: 每轮为什么问、用户怎么答、状态怎么变，都能被回放和审计。
- Citation need: references slide only.
- Recommended visual form: `fig_5_2_runtime_state_machine` 简化版，突出 interrupt/resume 和状态字段。
- Asset needs: `fig_5_2_runtime_state_machine.pdf` 或可编辑重绘。
- Speaking points: 这是工程完整性页，避免讲太多代码。
- Estimated time: 0:45.
- QA risk: 评委若问代码结构，备份准备实现路径。
- Backup/merge/split notes: 可与 Slide 14 合并为“系统实现证据”。

### Slide 14. 前端把偏好澄清过程呈现为可理解的取舍问题和推荐报告

- Action title: 前端把偏好澄清过程呈现为可理解的取舍问题和推荐报告。
- Core point: 展示系统可用性和交互闭环。
- Source facts: `material_inventory_v0.md` 终稿图表；`fact_ledger_v0.md` §9。
- Exhibit type: source figure.
- Exhibit claim: 用户侧能看到澄清问题和最终推荐报告，后台能查看日志审计。
- so_what_annotation: 内部偏好状态不是黑箱，而是通过取舍问题和报告解释呈现给用户。
- Citation need: references slide only.
- Recommended visual form: 左右两张论文截图：`fig_3_5_elicitation_console` + `fig_3_6_final_decision_report`，可选小角落放后台图。
- Asset needs: 终稿图目录中的 PDF/PNG。
- Speaking points: 讲界面服务方法，不变成产品 demo。
- Estimated time: 0:45.
- QA risk: 截图细节可能太小，后续 asset 阶段需要重排或裁剪。
- Backup/merge/split notes: 后台审计图可放备份。

### Slide 15. 受控测试集用隐藏底线用户画像检验系统是否真的恢复真实偏好

- Action title: 受控测试集用隐藏底线用户画像检验系统是否真的恢复真实偏好。
- Core point: 解释实验为什么这样设计。
- Source facts: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:101-127`。
- Exhibit type: process.
- Exhibit claim: 180 条受控测试画像、显式话语和隐藏评测边界共同构成机制验证环境。
- so_what_annotation: 评测重点从“答案像不像”转向“是否在多轮过程中识别隐藏底线”。
- Citation need: references slide only.
- Recommended visual form: `fig_4_2_benchmark_flow` + 简短指标说明：F1@N、MAE、过程指标。
- Asset needs: `fig_4_2_benchmark_flow.pdf` 或简化图。
- Speaking points: 说明模拟用户是当前局限，但适合控制变量做机制比较。
- Estimated time: 0:55.
- QA risk: 模拟用户外部有效性追问；主动承认局限。
- Backup/merge/split notes: 指标定义可放备份。

### Slide 16. 参考基线横评显示，完整系统的优势来自交互式证据链路而不是更强的单轮生成

- Action title: 参考基线横评显示，完整系统的优势来自交互式证据链路而不是更强的单轮生成。
- Core point: 展示完整系统与静态检索直接提示/思维链提示的横评结果。
- Source facts: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:151-183`。
- Exhibit type: data chart.
- Exhibit claim: 完整系统在五个模型上的 F1@1/F1@3/F1@5 整体优于静态检索提示。
- so_what_annotation: 换更强模型或提示方式不等于解决隐藏偏好，交互链路本身有贡献。
- Citation need: references slide only.
- Recommended visual form: `fig_4_5_c1_baseline_model_target`，加一句结论标注，不逐项念表。
- Asset needs: `fig_4_5_c1_baseline_model_target.pdf/png`。
- Speaking points: 强调趋势和设计意义，不夸大为所有场景显著领先。
- Estimated time: 0:55.
- QA risk: 静态基线指标差距不大时要解释“头部候选和可复查机制”价值。
- Backup/merge/split notes: 表格细节放备份。

### Slide 17. 主消融实验显示，主动探测和后验追踪分别支撑探测方向选择与反馈吸收

- Action title: 主消融实验显示，主动探测和后验追踪分别支撑探测方向选择与反馈吸收。
- Core point: 展示去除主动探测、去除后验追踪后的退化。
- Source facts: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:211-238`。
- Exhibit type: data chart.
- Exhibit claim: 完整系统在 MAE 和头部推荐指标上优于消融系统，去除模块会破坏闭环。
- so_what_annotation: 问对方向和记住反馈缺一不可。
- Citation need: references slide only.
- Recommended visual form: `fig_4_6_c1_ablation_core_metrics`，旁边放“三个系统变体”小图例。
- Asset needs: `fig_4_6_c1_ablation_core_metrics.pdf/png`。
- Speaking points: 不要只读数值，要解释模块作用。
- Estimated time: 0:55.
- QA risk: MAE 和 F1 的标准差较大，措辞用“整体趋势/支持机制贡献”。
- Backup/merge/split notes: 若时间不足，Slide 16-17 可保留，Slide 18 压缩。

### Slide 18. 过程指标说明完整系统更能形成有张力的问题并稳定更新偏好状态

- Action title: 过程指标说明完整系统更能形成有张力的问题并稳定更新偏好状态。
- Core point: 补充说明为什么完整系统有效，不只看最终 F1。
- Source facts: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:266-296`。
- Exhibit type: data chart.
- Exhibit claim: 完整系统更好地命中有效探测方向、保持权衡张力并更新后验状态。
- so_what_annotation: 效果不是魔法，而是“选对维度 -> 构造取舍 -> 写入状态”的过程链路在起作用。
- Citation need: references slide only.
- Recommended visual form: 三小图或三步解释，优先重排 `fig_4_8_1/2/3` 其中最清晰的一张。
- Asset needs: `fig_4_8_1_c1_planner_process`, `fig_4_8_2_c1_negotiator_process`, `fig_4_8_3_c1_tracker_process`。
- Speaking points: 这是实验解释页，可以根据时间压缩成一句。
- Estimated time: 0:40.
- QA risk: 三张过程图可能太拥挤；asset 阶段需择一或重绘。
- Backup/merge/split notes: 可降级为备份页；主线保留 Slide 16-17 即可。

### Slide 19. 本设计把事实证据、主动澄清、在线后验和可复查评测组织成一个工程闭环

- Action title: 本设计把事实证据、主动澄清、在线后验和可复查评测组织成一个工程闭环。
- Core point: 总结贡献并回扣开场的事实可信与偏好真实。
- Source facts: `fact_ledger_v0.md` §3；`ppt_defense_narrative_v0.md` §4.5。
- Exhibit type: diagram.
- Exhibit claim: 五项贡献共同构成闭环，不是孤立模块堆叠。
- so_what_annotation: 本设计证明了高风险推荐中“先问清底线再推荐”的可实现路径。
- Citation need: references slide only.
- Recommended visual form: 回到闭环图，标注五项贡献：问题定义、数据证据、决策模块、运行时链路、受控测试。
- Asset needs: 可编辑总结图。
- Speaking points: 快速回顾，不新增事实。
- Estimated time: 0:45.
- QA risk: 贡献太多会散；把五项收束到一句话。
- Backup/merge/split notes: 可与 Slide 20 合并，保留局限会更稳。

### Slide 20. 系统仍需真实用户研究和泛化验证，但已证明高风险推荐中先问清底线再推荐的技术路径

- Action title: 系统仍需真实用户研究和泛化验证，但已证明高风险推荐中先问清底线再推荐的技术路径。
- Core point: 主动交代局限和后续工作，降低过度声明风险。
- Source facts: `fact_ledger_v0.md` §1, §8；`07-conclusion.tex:28-38`。
- Exhibit type: none.
- Exhibit claim: not applicable.
- so_what_annotation: 本设计给出可审计机制和工程闭环，但不把当前系统说成生产级升学顾问。
- Citation need: references slide only.
- Recommended visual form: 三行局限 + 三行后续工作：真实用户、跨省跨年份、用户控制机制/更多证据维度。
- Asset needs: 可编辑文本页。
- Speaking points: 以稳健姿态结束，预埋 Q&A。
- Estimated time: 0:45.
- QA risk: 结尾不能显得贡献弱；先说已证明路径，再说后续扩展。
- Backup/merge/split notes: 可作为结论页，后接致谢。

### Slide 21. 致谢与 Q&A

- Action title: 谢谢各位老师，欢迎批评指正。
- Core point: 结束主讲，进入问答。
- Source facts: not applicable.
- Exhibit type: none.
- Exhibit claim: not applicable.
- so_what_annotation: not applicable.
- Citation need: not applicable.
- Recommended visual form: 简洁致谢页，保留学校风格。
- Asset needs: 模板风格元素。
- Speaking points: 控制在一句话。
- Estimated time: 0:10.
- QA risk: 无。
- Backup/merge/split notes: 不计入内容页。

## 2. Ghost-deck check

只读 action titles：

1. 先从高风险志愿推荐的双约束切入。
2. 用现有方案说明信息入口已经存在，但隐藏底线仍需澄清。
3. 定义问题：从不完整表达中发现真实底线。
4. 给出总解法：一次性推荐改造成事实约束下的多轮偏好澄清。
5. 用“数据 + Agent + Benchmark”说明支撑结构。
6. 先证明事实边界，再证明证据覆盖。
7. 说明静态检索不足，然后展开多轮决策闭环。
8. 依次解释 SAVF、UCB、Pareto/BT、状态机和前端。
9. 用受控测试、基线横评、消融和过程指标证明机制有效。
10. 最后收束贡献与边界。

结论：标题链条能讲清“现有方案入口 -> 隐藏偏好问题 -> 方法闭环 -> 工程实现 -> 实验证据 -> 贡献边界”。当前故事线满足 confirmed narrative，但 Slide 2 的具体素材、Slide 18 是否保留、Slide 10-12 是否压缩，需要和用户讨论。

## 3. Timing draft

| Segment | Slides | Time |
| --- | --- | ---: |
| 封面与场景入口 | 1-2 | 0:55 |
| 问题定义与总览 | 3-5 | 2:10 |
| 事实证据层 | 6-8 | 2:30 |
| 方法闭环 | 9-12 | 3:35 |
| 系统实现 | 13-14 | 1:30 |
| 实验证据 | 15-18 | 3:25 |
| 贡献、局限与 Q&A | 19-21 | 1:40 |
| **Total** | 21 slides | **15:45** |

Timing risk: 当前草案略超 15 分钟。后续建议压缩路径：

- 删除或备份 Slide 18，可减少 0:40。
- 合并 Slide 6-7，可减少 0:35。
- 合并 Slide 11-12，可减少 0:35。

推荐讨论版主线：保留 21 页结构，但正式讲稿阶段把 Slide 18 设为“时间够就讲，不够跳过”。

## 4. Storyline decisions to discuss with user

- Slide 2 的“阳光高考 / 夸克高考”具体展示形态：截图、关键词卡片，还是只用抽象产品入口图。
- Slide 5 的系统架构图横版重绘策略：基于原作图脚本派生宽屏版作为 PPT 主资产，还是仅在 Slide 5 使用其局部；原则是不放弃原架构图，也不直接把论文竖版硬塞进宽屏页。
- 是否保留 Slide 7 的数据覆盖页在主线，还是降为备份。
- 是否将 Slide 10-12 三个方法页压缩为两页，以保证 15 分钟。
- Slide 14 是否需要做 20 秒真实界面 demo 感，还是仅展示截图。
- Slide 18 过程指标是否保留在主线，还是作为评委追问时的备份。
- 结尾是否保留较完整局限性页，还是把局限性压到 Q&A 预答页。

## 5. Backup candidates for later Q&A stage

- LLM 事实边界：为什么 LLM 不生成事实候选。
- 专业树全量覆盖 v2：覆盖数字、验证集、错分边界。
- 地域树边界：414 省-市对、3,219 学校；不编码城市收益。
- UCB 非严格最优：工程启发式与后续对照实验计划。
- 模拟用户局限：为什么受控测试不能替代真实用户研究。
- 旧口径实验边界：`major_geo_v1`、`risk_band_v1`、`multi_axis_v2`、`v1_hybrid_rag` 只作为备份或历史口径。
