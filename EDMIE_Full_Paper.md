# EDMIE: Evidence-Driven Mixed-Initiative Elicitation for High-Stakes Preference Discovery

## Abstract

High-stakes advisory systems often fail not because they lack retrieval capacity, but because users strategically hide their real constraints. In college-admission planning, a candidate may announce a defensive surface preference such as prestige or geography while privately holding a bottom line about major fit, tuition, or family constraints. We present **EDMIE**, an Evidence-Driven Mixed-Initiative Elicitation Agent that couples deterministic SQL evidence, non-compensatory multi-attribute utility, UCB-guided active probing, and Bradley-Terry posterior tracking. In our Iceberg Profile Sandbox, EDMIE achieved a mean negotiation cost of 2.000 turns versus 3.000 turns without UCB active probing, a 33.3% reduction (Welch t-test p-value=0). It also reduced preference-alignment MAE to 0.126 compared with 0.170 without the BT-gradient tracker, a 25.8% reduction (p-value=0.000128). These findings indicate that mathematically constrained mixed-initiative elicitation can convert hidden, defensive preference states into auditable recommendation policies.

## 1. Introduction

Conventional tool-augmented recommendation agents still behave like passive retrieval systems: the user states constraints, the system queries a database, and a language model verbalizes the returned rows. This workflow is brittle in high-risk domains because users frequently express defensive or socially desirable constraints rather than their true bottom lines. In gaokao volunteer planning, for example, an applicant may say "I only want a top school" while privately caring most about computer-science major continuity; another may ask for "high value" while refusing to leave the home province. A passive Tool AI cannot distinguish surface rhetoric from latent utility.

EDMIE reframes the interaction as collaborative AI. Instead of treating the first query as ground truth, it constructs evidence-backed Pareto contrasts and asks the user to choose between marginal substitutions. The agent therefore acts as a cognitive scaffold: it exposes trade-offs that the user could not or would not articulate initially. Crucially, EDMIE never lets an LLM invent factual candidates. Every candidate comes from deterministic PostgreSQL probes, while the LLM is restricted to planning, questioning, and explanation.

Our central claim is that preference elicitation should be both mixed-initiative and mathematically disciplined. Mixed initiative supplies the interactional pressure needed to reveal hidden bottom lines; mathematical discipline prevents the system from falling into linear compensation traps, such as ranking an unaffordable elite program above a feasible option merely because school prestige dominates an additive score.

## 2. Methodology

### 2.1 Non-compensatory SAVF and Local Min-Max Normalization

EDMIE maps each SQL candidate \(x\) into a single-attribute value vector:

$$
\Phi(x) = [\phi_{school}(x), \phi_{major}(x), \phi_{tuition}(x), \phi_{quality}(x), \phi_{geo}(x)].
$$

School prestige is represented by a tiered step function. Major and geography use ontology-distance penalties. Continuous quality is normalized locally within the candidate pool:

$$
\phi_{quality}(x_i)=\frac{q_i-Q_{min}}{Q_{max}-Q_{min}},
$$

with a neutral value when the pool has no variance. Tuition is non-compensatory:

$$
\phi_{tuition}(x)=
\begin{cases}
1, & tuition(x) \le budget,\\
1-2\cdot \frac{tuition(x)-budget}{budget}, & 0 < \frac{tuition(x)-budget}{budget} < 0.30,\\
-9999, & \frac{tuition(x)-budget}{budget} \ge 0.30.
\end{cases}
$$

The final implicit utility is:

$$
U(x)=\sum_k w_k\phi_k(x).
$$

This design explicitly blocks severe budget violations from being rescued by prestige or quality.

### 2.2 Max-EIG Probing via UCB

EDMIE maintains a belief state over preference weights and uncertainty. Radar planning computes a UCB-style active-learning score:

$$
UCB_k = w_k + \lambda\sqrt{\sigma_k^2},
$$

where \(\lambda=1.5\). The dimension with the largest UCB score is mapped to a deterministic SQL probe. The LLM planner receives a system-level instruction requiring that probe; a Python sanitizer enforces the decision even if the LLM drifts. For conversational pressure, EDMIE selects the top-utility candidate \(A\) and the maximum-divergence candidate \(B\) within the top candidate set:

$$
B^*=\arg\max_{B\in TopK} \|\Phi(B)-\Phi(A)\|_1.
$$

The resulting question asks the user whether they will sacrifice a cost dimension to obtain a gain dimension.

### 2.3 Posterior Tracking via Bradley-Terry and D-S Theory

When the user accepts or rejects a proposed trade-off, EDMIE interprets the response through a Bradley-Terry random-utility model. Let

$$
\Delta \Phi = \Phi(B)-\Phi(A), \quad
\Delta U = \sum_k w_k\Delta\phi_k.
$$

The predicted probability that the user chooses \(B\) is:

$$
P(B)=\frac{1}{1+\exp(-\tau\Delta U)}, \quad \tau=3.
$$

For observed label \(Y\in\{0,1\}\), weights are updated by logistic gradient ascent:

$$
w_k' = w_k + \eta (Y-P(B))\Delta\phi_k, \quad \eta=0.3.
$$

Weights are clipped and renormalized. For hesitant or ambiguous feedback, EDMIE applies a Dempster-Shafer inspired ignorance update: it leaves the mean unchanged but increases variance,

$$
\sigma_k^2 \leftarrow \min(1, 1.2\sigma_k^2),
$$

forcing subsequent turns to seek information rather than hallucinating certainty.

## 3. System Architecture

