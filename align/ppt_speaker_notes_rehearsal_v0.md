---
stage: speaker_notes_rehearsal
stage_status: unconfirmed
requires_confirmed:
  - ppt_production_brief
  - fact_ledger
  - defense_narrative
  - storyboard
blocked_next_stage: ppt-defense-qa-backup-stage
previously_confirmed_by: user, 2026-05-31
reset_by: user, 2026-06-01
reset_reason: Storyboard exhibit-form decisions are unconfirmed; formula-vs-flow choices may change talk track.
created_at: 2026-05-31
source_brief: align/ppt_production_brief_v0.md
source_fact_ledger: align/fact_ledger_v0.md
source_defense_narrative: align/ppt_defense_narrative_v0.md
source_storyboard: align/PPT_storyboard_v0.md
---

# 答辩 PPT speaker notes / rehearsal v0

## 0.1 2026-06-01 reset note

Status reset to `unconfirmed` because the storyboard is now unconfirmed. Formula-first or formula-plus-diagram revisions may change the talk track, timing, and recovery lines.

## 0. Delivery contract

- 讲述语言：中文，正式但口语化；不照读论文，不堆术语。
- 讲稿形态：cue-card 风格。每页只保留“必须讲清的一句话 + 证据解释 + 转场”，避免逐字稿。
- 时间硬约束：15 分钟纯讲，不含 Q&A。标准版按 15:00 控制，实际排练目标建议 14:30-14:45，留给临场停顿。
- 叙事核心：事实可信、偏好可澄清、过程可复查。
- 过度声明禁区：不能说系统替代升学顾问、LLM 生成事实候选、专业树/地域树全语义正确、实验已证明生产级泛化。
- 当前阶段边界：不生成 Q&A 答案、不规划备份页、不做资产重绘、不生成 PPTX。

## 1. Full-talk timing budget

| Slide | Target | Cumulative | Checkpoint / cut rule |
| --- | ---: | ---: | --- |
| 1. 封面 | 0:15 | 0:15 | 只报题目和一句中心问题。 |
| 2. 现有方案入口 | 0:30 | 0:45 | 做简要现状评测，不展开竞品报告。 |
| 3. 问题定义 | 0:45 | 1:30 | 第一次讲清“显式话语不等于真实偏好”。 |
| 4. 总解法 | 0:40 | 2:10 | 说出“先锁事实、再问取舍、后给推荐”。 |
| 5. 架构总览 | 0:50 | 3:00 | 3 分钟前必须完成开场与总览。 |
| 6. 事实边界 | 0:55 | 3:55 | 回答“会不会幻觉”。 |
| 7. 数据覆盖 | 0:40 | 4:35 | 只读关键数字，不展开构建过程。 |
| 8. 静态检索不足 | 0:45 | 5:20 | 先肯定基线，再指出缺口。 |
| 9. 决策闭环 | 0:55 | 6:15 | 6:20 前进入方法细节。 |
| 10. SAVF | 0:50 | 7:05 | 不讲公式推导。 |
| 11. UCB | 0:50 | 7:55 | 明确是工程启发式。 |
| 12. Pareto / BT | 1:00 | 8:55 | 方法段最慢的一页。 |
| 13. 状态机 | 0:45 | 9:40 | 证明可回放，不讲代码细节。 |
| 14. 前端证据 | 0:40 | 10:20 | 10:30 前进入实验。 |
| 15. Benchmark 设计 | 0:55 | 11:15 | 说清 180 条受控画像和隐藏底线。 |
| 16. 基线横评 | 0:55 | 12:10 | 讲趋势，不逐项读图。 |
| 17. 主消融 | 0:55 | 13:05 | 讲模块作用，不只读数值。 |
| 18. 过程指标 | 0:25 | 13:30 | 超时则只读标题并跳过解释。 |
| 19. 贡献闭环 | 0:45 | 14:15 | 回扣开场，不新增事实。 |
| 20. 局限与后续 | 0:35 | 14:50 | 先肯定路径，再讲边界。 |
| 21. 致谢 | 0:10 | 15:00 | 一句话结束。 |

Hard checkpoint:

- Slide 5 结束晚于 3:15：Slide 7 压到 20 秒。
- Slide 9 结束晚于 6:35：Slide 10-12 每页少讲一个例子。
- Slide 14 结束晚于 10:45：Slide 18 直接跳过。
- Slide 17 结束晚于 13:25：Slide 18 跳过，Slide 20 压到 20 秒。

## 2. Per-slide speaker notes

### Slide 1. 封面

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 1.
- Target / checkpoint: 0:15, cumulative 0:15.
- Speaker notes:
  - “各位老师好，我的毕设题目是《大模型驱动的高考志愿推荐系统设计与实现》。”
  - “我关注的核心问题是：在高考志愿这样高风险的场景里，怎样既守住事实可信，又把用户没有说清楚的真实偏好问出来。”
