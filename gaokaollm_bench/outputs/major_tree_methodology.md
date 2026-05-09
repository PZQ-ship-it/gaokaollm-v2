# 高考专业聚类树构建方法学记录

## 摘要

本文记录 `gaokaollm_bench/outputs/major_tree_final_reviewed.json` 的构建过程、质量控制策略以及面向 `gaokaollm-bench` 的方法学意义。该专业聚类树服务于三类核心任务：专业约束解析、层级放宽推荐、以及反事实志愿集合生成。

与纯人工规则或黑箱向量聚类不同，本项目采用“人工可审计本体 + 真实数据库专业名扫描 + probe 辅助候选生成 + LLM 低置信审校 + 最终审计合成”的混合流程。其目标不是构造唯一正确的学科分类学，而是构造一棵可用于高考志愿决策评测的工程化语义树：既覆盖真实招生文本中的噪声和变体，又保留可解释的层级边界。

最终树统计如下：

| 指标 | 数值 |
|---|---:|
| 节点数 | 82 |
| Level 0 大类节点 | 8 |
| Level 1 中层节点 | 22 |
| Level 2 叶子簇 | 52 |
| 叶子簇 observed_names 条目 | 19,096 |
| 全节点 observed_names 条目 | 57,287 |

## 研究问题与设计原则

真实招生数据库中的 `admission_scores.major_name_raw` 不是干净的教育部标准专业目录，而是业务系统中的观测文本。它同时包含标准专业、专业大类、校区标注、培养方向、中外合作、实验班、高职专科名称和局部备注噪声。

因此，本项目的目标不是“还原标准专业目录”，而是为志愿决策 Agent 构建一棵可查询、可放宽、可审计的专业语义树。设计原则包括：

- **可审计性**：每个簇由人工定义的 `include_keywords`、`exclude_keywords` 和真实观测名称支撑。
- **覆盖真实文本**：通过扫描全库专业名，将真实招生场景中出现的名称变体纳入树中。
- **保守自动化**：embedding/probe 用于生成候选和辅助审校，不直接替代人工本体。
- **分层放宽可解释**：树必须支持从叶子簇、同父近邻、相邻大类到无专业限制的逐步放宽。
- **候选与标签分离**：候选生成可以激进，监督标签与最终树挂载必须保守。

## 数据来源

原始专业名来自 PostgreSQL 字段：

```text
admission_scores.major_name_raw
```

全库扫描统计：

| 指标 | 数值 |
|---|---:|
| distinct major names | 22,759 |
| admission score rows | 140,995 |

保留这些真实业务文本具有方法学意义：benchmark 面对的不是规范化目录，而是招生计划和录取分数表中的原始文本。因此我们将这些名称视为“观测专业名”，并通过树结构建立它们与可解释专业簇之间的映射。

## 构建流程

### 1. 人工本体骨架

初始树定义位于：

```text
gaokaollm_bench/data_gen/major_clusters.json
```

每个节点包含：

```json
{
  "id": "...",
  "label": "...",
  "parent": "...",
  "level": 2,
  "include_keywords": [],
  "exclude_keywords": [],
  "observed_names": []
}
```

该骨架承担两项功能。第一，它规定语义边界，例如医学执业医师相关类、计算机与软件类、经管类、人文社科类、传统工科类和高职应用技术类。第二，它为后续自动归类提供稳定叶子标签，使模型输出始终回到可解释簇，而不是产生不可审计的新类。

### 2. 基于规则的数据库扫描

规则扫描脚本：

```text
gaokaollm_bench/data_gen/build_major_tree.py
gaokaollm_bench/data_gen/major_tree_builder.py
```

流程为：

1. 聚合 `admission_scores.major_name_raw` 及其出现次数。
2. 对每个真实专业名执行树解析。
3. 优先匹配已有 `observed_names`。
4. 再根据 `include_keywords` / `exclude_keywords` 归入最具体叶子簇。
5. 将命中的专业名写入叶子节点及所有祖先节点的 `observed_names`。
6. 将未命中项输出为待处理候选。

