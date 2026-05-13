# EDMIE: Evidence-Driven Mixed-Initiative Elicitation for Hidden Preference Discovery in High-Stakes College Admission Planning

## Abstract

高考志愿填报是一类典型的高风险、多目标、强约束决策场景。与一般商品推荐不同，考生及家庭往往并不会在第一轮交互中如实、完整、稳定地表达自己的真实偏好；相反，他们常以防御性语言给出过度苛刻的显式约束，例如“非 985 不去”“绝对不出省”“专业必须热门”，而真正的底线可能隐藏在水面之下：可以为更强专业牺牲学校层次，可以为预算安全拒绝名校，可以在地域和专业之间进行复杂妥协。这种“冰山式偏好”使传统 Tool AI 或 RAG 系统容易陷入两个问题：其一，系统把用户的显式说辞当作完整目标，导致可行域被错误收窄；其二，系统用线性加权总分补偿严重违约项，造成“线性补偿陷阱”，例如学费严重超标的名校方案仍被高分推荐。

本文提出 EDMIE（Evidence-Driven Mixed-Initiative Elicitation），一个面向高风险志愿决策的证据驱动混合倡议偏好引出框架。EDMIE 将 PostgreSQL 确定性 SQL 探针作为事实来源，避免大模型幻觉；在候选层引入非补偿性单属性价值函数（SAVF）和局部 Min-Max 归一化；在交互层以 UCB 不确定性上界强控探针方向，并通过帕累托边际替代率提问迫使用户暴露隐藏底线；在状态层用 Bradley-Terry 随机选择模型和 Dempster-Shafer 式犹豫处理进行在线 posterior 更新。系统由 LangGraph `interrupt/resume` 实现探索与利用的时空隔离：探索期只提出高信息增益问题，终局期才生成带显示性偏好解释的志愿报告。

在 Robust Iceberg Benchmark 上，EDMIE 展现出显著优势。相较无记忆 tracker 消融组，EDMIE 将偏好对齐 MAE 从 `0.203000` 降至 `0.131290`，相对下降约 `35.3%`，Welch t-test 显示差异显著（`p = 3.49248e-07`）。相较无 UCB 主动探测组，EDMIE 将平均交互轮次从 `2.916667` 降至 `2.000000`，减少约 `31.4%`，差异达到 `p = 1.81537e-20`。在隐性底线维度识别任务中，EDMIE 的 F1 达到 `0.833333`，而 no-UCB、no-tracker、Initial-query LLM 与 V1 Hybrid RAG baseline 均仅为 `0.333333`。这些结果表明，EDMIE 的性能增益不是来自大模型对初始输入的零样本猜测，而是来自证据约束、主动探测与连续 posterior 更新共同构成的认知闭环。

## 1. Introduction

近年来，大语言模型与检索增强生成（Retrieval-Augmented Generation, RAG）系统快速进入教育咨询、金融规划、医疗问诊、法律辅助等高风险决策场景。它们的常见形态仍然是 Tool AI：用户给出问题，系统调用检索或工具，随后生成一段貌似合理的答案。这种范式适用于事实查询和低风险建议，却并不适合偏好本身尚未被发现、甚至被用户防御性伪装的场景。

高考志愿填报正是这种困难的集中体现。考生面对的是一组相互冲突的目标：学校层次、专业匹配、学费预算、培养质量、地域距离、录取风险以及家庭期待。更重要的是，用户的第一句话通常不是完整偏好函数，而是压力、焦虑、社会标签和风险厌恶共同塑造的防御性陈述。例如，一个考生说“我想冲 985，也说江浙沪都可以看”，并不意味着他真的愿意为了学校层次牺牲专业匹配；另一个考生说“学费最好别太夸张”，也可能意味着学费是不可触碰的一票否决底线。若系统把这种显式输入当作稳定目标，就会把“表层愿望”误认为“真实效用”。

传统 RAG 系统在这里面临三个结构性缺陷。第一，事实检索和偏好建模混在一起，语言模型可能用生成能力补齐不存在的事实，从而产生偏好幻觉。第二，推荐排序通常采用线性加权分数，使某个维度的灾难性违约被其他维度的高分抵消。例如一所名校可能因学校层次得分极高而掩盖学费超预算、专业偏离或地域不可接受的问题。第三，系统没有主动提问机制，无法通过对比方案和边际替代来压缩用户偏好的不确定性。一次性推荐表看似完整，却把认知负担直接转嫁给用户。