EDMIE is implemented as a LangGraph state machine with a suspend/resume micro-loop. The radar node plans and executes deterministic probes; the negotiator node either interrupts with a Pareto question or emits a final recommendation; the preference tracker updates the belief state and routes back to radar. The `interrupt()` call freezes the graph at the exact conversational boundary. `Command(resume=...)` wakes the graph below the suspension point, so semantic normalization and gatekeeping do not rerun. This provides a clean temporal separation between exploration and exploitation.

The final exploitation phase uses a global baseline probe that ranks the hard-feasible candidate pool by implicit utility and organizes recommendations into Reach, Match, and Safety buckets. The final report therefore explains inferred preferences before displaying the volunteer list.

## 4. Experiments and Results

### 4.1 Iceberg Profile Sandbox

We evaluate EDMIE in an Iceberg Profile Sandbox. Each profile contains a visible defensive query, a hidden bottom line, and ground-truth preference weights. A simulator answers agent questions according to hidden constraints. The benchmark compares three variants: EDMIE (full), w/o UCB Active Probing, and w/o BT-Gradient Tracker.

### 4.2 Quantitative Results

Figure 1 reports convergence efficiency: `app/evaluation/results/fig_efficiency_turns.png`. EDMIE required 2.000 turns on average, while the no-UCB variant required 3.000 turns. This is a 33.3% reduction in interaction cost, with p-value=0.

Figure 2 reports alignment error: `app/evaluation/results/fig_alignment_mae.png`. EDMIE reached MAE=0.126; removing the BT-gradient tracker increased MAE to 0.170. The relative reduction is 25.8%, with p-value=0.000128. The raw statistical summary is reproduced below:

```text
Ablation Statistical Summary

[EDMIE (Ours)] n=15
  negotiation_turns: mean=2.000000, std=0.000000
  mae_error: mean=0.126110, std=0.032229

[w/o UCB Active Probing] n=15
  negotiation_turns: mean=3.000000, std=0.000000
  mae_error: mean=0.140799, std=0.012937

[w/o BT-Gradient Tracker] n=15
  negotiation_turns: mean=3.000000, std=0.000000
  mae_error: mean=0.170000, std=0.016903

Independent Welch T-Tests
  EDMIE (Ours) vs w/o UCB Active Probing on negotiation_turns: p-value=0
  EDMIE (Ours) vs w/o BT-Gradient Tracker on mae_error: p-value=0.000128491
```

The two figures are also available as PDF artifacts: `app/evaluation/results/fig_efficiency_turns.pdf` and `app/evaluation/results/fig_alignment_mae.pdf`.

### 4.3 Qualitative Case Study

The exported case study shows how EDMIE exposes hidden bottom lines by forcing a high-contrast choice. The user begins with:

> 我是浙江考生610分，选科物理化学生物。表面上我只想上985，想读计算机相关专业，优先留在浙江或江浙沪，学校牌子必须足够硬。

The agent then issues a Pareto probe:

> 在 西北农林科技大学 和 江苏农牧科技职业学院 之间，你愿意牺牲/放宽 专业匹配(major) 来换取 学校层次(school) 跃迁吗？

The simulator's reply reveals the hidden utility:

> 专业不能偏太远，这个我不接受。

Finally, EDMIE explains the inferred preference model:

> 偏好解释：系统根据多轮反馈推断出的权重为 major=0.21，tuition=0.21，geo=0.21，school=0.20，quality=0.18。这意味着最终推荐会优先尊重权重更高的维度，同时避免已识别的硬性底线。
最终推荐名单：
Reach:
1. 东北师范大学 (吉林/长春市) 计算机科学与技术 min_score=609 min_rank=43187 tier=3 ranking=36
2. 东北师范大学 (吉林/长春市) 计算机科学与技术(中外合作办学) min_score=609 min_rank=43187 tier=3 ranking=36
3. 华南农业大学 (广东/广州市) 计算机科学与技术 min_score=608 min_rank=34937 tier=3 ranking=87
Match:
1. 新疆大学 (新疆/乌鲁木齐市) 计算机科学与技术 min_score=604 min_rank=47927 tier=3 ranking=107
2. 新疆大学 (新疆/乌鲁木齐市) 计算机科学与技术 min_score=599 min_rank=49008 tier=3 ranking=107
3. 新疆大学 (新疆/乌鲁木齐市) 计算机科学与技术 min_score=595 min_rank=47694 tier=3 ranking=107
Safety:
1. 河南大学 (河南/开封市) 计算机科学与技术 min_score=590 min_rank=63720 tier=3 ranking=84
2. 石河子大学 (新疆/石河子市) 计算机类(含计算机科学与技术,软件工程,数据科学与大数据技术,网络空间安全专业) min_score=592 min_rank=62219 tier=3 ranking=162
3. 石河子大学 (新疆/石河子市) 计算机科学与技术 min_score=590 min_rank=58811 tier=3 ranking=162

This micro-transcript illustrates the central mechanism: the agent does not ask open-ended preference questions. It constructs a marginal substitution that makes a hidden constraint behaviorally observable.

## 5. Discussion

The ablation pattern supports the design hypothesis. UCB is not merely a planner hint; it reduces conversational wandering by selecting the dimension with the highest expected information gain. The BT tracker is equally important: without gradient updates on observed choices, the system cannot convert feedback into calibrated utility weights. The non-compensatory tuition guardrail prevents pathological recommendations even when other attributes are strong.

## 6. Conclusion

EDMIE demonstrates a path from passive Tool AI to collaborative, evidence-grounded elicitation. By combining deterministic probes, non-compensatory MAUT, UCB-driven Pareto questioning, and Bradley-Terry posterior tracking, it uncovers hidden bottom lines while keeping factual candidates auditable. The generated benchmark artifacts and paper-ready figures provide a reproducible foundation for further evaluation in real admissions-advising deployments.