- Transition in: 开场直接进入题目，不解释背景。
- Transition out: “我先用一个很常见的志愿填报使用场景引入。”
- Emphasis cues:
  - Slow down: 题目和“两条线：事实可信、偏好真实”。
  - Skip if short: 个人信息之外的任何背景。
  - Avoid: 不说“我做了一个大模型聊天系统”。
- Source anchors: `material_inventory_v0.md` 封面字段；`ppt_defense_narrative_v0.md` §1。
- Term / pronunciation cues: “高考志愿推荐”不要读成泛化的“推荐系统”。
- Delivery risk and recovery line: 如果题目显得太应用化，补一句“这里的大模型不是事实来源，而是交互和表达层的一部分。”

### Slide 2. 现有志愿填报方案能提供信息和建议，但隐藏底线仍需要被证据化澄清

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 2.
- Target / checkpoint: 0:30, cumulative 0:45.
- Speaker notes:
  - “现在学生填志愿时，已经可以接触到很多信息入口和推荐工具，比如阳光高考、夸克高考这类方案。”
  - “简单概括，传统推荐形态更偏信息查询、条件筛选和规则化排序；AI empowered 形态进一步强化了问答和生成建议。”
  - “但从本文关注的问题看，无论是传统推荐，还是 AI 增强的方案，隐藏底线的证据化、多轮、可复查澄清仍然是一个没有被充分解决的环节。”
  - “所以本设计的切入点不是再做一个信息入口，而是把志愿推荐变成一个证据驱动的取舍澄清过程。”
- Transition in: “先看现有使用场景。”
- Transition out: “这就引出本文的问题定义。”
- Emphasis cues:
  - Slow down: “本文关注的问题：隐藏底线仍需证据化、多轮、可复查地澄清”。
  - Skip if short: 只保留“查询筛选/生成建议”与“缺少多轮澄清机制”两句。
  - Avoid: 不逐项贬低具体产品；不写未核验的具体功能或页面结论。
- Source anchors: `ppt_defense_narrative_v0.md` §4.1；`PPT_storyboard_v0.md` Slide 2。
- Term / demo cues: 后续 asset/layout 阶段需要核验截图和页面文字。
- Delivery risk and recovery line: 如果被追问产品功能，现场说“这页是简要现状评测，不作为论文实验基线；具体页面和功能表述会以公开页面核验为准。”

### Slide 3. 高考志愿填报的难点不是回答问题，而是从不完整表达中发现真实底线

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 3.
- Target / checkpoint: 0:45, cumulative 1:30.
- Speaker notes:
  - “高考志愿不是普通问答，它同时有分数、位次、选科、学费、地域、专业、风险偏好等多类约束。”
  - “用户第一轮通常只会说一部分，比如想去某个地域、想学某个方向、希望风险低一点。但预算、专业接受边界、是否愿意换城市、是否接受调剂，往往没有被完整表达。”
  - “我把这个问题理解为‘冰山式偏好’：水面上是显式话语，水面下是隐藏底线。”
- Transition in: “为什么只给一次答案不够？”
- Transition out: “因此系统不能一上来就替用户拍板，而要先组织澄清过程。”
- Emphasis cues:
  - Slow down: “显式话语不等于完整偏好”。
  - Skip if short: 约束类型少举两个即可。
  - Avoid: 不使用真实学生案例，不制造具体分数线。
- Source anchors: `fact_ledger_v0.md` §2；`01-introduction.tex:64-68`。
- Term / demo cues: “冰山式偏好”作为口语化解释，不额外引入新指标。
- Delivery risk and recovery line: 如果例子被认为太抽象，补一句“我后面会用 A/B 取舍机制说明系统怎样把抽象偏好落到真实候选上。”

### Slide 4. 本设计把一次性推荐改造成事实约束下的多轮偏好澄清系统

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 4.
- Target / checkpoint: 0:40, cumulative 2:10.
- Speaker notes:
  - “本文的总体思路可以概括为三步：先锁事实、再问取舍、后给推荐。”
  - “先锁事实，是指学校、专业、分数、位次、学费这些内容来自数据库和标准化证据层。”
  - “再问取舍，是指系统用真实候选构造 A/B 对比，让用户表达愿意放宽什么、不愿放宽什么。”
  - “最后才输出冲稳保和解释报告。”
- Transition in: “对应到系统设计，我不是把大模型直接放到答案生成位置。”
- Transition out: “下面用一张架构总览说明这三步分别落在哪些模块上。”
- Emphasis cues:
  - Slow down: “先锁事实、再问取舍、后给推荐”。
  - Skip if short: 冲稳保细节先不讲。
  - Avoid: 不说系统“替用户决策”。
- Source anchors: `fact_ledger_v0.md` §1-2；`ppt_defense_narrative_v0.md` §1。
- Term / demo cues: “sequential decision loop”可不说英文。
- Delivery risk and recovery line: 若“主动澄清”听起来像引导用户，补一句“系统只呈现证据化取舍，最终偏好由用户反馈确认。”