本文主张从 Tool AI 转向 Collaborative AI。Collaborative AI 不应只是被动执行用户的第一轮表达，而应主动形成假设、设计探针、提出反事实权衡、从反馈中更新 belief state，并在收敛后给出可解释建议。对于高考志愿填报，这意味着系统必须区分硬事实、显式约束、隐性权重和不确定性方差。它不能越过数据库事实编造候选；也不能让大模型自由决定哪些学校“更适合”；它需要在确定性候选池上用数学机制进行晚期融合，并把 LLM 限制在提问、解释和交互表达层。

为此，我们提出 EDMIE，一个 Evidence-Driven Mixed-Initiative Elicitation Agent。EDMIE 的关键思想是把“偏好引出”看作一个多轮序贯决策问题，而不是一次性问答。系统先用确定性 SQL 探针从 PostgreSQL 中检索事实候选，再将候选映射为无量纲特征向量；随后基于当前 posterior 的权重均值与方差，用 UCB 策略选择最值得探索的偏好维度；然后构造具有最大帕累托张力的候选对，向用户发起“放宽某项代价以换取某项收益”的边际替代提问；最后用用户的接受、拒绝或犹豫反馈更新权重和方差。这个循环持续到不确定性收敛或轮次达到上限，系统再进入终局推荐。

本文的贡献如下。

第一，我们提出一种高考志愿场景下的非补偿性候选价值映射，将学费等安全底线以一票否决形式嵌入 MAUT，避免线性补偿陷阱。

第二，我们提出 UCB 强控的主动探针规划，使大模型不能盲目规划问题，而必须围绕最高不确定性维度发起高信息增益探索。

第三，我们将 Bradley-Terry 随机选择模型引入 HITL 偏好追踪，把用户对候选对的接受/拒绝反馈转化为逻辑斯蒂梯度更新；同时用 Dempster-Shafer 风格机制处理犹豫反馈，使系统在模糊态度下推高方差而不误改均值。

第四，我们构建 Robust Iceberg Benchmark，用带隐藏底线的用户模拟器自动与 EDMIE 及消融系统对弈，并同时报告 MAE、交互轮次、偏好维度 F1、参考 baseline 和逐轮日志质量。

第五，我们展示真实日志中的微观机制：no-UCB 会连续提出泛化而无效的问题，no-tracker 会在没有 posterior 记忆时重复确认同一底线，而 EDMIE 能在第一轮命中真实偏好维度，并在第二轮完成收网。

## 2. Problem Formulation

我们将高考志愿偏好引出建模为一个带隐藏用户效用的序贯决策问题。给定候选方案集合 $\mathcal{X}$，每个候选 $x \in \mathcal{X}$ 来自确定性数据库探针，而非语言模型生成。系统不能创造候选事实，只能对已检索事实进行特征映射、排序和解释。

用户的真实偏好由一个隐藏权重向量表示：

$$
\mathbf{w}^* =
\left[
w^*_{\text{school}},
w^*_{\text{major}},
w^*_{\text{tuition}},
w^*_{\text{quality}},
w^*_{\text{geo}}
\right],
\quad
\sum_k w^*_k = 1,\quad w^*_k \ge 0.
$$

系统在任意时刻 $t$ 维护一个 belief state：

$$
B_t =
\left(
\mathbf{w}_t,
\mathbf{v}_t
\right),
$$

其中 $\mathbf{w}_t$ 是隐性偏好权重的 posterior 均值，$\mathbf{v}_t$ 是每个维度的不确定性方差。初始状态采用归一化均匀权重：

$$
\mathbf{w}_0 =
\left[
0.2,0.2,0.2,0.2,0.2
\right],
$$

该修正保证 no-tracker、随机权重 baseline、Initial-query LLM baseline 与 EDMIE full 都在同一概率单纯形上比较。方差初始较高，表示系统尚不了解用户底线。

用户初始输入 $q_0$ 只被视为显式说辞，不被视为完整偏好函数。系统通过多轮提问 $a_t$ 获取用户反馈 $r_t$：

$$
q_0 \rightarrow a_1 \rightarrow r_1 \rightarrow a_2 \rightarrow r_2 \rightarrow \cdots \rightarrow \hat{\mathbf{w}}.
$$

实验目标不是最大化一次性推荐命中率，而是最小化 $\hat{\mathbf{w}}$ 与 $\mathbf{w}^*$ 的差距，并用尽可能少的交互轮次识别隐藏底线维度。

## 3. Methodology

### 3.1 Non-compensatory SAVF: 非补偿性单属性价值映射

EDMIE 的事实候选严格来自 SQL 探针。为了让候选可以进入多属性效用计算，我们先定义单属性价值函数（Single-Attribute Value Functions, SAVF），把物理记录映射为 $[0,1]$ 上的无量纲特征。给定候选 $x$，其特征向量为：

