# EDMIE Robust Iceberg Benchmark 最终实验说明

本文档整理当前最终版实验的设计、方法、指标、结果与日志产物位置。当前结果来自 `robust` Iceberg Profile 数据集，在无 synthetic fallback 的条件下运行真实业务链路，并额外纳入随机权重、Initial-query LLM 与 V1 Hybrid RAG 候选反推基线。

## 1. 实验目标

EDMIE 的核心实验目标不是单纯检验推荐列表是否好看，而是检验系统能否在用户存在“防御性显式约束”和“隐藏真实底线”的情况下，通过混合倡议提问主动挖掘隐性偏好，并将其转化为可解释的权重 posterior。

因此实验回答三个问题：

1. **对齐精度**：最终推断出的五维偏好权重是否接近画像的 ground truth 权重。
2. **交互效率**：系统是否能用更少轮次完成偏好收敛。
3. **底线识别能力**：系统是否识别出了用户真正关心的隐性偏好维度集合。

## 2. 数据集设计

### 2.1 Iceberg Profile

每个 Iceberg Profile 包含四部分：

- `explicit_query`：用户对外显式说辞，例如只想去某地区、追求名校、预算模糊等。
- `hidden_bottom_line`：用户真实底线，例如专业不可偏离、绝不出省、学费一票否决等。
- `ground_truth_weights`：上帝视角下的五维真实偏好分布。
- `profile_id`：画像标识，用于日志和跑批追踪。

五个偏好维度为：

- `school`：学校层次
- `major`：专业匹配
- `tuition`：学费预算
- `quality`：培养质量
- `geo`：地域偏好

### 2.2 Robust 数据集

最终主实验使用 `robust` 数据集，而不是早期的 3 条 smoke 数据。该数据集覆盖以下类型：

- 单维极端底线：如 `major=0.85`、`geo=0.85`、`tuition=0.85`、`school=0.80`。
- 双维冲突底线：如 `major + tuition`、`school + geo`、`quality + major`、`geo + tuition`。
- 伪装反向画像：显式强调某维，但真实权重中该维较低。
- 近均衡画像：多维权重接近，用于验证系统不会过拟合单一极端维度。
- 低权重诱饵画像：显式强调的维度在 ground truth 中并不重要。

本次最终结果共包含：

- `ablation_results.csv`：108 行
- `classification_metrics.csv`：132 行
- `reference_baselines.csv`：38 行
- `episode_logs.jsonl`：393 行逐轮交互日志

## 3. 系统变体与参考基线

### 3.1 Agent 消融变体

| 变体 | 含义 |
| --- | --- |
| `full` / EDMIE (Ours) | 完整系统，启用 UCB 主动探针规划、帕累托提问、Bradley-Terry 梯度更新与 D-S 犹豫处理。 |
| `no_ucb` | 关闭 UCB 主动探测，探针选择退化为随机/非强控规划。 |
| `no_tracker` | 关闭 Bradley-Terry 与 D-S posterior 更新，权重与方差保持初始状态。 |

### 3.2 参考基线

| 基线 | 含义 |
| --- | --- |
| Random Dirichlet Baseline | 在五维概率单纯形上采样随机权重，估计随机猜测的 MAE 期望。 |
| Initial-query LLM Baseline | 只读取用户初始显式输入，用结构化 LLM 估计初始权重，不使用后续交互。 |
| V1 Hybrid RAG Baseline | 接入 V1 混合检索 + 二阶重排系统，再从最终候选反推隐含偏好权重。 |

参考基线只参与 MAE 和偏好维度识别，不参与交互轮次比较，因为它们不是 HITL 交互式系统。

## 4. 实验方法

### 4.1 运行命令

最终主实验采用如下流程：

```powershell
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.benchmark --require-real --dataset robust --repeats 3 --turn-timeout 180 --max-turns 4
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.reference_baselines --dataset robust --samples 50000 --require-real --include-v1-hybrid --v1-timeout 180
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.log_analyzer
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.plotter
```

说明：

- 使用 `--require-real`，因此不允许 synthetic fallback 混入主结果。
- PowerShell 输出可能因控制台编码显示中文乱码；实验文件本身按 UTF-8 写入。
- `episode_logs.jsonl` 持久化每一轮 Agent 提问、Simulator 回复、当前探针、目标维度、权重和状态，便于复盘中间过程。

### 4.2 MAE 指标

MAE 衡量系统推断权重和 ground truth 权重之间的平均绝对误差：