产物：

```text
gaokaollm_bench/sample_data/major_tree_observed_full.json
gaokaollm_bench/sample_data/major_tree_unassigned_full.json
```

规则扫描覆盖情况：

| 指标 | 数值 |
|---|---:|
| assigned distinct names | 18,587 |
| unassigned distinct names | 4,172 |
| assigned rows | 116,687 |
| unassigned rows | 24,308 |

从树统计看，人工骨架的叶子 `observed_names` 为 224 条，规则扫描后叶子 `observed_names` 增至 18,596 条。这一阶段建立了“规则可解释 + 真实文本覆盖”的基础树。

### 3. Probe 辅助候选生成

probe 训练与推理脚本包括：

```text
gaokaollm_bench/data_gen/major_training_set_builder.py
gaokaollm_bench/data_gen/major_embedding_cache.py
gaokaollm_bench/data_gen/major_train_val_split.py
gaokaollm_bench/data_gen/major_probe_train.py
gaokaollm_bench/data_gen/major_probe_predict.py
gaokaollm_bench/data_gen/major_probe_review_candidates.py
```

probe 不微调 embedding 模型，而是在 4096 维文本向量上训练轻量分类头，监督标签为叶子簇 `leaf_id`。该设计有两个优点：

- **低成本**：只需缓存 embedding，CPU 环境即可训练。
- **可替换**：embedding 模型、probe 结构和树标签可分别迭代。

在树构建中，probe 的角色不是直接决定最终树，而是为未归类专业生成 top-k 叶子候选，再交给后续审校流程处理。

### 4. LLM 低置信审校

审校脚本：

```text
gaokaollm_bench/data_gen/major_probe_llm_review.py
```

LLM 只处理 `review_status = low_confidence` 的项目。为了避免概率锚定，传给 LLM 的内容只包含：

```json
{
  "major_name": "...",
  "candidates": [
    {"label": "...", "label_name": "..."}
  ]
}
```

不提供：

```text
recommended_probability
probe prediction probability
row_count
```

该设计让 LLM 作为语义审校者，而不是复述 probe 的置信度排序。审校产物：

```text
gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json
```

审校统计：

| 指标 | 数值 |
|---|---:|
| candidates | 500 |
| pending | 408 |
| llm_reviewed | 64 |
| still low_confidence | 28 |
| missing recommended_label | 0 |

### 5. 最终树合成

最终合成脚本：

```text
gaokaollm_bench/data_gen/major_tree_finalize_from_reviews.py
```

输入：

```text
base tree: gaokaollm_bench/sample_data/major_tree_observed_full.json
reviews:   gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json
```

处理逻辑：

1. 读取规则阶段 observed tree。
2. 遍历 reviewed candidates。
3. 读取当前 `recommended_label`。
4. 将 `major_name` 加入目标叶子节点 `observed_names`。
5. 同步加入所有祖先节点的 `observed_names`。
6. 在叶子节点写入 `probe_review_assigned` 审计字段。
7. 输出最终树和审计文件。

输出：

```text
gaokaollm_bench/outputs/major_tree_final_reviewed.json
gaokaollm_bench/outputs/major_tree_final_reviewed_audit.json
```

最终 reviewed tree 在规则扫描基础上增加了 500 条叶子观测名称，使叶子 `observed_names` 从 18,596 增至 19,096。

## 质量控制

专业树构建中区分两类问题：

1. **方法变量**：例如是否使用 LLM 审校、是否使用 probe 候选、是否过滤复合专业、是否增强低样本类。这些适合进入消融实验。
2. **工程质量问题**：例如候选树被误用为监督标签源、编码归一化不一致、embedding cache 缺失。这些不应作为学术消融因素，而应作为质量控制和复现前提处理。

