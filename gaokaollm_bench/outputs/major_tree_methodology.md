# 高考专业聚类树构建方法学记录

## 摘要

本文档记录 `major_tree_final_reviewed.json` 的构建过程。该专业聚类树用于 `gaokaollm-bench` 中的专业约束解析、层级放宽与反事实志愿生成。构建流程采用“人工可审计本体 + 数据库真实专业名扫描 + 线性探针辅助归类 + 大语言模型审校”的混合方法，目标是在保持可解释性的同时，提高对真实招生数据库中专业名称变体的覆盖率。

最终产物为：

- `gaokaollm_bench/outputs/major_tree_final_reviewed.json`
- `gaokaollm_bench/outputs/major_tree_final_reviewed_audit.json`

## 数据来源

原始专业名称来自 PostgreSQL 表：

```text
admission_scores.major_name_raw
```

全库扫描统计如下：

```text
distinct major names: 22759
admission score rows: 140995
```

该字段包含标准本科专业名、高职专科专业名、专业大类、实验班、中外合作办学标注、校区标注、师范方向标注等多种真实噪声。因此，本研究不将专业名视为静态枚举，而是将其视为来自招生业务系统的观测文本。

## 人工本体骨架

初始聚类树定义在：

```text
gaokaollm_bench/data_gen/major_clusters.json
```

该文件采用人工可审计的树形/森林结构。每个节点包含：

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

人工骨架主要承担两类职责：

1. 定义稳定的专业语义边界，例如医学、计算机、传统工科、经管、人文社科、理学农学、艺术设计、高职应用技术等。
2. 为规则解析和后续模型归类提供可解释的叶子簇标签。

我们没有直接使用黑箱 embedding 聚类覆盖人工本体，而是将人工树作为主干，后续模型只负责补充未命中的真实专业名称。

## 第一阶段：规则扫描归类

脚本：

```text
gaokaollm_bench/data_gen/build_major_tree.py
gaokaollm_bench/data_gen/major_tree_builder.py
```

规则扫描过程为：

1. 聚合 `admission_scores.major_name_raw` 及其出现次数。
2. 对每个真实专业名执行专业树解析。
3. 优先匹配叶子簇 `observed_names`。
4. 再匹配 `include_keywords` / `exclude_keywords`。
5. 将命中专业名写入叶子节点及其祖先节点的 `observed_names`。
6. 将未命中的专业名输出为待处理清单。

规则扫描后生成：

```text
gaokaollm_bench/sample_data/major_tree_observed_full.json
gaokaollm_bench/sample_data/major_tree_unassigned_full.json
```

规则阶段覆盖情况：

```text
assigned distinct names: 18587
unassigned distinct names: 4172
assigned rows: 116687
unassigned rows: 24308
```

这一阶段覆盖了多数高频和标准专业名；剩余项主要是本科边缘类、高职细分名称、实验班、方向标注、小语种、行业技术类专业等。

## 第二阶段：训练线性探针

脚本：

```text
gaokaollm_bench/data_gen/major_training_set_builder.py
gaokaollm_bench/data_gen/major_embedding_cache.py
gaokaollm_bench/data_gen/major_train_val_split.py
gaokaollm_bench/data_gen/major_probe_train.py
gaokaollm_bench/data_gen/major_probe_validate.py
```

线性探针不微调 embedding 模型，只在缓存的专业文本向量上训练一个线性分类头。训练标签为叶子簇 `leaf_id`。

主要产物：

```text
gaokaollm_bench/outputs/major_training/embeddings.npz
gaokaollm_bench/outputs/major_training/splits/train.jsonl
gaokaollm_bench/outputs/major_training/splits/val.jsonl
gaokaollm_bench/outputs/major_training_probe/best_probe.pt
gaokaollm_bench/outputs/major_training_probe/label_map.json
gaokaollm_bench/outputs/major_training_probe/train_history.jsonl
gaokaollm_bench/outputs/major_training_probe/metrics.json
```

训练中记录了逐 epoch 的：

```text
train_loss
train_accuracy
val_loss
val_accuracy
val_macro_f1
missing_val_texts
```

在 64 epoch 训练中，验证集表现出现轻微过拟合趋势。因此最终保存策略改为按 `val_accuracy` 选择最佳 epoch 的权重，并保存为：

```text
best_probe.pt
```

## 第三阶段：probe 生成待审校候选

脚本：

```text
gaokaollm_bench/data_gen/major_probe_review_candidates.py
```

该步骤读取规则阶段未归类文件：

```text
gaokaollm_bench/sample_data/major_tree_unassigned_full.json
```

然后使用：

```text
best_probe.pt
label_map.json
```

对未归类专业生成 top-k 叶子簇候选，输出：

```text
gaokaollm_bench/outputs/major_probe_review_candidates.json
```

每条候选包含：

```json
{
  "major_name": "...",
  "row_count": 123,
  "recommended_label": "...",
  "recommended_label_name": "...",
  "recommended_probability": 0.73,
  "probe_predictions": [],
  "review_status": "pending"
}
```

其中 `low_confidence` 用于标记 top-1 概率低于阈值的样本。这些样本进入 LLM 审校阶段。

## 第四阶段：LLM 审校低置信候选

脚本：

```text
gaokaollm_bench/data_gen/major_probe_llm_review.py
```

LLM 审校只处理：

```json
"review_status": "low_confidence"
```

为了避免概率偏置，传给大语言模型的信息仅包括：