$$
\mathrm{MAE}(\hat{w}, w^*) =
\frac{1}{|\mathcal{D}|}
\sum_{k \in \mathcal{D}}
|\hat{w}_k - w^*_k|
$$

其中 $\mathcal{D}=\{\text{school}, \text{major}, \text{tuition}, \text{quality}, \text{geo}\}$。权重已经统一归一化到概率单纯形，保证 EDMIE、no-tracker、随机基线和 Initial-query LLM 在同一口径下比较。

### 4.3 偏好维度 Precision / Recall / F1

真实标签集合：

$$
G = \{k \mid w^*_k \ge 0.35\}
$$

若不存在权重超过阈值的维度，则回退取 ground truth Top-1。

预测集合从最终 inferred weights 中取 Top-k，且 $k=|G|$：

$$
P = \mathrm{TopK}(\hat{w}, |G|)
$$

Precision、Recall、F1 定义为：

$$
\mathrm{Precision} = \frac{|P \cap G|}{|P|}, \quad
\mathrm{Recall} = \frac{|P \cap G|}{|G|}, \quad
F1 = \frac{2PR}{P+R}
$$

该指标衡量系统是否抓住了用户真实底线所在维度，而不是只看数值误差。

### 4.4 日志质量指标

`log_analyzer` 对逐轮日志计算以下质量指标：

- `repeated_question_rate`：重复问题比例。
- `cost_equals_benefit_rate`：是否出现“牺牲 X 换取 X”的无效问法。
- `same_candidate_pair_rate`：是否出现 A/B 方案本质相同的问题。
- `target_dimension_hit_rate`：提问是否命中该 profile 的真实目标维度。
- `simulator_ambiguous_reply_rate`：Simulator 是否产生模糊/犹豫反馈。

## 5. 实验结果

### 5.1 Agent 变体主结果

| 变体 | n | 平均轮次 | 轮次标准差 | MAE 均值 | MAE 标准差 | F1 均值 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| EDMIE (Ours) | 36 | 2.000000 | 0.000000 | 0.131290 | 0.017403 | 0.833333 |
| w/o UCB Active Probing | 36 | 2.916667 | 0.280306 | 0.213054 | 0.042083 | 0.333333 |
| w/o BT-Gradient Tracker | 36 | 3.000000 | 0.000000 | 0.203000 | 0.068268 | 0.333333 |

相对 `no_ucb`，EDMIE 平均减少 `0.916667` 轮交互，约降低 `31.4%`。Welch t-test 显示交互轮次差异显著：

$$
p = 1.81537 \times 10^{-20}
$$

相对 `no_tracker`，EDMIE 的 MAE 从 `0.203000` 降至 `0.131290`，绝对下降 `0.071710`，相对下降约 `35.3%`。Welch t-test 显示对齐误差差异显著：

$$
p = 3.49248 \times 10^{-7}
$$

偏好维度 F1 从两个消融组的 `0.333333` 提升到 `0.833333`，说明完整系统不只是让权重数值更近，也更稳定地识别出了用户隐藏底线所在维度。

### 5.2 参考基线结果

| 参考基线 | MAE | n |
| --- | ---: | ---: |
| Random Dirichlet Baseline | 0.222274 | 1 |
| Initial-query LLM Baseline | 0.204667 | 12 |
| V1 Hybrid RAG Baseline | 0.206510 | 1 |

参考基线说明：

- 随机 Dirichlet baseline 的 MAE 约为 `0.222274`，是完全随机猜测在该 robust 数据集上的误差参考。
- Initial-query LLM 的 MAE 为 `0.204667`，说明只读显式 query 无法充分恢复隐藏底线。
- V1 Hybrid RAG candidate proxy 的 MAE 为 `0.206510`，接近 Initial-query LLM，说明一次性检索重排系统即使候选质量不错，也不会自然形成稳定的隐性偏好 posterior。

### 5.3 偏好维度分类结果

| 模型或基线 | n | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| EDMIE (Ours) | 36 | 0.833333 | 0.833333 | 0.833333 |
| w/o UCB Active Probing | 36 | 0.333333 | 0.333333 | 0.333333 |
| w/o BT-Gradient Tracker | 36 | 0.333333 | 0.333333 | 0.333333 |
| Initial-query LLM Baseline | 12 | 0.333333 | 0.333333 | 0.333333 |
| V1 Hybrid RAG Baseline | 12 | 0.333333 | 0.333333 | 0.333333 |

