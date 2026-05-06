# 线性探针训练（方案 B）部署与训练说明

本方案**不微调 embedding 模型**，仅训练线性分类头。适用于 API embedding 场景。

## 目录

- 缓存 embedding（API）
- 训练线性探针
- 切分训练/验证集
- 验证评估脚本
- 输出文件说明
- 迁移部署建议

---

## 1) 缓存 embedding（在有 API 访问权限的机器）

> 只做向量缓存，不训练。

**脚本**：`gaokaollm_bench/data_gen/major_embedding_cache.py`

**默认输入**：

- `gaokaollm_bench/outputs/major_training/train.jsonl`

**默认输出**：

- `gaokaollm_bench/outputs/major_training/embeddings.npz`

**运行命令**：

```bash
python -m gaokaollm_bench.data_gen.major_embedding_cache \
  --input gaokaollm_bench/outputs/major_training/splits/train.jsonl \
  --output gaokaollm_bench/outputs/major_training/embeddings.npz \
  --text-field normalized_text \
  --batch-size 128
```

> 需要 `.env` 中配置 `OPENAI_API_KEY`、`EMBEDDING_MODEL`、可选 `OPENAI_BASE_URL`。

---

## 2) 训练线性探针（在有训练资源的机器）

**脚本**：`gaokaollm_bench/data_gen/major_probe_train.py`

**输入**：

- `train.jsonl`
- `embeddings.npz`（由上一步生成）

**输出**：

- `gaokaollm_bench/outputs/major_training_probe/probe.pt`
- `gaokaollm_bench/outputs/major_training_probe/metrics.json`
- `gaokaollm_bench/outputs/major_training_probe/label_map.json`

**运行命令**：

```bash
python -m gaokaollm_bench.data_gen.major_probe_train \
  --input-jsonl gaokaollm_bench/outputs/major_training/splits/train.jsonl \
  --embeddings gaokaollm_bench/outputs/major_training/embeddings.npz \
  --output-dir gaokaollm_bench/outputs/major_training_probe \
  --label-field leaf_id \
  --batch-size 64 \
  --epochs 8 \
  --lr 0.001 \
  --seed 42
```

---

## 3) 切分训练/验证集

**脚本**：`gaokaollm_bench/data_gen/major_train_val_split.py`

**默认输出**：

- `gaokaollm_bench/outputs/major_training/splits/train.jsonl`
- `gaokaollm_bench/outputs/major_training/splits/val.jsonl`

**运行命令**：

```bash
C:/ProgramData/anaconda3/envs/gaokao_pg/python.exe -m gaokaollm_bench.data_gen.major_train_val_split \
  --input gaokaollm_bench/outputs/major_training/train.jsonl \
  --output-dir gaokaollm_bench/outputs/major_training/splits \
  --label-field leaf_id \
  --val-ratio 0.1 \
  --seed 42
```

---

## 4) 验证评估脚本

**脚本**：`gaokaollm_bench/data_gen/major_probe_validate.py`

**输入**：

- `splits/val.jsonl`
- `embeddings.npz`
- `probe.pt`
- `label_map.json`

**运行命令**：

```bash
python -m gaokaollm_bench.data_gen.major_probe_validate \
  --input-jsonl gaokaollm_bench/outputs/major_training/splits/val.jsonl \
  --embeddings gaokaollm_bench/outputs/major_training/embeddings.npz \
  --label-map gaokaollm_bench/outputs/major_training_probe/label_map.json \
  --probe gaokaollm_bench/outputs/major_training_probe/probe.pt
```

---

## 5) 输出文件说明

- `probe.pt`：线性探针权重（PyTorch）
- `label_map.json`：类别映射（label -> id）
- `metrics.json`：验证与测试指标

---

## 6) 迁移部署建议

- 生产环境中**固定 embedding 模型版本**，避免向量分布漂移。
- 训练与推理必须使用**同一套 embedding 模型/参数**。
- 推理时：先调用 embedding API，再用 `probe.pt + label_map.json` 输出类别。

---

## 7) 依赖

建议在训练机安装：

- `torch`
- `numpy`
- `scikit-learn`

API 缓存机需要：

- `numpy`
- `openai`
- `python-dotenv`