### Slide 5. 系统架构把 Data、Agent 和 Benchmark 串成可复查闭环

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 5.
- Target / checkpoint: 0:50, cumulative 3:00.
- Speaker notes:
  - “这页是整套系统的路线图。Data、Agent、Benchmark 不是三块孤立工作，而是分别回答三个答辩问题。”
  - “Data 回答事实从哪里来，为什么不让大模型编候选。”
  - “Agent 或推荐决策模块回答系统怎样把用户没说清的底线问出来。”
  - “Benchmark 回答怎么证明这个交互链路有效，而不是只靠单轮生成。”
  - “后面我会按这条链路展开：先讲事实边界，再讲偏好澄清机制，最后讲实验验证。”
- Transition in: “先看总览。”
- Transition out: “第一部分先回答事实可信问题。”
- Emphasis cues:
  - Slow down: 三个回答对象：事实来源、偏好澄清、机制验证。
  - Skip if short: 架构图中的小模块名不逐个读。
  - Avoid: 不回到旧的三贡献机械目录页。
- Source anchors: `ppt_defense_narrative_v0.md` §2, §9；`fact_ledger_v0.md` §3；`PPT_storyboard_v0.md` Slide 5。
- Term / demo cues: 后续 asset/layout 阶段应使用 `render_system_architecture()` 派生横版架构图，不覆盖论文竖版。
- Delivery risk and recovery line: 如果图复杂，恢复句是“请先看颜色和层级，不必记住每个模块名；这页只说明三类工作在同一个闭环里。”

### Slide 6. 事实候选由结构化证据层给出，LLM 不生成学校、专业、分数或学费

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 6.
- Target / checkpoint: 0:55, cumulative 3:55.
- Speaker notes:
  - “高考志愿场景里最不能出错的是事实：学校、专业、分数、位次、学费，都不能由语言模型自由生成。”
  - “所以系统把事实候选限定在 PostgreSQL 和标准化证据层里；LLM 主要负责语义归一、探测规划和表达组织。”
  - “换句话说，模型可以帮助理解用户说法和组织问题，但候选事实必须有数据库证据。”
- Transition in: “先回答大模型会不会幻觉的问题。”
- Transition out: “在这个事实边界下，我进一步构建了专业树和地域树等证据结构。”
- Emphasis cues:
  - Slow down: “LLM 不生成事实候选”。
  - Skip if short: 数据表字段不展开。
  - Avoid: 不说“完全没有错误”，只说候选来源受控。
- Source anchors: `fact_ledger_v0.md` §2, §5, §8；`01-introduction.tex:66,74`。
- Term / demo cues: PostgreSQL 读作数据库证据层即可，不必解释数据库技术。
- Delivery risk and recovery line: 如果被质疑仍可能输出错误，回答范围留到 Q&A；主线恢复句是“本页强调的是候选生成边界，表达层错误仍需要后续审计和用户确认。”

### Slide 7. 专业树和地域树提供可审计覆盖，但不被夸大为全部语义人工正确

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 7.
- Target / checkpoint: 0:40, cumulative 4:35.
- Speaker notes:
  - “数据贡献的重点不是把数字说得很满，而是让事实有可审计路径。”
  - “专业层级本体覆盖 22,759 个原始去重专业名，对应 140,995 条录取记录；地域层级覆盖 414 个省-市对和 3,219 所学校。”
  - “但这里的覆盖是可审计挂载覆盖，不等于每个语义边界都已经人工确认完全正确。”
  - “这个边界主动说清楚，是为了避免把数据工程贡献夸大成全自动语义标注。”
- Transition in: “事实层还需要结构化组织。”
- Transition out: “有了事实层之后，静态检索是不是就够了？下面说明为什么还不够。”
- Emphasis cues:
  - Slow down: “覆盖不等于全对”。
  - Skip if short: 地域树来源分布不讲。
  - Avoid: 不说“专业树完全正确”。
- Source anchors: `fact_ledger_v0.md` §4；`major_tree_annotation_summary.md`；`region_urban_tier_tree_full_coverage_v2_report.md`。
- Term / demo cues: Hit@10、Macro-F1 等验证指标留给备份或 Q&A。
- Delivery risk and recovery line: 如果被追问准确率，恢复句是“主线先讲覆盖含义，验证集错分和 Hit@10 我会在问答或备份页展开。”

### Slide 8. 静态检索能找到事实，却难以判断用户愿意为哪类收益放宽哪条约束

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 8.
- Target / checkpoint: 0:45, cumulative 5:20.
- Speaker notes:
  - “在事实层基础上，静态混合检索是一个合理而且强的工程基线：它可以解析显式约束、做数据库过滤、向量召回和重排。”
  - “但它主要回答‘有哪些候选’，很难回答‘用户愿意为了什么收益放宽哪条底线’。”
  - “比如用户说想留在某个地域，系统还要知道他是否愿意为了专业质量、学校层次或风险降低而调整地域范围。”
  - “这类偏好不是一次排序能自然恢复的。”