该结果说明：EDMIE 的增益并非来自“初始输入里已经写明了偏好”，而是来自中间多轮帕累托提问和 posterior 更新。

### 5.4 中间日志质量

| 模式 | interrupt 数 | 重复问题率 | cost=benefit 率 | 同候选对率 | 目标维度命中率 | 模糊回复率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| full | 72 | 0.000000 | 0.000000 | 0.000000 | 0.875000 | 0.083333 |
| no_tracker | 108 | 0.000000 | 0.000000 | 0.000000 | 0.861111 | 0.083333 |
| no_ucb | 105 | 0.133333 | 0.000000 | 0.000000 | 0.000000 | 1.000000 |

日志分析显示，最终版提问已经规避了“牺牲同一维度换取同一维度”的无效句式，`cost_equals_benefit_rate=0`。完整模式下 `target_dimension_hit_rate=0.875`，而 no-UCB 下为 `0`，说明 UCB 强控确实把提问对准了需要被探索的隐性底线维度。

## 6. 图表与文件产物

核心实验产物均位于：

```text
app/evaluation/results/
```

主要文件：

- `ablation_results.csv`：主消融 MAE 与轮次结果。
- `classification_metrics.csv`：偏好维度 Precision / Recall / F1。
- `reference_baselines.csv`：随机、Initial-query LLM、V1 Hybrid RAG 参考基线。
- `episode_logs.jsonl`：最后一次 robust 跑批的逐轮交互日志。
- `episode_log_analysis.md`：逐轮日志质量分析报告。
- `case_study.md`：从真实 episode log 导出的案例剧本。
- `statistical_summary.txt`：均值、标准差、p-value 与参考 baseline 汇总。
- `fig_efficiency_turns.png` / `fig_efficiency_turns.pdf`：交互轮次图。
- `fig_alignment_mae.png` / `fig_alignment_mae.pdf`：MAE 对齐误差图。
- `fig_dimension_f1.png` / `fig_dimension_f1.pdf`：偏好维度 F1 图。

## 7. Case Study 摘要

当前 `case_study.md` 已优先从真实 `episode_logs.jsonl` 导出，而不是 fallback 模板。一个典型案例中，用户显式说法是：

> 我是浙江考生626分，物理化学生物，想读计算机类，预算最多8000元，优先看名校，地域可以商量。

Agent 的帕累托追问聚焦学费底线，同时避免把不存在的收益包装成补偿：

> 本轮候选不足以形成取舍。以 西北农林科技大学 为参照，目前只看到 学费预算(tuition) 边界在「学费=60000」，但没有可验证收益维度可供换取；我不建议你牺牲/放宽 学费预算(tuition) 去换取不存在的收益，这属于低信息量探测。你是否先保留 学费预算(tuition)，让我下一轮改看其他候选？

Simulator 回复：

> 预算不能超，学费太贵绝对不行。

这一轮交互暴露了用户“学费预算”维度的真实底线，使 tracker 能将 posterior 往 tuition 维度收敛。该案例体现了 EDMIE 的核心机制：不是被动解释候选，也不是伪造收益制造戏剧性，而是在事实候选不足时如实标注低信息量探测，并用用户反馈更新隐藏约束。

## 8. 结论

最终 robust 实验支持以下结论：

1. EDMIE 在权重对齐上显著优于 no-tracker，MAE 从 `0.203000` 降至 `0.131290`，且差异显著。
2. EDMIE 在交互效率上显著优于 no-UCB，平均轮次从 `2.916667` 降至 `2.000000`。
3. EDMIE 在隐性偏好维度识别上显著优于消融组与参考基线，F1 达到 `0.833333`。
4. 中间日志证明最终提问质量已经修正：无 cost=benefit 问题、无同候选对问题，完整模式下目标维度命中率达到 `87.5%`。

因此，当前实验版本已经能支撑论文中的核心论点：EDMIE 的收益来自 UCB 主动探测、帕累托差分提问与 Bradley-Terry posterior 更新的组合，而不是来自初始输入猜测或一次性 RAG 检索。

## 9. 最后一次跑批日志位置

最后一次真实 robust 跑批的逐轮日志文件为：

```text
d:\gaokaollm-v2\app\evaluation\results\episode_logs.jsonl
```

对应的自动分析报告为：

```text
d:\gaokaollm-v2\app\evaluation\results\episode_log_analysis.md
```

若需要复盘某一轮具体交互，优先读取 `episode_logs.jsonl`；若只想看汇总指标，读取 `episode_log_analysis.md`。
