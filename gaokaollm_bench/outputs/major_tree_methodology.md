# 高考专业聚类树构建方法学记录

## 摘要

本文记录 `gaokaollm_bench/outputs/major_tree_final_reviewed.json` 的构建过程及其方法学意义。该专业聚类树服务于 `gaokaollm-bench` 中的专业约束解析、层级放宽推荐、未归类专业判别和反事实志愿生成。与单纯依赖人工规则或黑箱向量聚类不同，我们采用“人工可审计本体 + 数据库真实专业名扫描 + probe 辅助归类 + LLM 低置信审校 + 最终审计合成”的混合流程，在覆盖真实招生噪声的同时保留可解释边界。

最终树的统计如下：

| 指标 | 数值 |
|---|---:|
| 节点数 | 82 |
| Level 0 大类节点 | 8 |
| Level 1 中层节点 | 22 |
| Level 2 叶子簇 | 52 |
| 叶子簇 observed_names 条目 | 19,096 |
| 全节点 observed_names 条目 | 57,287 |

## 研究问题与设计原则

真实招生数据库中的专业名不是干净的标准 taxonomy，而是业务系统中的观测文本。`admission_scores.major_name_raw` 中同时存在标准专业、专业大类、校区标注、培养方向、中外合作、实验班、高职专科名称和局部噪声。因此，本项目的目标不是构造一棵“唯一正确”的学科分类树，而是构造一棵可用于决策评测的工程化语义树。

设计原则包括：

- **可审计性**：每个簇由人工定义的 `include_keywords`、`exclude_keywords` 和真实观测名支撑，避免完全黑箱聚类。
- **覆盖性**：通过扫描全库专业名，将招生场景中实际出现的名称变体纳入树中。
- **保守自动化**：embedding/probe 只用于辅助候选生成，不直接覆盖人工本体。
- **分层放宽可解释**：树结构必须支持从叶子簇、同父近邻、邻接大类到无专业限制的逐步放宽。
- **错误可追踪**：候选归类、LLM 审校、最终挂载均保留审计文件，便于复盘。

## 数据来源

原始专业名来自 PostgreSQL 表字段：

```text
admission_scores.major_name_raw
```

全库扫描统计：

| 指标 | 数值 |
|---|---:|
| distinct major names | 22,759 |
| admission score rows | 140,995 |

该字段包含大量真实业务噪声。保留这些噪声具有方法学意义：benchmark 的被测系统最终面对的并不是教育部标准专业目录，而是招生计划和录取分数表中的真实文本。因此，我们将这些名称视为“观测专业名”，并通过树结构建立它们与可解释专业簇之间的映射。

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

人工骨架承担两项核心功能。第一，它规定语义边界，例如医学执业医师相关类、计算机与软件类、经管类、人文社科类、传统工科类、高职应用技术类等。第二，它为后续自动归类提供稳定的叶子标签，使模型输出始终可以回到可解释簇，而不是产生不可审计的新类。

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

这一阶段的意义在于建立“干净可训练”的基础树。后续 probe 训练集必须来自 `major_tree_observed_full.json`，而不能来自 embedding auto-assigned 版本。此前曾观察到 `中文(南校区)` 被错误归入 `medical_tcm`，原因正是低置信 embedding 自动归类结果被写入了 auto-assigned tree。现已将训练集生成器默认源改为干净 observed tree，并禁止默认使用 `auto_assigned` 树作为规则标注源。

### 3. Probe 辅助未归类专业判别

训练与推理脚本：

```text
gaokaollm_bench/data_gen/major_training_set_builder.py
gaokaollm_bench/data_gen/major_embedding_cache.py
gaokaollm_bench/data_gen/major_train_val_split.py
gaokaollm_bench/data_gen/major_probe_train.py
gaokaollm_bench/data_gen/major_probe_predict.py
gaokaollm_bench/data_gen/major_probe_review_candidates.py
```

probe 不微调 embedding 模型，只在 4096 维文本向量上训练分类头。训练标签为叶子簇 `leaf_id`。这一设计使分类器具备两个性质：

- 低成本：只需缓存 embedding，CPU 环境即可训练 probe。
- 可替换：embedding 模型、probe 结构和树标签可以分别迭代。