$$
\Phi(x)=
\left[
\phi_{\text{school}}(x),
\phi_{\text{major}}(x),
\phi_{\text{tuition}}(x),
\phi_{\text{quality}}(x),
\phi_{\text{geo}}(x)
\right].
$$

学校层次采用阶梯函数。若学校层次包含 C9 或顶尖 985，则 $\phi_{\text{school}}=1.0$；若包含 985，则为 $0.85$；若包含 211 或双一流，则为 $0.70$；若为一本或重点，则为 $0.40$；否则为 $0.10$。该函数并不声称学校层次是线性连续变量，而是把社会认知中的离散层级稳定地映射到有限刻度。

专业匹配和地域距离采用放宽惩罚：

$$
\phi_{\text{major}}(x)
=
\max(0, 1 - 0.35 \cdot L_{\text{major}}(x)),
$$

$$
\phi_{\text{geo}}(x)
=
\max(0, 1 - 0.30 \cdot L_{\text{geo}}(x)),
$$

其中 $L_{\text{major}}$ 和 $L_{\text{geo}}$ 分别表示专业本体树和地域约束树上的放宽层级。这样，专业从“计算机科学与技术”放宽到相邻专业，与放宽到完全无关专业，会获得不同程度的惩罚。

培养质量使用局部 Min-Max 归一化，而不是简单除以 100。对当前候选池 $\mathcal{C}$，设质量分数为 $Q(x)$，则：

$$
\phi_{\text{quality}}(x)
=
\frac{Q(x)-Q_{\min}}{Q_{\max}-Q_{\min}+\epsilon},
\quad
Q_{\min}=\min_{x \in \mathcal{C}} Q(x),
\quad
Q_{\max}=\max_{x \in \mathcal{C}} Q(x).
$$

若 $Q_{\max}=Q_{\min}$，则所有候选质量特征设为 $0.5$。这种局部归一化强调当前候选池内的相对差异，避免所有候选质量分集中在高区间时无法拉开差距。

学费维度采用非补偿性一票否决。设用户预算为 $B$，候选学费为 $T(x)$。若 $T(x)\le B$，则：

$$
\phi_{\text{tuition}}(x)=1.
$$

若超预算，则计算超额比例：

$$
\rho(x)=\frac{T(x)-B}{B}.
$$

当 $\rho(x)\ge 0.30$ 时，触发一票否决：

$$
\phi_{\text{tuition}}(x)=-9999.
$$

否则使用线性惩罚：

$$
\phi_{\text{tuition}}(x)=
\max(0,1-2\rho(x)).
$$

这一步是防止线性补偿陷阱的关键。传统 MAUT 若只允许各维度在 $[0,1]$ 间线性加权，则学校层次的高分可能抵消学费灾难性违约；EDMIE 将严重超预算编码为非补偿性负极值，使这种候选无论学校多好都不会被总分错误推高。

最终隐性效用为：

$$
U(x;\mathbf{w}_t)=
\sum_{k \in \mathcal{D}}
w_{t,k}\phi_k(x),
\quad
\mathcal{D}=
\{\text{school},\text{major},\text{tuition},\text{quality},\text{geo}\}.
$$

数据库候选在返回前均经过该效用排序，并附加 `_phi_features` 与 `_implicit_utility` 字段。这样，事实来源仍是 SQL，个性化排序则由 Python 侧确定性数学逻辑完成。

### 3.2 Max-EIG Probing via UCB: 基于置信上限的主动探测强控

EDMIE 并不把探针规划完全交给大语言模型。LLM 擅长生成自然语言问题，但并不天然知道哪一个偏好维度当前最有信息价值。因此，在调用语言模型之前，系统先用 UCB 计算每个维度的主动学习分数：

$$
\mathrm{UCB}_k
=
w_{t,k}
\beta \sqrt{v_{t,k}},
$$

其中 $\beta=1.5$ 控制探索强度。系统选择：

$$
k_t^*=
\arg\max_k \mathrm{UCB}_k.
$$

该维度会被映射到具体 SQL 探针。例如，`major` 和 `geo` 映射到 `major_geo_relax`，`tuition` 映射到 `tuition_value_relax`，`school` 映射到 `strength_relax`。即使 LLM 规划偏离，Python sanitizer 也会把 UCB 目标探针插入或提前到计划首位，从而保证主动探测不是提示词建议，而是真实控制约束。

在获得候选后，系统选择具有最大帕累托张力的候选对。基准解 $A$ 固定为当前效用 Top-1；候选 $B$ 从 Top-2 到 Top-10 中选择与 $A$ 特征差异最大的方案：

