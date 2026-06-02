---
stage: defense_qa_backup
stage_status: unconfirmed
requires_confirmed:
  - ppt_production_brief
  - fact_ledger
  - defense_narrative
  - storyboard
  - speaker_notes_rehearsal
blocked_next_stage: ppt-asset-layout-plan
previously_confirmed_by: user, 2026-05-31
reset_by: user, 2026-06-01
reset_reason: Storyboard and speaker notes are unconfirmed; backup formula pages and Q&A posture may need revision.
created_at: 2026-05-31
source_brief: align/ppt_production_brief_v0.md
source_fact_ledger: align/fact_ledger_v0.md
source_defense_narrative: align/ppt_defense_narrative_v0.md
source_storyboard: align/PPT_storyboard_v0.md
source_speaker_notes: align/ppt_speaker_notes_rehearsal_v0.md
---

# 答辩 Q&A 与 backup slide plan v0

## 0.1 2026-06-01 reset note

Status reset to `unconfirmed` because the storyboard and speaker notes may change. Backup formula pages and formula-related Q&A answers should be reconsidered after detailed user feedback.

## 0. Stage contract

- 本阶段目标：准备答辩问答策略和 backup-only slides，帮助现场追问时快速回到证据、边界和安全说法。
- 本阶段不做：不改 confirmed storyboard / speaker notes，不做资产布局，不写 image2 prompt，不生成图，不生成 PPTX。
- 回答风格：先正面回答，再给证据锚点，最后主动标明边界；避免防御性、绝对化和超出终稿的承诺。
- 安全总句：本系统不是让 LLM 自由生成志愿事实，而是把确定性招生事实、多轮偏好澄清和可复查评测组织成一个工程闭环。

## 1. Answer posture

| Situation | Recommended posture | Avoid |
| --- | --- | --- |
| 被问“是不是只是大模型应用” | 承认使用 LLM，但强调 LLM 边界与偏好澄清机制。 | “完全自主智能体”“全自动决策”。 |
| 被问实验显著性或提升幅度 | 用“趋势支持机制贡献”“头部候选与过程可复查价值”回答。 | “显著碾压”“所有模型都绝对领先”。 |
| 被问模拟用户局限 | 主动承认外部有效性边界，同时说明受控测试适合机制比较。 | 把模拟用户等同真实用户。 |
| 被问数据覆盖 | 解释“可审计挂载覆盖”，同时说明不等于全部语义人工正确。 | “专业树全对”“地域树能代表就业机会”。 |
| 被问 image2 / 算法图 | 说明它只是候选解释性视觉，需后续 asset/layout、academic prompt 和 fidelity QA。 | 当前阶段承诺生成或把图当实验事实。 |

## 2. Question matrix

### Q01. 这个题目是不是只是 RAG + prompt 包装？

- Concern: 贡献新意、方法深度。
- Answer thesis: 静态 RAG 解决事实召回，但本文的核心贡献是事实约束下的多轮偏好澄清和后验状态更新。
- Concise answer draft: “RAG 或静态检索能帮助找到候选事实，但它主要依赖用户显式话语和一次性排序。本文进一步解决的是用户首轮表达不完整时，系统如何通过 SAVF、UCB、Pareto A/B 和 Bradley-Terry 后验，把隐藏底线转化为可回答、可记忆、可复查的取舍过程。”
- Source anchors: `fact_ledger_v0.md` §1, §2, §5；`ppt_defense_narrative_v0.md` §6；main Slides 8-12。
- Rubric concern: contribution novelty; method validity.
- Backup slide anchor: B04, B05, B06, B07.
- Risk level: High.
- Safe fallback: “如果只看事实召回，可以把它视作 RAG 增强；但论文的主要比较对象和消融关注的是交互式偏好澄清链路。”

### Q02. 现有志愿填报产品和 AI 工具已经很多，你的系统差异在哪里？