```json
{
  "major_name": "...",
  "candidates": [
    {"label": "...", "label_name": "..."}
  ]
}
```

不会向 LLM 提供：

```text
recommended_probability
probe prediction probability
row_count
```

LLM 只能从候选项中选择一个 `label`，或返回 `null` 表示不修改。审校后的文件为：

```text
gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json
```

该文件中共有 500 条候选：

```text
pending: 408
llm_reviewed: 64
low_confidence: 28
```

其中最终挂载审计来源为：

```text
probe: 414
llm: 86
```

这里的 `llm` 包括带有 `llm_review` 记录的项目。

## 第五阶段：合成最终专业树

脚本：

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
3. 对每条记录读取当前 `recommended_label`。
4. 将 `major_name` 加入目标叶子节点 `observed_names`。
5. 同步加入所有祖先节点的 `observed_names`。
6. 在叶子节点写入 `probe_review_assigned` 审计字段。
7. 输出最终树和审计表。

输出：

```text
gaokaollm_bench/outputs/major_tree_final_reviewed.json
gaokaollm_bench/outputs/major_tree_final_reviewed_audit.json
```

最终树统计：

```text
total distinct names: 22759
total rows: 140995

assigned distinct names: 19087
unassigned distinct names: 3672

assigned rows: 134547
unassigned rows: 6448
```

本次 reviewed candidates 合成贡献：

```text
assigned distinct names: 500
assigned rows: 17860
skipped: 0
```

剩余未归类项数量仍为 3672，但其总行数仅 6448，说明未处理部分主要为低频长尾专业名。

## 可复现命令摘要

构建 observed tree：

```bash
python -m gaokaollm_bench.data_gen.build_major_tree \
  --top-unassigned 5000 \
  --output gaokaollm_bench/sample_data/major_tree_observed_full.json \
  --unassigned-output gaokaollm_bench/sample_data/major_tree_unassigned_full.json
```

训练 probe：

```bash
python -m gaokaollm_bench.data_gen.major_probe_train \
  --input-jsonl gaokaollm_bench/outputs/major_training/splits/train.jsonl \
  --embeddings gaokaollm_bench/outputs/major_training/embeddings.npz \
  --output-dir gaokaollm_bench/outputs/major_training_probe \
  --label-field leaf_id \
  --batch-size 64 \
  --epochs 64 \
  --lr 0.001 \
  --seed 42
```

生成 probe 待审校候选：

```bash
python -m gaokaollm_bench.data_gen.major_probe_review_candidates \
  --unassigned gaokaollm_bench/sample_data/major_tree_unassigned_full.json \
  --probe gaokaollm_bench/outputs/major_training_probe/best_probe.pt \
  --label-map gaokaollm_bench/outputs/major_training_probe/label_map.json \
  --output gaokaollm_bench/outputs/major_probe_review_candidates.json \
  --top-k 5 \
  --batch-size 128 \
  --min-confidence 0.35
```

LLM 审校低置信候选：

```bash
python -m gaokaollm_bench.data_gen.major_probe_llm_review \
  --input gaokaollm_bench/outputs/major_probe_review_candidates.json \
  --output gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json \
  --batch-size 10 \
  --per-item \
  --concurrency 10
```

合成最终树：

```bash
python -m gaokaollm_bench.data_gen.major_tree_finalize_from_reviews \
  --base-tree gaokaollm_bench/sample_data/major_tree_observed_full.json \
  --reviews gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json \
  --output gaokaollm_bench/outputs/major_tree_final_reviewed.json \
  --audit-output gaokaollm_bench/outputs/major_tree_final_reviewed_audit.json
```

## 质量控制与可审计性

本流程的核心原则是：任何非规则阶段的自动补全都必须可追溯。

因此最终树中，规则阶段归类专业记录在 `observed_names`；probe/LLM 审校补入的专业额外记录在：

```text
probe_review_assigned
```

审计字段包括：

```text
major_name
row_count
review_status
source
recommended_probability
review_decision
review_notes
```

这使得后续可以：

1. 按 source 区分规则归类、probe 归类和 LLM 审校归类。
2. 回滚某一批自动归类。
3. 发现高频错误后补入人工规则。
4. 将审校后的结果反哺下一轮训练集。

## 局限性

当前最终树仍有若干局限：

1. 长尾专业名尚未完全覆盖。最终仍有 3672 个 distinct 专业名未归类，但总行数较少。
2. probe 是线性分类头，表达能力有限，容易受训练标签边界和类别不均衡影响。
3. LLM 审校只在 probe top-k 候选中选择，若 top-k 不含正确类别，则 LLM 无法给出树外新类。
4. 部分专业存在天然交叉属性，例如 `生物工程`、`生物医学工程`、`信息管理与信息系统`，单一叶子簇可能无法完全表达其学科交叉性。
5. 当前树主要服务志愿推荐中的“约束放宽”与“专业相似性”任务，不等同于教育部正式专业目录分类。

## 后续迭代建议

后续可继续推进：

1. 对剩余 3672 个长尾未归类项继续生成 review candidates。
2. 将 LLM 审校通过的样本并入训练集，重训 probe。
3. 对高频错误簇补充人工 `include_keywords` 和 `exclude_keywords`。
4. 为交叉学科增加多标签辅助字段，例如 `secondary_cluster_ids`。
5. 引入置信度校准，区分高可信 probe 归类和必须人工审校的低可信归类。