$$
B^*
=
\arg\max_{x \in \mathcal{C}_{2:10}}
\left\|
\Phi(x)-\Phi(A)
\right\|_1.
$$

由此得到差分向量：

$$
\Delta \Phi =
\Phi(B^*)-\Phi(A).
$$

理想情况下，这个候选对会构成清晰的边际替代：方案 $B$ 在某个代价维度下降，但在某个收益维度上升。系统随后要求 LLM 用自然语言表达这种权衡，例如“从某专业放宽到另一专业，以换取学校层次提升”。在最终日志中，为了避免伪造收益，系统已经会在没有明确正向跃迁时如实说明“当前候选没有带来明确的学校层次正向提升”，并转化为底线确认问题。这种保守表达牺牲了一部分话术张力，但避免把不存在的收益包装成真实收益。

帕累托提问的核心并不是说服用户接受系统建议，而是通过反事实压力暴露底线。当用户面对“是否愿意放宽专业匹配”的问题时，若其真实底线是专业不可偏离，拒绝就成为可用于 posterior 更新的强证据。

### 3.3 Online Posterior Tracking: Bradley-Terry 与 D-S 犹豫机制

EDMIE 将用户对候选对的反馈视为随机选择模型下的观测。若系统提出方案 $A$ 与方案 $B$ 的比较，且差分为 $\Delta \Phi=\Phi(B)-\Phi(A)$，则在当前权重 $\mathbf{w}_t$ 下，用户选择或接受 $B$ 的概率为：

$$
P_t(B)
=
\sigma
\left(
\tau \mathbf{w}_t^\top \Delta \Phi
\right)
=
\frac{1}{
1+\exp\left(-\tau \mathbf{w}_t^\top \Delta \Phi\right)
},
$$

其中 $\tau=3.0$ 是逆温度参数，控制选择概率对效用差的敏感程度。

若用户接受妥协，则标签 $Y=1$；若拒绝妥协、坚持原底线，则标签 $Y=0$。系统执行逻辑斯蒂梯度上升：

$$
\mathbf{w}_{t+1}
=
\mathbf{w}_t
\eta
\left(
Y-P_t(B)
\right)
\Delta \Phi,
$$

其中学习率 $\eta=0.3$。随后对权重进行截断并归一化：

$$
\tilde{w}_{t+1,k}
=
\mathrm{clip}(w_{t+1,k},0.05,0.95),
\quad
w_{t+1,k}
=
\frac{\tilde{w}_{t+1,k}}{\sum_j \tilde{w}_{t+1,j}}.
$$

在明确接受或拒绝时，系统同时降低方差以表示不确定性收敛：

$$
v_{t+1,k}
=
0.5 v_{t,k}.
$$

对于用户犹豫、模糊或问题没有命中底线的情况，EDMIE 不强行修改均值。我们将这种反馈视为 Dempster-Shafer 证据理论中的 ignorance，而非正负偏好证据。若目标维度为 $k$，则：

$$
w_{t+1,k}=w_{t,k},
\quad
v_{t+1,k}
=
\min(1.0,1.2v_{t,k}).
$$

若目标维度未知，则可提升所有维度方差。这一机制很重要：在 no-UCB 组中，系统经常提出泛化问题，模拟用户回复“这个问题没问到我的真正底线，我先保留。”若系统把这种犹豫误解释为接受或拒绝，会产生错误 posterior；EDMIE 则保持均值不变、提高不确定性，促使下一轮换方向继续探索。

### 3.4 Global Exploitation and 冲稳保收口

当总方差低于阈值或交互轮次达到上限时，radar 绕过 UCB 与 LLM planner，直接切换到全局收网探针 `probe_global_baseline`。该探针在硬约束安全可行域内检索较大候选池，再用当前隐性效用排序，并根据分差构建“冲、稳、保”矩阵：

$$
\text{reach}: m(x)\in[-5,5],
\quad
\text{match}: m(x)\in(5,15],
\quad
\text{safety}: m(x)>15.
$$

每个桶内按 `_implicit_utility` 降序取 Top-3。这样，终局推荐不只是给出效用最高的学校列表，而是符合高考志愿业务习惯的风险梯度结构。

## 4. System Architecture

EDMIE 的实现基于 LangGraph 状态机。传统聊天系统通常是“一跑到底”：用户输入后，图从语义解析一路执行到最终回答，中间不再停顿。这种结构不适合偏好引出，因为真正有价值的信息往往来自中途的反问与用户反馈。EDMIE 因此将控制流改造成 HITL 微循环。

图的关键节点包括：