当前训练集构建默认只从干净的 `major_tree_observed_full.json` 或最终 reviewed tree 生成监督样本，不将中间 auto-assigned tree 作为规则标注源。embedding cache 也默认要求训练和验证侧 `missing=0`，避免把数据完整性问题误当作模型效果差异。

## 消融实验设计

本节只讨论具有方法学意义且仍被保留的 probe 分类因素。工程完整性问题，例如 embedding 缺失、SSL/cache 问题、候选污染，不作为消融项；它们被视为实验前提。验证集文本混入训练集的协议已判定为不符合泛化评估原则；ambiguity-filtered、low-sample augmentation 和 full balanced class weight 在严格协议下没有带来正收益，相关脚本与结果已清理，不纳入论文式结论。

### 实验协议

本轮 probe 分类消融统一使用 DB observed tree 作为监督标签来源，不消融树覆盖策略，不消融 LLM/人工审校策略，也不讨论推荐级 Stage 命中率。为避免同一专业文本泄漏到训练与验证两侧，实验从原始训练集构造 `raw_train_only.jsonl`：剔除固定验证集 `val.jsonl` 中出现过的 canonical normalized text。

| 数据版本 | 原始行数 | 剔除 val overlap 后行数 | 叶子标签数 |
|---|---:|---:|---:|
| raw training set | 1,421 | 784 | 52 |
| validation set | 166 | 166 | 52 |

所有保留消融均满足：

- train missing rows = 0
- validation missing rows = 0
- 固定验证集为 `gaokaollm_bench/outputs/major_training/splits/val.jsonl`
- 每个配置运行 seeds 42、43、44
- selection metric 为 `val_macro_f1`
- early stopping patience 为 15

### 保留因素与结果

完整实验产物位于：

```text
gaokaollm_bench/outputs/major_probe_classification_ablation/
```

聚合结果如下：

| Group | Runs | Macro-F1 Mean | Macro-F1 Std | Accuracy Mean | Accuracy Std | Top-3 Mean | Top-3 Std |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw + MLP + sqrt_balanced | 3 | 0.6862 | 0.0195 | 0.7068 | 0.0057 | 0.8554 | 0.0085 |
| raw + MLP + none | 3 | 0.6795 | 0.0136 | 0.7088 | 0.0057 | 0.8474 | 0.0028 |
| raw + Linear + sqrt_balanced | 3 | 0.6109 | 0.0025 | 0.6888 | 0.0028 | 0.8454 | 0.0057 |
| raw + Linear + none | 3 | 0.5552 | 0.0024 | 0.6566 | 0.0000 | 0.8594 | 0.0057 |

### 贡献解释

1. **非线性分类头带来主要正收益**：在无类别权重时，MLP 相比 Linear 将 Macro-F1 从 0.5552 提升到 0.6795；在 sqrt-balanced 权重下，从 0.6109 提升到 0.6862。说明 4096 维 embedding 上仍存在需要非线性边界表达的专业语义差异。
2. **sqrt-balanced 类别权重带来温和正收益**：Linear 下 Macro-F1 从 0.5552 提升到 0.6109；MLP 下从 0.6795 提升到 0.6862。它更偏向改善小类召回，因此 Macro-F1 更好，但 MLP 下 top-1 accuracy 略低于 none。
3. **推荐配置**：若以 Macro-F1 为主目标，采用 `raw train-only + MLP h256 + sqrt_balanced`；若更看重 top-1 accuracy，保留 `raw train-only + MLP h256 + none` 作为对照。
4. **不叙述负贡献试错**：full-data overlap、filtered、augmented、full balanced class weight 均作为工程试错清理，不作为最终方法贡献。

## 对 benchmark 的意义

专业树不是孤立的数据清洗产物，而是 `gaokaollm-bench` 多轮反事实评测的基础设施。它至少支持三类能力：