- Concern: 实际价值、与现有方案关系。
- Answer thesis: 现有方案可提供信息入口、条件筛选和建议生成；本文聚焦的是隐藏底线的证据化、多轮、可复查澄清。
- Concise answer draft: “现有产品能帮助查信息、筛条件或生成建议。我的答辩里只做简要现状评测，不把阳光高考、夸克高考等作为实验基线。本文关注的差异是：当用户第一句话不完整时，系统能否在真实证据范围内追问放宽什么、坚持什么，并把反馈写入状态。”
- Source anchors: `ppt_speaker_notes_rehearsal_v0.md` Slide 2；`ppt_defense_narrative_v0.md` §4.1；`PPT_storyboard_v0.md` Slide 2。
- Rubric concern: relation to prior work; practical significance.
- Backup slide anchor: B14.
- Risk level: Medium.
- Safe fallback: “具体产品功能需要后续公开页面核验；主线只讨论本文问题视角，不做完整竞品评测。”

### Q03. 大模型会不会编造学校、专业、分数、位次或学费？

- Concern: 高风险事实可信度。
- Answer thesis: 事实候选来自 PostgreSQL 和标准化证据层，LLM 不直接生成事实候选。
- Concise answer draft: “这正是系统设计的边界。学校、专业、分数、位次、学费等事实不由 LLM 自由生成，而由 PostgreSQL 和标准化证据层返回。LLM 的职责是语义归一、探测规划和表达组织。”
- Source anchors: `fact_ledger_v0.md` §1, §2, §5, §8；main Slide 6。
- Rubric concern: system reliability; safety.
- Backup slide anchor: B01.
- Risk level: High.
- Safe fallback: “这不意味着表达层永远不会出错，所以后续仍需要审计、日志和用户确认；但候选事实来源边界是受控的。”

### Q04. 专业树全量覆盖是不是代表专业语义都完全正确？

- Concern: 数据质量、过度声明。
- Answer thesis: 全量覆盖是可审计挂载覆盖，不等于全部语义边界人工正确。
- Concise answer draft: “专业树覆盖 22,759 / 22,759 个原始去重专业名，并挂载 140,995 / 140,995 条录取记录，remaining_unassigned 为 0。但这指的是可审计挂载覆盖，不代表每个语义边界都人工确认无误。验证集中仍有错分边界，后续可通过 HITL 优化。”
- Source anchors: `fact_ledger_v0.md` §4；`major_tree_annotation_summary.md`; main Slide 7。
- Rubric concern: data validity.
- Backup slide anchor: B02.
- Risk level: High.
- Safe fallback: “我不会把覆盖率说成全库语义正确率；如果老师关心准确率，我会展示 clean validation 和错分边界。”

### Q05. 地域树能否代表就业机会、生活成本或城市生活质量？

- Concern: 不当因果、数据边界。
- Answer thesis: 地域树提供地理/城市层级证据，不编码城市收益或生活质量收益。
- Concise answer draft: “地域树覆盖 414 个省-市对、3,219 所学校和 35 个省份映射，用于组织地理和城市层级证据。它不能直接等价为就业机会、生活成本或城市生活质量，这些属于后续更复杂的证据维度。”
- Source anchors: `fact_ledger_v0.md` §4, §8；main Slide 7。
- Rubric concern: validity and generalization.
- Backup slide anchor: B03.
- Risk level: Medium.
- Safe fallback: “当前系统只把地域作为证据结构之一，不把城市层级解释成经济收益或生活质量收益。”

### Q06. 为什么不用线性加权推荐？

- Concern: 方法必要性。
- Answer thesis: 高考志愿存在预算、专业、地域和风险等非补偿性底线，线性总分容易掩盖严重违约。
- Concise answer draft: “线性加权会让一个维度的高分抵消另一个维度的严重违约。高考志愿中，超预算或严重专业偏离往往不是学校层次高就能补偿的，所以需要 SAVF 和惩罚机制先保护底线，再做取舍澄清。”
- Source anchors: `fact_ledger_v0.md` §5；`02-problem-algorithm.tex:119-152`; main Slide 10。
- Rubric concern: method validity.
- Backup slide anchor: B05.
- Risk level: Medium.
- Safe fallback: “我主线讲机制直觉，公式细节和参数解释放在备份页。”

### Q07. UCB 在这里是不是理论最优？