- Transition in: “先肯定静态检索能解决事实召回。”
- Transition out: “因此本文的核心方法是把事实候选转化成可回答的取舍问题。”
- Emphasis cues:
  - Slow down: “事实召回”和“偏好澄清”的区别。
  - Skip if short: embedding、reranker 技术名不讲。
  - Avoid: 不贬低 RAG 或现有工具。
- Source anchors: `fact_ledger_v0.md` §5；`02-problem-algorithm.tex:81-103`。
- Term / demo cues: RAG 可以说“检索增强”，不展开工程细节。
- Delivery risk and recovery line: 如果被问为什么还做静态基线，恢复句是“正因为它是合理基线，后面的实验比较才有意义。”

### Slide 9. 推荐决策闭环把事实候选转化为可回答的偏好取舍

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 9.
- Target / checkpoint: 0:55, cumulative 6:15.
- Speaker notes:
  - “这页是方法总览。闭环里每个机制只解决一个问题。”
  - “SAVF 负责保护底线，避免严重违约被其他高分维度抵消。”
  - “UCB 负责决定下一轮优先问哪个偏好维度。”
  - “Pareto A/B 候选负责把抽象偏好变成具体取舍。”
  - “Bradley-Terry 后验负责把用户反馈写回偏好状态，让下一轮不是从零开始。”
- Transition in: “从这里开始进入方法部分。”
- Transition out: “先看第一个问题：为什么不能简单线性加权。”
- Emphasis cues:
  - Slow down: “保护底线、问什么、怎么问、如何记住反馈”。
  - Skip if short: 不解释每个缩写的数学细节。
  - Avoid: 不把机制讲成全自动价值判断。
- Source anchors: `fact_ledger_v0.md` §5；`02-problem-algorithm.tex`；`03-system-design.tex`。
- Term / demo cues: SAVF、UCB、Pareto、Bradley-Terry 第一次出现要读慢。
- Delivery risk and recovery line: 如果听众觉得模块多，恢复句是“可以只记住四个动词：保护、选择、呈现、记住。”

### Slide 10. 非补偿性价值映射防止预算、专业等底线被线性总分掩盖

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 10.
- Target / checkpoint: 0:50, cumulative 7:05.
- Speaker notes:
  - “传统线性加权容易出现一个问题：某个候选在学校层次上得分很高，但如果它严重超预算，或者专业方向完全不接受，就不应该被高分维度抵消。”
  - “高考志愿里的很多约束具有非补偿性，尤其是预算、专业底线、地域底线和风险底线。”
  - “因此我用单属性价值函数和惩罚机制，让严重违约先被压下来，再进入后续取舍。”
- Transition in: “先讲底线保护。”
- Transition out: “底线被保护之后，下一步是有限轮次里优先问什么。”
- Emphasis cues:
  - Slow down: “不能被抵消”。
  - Skip if short: 数学函数形式不讲。
  - Avoid: 不说所有维度都绝对不可补偿；讲“底线维度”。
- Source anchors: `fact_ledger_v0.md` §5；`02-problem-algorithm.tex:119-152`。
- Term / demo cues: SAVF 可解释为“单属性价值函数”，不要停留在缩写。
- Delivery risk and recovery line: 如果被问公式，恢复句是“主线里只讲机制直觉，公式和参数设置我放在备份材料里展开。”

### Slide 11. UCB 主动探测让系统优先询问最有诊断价值的偏好维度

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 11.
- Target / checkpoint: 0:50, cumulative 7:55.
- Speaker notes:
  - “有限轮次里，系统不能随便问，也不能把所有维度都问一遍。”
  - “UCB 在这里作为工程启发式：一方面看某个维度可能带来的收益线索，另一方面看当前偏好不确定性。”
  - “它的作用不是证明理论最优，而是让系统优先询问更可能暴露隐藏底线的维度。”
- Transition in: “解决了底线保护，还要解决问什么。”
- Transition out: “选好维度之后，还要把问题构造成用户能回答的具体取舍。”
- Emphasis cues:
  - Slow down: “工程启发式，不是严格最优”。
  - Skip if short: UCB 公式不讲。
  - Avoid: 不说“最优信息增益”。
- Source anchors: `fact_ledger_v0.md` §5；`ppt_defense_narrative_v0.md` §6；`fig:ucb-dispatch`。
- Term / demo cues: UCB 可以读作“上置信界启发式”，但不要展开 bandit 背景。
- Delivery risk and recovery line: 如果被问理论依据，恢复句是“本文把它作为可实现的选轴策略，后续工作会继续比较随机选轴、最大方差和最大均值等策略。”