1. **专业约束解析**：将考生口语化偏好映射为可查询的专业簇。
2. **层级放宽推荐**：从同叶子变体、同父近邻、相邻大类、无专业限制逐步扩展搜索空间。
3. **反事实 Gap 生成**：在真实 DB 中寻找“坚持原约束 vs 放宽约束”之间的院校层次跃迁。

树质量会直接影响 persona 生成、志愿集合质量、target agent 是否能提出真实可验证的妥协方案，以及 evaluator 能否对推荐进行事实核验。

## Probe 分类消融协议升级

为避免把后续推荐环节和树审校环节混入 probe 结论，本轮消融只讨论专业分类器本身。实验统一采用 DB observed tree 作为监督标签来源，不消融树覆盖策略，不消融 LLM/人工审校策略，也不讨论推荐级 Stage 命中率。

此前试跑过验证集文本混入训练集的 full-data 协议，也试跑过 ambiguity-filtered、augmented 和 full balanced class weight。前者因 `normalized_text` overlap 不符合泛化评估原则，后者在严格协议下没有带来正收益，因此均作为工程试错清理，不进入最终论文式消融结果。

本轮固定前提如下：

1. **树基底固定**：统一使用 DB observed tree 派生的训练数据。
2. **验证集固定**：使用 `gaokaollm_bench/outputs/major_training/splits/val.jsonl`。
3. **无文本泄漏**：训练集使用 train-only 派生版本，剔除验证集中出现过的 `normalized_text`。
4. **完整 embedding 前提**：训练和验证文本在 embedding cache 中必须全部命中，`missing_texts = 0`。
5. **多 seed**：每个配置跑 3 个 seed，报告 `mean ± std`。
6. **选择指标**：以 `val_macro_f1` 选择 checkpoint，同时报告 `accuracy` 和 `top3_accuracy`。
7. **保留变量**：最终只保留 raw train-only 数据上的模型结构与温和类别权重消融。

本协议对应新增工具：

```text
gaokaollm_bench/data_gen/major_eval_protocol.py
gaokaollm_bench/tests/manual/major_ablation_report.py
gaokaollm_bench/tests/manual/major_probe_classification_ablation.py
```

### Probe 分类消融结果

完整实验产物位于：

```text
gaokaollm_bench/outputs/major_probe_classification_ablation/
```

聚合表如下：

| Group | Runs | Macro-F1 Mean | Macro-F1 Std | Accuracy Mean | Accuracy Std | Top-3 Mean |
|---|---:|---:|---:|---:|---:|---:|
| raw + MLP + sqrt_balanced | 3 | 0.6862 | 0.0195 | 0.7068 | 0.0057 | 0.8554 |
| raw + MLP + none | 3 | 0.6795 | 0.0136 | 0.7088 | 0.0057 | 0.8474 |
| raw + Linear + sqrt_balanced | 3 | 0.6109 | 0.0025 | 0.6888 | 0.0028 | 0.8454 |
| raw + Linear + none | 3 | 0.5552 | 0.0024 | 0.6566 | 0.0000 | 0.8594 |

### 当前保留因素的贡献

1. **MLP 是明确正收益**：在无类别权重时，Macro-F1 从 0.5552 提升到 0.6795；在 sqrt-balanced 权重下，从 0.6109 提升到 0.6862。说明 4096 维 embedding 上的非线性分类边界确实有价值。
2. **sqrt-balanced 是温和正收益**：Linear 下从 0.5552 提升到 0.6109，MLP 下从 0.6795 提升到 0.6862。它主要改善 Macro-F1，但 MLP 下 accuracy 略低于 none。
3. **最终推荐分类配置**：若以 Macro-F1 为主目标，采用 `raw train-only + MLP h256 + sqrt_balanced`；若更看重 top-1 accuracy，可保留 `raw train-only + MLP h256 + none` 作为对照。
4. **不纳入论文的试错项**：full-data overlap、filtered、augmented、full balanced class weight 均已清理，不作为最终方法贡献叙述。