1. `semantic_normalizer`：将用户自然语言输入标准化为结构化约束。
2. `gatekeeper`：检查硬约束是否足够，例如分数、选科、生源地、专业方向。
3. `radar`：基于 UCB 选择下一轮探针，并执行 SQL 检索。
4. `negotiator`：根据候选差异生成帕累托提问，或在终局生成 XAI 推荐报告。
5. `preference_tracker`：在 resume 后读取用户反馈，更新隐性权重和方差。

探索期的核心是 `interrupt()`。当 negotiator 构造出提问后，图在该位置冻结，并将问题交给外层调用者。用户或模拟器回复后，外层以 `Command(resume=...)` 唤醒图。LangGraph 会从原来的 `interrupt()` 调用点继续执行，而不是重新跑 semantic normalizer 或 gatekeeper。这一点保证了“原地唤醒”的认知连续性。

这种结构实现了探索与利用的时空物理隔离。在探索期，系统绝不输出完整推荐表，而是只提出一个短问题，例如是否愿意放宽专业匹配、地域距离或学费预算。这样可以避免长推荐列表对用户造成认知过载，也避免用户在偏好尚未澄清时被表面候选吸引。只有当 posterior 收敛后，系统才进入 exploitation，执行 global baseline，生成最终志愿报告。

EDMIE 还区分 LLM 的职责边界。候选事实来自 SQL，排序来自 MAUT 和 posterior，探针选择来自 UCB，偏好更新来自 Bradley-Terry 梯度。LLM 主要负责结构化抽取、自然语言提问和终局解释。换言之，LLM 是表达层和解析层，而不是事实裁判或效用函数本身。

## 5. Experiments & Results

### 5.1 Iceberg Sandbox Benchmark

为了评估系统是否能发现隐藏底线，我们构建了 Robust Iceberg Benchmark。每个 Iceberg Profile 包含用户显式输入、隐藏底线和 ground truth 权重。例如，`robust_major_extreme` 的显式输入为：

> 我是浙江考生612分，选科物理化学生物，想读计算机相关专业。表面上我想冲985，也说江浙沪都可以看。

该 profile 的真实底线并不是“冲 985”，而是专业匹配不可严重偏离。系统只有通过提问才能发现这一点。

本实验比较三种 Agent 变体：

- EDMIE full：启用 UCB 主动探测与 BT/D-S tracker。
- no-UCB：关闭 UCB 强控，探针选择退化为随机或非目标化问题。
- no-tracker：关闭 posterior 更新，权重保持均匀状态。

此外纳入三类参考基线：

- Random Dirichlet Baseline：随机采样五维权重。
- Initial-query LLM Baseline：只读初始显式输入估计权重。
- V1 Hybrid RAG Baseline：接入 V1 混合检索 + 二阶重排，再从最终候选反推隐含权重。

主指标包括 MAE、交互轮次和偏好维度 F1。MAE 衡量最终权重与 ground truth 权重的平均绝对误差；轮次衡量收敛效率；F1 衡量系统是否识别出真实底线维度集合。

### 5.2 Quantitative Analysis

图 1 展示交互效率，图 2 展示偏好对齐 MAE，图 3 展示隐性维度识别 F1。

![Efficiency](app/evaluation/results/fig_efficiency_turns.pdf)

![Alignment](app/evaluation/results/fig_alignment_mae.pdf)

![Dimension F1](app/evaluation/results/fig_dimension_f1.pdf)

表 1 汇总主实验结果。

| Model Variant | n | Turns Mean | Turns Std | MAE Mean | MAE Std | F1 Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| EDMIE (Ours) | 36 | 2.000000 | 0.000000 | 0.131290 | 0.017403 | 0.833333 |
| w/o UCB Active Probing | 36 | 2.916667 | 0.280306 | 0.213054 | 0.042083 | 0.333333 |
| w/o BT-Gradient Tracker | 36 | 3.000000 | 0.000000 | 0.203000 | 0.068268 | 0.333333 |

EDMIE 的平均交互轮次为 `2.000000`，no-UCB 为 `2.916667`。相对 no-UCB，EDMIE 平均少用 `0.916667` 轮，降低约 `31.4%`。Welch 独立样本 t 检验给出：

$$
p_{\text{turns}}=1.81537 \times 10^{-20}.
$$

该结果说明 UCB 主动探测显著提升了提问效率。no-UCB 不是不能提问，而是不知道问什么。它在日志中经常问“愿意接受更高录取风险吗”“愿意先比较整体吸引力吗”等泛化问题，这些问题对隐藏底线没有信息增益，导致系统不断消耗轮次。