### Slide 12. 帕累托 A/B 候选把抽象偏好变成用户能够回答的具体取舍

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 12.
- Target / checkpoint: 1:00, cumulative 8:55.
- Speaker notes:
  - “选好要澄清的维度之后，系统不会问一个抽象问题，比如‘你到底更看重什么’。”
  - “它会在真实候选附近构造 A/B 对比，让用户看到放宽什么、换来什么。”
  - “用户只需要表达接受、拒绝或更偏向哪一边，不需要直接写出完整效用函数。”
  - “这些反馈会通过 Bradley-Terry 后验更新偏好状态，影响下一轮问题和最终推荐。”
- Transition in: “这是‘怎么问’的问题。”
- Transition out: “这些多轮反馈还需要被工程链路保存和回放。”
- Emphasis cues:
  - Slow down: “放宽什么、换来什么”。
  - Skip if short: Bradley-Terry 名称只说一遍。
  - Avoid: 不放未核验具体学校名。
- Source anchors: `fact_ledger_v0.md` §5；`03-system-design.tex:317-339`。
- Term / demo cues: Pareto 可解释为“互有优势、形成边际替代关系的候选对”。
- Delivery risk and recovery line: 如果评委问具体 case，恢复句是“主线先用抽象卡片避免事实错误，真实候选示例需要在备份页按数据库记录核验。”

### Slide 13. 运行时状态机把澄清、反馈和终局推荐串成可回放链路

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 13.
- Target / checkpoint: 0:45, cumulative 9:40.
- Speaker notes:
  - “方法闭环要真正运行，需要有状态管理。”
  - “系统把探索期和终局推荐期分开：探索期通过 interrupt/resume 组织澄清问题和用户反馈，终局阶段再生成推荐解释。”
  - “这样每轮为什么问、用户怎么答、偏好状态怎么变，都可以回放和审计。”
- Transition in: “前面是算法机制，下面说明它怎样落成系统。”
- Transition out: “用户侧看到的，就是取舍问题和最终推荐报告。”
- Emphasis cues:
  - Slow down: “可回放”和“探索期/终局期分离”。
  - Skip if short: 状态字段细节不讲。
  - Avoid: 不讲成完全自治多智能体。
- Source anchors: `fact_ledger_v0.md` §3, §5；`fig:runtime-state-machine`。
- Term / demo cues: LangGraph interrupt/resume 可中文解释，不必展开框架 API。
- Delivery risk and recovery line: 如果被问代码结构，恢复句是“主线里我只展示运行逻辑，具体模块路径和状态字段可在后续备份材料中说明。”

### Slide 14. 前端把偏好澄清过程呈现为可理解的取舍问题和推荐报告

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 14.
- Target / checkpoint: 0:40, cumulative 10:20.
- Speaker notes:
  - “这页展示系统对用户的呈现方式。”
  - “用户看到的不是内部参数，而是基于真实候选构造出的取舍问题，以及最后的推荐报告。”
  - “这说明前面的偏好状态不是黑箱，它通过问题、反馈和报告解释被外显出来。”
  - “这里我不展开 demo 细节，因为答辩主线还是方法和验证。”
- Transition in: “系统实现最后落在用户交互上。”
- Transition out: “接下来讲怎样验证这个链路确实有作用。”
- Emphasis cues:
  - Slow down: “界面服务方法，不是产品展示”。
  - Skip if short: 后台日志图不讲。
  - Avoid: 不逐个讲按钮和控件。
- Source anchors: `material_inventory_v0.md` 终稿图表；`fact_ledger_v0.md` §9。
- Term / demo cues: 后续 asset 阶段要裁剪截图，保证投影可读。
- Delivery risk and recovery line: 如果截图太小或看不清，恢复句是“本页只证明交互链路存在，具体界面细节可以在备份或实际系统中查看。”

### Slide 15. 受控测试集用隐藏底线用户画像检验系统是否真的恢复真实偏好

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 15.
- Target / checkpoint: 0:55, cumulative 11:15.
- Speaker notes:
  - “实验部分不是只看答案是否像，而是看系统能否在多轮过程中恢复隐藏底线。”
  - “终稿第 4 章围绕 180 条受控测试画像组织自动化运行。”
  - “画像里有显式话语，也有只供 simulator 和 evaluator 使用的隐藏偏好字段；Agent 本身不能读取 hidden persona。”
  - “这样可以控制变量，比较完整系统、静态检索基线和消融系统在同一类隐藏偏好任务上的表现。”
- Transition in: “从这里进入验证。”
- Transition out: “先看完整系统和静态检索提示的横向比较。”
- Emphasis cues:
  - Slow down: “Agent 不读取 hidden persona”。
  - Skip if short: 指标定义只点名 F1@N 和 MAE。
  - Avoid: 不说模拟用户等同真实用户。