### 复杂 Probe 结构试探

在确认 MLP 明显优于 Linear 后，我们进一步测试了更复杂的 probe 分类头，以判断瓶颈是否来自模型容量不足。实验仍然使用 raw train-only、固定验证集、完整 embedding 和 3 seeds，不覆盖默认 probe。

产物位于：

```text
gaokaollm_bench/outputs/major_probe_architecture_trials/
```

双指标覆盖门槛为 `Macro-F1 > 0.6862` 且 `Accuracy >= 0.7088`。结果如下：

| Architecture | Runs | Macro-F1 Mean | Macro-F1 Std | Accuracy Mean | Top-3 Mean | Promotion Candidate |
|---|---:|---:|---:|---:|---:|---|
| baseline_mlp_h256_l1_do0p1_sqrt | 3 | 0.6862 | 0.0239 | 0.7068 | 0.8554 | no |
| deep_mlp_h256_l2_do0p1_sqrt | 3 | 0.6541 | 0.0023 | 0.6908 | 0.8474 | no |
| residual_mlp_h256_b2_do0p1_sqrt | 3 | 0.6420 | 0.0149 | 0.6787 | 0.8133 | no |
| deep_mlp_h384_l2_do0p15_sqrt | 3 | 0.6417 | 0.0091 | 0.6767 | 0.8474 | no |
| residual_mlp_h384_b2_do0p15_sqrt | 3 | 0.6386 | 0.0181 | 0.6787 | 0.8092 | no |
| deep_mlp_h256_l3_do0p15_sqrt | 3 | 0.6018 | 0.0254 | 0.6486 | 0.8052 | no |

结论：在当前样本规模与严格去重协议下，进一步增加 probe 深度或加入残差块没有带来正收益，反而更容易过早拟合训练集并降低验证表现。因此当前瓶颈主要不是分类头容量不足；后续优化应优先转向错误样本诊断、标签边界重审、验证协议扩展和更精确的困难样本修复，而不是继续盲目加深 probe。

### FR-KAN 分类头试探

进一步地，我们测试了 Fourier Kolmogorov-Arnold Network 形式的分类头。该实验将 Transformer 冻结骨干等价为当前已缓存的 4096 维 embedding，仅替换 probe 分类头，不改树、不改训练集、不覆盖默认模型。FR-KAN 使用 Fourier 单变量函数基，网格大小 `G` 记录为 `fourier_grid_size`。

产物位于：

```text
gaokaollm_bench/outputs/major_probe_frkan_trials/
```

实验同时比较两类协议：

1. **fair probe protocol**：沿用当前 probe 训练协议，`lr=0.001`、最多 100 epochs、patience 20，便于与 MLP 公平比较。
2. **paper-suggested protocol**：采用 FR-KAN 建议的 `G=5`、`lr=2e-5`、5 epochs，用于检验该建议在 cached embedding probe 场景下是否可迁移。

结果如下：

| Trial | Protocol | Runs | Grid | LR | Epochs | Macro-F1 Mean | Accuracy Mean | Top-3 Mean | Promotion Candidate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| baseline_mlp_h256_sqrt_fair | fair_probe | 3 | 5 | 0.0010 | 100 | 0.6862 | 0.7068 | 0.8554 | no |
| frkan_g3_fair | fair_probe | 3 | 3 | 0.0010 | 100 | 0.5113 | 0.6024 | 0.7490 | no |
| frkan_g5_fair | fair_probe | 3 | 5 | 0.0010 | 100 | 0.4814 | 0.5723 | 0.7289 | no |
| frkan_g7_fair | fair_probe | 3 | 7 | 0.0010 | 100 | 0.4653 | 0.5462 | 0.7209 | no |
| frkan_g5_paper_lr2e5_e5 | paper_suggested | 3 | 5 | 0.00002 | 5 | 0.4156 | 0.5000 | 0.7048 | no |