当前默认 probe 已从线性分类头升级为 MLP：

| 配置项 | 当前值 |
|---|---|
| input_dim | 4096 |
| output_dim | 52 |
| model_kind | MLP |
| hidden_dim | 256 |
| dropout | 0.1 |
| class_weight | balanced |
| selection_metric | val_macro_f1 |
| best_epoch | 38 |
| val_accuracy | 0.7711 |
| val_macro_f1 | 0.7588 |
| val_loss | 0.8274 |

probe 的角色不是直接“决定最终树”，而是为未归类专业生成 top-k 叶子簇候选。这样可以将大规模候选生成自动化，同时把低置信样本交给后续审校流程。

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

不会提供：

```text
recommended_probability
probe prediction probability
row_count
```

这一设计的意义是让 LLM 作为语义审校者，而不是让它复述 probe 的置信度排序。审校后文件为：

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
| final source = probe | 414 |
| final source = llm | 86 |
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

## 质量控制与污染修复

构建过程中发现了一个重要负例：`中文(南校区)`、`中文(青云谱校区)` 等语言类专业曾被写入 `medical_tcm`。复盘显示，这不是人工规则树错误，也不是最终 reviewed tree 的错误，而是中间的 embedding auto-assigned tree 将 `manual_review` 项误写入 `observed_names`。

因此我们做了三项修复：

- 规则标注训练集默认只从 `major_tree_observed_full.json` 生成。
- 训练集构建脚本默认拒绝 `auto_assigned` tree，除非显式传入实验开关。
- 新增回归测试，确保语言类观测名不会进入中医中药临床类。

这类修复的意义在于区分“候选生成”和“监督标签”两个层次。候选可以激进，标签必须保守。

## 消融实验

### Probe 结构与训练策略消融

当前已有实验如下，指标来自验证集：

| Rank | 实验 | Macro-F1 | Accuracy | Val Loss | Best Epoch | 模型 | LR | Weight Decay | Class Weight |
|---:|---|---:|---:|---:|---:|---|---:|---:|---|
| 1 | mlp_h256_d0.1_lr1e-3_wd1e-4_balanced | 0.7588 | 0.7711 | 0.8274 | 38 | MLP | 0.0010 | 0.0001 | balanced |
| 2 | mlp_h512_d0.2_lr5e-4_wd1e-4_balanced | 0.7328 | 0.7470 | 0.8239 | 59 | MLP | 0.0005 | 0.0001 | balanced |
| 3 | linear_lr1e-3_wd1e-4_balanced | 0.7098 | 0.7470 | 0.8860 | 96 | Linear | 0.0010 | 0.0001 | balanced |
| 4 | linear_lr1e-3_wd1e-4_sqrt_balanced | 0.6929 | 0.7530 | 0.8593 | 100 | Linear | 0.0010 | 0.0001 | sqrt_balanced |
| 5 | linear_lr1e-3_wd1e-4 | 0.6657 | 0.7590 | 0.8399 | 156 | Linear | 0.0010 | 0.0001 | none |
| 6 | linear_lr1e-3_wd1e-5 | 0.6657 | 0.7590 | 0.8399 | 156 | Linear | 0.0010 | 0.00001 | none |
| 7 | baseline_linear_macro | 0.6446 | 0.7530 | 0.8888 | 96 | Linear | 0.0010 | 0 | none |
| 8 | linear_lr5e-4_wd1e-4 | 0.6226 | 0.7470 | 0.9141 | 160 | Linear | 0.0005 | 0.0001 | none |

实验显示：

- 使用 `val_macro_f1` 作为选择指标优于只看 accuracy，尤其适合不均衡专业簇。
- `balanced` class weight 显著提升小类表现，是从 Linear 0.6657 到 0.7098 的关键因素。
- MLP probe 相比线性 probe 有明显收益，当前最佳 Macro-F1 达到 0.7588。
- 低学习率 `5e-4` 在当前训练预算内收敛偏慢，不如 `1e-3`。

### 树构建流程消融

部分流程尚未做严格独立消融，当前记录如下：