- Source anchors: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:101-127`。
- Term / demo cues: hidden persona、simulator、evaluator 可用中文解释。
- Delivery risk and recovery line: 如果被质疑模拟用户，恢复句是“这类评测适合做机制差异的受控比较，但不能替代真实用户研究，结尾我会主动说明这个局限。”

### Slide 16. 参考基线横评显示，完整系统的优势来自交互式证据链路而不是更强的单轮生成

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 16.
- Target / checkpoint: 0:55, cumulative 12:10.
- Speaker notes:
  - “参考基线横评覆盖五个基座模型，每个模型比较完整系统、静态检索直接提示和静态检索思维链提示。”
  - “从结果上看，完整系统在 F1@1、F1@3、F1@5 上整体优于静态检索提示；思维链提示也没有稳定超过完整系统。”
  - “我这里不逐项读表，重点是设计含义：更强模型或更长提示不一定能解决隐藏偏好，交互式证据链路本身有贡献。”
- Transition in: “第一组证据是横向基线比较。”
- Transition out: “第二组证据是固定模型下的内部消融。”
- Emphasis cues:
  - Slow down: “整体优于”“没有稳定超过”，不要说成绝对碾压。
  - Skip if short: 五个模型名称不逐个念，只说图中列出。
  - Avoid: 不说所有场景显著领先。
- Source anchors: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:151-183`。
- Term / demo cues: F1@N 只解释为头部推荐命中质量即可。
- Delivery risk and recovery line: 如果差距看起来不大，恢复句是“在高风险推荐里，除了最终分数，头部候选边界和过程可复查同样重要。”

### Slide 17. 主消融实验显示，主动探测和后验追踪分别支撑探测方向选择与反馈吸收

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 17.
- Target / checkpoint: 0:55, cumulative 13:05.
- Speaker notes:
  - “主消融固定 GLM-5.1，比完整系统、去除主动探测、去除后验追踪三个版本。”
  - “完整系统的 MAE 为 0.144±0.045，去除主动探测后 MAE 上升到 0.178±0.035；去除后验追踪后，F1 系列也低于完整系统。”
  - “这说明两个机制分别有作用：主动探测帮助系统问对方向，后验追踪帮助系统吸收反馈。”
  - “所以完整链路不是单个模块堆叠，而是问对方向和记住反馈缺一不可。”
- Transition in: “横评说明完整链路有价值，消融说明价值来自哪里。”
- Transition out: “如果时间允许，我再用过程指标补一句为什么这些机制起作用。”
- Emphasis cues:
  - Slow down: “问对方向、记住反馈”。
  - Skip if short: 只讲 MAE 和 F1 退化，不读标准差。
  - Avoid: 不把标准差较大的结果说成强统计结论。
- Source anchors: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:211-238`。
- Term / demo cues: MAE 可解释为偏好恢复误差，F1@N 可解释为头部候选匹配。
- Delivery risk and recovery line: 如果被问显著性，恢复句是“主线里我采用稳健表述：结果支持机制贡献趋势，外部有效性和更大规模验证仍是后续工作。”

### Slide 18. 过程指标说明完整系统更能形成有张力的问题并稳定更新偏好状态

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 18.
- Target / checkpoint: 0:25, cumulative 13:30.
- Speaker notes:
  - Standard version: “过程指标补充说明了刚才的消融结论：完整系统更能选到有效探测方向、构造有张力的取舍问题，并把反馈稳定写入后验状态。”
  - “如果时间紧，这页可以只作为一句解释，不展开三张图。”
  - “核心就是：效果不是魔法，而是选轴、构造取舍、更新状态这条链路在起作用。”
- Transition in: “用过程指标补一个机制解释。”
- Transition out: “最后回到本设计的总体贡献。”
- Emphasis cues:
  - Slow down: 只慢读“选轴 -> 取舍 -> 后验”。
  - Skip if short: 全页跳过，只在 Slide 17 末尾加一句。
  - Avoid: 不展开所有过程指标数值。
- Source anchors: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:266-296`。
- Term / demo cues: 资产阶段应择一张过程图或重绘三步解释，避免拥挤。
- Delivery risk and recovery line: 如果已经超时，恢复句是“过程指标细节我放到备份材料，这里直接进入贡献总结。”

### Slide 19. 本设计把事实证据、主动澄清、在线后验和可复查评测组织成一个工程闭环

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 19.
- Target / checkpoint: 0:45, cumulative 14:15.
- Speaker notes:
  - “回到开场的问题：高考志愿推荐要同时守住事实可信和偏好真实。”
  - “本设计的贡献可以收束成一个闭环：问题定义上提出隐藏底线澄清，数据层提供可审计事实，决策层完成主动取舍，运行时链路保存过程，受控测试验证机制。”
  - “所以它不是简单把大模型接到推荐系统后面，而是把事实、取舍、反馈和评测组织成一个可复查的工程系统。”