结论：在当前 cached embedding + 小样本 leaf 分类协议下，FR-KAN 未优于浅层 MLP，且随着 `G` 从 3 增至 7，验证指标呈下降趋势。论文建议的 `lr=2e-5, epochs=5` 在本场景中明显欠训练。该结果说明 Fourier 单变量函数基并不能直接替代当前浅层 MLP；若未来继续探索 KAN 类结构，应优先考虑输入尺度、频率归一化、低秩参数化或更强正则，而不是直接增大 Fourier grid。

## 进一步提升结果的路线

下一轮仍然先聚焦 probe 分类分数，不进入推荐级评估。优先级如下：

1. **错误样本诊断**：对 `raw + MLP + sqrt_balanced` 输出 per-sample top-k、低 F1 leaf、主要 confusion pairs。
2. **困难样本增强**：后续若重新引入增强，必须围绕高频混淆对补真实 observed names 或人工构造边界样本，并单独验证正收益后再进入主实验。
3. **模型小 sweep**：复杂结构试探未显示正收益后，模型侧仅保留围绕单隐层 MLP 的 h128/h256/h384、dropout 0.05/0.1/0.15、lr 0.0008/0.001 等轻量调参。
4. **KAN 类后续方向**：直接 FR-KAN 不优于 MLP，后续只有在引入输入尺度控制、频率正则或低秩 Fourier 参数化时才值得重开。
5. **类别权重替代**：可尝试介于 none 与 sqrt_balanced 之间的温和权重，或 label smoothing；不再默认使用 full balanced。
6. **验证协议扩展**：当前 fixed val 可以判断方向，但最终仍需 grouped k-fold 复核，避免对 166 条验证集过拟合。

## 局限性与后续工作

当前树和 probe 仍存在若干局限：

- 验证集仅 166 条，单条样本会带来约 0.6% accuracy 波动，后续应采用多 seed 或 k-fold。
- 严格去除文本重叠后，训练样本量明显下降，说明 observed_names 中存在大量规范化重复项；后续需要构建按 normalized text 分组的正式 split。
- 少数极小叶子簇仍不稳定，尤其是部分高职类、软件工程、商务管理等边界类。
- 简单低样本增强未提升严格消融指标，说明后续增强应针对错误样本和混淆对，而不是机械补足样本数。
- LLM 审校只处理低置信样本，尚未对高置信 probe 挂载项做系统抽样审计。
- 最终树的叶子层级固定为 52 类，是否需要合并过细高职类仍需结合推荐任务效果评估。
- embedding 模型版本会影响 probe 表现，生产环境需固定 `EMBEDDING_MODEL` 和向量维度。

后续优先级建议：

1. 构建按 normalized text 分组的正式 train/val/test split。
2. 针对低 F1 叶子簇和高频混淆对做人工补样与边界重审。
3. 对 probe 高置信挂载项抽样人工审计，估计 precision。
4. 在真实 DB 推荐生成中比较不同树版本对 stage 命中率、志愿多样性和专业相关性的影响。
5. 如果任务表现仍受专业边界影响，再考虑引入 embedding 辅助的新簇建议，但不直接自动改写最终树。

## 复现实验命令

构建 observed tree：

```bash
python -m gaokaollm_bench.data_gen.build_major_tree \
  --base-tree gaokaollm_bench/data_gen/major_clusters.json \
  --output gaokaollm_bench/sample_data/major_tree_observed_full.json \
  --unassigned-output gaokaollm_bench/sample_data/major_tree_unassigned_full.json \
  --min-count 1 \
  --top-unassigned 5000
```

从 observed tree 构建训练集：

```bash
python -m gaokaollm_bench.data_gen.major_training_set_builder \
  --tree-path gaokaollm_bench/sample_data/major_tree_observed_full.json \
  --output gaokaollm_bench/outputs/major_training/data.jsonl \
  --dedupe-on normalized_text
```