| 组件 | 作用 | 已有结果 | 状态 |
|---|---|---:|---|
| 人工本体骨架 | 提供稳定语义边界和叶子标签 | 82 节点 / 52 叶子簇 | 已完成 |
| 规则扫描 observed tree | 从真实 DB 收集可审计专业名 | 18,587 distinct assigned | 已完成 |
| 禁用 auto-assigned 训练源 | 防止低置信 embedding 污染监督标签 | 修复 `中文 -> medical_tcm` 污染 | 已完成 |
| Probe 候选生成 | 为未归类专业生成 top-k 叶子候选 | 500 review candidates | 已完成 |
| LLM 低置信审校 | 对低置信候选做语义复核 | 86 项最终来源含 LLM 审校 | 已完成 |
| 不使用 LLM 审校的最终树 | 对比最终 coverage 与人工错误率 | 待测 | 待测 |
| 只用规则扫描、不用 probe 补全 | 对比未归类覆盖率 | 待测 | 待测 |
| embedding 原生 nearest neighbor 直接挂载 | 对比污染率 | 已发现污染案例，未系统量化 | 部分完成 |
| 多 seed / k-fold probe 验证 | 检验验证集稳定性 | 待测 | 待测 |

## 对 benchmark 的意义

专业树不是孤立的数据清洗产物，而是 `gaokaollm-bench` 多轮反事实评测的基础设施。它至少支持三类能力：

1. **专业约束解析**：将考生口语化偏好映射为可查询的专业簇。
2. **层级放宽推荐**：从同叶子变体、同父近邻、邻接大类、无专业限制逐步扩张搜索空间。
3. **反事实 Gap 生成**：在真实 DB 中寻找“坚持原约束 vs 放宽约束”之间的院校层次跃迁。

因此，专业树的质量直接影响 persona 生成、志愿集合质量、target agent 是否能提出真实可验证的妥协方案，以及 evaluator 能否对推荐进行事实核验。

## 局限与后续工作

当前树和 probe 仍存在若干局限：

- 验证集仅 166 条，单条样本会带来约 0.6% accuracy 波动，后续应采用多 seed 或 k-fold。
- 少数极小样本叶子簇仍表现不稳，例如部分高职类、软件工程、商务管理等。
- LLM 审校只处理低置信样本，尚未对高置信 probe 样本做抽样人工审计。
- 最终树的叶子层级固定为 52 类，是否需要合并过细高职类仍需结合推荐任务效果评估。
- embedding 模型版本会影响 probe 表现，生产环境需固定 `EMBEDDING_MODEL` 和向量维度。

后续优先级建议：

1. 对低 F1 叶子簇补充 observed_names / include_keywords。
2. 做 k-fold 或多 seed probe 验证，确认 0.7588 Macro-F1 的稳定性。
3. 对 probe 高置信挂载项抽样人工审计，估计精度。
4. 在真实 DB 推荐生成中评估不同树版本对 stage 命中率、志愿多样性和专业相关性的影响。
5. 若任务表现仍受专业边界影响，再考虑引入 embedding 辅助的“新簇建议”，但不直接自动改写最终树。

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

从干净 observed tree 构建训练集：

```bash
python -m gaokaollm_bench.data_gen.major_training_set_builder \
  --tree-path gaokaollm_bench/sample_data/major_tree_observed_full.json \
  --output gaokaollm_bench/outputs/major_training/data.jsonl \
  --dedupe-on normalized_text
```

训练当前最佳 probe：

```bash
python -m gaokaollm_bench.data_gen.major_probe_train \
  --input-jsonl gaokaollm_bench/outputs/major_training/splits/train.jsonl \
  --embeddings gaokaollm_bench/outputs/major_training/embeddings.npz \
  --output-dir gaokaollm_bench/outputs/major_training_probe \
  --label-field leaf_id \
  --batch-size 64 \
  --epochs 160 \
  --lr 0.001 \
  --weight-decay 0.0001 \
  --model-kind mlp \
  --hidden-dim 256 \
  --dropout 0.1 \
  --class-weight balanced \
  --selection-metric val_macro_f1 \
  --early-stopping-patience 20 \
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