在偏好对齐方面，EDMIE 的 MAE 为 `0.131290`，no-tracker 为 `0.203000`。绝对下降为：

$$
0.203000-0.131290=0.071710,
$$

相对下降约：

$$
\frac{0.203000-0.131290}{0.203000}\approx 35.3\%.
$$

Welch t-test 给出：

$$
p_{\text{MAE}}=3.49248 \times 10^{-7}.
$$

这说明 posterior tracker 是偏好对齐的关键来源。若没有 BT/D-S 更新，即使系统问到了正确问题，权重仍停留在初始均匀分布，无法把用户反馈转化为可用于终局排序的数值状态。

偏好维度识别结果更加直接。EDMIE 的 precision、recall、F1 均为 `0.833333`；no-UCB、no-tracker、Initial-query LLM 和 V1 Hybrid RAG 均为 `0.333333`。该结果说明 EDMIE 不仅让权重数值更接近 ground truth，也更准确地识别出用户隐藏底线所在维度。

参考 baseline 的 MAE 如下。

| Reference Baseline | MAE | n |
| --- | ---: | ---: |
| Random Dirichlet Baseline | 0.222274 | 1 |
| Initial-query LLM Baseline | 0.204667 | 12 |
| V1 Hybrid RAG Baseline | 0.206510 | 1 |

Initial-query LLM 的 MAE 为 `0.204667`，接近 no-tracker 的 `0.203000`。这表明仅依赖初始显式输入，即便调用结构化 LLM，也无法恢复隐藏底线。V1 Hybrid RAG Baseline 的 MAE 为 `0.206510`，同样明显弱于 EDMIE。这并不意味着 V1 检索质量低，而是说明一次性混合检索和二阶重排不会自然形成“用户真实偏好权重”的 posterior。它能推荐候选，却不能通过用户反馈更新 belief state。

因此，EDMIE 的增益不是“大模型更聪明”或“检索更多候选”带来的，而是来自完整闭环：UCB 选择高不确定性维度，帕累托提问产生可解释反馈，BT/D-S tracker 将反馈写入权重和方差，radar 再基于新 state 规划下一轮。

### 5.3 Qualitative Case Study: robust_major_extreme

定量结果说明 EDMIE 有显著优势，但真正揭示系统差异的是逐轮日志。我们以 `robust_major_extreme` 为例。该用户显式声称想冲 985，也说江浙沪都可以看；但隐藏底线是“专业不能偏太远”。三个系统变体在同一 profile 上表现出截然不同的行为。

#### no-UCB: 泛化无效提问

no-UCB 组第一轮选择 `major_quality_relax`，但没有围绕用户真实底线发起具体权衡，而是问：

> 我先随机看一个证据丰富度方向：你愿意接受这个方案的不确定性吗？

模拟用户回复：

> 这个问题没问到我的真正底线，我先保留。

第二轮 no-UCB 又切到 `risk_band_relax`，问：

> 我先随机看一个组合编排方向：你愿意接受更高录取风险吗？

用户仍然回复：

> 这个问题没问到我的真正底线，我先保留。

第三轮 no-UCB 继续问：

> 我先随机看一个相邻范围方向：你愿意考虑不完全相同的选择范围吗？

用户再次回复：

> 这个问题没问到我的真正底线，我先保留。

这三轮对话清楚展示了 no-UCB 的问题：它不是没有交互，而是交互没有方向。问题缺少候选差异、缺少明确代价维度、缺少真实收益比较，因此用户只能给出保留态度。最终 no-UCB 的 inferred weights 仍为：

$$
[0.2,0.2,0.2,0.2,0.2].
$$

这解释了为什么 no-UCB 的平均轮次达到 `2.916667`，且 F1 只有 `0.333333`。

#### no-tracker: 无 posterior 记忆的复读循环

no-tracker 组第一轮虽然命中了 `major` 维度，提出的问题是：

> 在 西北农林科技大学 和 江苏农牧科技职业学院 之间，方案B主要要求你放宽 专业匹配(major)：从「植物保护，放宽层级=5」放宽到「计算机应用技术」；但当前候选没有带来明确的 学校层次(school) 正向提升。你是否仍愿意放宽这条底线？

用户明确拒绝：

> 专业不能偏太远，这个我不接受。

如果系统具备 tracker，这一反馈应当显著提高 `major` 权重，并降低 major 方差。但 no-tracker 被设计为冻结 posterior，因此第二轮仍然围绕同一底线做确认：

> 上一轮你已经回应过一次。第 2 轮我换成底线确认：当前没有明确的正向收益跃迁，我只确认底线：专业匹配(major) 当前为「植物保护，放宽层级=5」。你是否仍然不愿放宽 专业匹配(major) 来换取 学校层次(school) 跃迁？