运行当前保留的 probe 分类配置示例：

```bash
python -m gaokaollm_bench.data_gen.major_probe_train \
  --input-jsonl gaokaollm_bench/outputs/major_probe_classification_ablation/data/raw_train_only.jsonl \
  --val-jsonl gaokaollm_bench/outputs/major_training/splits/val.jsonl \
  --embeddings gaokaollm_bench/outputs/major_training/embeddings_union_val_filled.npz \
  --output-dir gaokaollm_bench/outputs/major_probe_classification_ablation/manual_mlp_sqrt_balanced \
  --label-field leaf_id \
  --batch-size 64 \
  --epochs 80 \
  --lr 0.001 \
  --weight-decay 0.0001 \
  --model-kind mlp \
  --hidden-dim 256 \
  --dropout 0.1 \
  --class-weight sqrt_balanced \
  --selection-metric val_macro_f1 \
  --early-stopping-patience 15 \
  --seed 42
```

合成最终 reviewed tree：

```bash
python -m gaokaollm_bench.data_gen.major_tree_finalize_from_reviews \
  --base-tree gaokaollm_bench/sample_data/major_tree_observed_full.json \
  --reviews gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json \
  --output gaokaollm_bench/outputs/major_tree_final_reviewed.json \
  --audit-output gaokaollm_bench/outputs/major_tree_final_reviewed_audit.json
```

运行本次严格去重消融实验时，先构造 train-only 派生集，再调用 `major_probe_train.py`。实验产物位于：

```text
gaokaollm_bench/outputs/major_probe_classification_ablation/
```

生成正式 grouped split：

```bash
python -m gaokaollm_bench.data_gen.major_eval_protocol grouped-split \
  --input gaokaollm_bench/outputs/major_training/data.jsonl \
  --output-dir gaokaollm_bench/outputs/major_training_grouped/split_seed42 \
  --val-ratio 0.2 \
  --seed 42
```

生成 grouped k-fold：

```bash
python -m gaokaollm_bench.data_gen.major_eval_protocol grouped-kfold \
  --input gaokaollm_bench/outputs/major_training/data.jsonl \
  --output-dir gaokaollm_bench/outputs/major_training_grouped/kfold_seed42 \
  --folds 5 \
  --seed 42
```

检查 embedding 完整性：

```bash
python -m gaokaollm_bench.data_gen.major_eval_protocol check-embeddings \
  --input gaokaollm_bench/outputs/major_training_grouped/split_seed42/train.jsonl \
  --embeddings gaokaollm_bench/outputs/major_training/embeddings_union_val_filled.npz
```

运行 probe-only 分类消融：

```bash
python -m gaokaollm_bench.tests.manual.major_probe_classification_ablation \
  --output-root gaokaollm_bench/outputs/major_probe_classification_ablation \
  --epochs 80 \
  --early-stopping-patience 15
```

汇总 probe-only 分类消融：

```bash
python -m gaokaollm_bench.tests.manual.major_ablation_report \
  --root gaokaollm_bench/outputs/major_probe_classification_ablation \
  --output-json gaokaollm_bench/outputs/major_probe_classification_ablation/summary.json \
  --output-md gaokaollm_bench/outputs/major_probe_classification_ablation/summary.md
```

运行复杂 probe 结构试探：

```bash
python -m gaokaollm_bench.tests.manual.major_probe_architecture_trials --skip-existing
```

仅重新汇总复杂结构结果：

```bash
python -m gaokaollm_bench.tests.manual.major_probe_architecture_trials --summarize-only
```

运行 FR-KAN 分类头试探：

```bash
python -m gaokaollm_bench.tests.manual.major_probe_frkan_trials --skip-existing
```

仅重新汇总 FR-KAN 结果：

```bash
python -m gaokaollm_bench.tests.manual.major_probe_frkan_trials --summarize-only
```