- Concern: 理论过度声明。
- Answer thesis: UCB 在本文中是工程启发式选轴策略，不是严格最优信息增益证明。
- Concise answer draft: “本文用 UCB 是为了在有限轮次中优先问更可能暴露隐藏底线的维度，它结合收益线索和不确定性。它不是严格最优信息增益推导，后续工作可以比较随机选轴、最大方差、最大均值等策略。”
- Source anchors: `fact_ledger_v0.md` §5, §8；`ppt_defense_narrative_v0.md` §6；main Slide 11。
- Rubric concern: method validity; limitations.
- Backup slide anchor: B06.
- Risk level: High.
- Safe fallback: “我不会把它说成理论最优，只说它是当前系统中可实现、可消融验证的选轴策略。”

### Q08. Pareto A/B 和 Bradley-Terry 后验到底解决了什么？

- Concern: 方法机制是否清楚。
- Answer thesis: Pareto A/B 把抽象偏好转成具体取舍，BT 后验把反馈写入可延续偏好状态。
- Concise answer draft: “用户不需要直接说出完整效用函数。系统构造具有边际替代关系的 A/B 候选，让用户看到放宽什么、换来什么；接受、拒绝或偏好反馈再通过 Bradley-Terry 后验更新偏好状态，影响下一轮选轴、候选打分或最终解释。”
- Source anchors: `fact_ledger_v0.md` §5；`03-system-design.tex:317-339`; main Slide 12。
- Rubric concern: method validity; user interaction.
- Backup slide anchor: B07.
- Risk level: Medium.
- Safe fallback: “我不说 BT 直接改写数据库查询参数；安全说法是反馈写入偏好状态，并影响后续决策。”

### Q09. 为什么实验主要用模拟用户，而不是真实学生？

- Concern: 外部有效性、实验设计。
- Answer thesis: 受控画像适合机制差异比较，但不能替代真实用户研究。
- Concise answer draft: “当前第 4 章实验围绕 180 条受控测试画像，适合控制变量，比较完整系统、静态检索基线和消融系统是否能恢复隐藏底线。但这不能替代真实学生或专家评估，我在结尾明确把真实用户研究和跨省跨年份泛化作为后续工作。”
- Source anchors: `fact_ledger_v0.md` §6.1, §8；`04-system-test-evaluation.tex:101-127`; main Slides 15, 20。
- Rubric concern: threats to validity; limitations.
- Backup slide anchor: B09, B13.
- Risk level: High.
- Safe fallback: “当前结论是机制验证，不是生产级用户有效性证明。”

### Q10. Agent 会不会读取 hidden persona，导致评测不公平？

- Concern: Benchmark 泄漏、评测可信度。
- Answer thesis: hidden persona 字段只供 simulator / evaluator 使用，不给 Agent。
- Concise answer draft: “评测中显式话语和隐藏偏好分离，hidden persona、implicit flexibilities、volunteer_set 等字段只供 simulator 和 evaluator 使用，Agent 不读取这些字段。这样才能检查系统是否通过多轮交互恢复隐藏底线。”
- Source anchors: `ppt_production_brief_v0.md` §4；`fact_ledger_v0.md` §7；`ppt_speaker_notes_rehearsal_v0.md` Slide 15。
- Rubric concern: experimental design.
- Backup slide anchor: B09.
- Risk level: High.
- Safe fallback: “如果老师需要，我会展示 benchmark flow 中的信息边界，而不是展开全部数据字段。”

### Q11. 指标提升幅度不大，为什么还值得做？

- Concern: 实验说服力、实际价值。
- Answer thesis: 高风险推荐更重视头部候选、偏好边界可信度和过程可复查；结果应表述为支持机制贡献趋势。
- Concise answer draft: “我不把结果说成显著碾压。完整系统在参考基线横评和主消融中呈现更好的头部推荐和偏好对齐趋势。更重要的是，完整系统把事实、取舍、反馈和后验状态连成可复查过程，这对高风险推荐比单轮答案分数更重要。”
- Source anchors: `fact_ledger_v0.md` §1, §6.1, §8；main Slides 16-18。
- Rubric concern: evidence strength.
- Backup slide anchor: B10, B11.
- Risk level: High.
- Safe fallback: “我会使用‘趋势支持’而不是‘充分证明生产有效’。”

### Q12. 为什么选择这些基线和消融？