- Transition in: “最后总结贡献。”
- Transition out: “当然，这个系统也有明确边界。”
- Emphasis cues:
  - Slow down: “不是简单接大模型，而是组织闭环”。
  - Skip if short: 五项贡献只读关键词。
  - Avoid: 不新增任何新贡献。
- Source anchors: `fact_ledger_v0.md` §3；`ppt_defense_narrative_v0.md` §4.5。
- Term / demo cues: “工程闭环”要连接到前面的 Data / Agent / Benchmark。
- Delivery risk and recovery line: 如果贡献显得多，恢复句是“这些贡献共同服务同一个目标：先问清底线，再推荐。”

### Slide 20. 系统仍需真实用户研究和泛化验证，但已证明高风险推荐中先问清底线再推荐的技术路径

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 20.
- Target / checkpoint: 0:35, cumulative 14:50.
- Speaker notes:
  - “最后，我也不把系统说成生产级升学顾问。”
  - “当前实验主要基于模拟用户和受控测试画像，后续还需要真实用户或专家评估、跨省跨年份泛化验证，以及更完善的用户控制机制。”
  - “在当前范围内，实验结果初步支持了一个技术路径：高风险推荐里，应该先用确定性事实锁住边界，再通过多轮取舍问清底线，最后再给出推荐解释。”
- Transition in: “讲清边界，避免过度声明。”
- Transition out: “我的汇报到这里，谢谢各位老师。”
- Emphasis cues:
  - Slow down: “不说成生产级升学顾问”。
  - Skip if short: 后续工作三项只保留前两项。
  - Avoid: 不让局限压过贡献；先说已证明路径，再说扩展方向。
- Source anchors: `fact_ledger_v0.md` §1, §8；`07-conclusion.tex:28-38`。
- Term / demo cues: “真实用户研究”和“泛化验证”要自然过渡到 Q&A。
- Delivery risk and recovery line: 如果结尾显弱，恢复句是“这些局限并不否定当前贡献，而是说明从机制验证走向真实部署还需要更严格验证。”

### Slide 21. 致谢与 Q&A

- Linked storyboard item: `PPT_storyboard_v0.md` Slide 21.
- Target / checkpoint: 0:10, cumulative 15:00.
- Speaker notes:
  - “我的汇报结束，感谢各位老师，欢迎批评指正。”
- Transition in: 结束主讲。
- Transition out: 进入 Q&A。
- Emphasis cues:
  - Slow down: 不需要。
  - Skip if short: 不可跳过，但只保留一句。
  - Avoid: 不继续补充新内容。
- Source anchors: not applicable.
- Term / demo cues: not applicable.
- Delivery risk and recovery line: 如果时间已到，直接结束，不补讲备份信息。

## 3. First dry-run checklist

Before rehearsal:

- 打开 storyboard，确认每页 action title 能单独串成故事。
- 对 Slide 2 讲“简要现状评测”，但不要讲未核验产品功能；重点是从本文问题视角看，传统推荐和 AI empowered 方案仍需要进一步解决隐藏底线的证据化、多轮、可复查澄清。
- 对 Slide 5 记住横版架构图还未生成，当前讲稿只绑定“应展示什么”。
- 对 Slide 16-17 准备只讲图上最关键趋势，不逐项读数。

During rehearsal:

- 开手机秒表或录音，按 Slide 5 / 9 / 14 / 18 / 21 做时间标记。
- 每页讲完立刻转，不在同一页补充“顺便说一下”。
- 遇到公式页只讲直觉，公式细节留给后续 Q&A/backup 阶段。
- Slide 18 只给 25 秒，训练自己能自然跳过。

After rehearsal:

- 记录实际总时长和超时页。
- 标出哪几页讲起来像背稿，改成更短 cue。
- 标出哪几页需要真实图后才能讲顺，交给后续 asset/layout 阶段。
- 如果总时长超过 15:30，优先执行 cut-down plan A。

## 4. Cut-down plan

### Plan A: 14:30 稳妥版

- Slide 2 压到 20 秒：只说“现有方案能查询/生成建议，但缺少证据化多轮澄清机制”。
- Slide 7 压到 25 秒：只读 22,759、140,995、3,219 三个数和“覆盖不等于全对”。
- Slide 10-12 每页少一个例子，保留机制动词。
- Slide 18 直接跳过，用 Slide 17 末尾一句带过。
- Slide 20 压到 25 秒。

### Plan B: 13:30 快讲版

- Slide 2 合并到 Slide 3 的开场口播。
- Slide 7 合并到 Slide 6，只保留“专业树/地域树提供可审计覆盖”。
- Slide 11-12 合并讲成“问什么/怎么问”。
- Slide 18 删除。
- Slide 14 只展示截图，不解释后台审计。

### Plan C: 临场超时急救