用户再次回复：

> 专业不能偏太远，这个我不接受。

第三轮仍然继续：

> 上一轮你已经回应过一次。第 3 轮我换成底线确认：当前没有明确的正向收益跃迁，我只确认底线：专业匹配(major) 当前为「植物保护，放宽层级=5」。你是否仍然不愿放宽 专业匹配(major) 来换取 学校层次(school) 跃迁？

用户第三次回复：

> 专业不能偏太远，这个我不接受。

no-tracker 的问题不是“问不到”，而是“记不住”。它已经获得强证据，却无法把证据写入 belief state。三轮之后 inferred weights 仍为：

$$
[0.2,0.2,0.2,0.2,0.2].
$$

这正是无后验更新系统的 Amnesia Repetition Loop：每一轮都像第一次听到用户反馈，无法将拒绝转化为稳定偏好。

#### EDMIE full: 一击命中与快速收网

EDMIE full 模式第一轮同样选择 `major_geo_relax`，但它的选择不是随机的，而是由 UCB 确定当前最高不确定性目标维度为 `major`。它提出：

> 在 西北农林科技大学 和 江苏农牧科技职业学院 之间，方案B主要要求你放宽 专业匹配(major)：从「植物保护，放宽层级=5」放宽到「计算机应用技术」；但当前候选没有带来明确的 学校层次(school) 正向提升。你是否仍愿意放宽这条底线？

这个问题虽然没有发现正向学校跃迁，但它清楚地把代价维度放在“专业匹配”上，并把具体放宽路径说清楚：从“植物保护，放宽层级=5”到“计算机应用技术”。用户直接暴露底线：

> 专业不能偏太远，这个我不接受。

经过 tracker 更新后，第二轮前 inferred weights 已经变为：

$$
\mathbf{w}_1 =
[0.1580,0.3680,0.1580,0.1580,0.1580],
$$

其中 major 权重明显上升。第二轮系统不再泛化探索，而是确认底线：

> 上一轮你已经回应过一次。第 2 轮我换成底线确认：当前没有明确的正向收益跃迁，我只确认底线：专业匹配(major) 当前为「植物保护，放宽层级=5」。你是否仍然不愿放宽 专业匹配(major) 来换取 学校层次(school) 跃迁？

用户再次拒绝：

> 专业不能偏太远，这个我不接受。

终局时 major 权重进一步升至：

$$
\mathbf{w}_{\text{final}} =
[0.1331,0.4674,0.1331,0.1331,0.1331].
$$

这里的 `0.4674289304072983` 与 profile 的真实底线一致，说明 EDMIE 将拒绝反馈成功转化为 posterior。相比 no-UCB 的三轮保留和 no-tracker 的三轮复读，full 模式在两轮内完成底线识别和收网。

### 5.4 Log-level Diagnostics

日志质量分析进一步支持上述观察。最终 robust 跑批中，full 模式共有 72 条 interrupt 记录，重复问题率为 `0.0`，cost=benefit 率为 `0.0`，同候选对率为 `0.0`，目标维度命中率达到 `0.875`，模糊回复率为 `0.083333`。相比之下，no-UCB 的目标维度命中率为 `0.0`，模拟器模糊回复率为 `1.0`。这意味着 no-UCB 的问题几乎从未触及真实底线，用户自然只能保留意见。

这些日志也揭示了系统当前设计的保守性。当候选池没有真实正向收益跃迁时，EDMIE 不再强行说“牺牲 X 换取 Y”，而是明确写出“当前候选没有带来明确的正向提升”。这使定性问题更诚实，也与本文的 evidence-driven 原则一致：LLM 不能为了提问戏剧性而编造候选收益。

## 6. Discussion

### 6.1 Why Initial-query LLM Is Not Enough

Initial-query LLM baseline 的 MAE 为 `0.204667`，与 no-tracker 的 `0.203000` 接近。这说明，单靠显式输入的语义理解无法穿透防御性伪装。用户说“想冲 985”可能是真的，也可能只是社会标签压力；用户说“学费别太夸张”可能是轻微偏好，也可能是一票否决底线。没有对比方案和后续反馈，LLM 无法可靠区分这些情况。

EDMIE 的优势在于把初始输入降级为假设，而不是结论。它不要求用户一开始就知道自己真实权重，而是在候选对压力下让用户作出具体选择。选择比陈述更接近真实偏好。

### 6.2 Why V1 Hybrid RAG Cannot Replace Posterior Tracking