- Concern: Baseline fairness, ablation validity.
- Answer thesis: 参考基线比较完整系统与静态检索提示，主消融固定模型检查主动探测和后验追踪贡献。
- Concise answer draft: “第 4 章先在五个基座模型上比较完整系统、静态检索直接提示和静态检索思维链提示；再固定 GLM-5.1 做主消融，比较完整系统、去除主动探测、去除后验追踪。前者回答交互链路是否优于单轮提示，后者回答链路中的关键模块是否有贡献。”
- Source anchors: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:101-124`; main Slides 16-17。
- Rubric concern: experimental design.
- Backup slide anchor: B10.
- Risk level: Medium.
- Safe fallback: “旧七组实验、multi_axis_v2 和 v1_hybrid_rag 是历史或补充口径，不覆盖当前终稿主实验。”

### Q13. 系统是否已经能替代真实升学顾问？

- Concern: 过度应用声明。
- Answer thesis: 不能替代，当前定位是高风险推荐中的决策支持和机制验证。
- Concise answer draft: “不能替代真实升学顾问。当前系统证明的是一种先锁事实、再问取舍、后给推荐解释的技术路径。真实部署还需要真实用户研究、专家评估、跨省跨年份验证、隐私合规和更丰富的证据维度。”
- Source anchors: `fact_ledger_v0.md` §1, §8；`07-conclusion.tex:28-38`; main Slide 20。
- Rubric concern: practical significance; limitations.
- Backup slide anchor: B13.
- Risk level: Medium.
- Safe fallback: “我会把它称为可审计决策支持系统，而不是自动升学决策系统。”

### Q14. 系统工程是否真正落地，还是只有概念图？

- Concern: 工程完整性。
- Answer thesis: 系统包含数据证据层、推荐决策层、智能体服务层、交互展示层和受控测试环境，并用状态机组织交互过程。
- Concise answer draft: “系统不是纯概念图。主线里有四层架构，数据证据层负责候选事实，推荐决策层负责 SAVF/UCB/Pareto/BT，智能体服务层组织语义归一和探测规划，前端呈现取舍问题与推荐报告，评测环境用于自动化受控测试。”
- Source anchors: `fact_ledger_v0.md` §3, §5, §9；main Slides 5, 13-14。
- Rubric concern: engineering completeness.
- Backup slide anchor: B08, B15.
- Risk level: Medium.
- Safe fallback: “如果需要具体代码路径，放到备份页讲，不在主线展开。”

### Q15. 为什么更强模型或更长 CoT 提示不能解决问题？

- Concern: relation to LLM prompting / prior work.
- Answer thesis: 提示增强可能改善表达，但隐藏偏好需要交互式证据链路和状态更新。
- Concise answer draft: “更强模型和思维链提示可以改善单轮表达，但不等于知道用户愿意放宽哪条底线。横评中思维链提示没有稳定超过完整系统，说明隐藏偏好问题不能只靠单轮生成解决，还需要证据驱动的多轮取舍和后验状态。”
- Source anchors: `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:151-183`; main Slide 16。
- Rubric concern: relation to prior work; experimental evidence.
- Backup slide anchor: B10.
- Risk level: Medium.
- Safe fallback: “我会说‘没有稳定超过’，不说 CoT 一定无效。”

### Q16. image2 生成的算法示意图会不会变成新的未经验证内容？

- Concern: visual fidelity, stage gate, content integrity.
- Answer thesis: 该图只作为候选解释性视觉，不能承载新增事实；正式生成必须等 asset/layout、academic prompt 和 content fidelity QA。
- Concise answer draft: “我计划把它作为后续候选解释性视觉，用来帮助理解 SAVF、UCB、Pareto/BT 的输入输出表征。它不作为实验结果，也不新增事实。若最终决定使用，必须先在 asset/layout 阶段确认需要，再写 academic figure prompt，经过 content fidelity QA 后才允许生成。”
- Source anchors: `ppt_speaker_notes_rehearsal_v0.md` §6-7；`manuscript-to-ppt-workflow` stage gate；main Slides 9-12。
- Rubric concern: visual integrity; workflow compliance.
- Backup slide anchor: B16.
- Risk level: Medium.
- Safe fallback: “如果不确定，就改为可编辑流程图或把完整三 inset 版本放到备份。”

### Q17. 失败样本或旧口径实验怎么处理？

- Concern: consistency with final thesis, honesty about failures.
- Answer thesis: 旧口径实验可作为项目演化备份，终稿主线以第 4 章 180 条受控画像实验为准。
- Concise answer draft: “项目 manifest 里有旧七组实验、压力测试和 pilot 数值，但当前答辩以最终 LaTeX 第 4 章为主。像 `major_geo_v1` 不是 100% 成功，失败样本 `real-db-set-浙江-569-009` 只在追问项目演化或失败边界时作为备份说明。”
- Source anchors: `fact_ledger_v0.md` §6.2, §10；`ppt_production_brief_v0.md` §4。
- Rubric concern: evidence consistency; failure cases.
- Backup slide anchor: B12.
- Risk level: Medium.
- Safe fallback: “不把旧实验写成当前主实验，不用历史口径覆盖终稿。”

## 3. Backup-only slide plan

| Backup ID | Action title | Answers | Evidence source / fact IDs | Visual or table needed | Asset source or redraw requirement | Placement policy | Count in talk? | Editability / QA risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B01 | LLM 不生成事实候选，事实边界由证据层控制 | Q03 | `fact_ledger_v0.md` §1, §2, §5, §8 | LLM 与 PostgreSQL/证据层分工图 | 可编辑简图，或从数据库物理图抽象重画 | Hidden appendix | No | 避免画成 LLM 直接连学校分数生成。 |
| B02 | 专业树覆盖是可审计挂载，不等于全语义正确 | Q04 | `fact_ledger_v0.md` §4；`major_tree_annotation_summary.md` | 覆盖数字 + validation 小表 | 可编辑表格；可用专业树缩略图 | Hidden appendix | No | 数字必须与 ledger 一致；避免“全对”。 |
| B03 | 地域树提供地理层级证据，不编码就业或生活质量 | Q05 | `fact_ledger_v0.md` §4, §8 | 省-市-学校层级小图 + 边界标注 | 可编辑层级图 | Hidden appendix | No | 不写城市收益、生活成本、就业机会。 |
| B04 | 静态检索是强基线，但不能自然恢复隐藏底线 | Q01, Q12, Q15 | `fact_ledger_v0.md` §5；`02-problem-algorithm.tex:81-103` | 静态检索链路 vs 缺少偏好更新标注 | 可编辑流程图或复用静态 RAG 图 | Hidden appendix | No | 不贬低 RAG，只说明缺口。 |
| B05 | SAVF 保护底线，防止线性总分掩盖严重违约 | Q06 | `fact_ledger_v0.md` §5；`02-problem-algorithm.tex:119-152` | 线性补偿 vs SAVF 截断示意 | 可编辑示意图 | Hidden appendix | No | 公式可简化，不引入未确认参数。 |
| B06 | UCB 是工程启发式选轴，不是严格最优证明 | Q07 | `fact_ledger_v0.md` §5, §8；`fig:ucb-dispatch` | 收益线索 + 不确定性 -> 选轴分数 | 可编辑流程图或重绘 UCB 图 | Hidden appendix | No | 必须显式写“heuristic”。 |
| B07 | Pareto A/B 与 BT 后验把取舍反馈写入偏好状态 | Q08 | `fact_ledger_v0.md` §5；`03-system-design.tex:317-339` | A/B 卡片 + 后验权重条 | 可编辑 mockup；不使用未核验学校名 | Hidden appendix | No | 不说 BT 直接改写查询参数。 |
| B08 | 运行时状态机让澄清和终局推荐可回放 | Q14 | `fact_ledger_v0.md` §3, §5；`fig:runtime-state-machine` | 状态机简化图 | 复用或重排 `fig_5_2_runtime_state_machine` | Hidden appendix | No | 避免代码细节拥挤。 |
| B09 | Benchmark 信息边界：Agent 不读取 hidden persona | Q09, Q10 | `ppt_production_brief_v0.md` §4；`fact_ledger_v0.md` §7 | simulator / agent / evaluator 三栏边界图 | 可编辑流程图 | Hidden appendix | No | hidden 字段只作为评测端 ground truth。 |
| B10 | 基线横评和主消融用不同问题回答机制贡献 | Q11, Q12, Q15 | `fact_ledger_v0.md` §6.1 | 五模型横评 + GLM-5.1 消融小表 | 复用 `fig_4_5` / `fig_4_6` 或可编辑表 | Hidden appendix | No | 不逐项放满数值；避免显著性过度声明。 |
| B11 | 过程指标解释“选轴 -> 取舍 -> 后验”为什么起作用 | Q11 | `fact_ledger_v0.md` §6.1；`04-system-test-evaluation.tex:266-296` | 三步过程指标图 | 选择 `fig_4_8_1/2/3` 中最清晰者或重绘 | Hidden appendix | No | 图太多会拥挤，asset 阶段择一。 |
| B12 | 旧口径实验只作项目演化备份，不覆盖终稿主线 | Q17 | `fact_ledger_v0.md` §6.2, §10 | 旧口径/终稿口径对照表 | 可编辑表格 | Hidden appendix | No | 明确 `multi_axis_v2`、`v1_hybrid_rag` 边界。 |
| B13 | 局限与后续工作：真实用户、跨省跨年份、用户控制 | Q09, Q13 | `fact_ledger_v0.md` §1, §8；`07-conclusion.tex:28-38` | limitation / future work matrix | 可编辑表格 | After Q&A separator | No | 先强调当前机制验证价值，再讲边界。 |
| B14 | 现有产品简要现状评测不等于竞品报告 | Q02 | `ppt_defense_narrative_v0.md` §4.1；`ppt_speaker_notes_rehearsal_v0.md` Slide 2 | 传统推荐 / AI empowered / 本文关注点三栏 | 后续 asset/layout 阶段核验截图或抽象图 | Hidden appendix | No | 具体产品页面必须核验，避免事实错误。 |
| B15 | 工程实现路径：四层架构与关键模块归属 | Q14 | `fact_ledger_v0.md` §3, §5, §9 | 横版系统架构局部或模块表 | 由原作图脚本派生横版，不覆盖论文竖版 | Hidden appendix | No | 资产阶段执行，不在本阶段重绘。 |
| B16 | 算法示意图若使用，只是解释性视觉，不是新增证据 | Q16 | `ppt_speaker_notes_rehearsal_v0.md` §6-7；workflow stage gate | 主流程 + 三个算法 inset 的概念草图 | 先在 asset/layout 判断；需要 AI 图则走 academic prompt | Hidden appendix or candidate visual | No | 不写正式 prompt，不生成图，不新增事实。 |

## 4. Backup prioritization

优先级 A：强烈建议保留，答辩追问概率高。

- B01 LLM 事实边界。
- B02 专业树覆盖边界。
- B06 UCB 非严格最优。
- B09 Benchmark hidden persona 边界。
- B10 基线横评和主消融。
- B13 局限与后续工作。

优先级 B：建议保留，但可按 PPT 篇幅裁剪。

- B03 地域树边界。
- B04 静态检索基线不足。
- B05 SAVF 非补偿性。
- B07 Pareto A/B + BT 后验。
- B08 运行时状态机。
- B12 旧口径实验边界。

优先级 C：进入 asset/layout 阶段再判断。

- B11 过程指标解释图。
- B14 现有产品评测补充。
- B15 工程实现路径。
- B16 算法示意图生成边界。

## 5. Open decisions

- 现有产品页：是否需要把阳光高考、夸克高考截图放入备份，还是只保留三栏抽象对照。
- 备份页数量：A 级 6 页必须准备；B/C 级是否全部进入隐藏 appendix 待确认。
- 过程指标：B11 是否保留三张过程图，还是择一张最清晰图。
- 算法示意图：B16 / Slide 9-12 候选视觉是否在 asset/layout 阶段转入 academic figure prompt。
- 旧口径实验：B12 是否只列风险边界，还是加入具体失败样本 `real-db-set-浙江-569-009`。

## 6. Current status

This artifact is currently `unconfirmed` because the storyboard and speaker notes have been reset. Formula-related backup pages and Q&A posture may change after detailed storyboard feedback.

Next required action: revise and confirm the storyboard, rerun speaker notes, then rerun this Q&A/backup stage.