- 如果 Slide 14 结束时已经超过 11:00：实验部分只讲 Slide 15、16、17，跳过 18。
- 如果 Slide 17 结束时已经超过 13:45：Slide 19 只讲一句贡献闭环，Slide 20 只讲“真实用户和泛化仍是后续工作”。
- 如果时间只剩 30 秒：直接跳到 Slide 20 的最后一句和 Slide 21。

## 5. Sections to rehearse slowly

- Slide 3-4：必须把“隐藏底线”和“三步总解法”说顺，这是全场入口。
- Slide 5：架构图不要读模块名，要讲清 Data / Agent / Benchmark 的角色。
- Slide 9-12：方法段最容易术语堆叠，按“保护、选择、呈现、记住”四个动词练。
- Slide 16-17：结果页要练“不逐项读图”的表达，并保持谨慎措辞。
- Slide 20：局限性要稳，不要讲成自我否定。

## 6. Slides needing user confirmation before confident delivery

- Slide 2：阳光高考、夸克高考的具体展示形态、截图文字，以及“传统推荐 / AI empowered”两类现状评测措辞，需要后续 asset/layout 阶段核验。
- Slide 5：系统架构图应从原作图脚本重排横版，确认是全图主视觉还是局部标注。
- Slide 9-12：候选解释性视觉：后续 asset/layout 阶段判断是否加入一张“宏观流程 + 算法显微镜”示意图，用输入输出的可视化表征展示“用户显式话语 + 事实候选 -> 底线保护 -> 探测选轴 -> A/B 取舍 -> 后验状态 -> 推荐解释”。若确认需要 AI 生成学术图，再进入 academic figure prompt、content fidelity QA 和用户批准生成。图中可考虑 3 个细节 inset：SAVF 内部机理（单属性价值曲线、底线惩罚、截断/压低候选）、UCB 内部机理（收益线索 + 不确定性 -> 选轴分数）、BT 后验/偏好状态如何影响下一轮选轴、候选打分或最终解释。该图只作解释性视觉，不承载新增实验事实。
- Slide 12：是否加入一个贯穿 A/B 取舍小例子；若用具体学校或专业，必须先做事实核验。
- Slide 14：前端截图是否足够清晰，是否需要裁剪或重排。
- Slide 18：正式主讲是否保留，还是移入备份。
- Slide 20：局限性页的语气是否更偏“稳健”还是更偏“未来工作展望”。

## 7. Known unresolved delivery risks

| Risk | Affected slides | Rehearsal handling |
| --- | --- | --- |
| 时间略紧 | 7, 10-12, 18 | 按 cut-down plan 训练一遍 14:30 版本。 |
| 方法术语密度高 | 9-12 | 始终用“保护、选择、呈现、记住”复述。 |
| 算法流程示意图候选需后续决策 | 9-12 | 建议采用“主流程 + SAVF/UCB/偏好状态影响候选打分或解释三个 inset”；进入 asset/layout 后判断是否需要，若需要 AI 图，再写 prompt 并过 content fidelity QA。 |
| 产品对比事实未核验 | 2 | 讲简要现状评测，但不展开竞品报告；具体功能和截图后续核验。 |
| 架构图当前为论文竖版 | 5 | 讲稿保留横版重排意图，资产阶段再执行。 |
| 数据覆盖容易被误解为全对 | 7 | 主线主动说“覆盖不等于全部语义人工正确”。 |
| 模拟用户外部有效性 | 15, 20 | 主线主动承认受控测试局限。 |
| 实验结果被要求显著性 | 16-17 | 用“整体趋势、支持机制贡献”措辞，不夸大。 |

## 8. Handoff notes for `ppt-defense-qa-backup-stage`

只记录后续 Q&A/backup 阶段需要覆盖的主题，不在本阶段生成回答或备份页：

- LLM 事实边界与幻觉风险。
- 专业树覆盖、验证集错分和 Hit@10 边界。
- 地域树是否能代表就业、生活成本或城市收益。
- UCB 作为工程启发式而非严格最优策略。
- 模拟用户和受控测试画像的外部有效性。
- 指标提升幅度、标准差和“机制贡献趋势”的表述边界。
- 旧口径实验与终稿第 4 章实验之间的边界。
- 横版系统架构图重绘的脚本来源和不覆盖论文竖版原则。

## 9. Rehearsal evidence status

- 当前没有用户提供的录音、试讲记录或逐页计时日志。
- 因此本阶段不创建 `align/rehearsal_evidence_v*.md`。
- 用户试讲后可补充实际时长、卡顿页和不顺的转场，再单独生成 rehearsal evidence artifact。

## 10. Current status

This artifact is currently `unconfirmed` because the storyboard has been reset. Before this can be confirmed again, first revise and confirm the storyboard exhibit-form decisions, especially where formulas should replace or complement flow diagrams.

Next required action: wait for detailed storyboard feedback, revise `align/PPT_storyboard_v0.md`, then rerun this speaker-notes stage.