V1 Hybrid RAG Baseline 的 MAE 为 `0.206510`，F1 为 `0.333333`。这并不否定混合检索和二阶重排的价值；它们可以改善候选召回和排序质量。但 V1 的输出是推荐候选，不是用户偏好 posterior。我们通过候选反推权重只能得到“推荐结果隐含的偏好画像”，而不是“用户真实底线画像”。如果没有多轮交互反馈，系统仍然无法知道用户会拒绝哪一种边际替代。

EDMIE 将候选推荐与偏好识别解耦：候选来自 RAG/SQL，偏好来自 HITL posterior。这个分离让系统既能保持事实可靠，又能主动学习用户。

### 6.3 The Role of Non-compensation

非补偿性 SAVF 是 EDMIE 与普通线性重排的另一个关键差异。在高风险决策中，并非所有维度都可被补偿。学费超预算 50%、专业完全不相关、地域触碰家庭底线，这些情况不能简单地用学校层次高分抵消。一票否决项在数学上看似激烈，但在实际志愿填报中符合用户真实决策逻辑。

这也解释了为什么 EDMIE 的问题常围绕“是否愿意放宽底线”。系统不是把用户当作固定效用函数的输入者，而是把用户视为需要被帮助澄清底线的决策主体。

### 6.4 Limitations

本文实验仍有局限。第一，Robust Iceberg Benchmark 虽然覆盖了单维极端、双维冲突、伪装反向和均衡画像，但仍是模拟器环境。真实考生可能有更复杂的家庭博弈、情绪波动和信息不对称。第二，当前候选池在部分 profile 中不能总是形成清晰的正向收益跃迁，导致系统有时退化为底线确认问题。第三，BT 更新使用固定学习率和逆温度参数，未来可以用层级贝叶斯或 Thompson Sampling 学习个体差异。第四，当前 F1 使用 Top-k 维度集合评价，未来可结合阈值校准、排序相关性和推荐结果满意度进行更全面评估。

尽管如此，本实验已经足以支持核心结论：EDMIE 的性能优势来自闭环结构，而不是更大的模型、更长的 prompt 或更复杂的一次性检索。

## 7. Conclusion

本文提出 EDMIE，一个面向高考志愿填报等高风险决策场景的证据驱动混合倡议偏好引出系统。EDMIE 将事实检索、候选排序、主动探测、后验更新和终局解释分离到不同层次：SQL 探针保证事实确定性，非补偿性 SAVF 防止线性补偿陷阱，UCB 强控探针规划提升信息增益，Bradley-Terry 与 D-S 机制将用户反馈转化为可更新的 belief state，LangGraph `interrupt/resume` 则提供了人机协作所需的挂起与唤醒控制流。

在 Robust Iceberg Benchmark 上，EDMIE 相比 no-tracker 将 MAE 从 `0.203000` 降至 `0.131290`，相对下降 `35.3%`，并取得 `p = 3.49248e-07` 的显著性；相比 no-UCB 将平均轮次从 `2.916667` 降至 `2.000000`，下降约 `31.4%`，显著性达到 `p = 1.81537e-20`；隐性底线维度 F1 达到 `0.833333`，明显高于所有消融组和参考基线的 `0.333333`。真实日志进一步显示，no-UCB 会连续提出无目标问题，no-tracker 会重复确认已被拒绝的底线，而 EDMIE 能在第一轮命中关键维度，并在第二轮收敛。

这些发现支持一个更一般的观点：面向高风险决策的 AI 不应只是被动工具，而应成为协作式偏好引出者。真正可靠的智能系统必须知道何时检索事实、何时提出问题、何时更新信念、何时停止探索并给出解释。EDMIE 展示了这一范式在高考志愿填报中的可行实现，也为未来面向医疗、金融、法律和教育规划的混合倡议决策系统提供了可复用的架构模板。

## Appendix A. Reproducibility Artifacts

本文使用的主要实验产物如下：

- `app/evaluation/results/statistical_summary.txt`
- `app/evaluation/results/ablation_results.csv`
- `app/evaluation/results/classification_metrics.csv`
- `app/evaluation/results/reference_baselines.csv`
- `app/evaluation/results/episode_logs.jsonl`
- `app/evaluation/results/case_study.md`
- `app/evaluation/results/fig_efficiency_turns.pdf`
- `app/evaluation/results/fig_alignment_mae.pdf`
- `app/evaluation/results/fig_dimension_f1.pdf`

其中 `episode_logs.jsonl` 包含逐轮问题、模拟器反馈、当前探针、UCB 目标维度、inferred weights 和状态，可用于复核本文定性案例中引用的所有对话原文。
