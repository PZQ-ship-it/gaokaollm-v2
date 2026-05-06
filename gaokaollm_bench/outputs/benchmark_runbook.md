# gaokaollm-bench 运行命令手册

本文档记录 `gaokaollm-bench` 当前各部分的常用运行命令。所有命令默认在项目根目录执行：

```bash
cd /d/gaokaollm-v2
conda activate gaokao_pg
```

Windows PowerShell 路径可对应为：

```powershell
cd D:\gaokaollm-v2
conda activate gaokao_pg
```

注意：测试请使用 `python -m pytest ...`，不要直接运行 `python gaokaollm_bench/tests/test_xxx.py`。直接运行测试文件时，Python 的 import path 可能不包含项目根目录，从而报 `ModuleNotFoundError: No module named 'gaokaollm_bench'`。

## 0. 环境自检

确认包可导入：

```bash
python -c "import gaokaollm_bench; print(gaokaollm_bench.__file__)"
```

确认 CPU PyTorch 和 probe 可用：

```bash
python -c "import torch; print(torch.__version__); print('cuda_available=', torch.cuda.is_available())"
```

加载当前最佳 probe：

```bash
python -c "from gaokaollm_bench.data_gen.major_probe_predict import _load_probe; m, labels, nodes = _load_probe(probe_path='gaokaollm_bench/outputs/major_training_probe/best_probe.pt', label_map_path='gaokaollm_bench/outputs/major_training_probe/label_map.json', major_tree_path='gaokaollm_bench/outputs/major_tree_final_reviewed.json'); print(type(m).__name__, m.in_features, m.out_features, len(labels), len(nodes))"
```

如果 Git Bash 中仍遇到 OpenMP 冲突，可临时设置：

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
```

## 1. 基础测试

运行 Phase 1-5 单元测试：

```bash
python -m pytest gaokaollm_bench/tests/test_phase1.py -q
python -m pytest gaokaollm_bench/tests/test_phase2.py -q
python -m pytest gaokaollm_bench/tests/test_phase3.py -q
python -m pytest gaokaollm_bench/tests/test_phase4.py -q
python -m pytest gaokaollm_bench/tests/test_phase5.py -q
```

一次性运行 benchmark 相关测试：

```bash
python -m pytest gaokaollm_bench/tests -q
```

运行真实 DB 生成器、专业树、probe 相关测试：

```bash
python -m pytest gaokaollm_bench/tests/test_real_db_generator_cli.py -q
```

## 2. 专业树构建

### 2.1 从数据库扫描真实专业名

依赖：PostgreSQL 配置可用，`app.core.db_pg` 能连接真实库。

```bash
python -m gaokaollm_bench.data_gen.build_major_tree \
  --base-tree gaokaollm_bench/data_gen/major_clusters.json \
  --output gaokaollm_bench/sample_data/major_tree_observed_full.json \
  --unassigned-output gaokaollm_bench/sample_data/major_tree_unassigned_full.json \
  --min-count 1 \
  --top-unassigned 5000
```

可选：对未归类专业生成 embedding 建议。

```bash
python -m gaokaollm_bench.data_gen.build_major_tree \
  --base-tree gaokaollm_bench/data_gen/major_clusters.json \
  --output gaokaollm_bench/sample_data/major_tree_observed_embedding_preview.json \
  --unassigned-output gaokaollm_bench/sample_data/major_tree_unassigned_embedding_preview.json \
  --embedding-suggestions \
  --embedding-suggestion-limit 200
```

可选：使用 embedding 自动归类未命中项。

```bash
python -m gaokaollm_bench.data_gen.build_major_tree \
  --base-tree gaokaollm_bench/data_gen/major_clusters.json \
  --output gaokaollm_bench/sample_data/major_tree_observed_auto_assigned_full.json \
  --unassigned-output gaokaollm_bench/sample_data/major_tree_embedding_auto_assignment_audit_full.json \
  --embedding-auto-assign \
  --embedding-major-batch-size 256
```

## 3. Probe 训练与验证

### 3.1 从专业树生成训练集

```bash
python -m gaokaollm_bench.data_gen.major_training_set_builder \
  --tree-path gaokaollm_bench/outputs/major_tree_final_reviewed.json \
  --output gaokaollm_bench/outputs/major_training/data.jsonl \
  --dedupe-on normalized_text
```

### 3.2 切分训练集和验证集

```bash
python -m gaokaollm_bench.data_gen.major_train_val_split \
  --input gaokaollm_bench/outputs/major_training/data.jsonl \
  --output-dir gaokaollm_bench/outputs/major_training/splits \
  --label-field leaf_id \
  --val-ratio 0.1 \
  --seed 42
```

### 3.3 缓存 embedding

依赖：`.env` 中配置 `OPENAI_API_KEY`、`EMBEDDING_MODEL`，可选 `OPENAI_BASE_URL`。

```bash
python -m gaokaollm_bench.data_gen.major_embedding_cache \
  --input gaokaollm_bench/outputs/major_training/data.jsonl \
  --output gaokaollm_bench/outputs/major_training/embeddings.npz \
  --text-field normalized_text \
  --batch-size 128
```

### 3.4 训练线性 probe

CPU 可运行，不需要独显。

```bash
python -m gaokaollm_bench.data_gen.major_probe_train \
  --input-jsonl gaokaollm_bench/outputs/major_training/splits/train.jsonl \
  --embeddings gaokaollm_bench/outputs/major_training/embeddings.npz \
  --output-dir gaokaollm_bench/outputs/major_training_probe \
  --label-field leaf_id \
  --batch-size 64 \
  --epochs 64 \
  --lr 0.001 \
  --seed 42 \
  --selection-metric val_accuracy
```

如需保存每个 epoch 的 checkpoint：

```bash
python -m gaokaollm_bench.data_gen.major_probe_train \
  --input-jsonl gaokaollm_bench/outputs/major_training/splits/train.jsonl \
  --embeddings gaokaollm_bench/outputs/major_training/embeddings.npz \
  --output-dir gaokaollm_bench/outputs/major_training_probe \
  --label-field leaf_id \
  --batch-size 64 \
  --epochs 64 \
  --lr 0.001 \
  --seed 42 \
  --selection-metric val_accuracy \
  --save-epoch-checkpoints
```

### 3.5 验证 probe

```bash
python -m gaokaollm_bench.data_gen.major_probe_validate \
  --input-jsonl gaokaollm_bench/outputs/major_training/splits/val.jsonl \
  --embeddings gaokaollm_bench/outputs/major_training/embeddings.npz \
  --label-map gaokaollm_bench/outputs/major_training_probe/label_map.json \
  --probe gaokaollm_bench/outputs/major_training_probe/best_probe.pt \
  --label-field leaf_id \
  --text-field normalized_text
```

### 3.6 单条专业 probe 推理

依赖：embedding API 可用。

```bash
python -m gaokaollm_bench.data_gen.major_probe_predict \
  --text 中文 \
  --text "中文(南校区)" \
  --text 汉语言文学 \
  --top-k 10 \
  --probe gaokaollm_bench/outputs/major_training_probe/best_probe.pt \
  --label-map gaokaollm_bench/outputs/major_training_probe/label_map.json \
  --major-tree gaokaollm_bench/outputs/major_tree_final_reviewed.json
```

JSON 输出：

```bash
python -m gaokaollm_bench.data_gen.major_probe_predict \
  --text 临床医学 \
  --top-k 10 \
  --json \
  --probe gaokaollm_bench/outputs/major_training_probe/best_probe.pt \
  --label-map gaokaollm_bench/outputs/major_training_probe/label_map.json \
  --major-tree gaokaollm_bench/outputs/major_tree_final_reviewed.json
```

## 4. Probe 候选审校与最终专业树

### 4.1 对未归类专业生成 probe 待审校候选

```bash
python -m gaokaollm_bench.data_gen.major_probe_review_candidates \
  --unassigned gaokaollm_bench/sample_data/major_tree_unassigned_full.json \
  --probe gaokaollm_bench/outputs/major_training_probe/best_probe.pt \
  --label-map gaokaollm_bench/outputs/major_training_probe/label_map.json \
  --major-tree gaokaollm_bench/outputs/major_tree_final_reviewed.json \
  --output gaokaollm_bench/outputs/major_probe_review_candidates.json \
  --top-k 5 \
  --batch-size 128 \
  --min-confidence 0.35
```

### 4.2 LLM 审校低置信候选

依赖：`.env` 中配置 `OPENAI_API_KEY`，可选 `OPENAI_BASE_URL`、`LLM_REVIEW_MODEL` 或 `OPENAI_MODEL`。

推荐每个请求只审一个 item，并发 10：

```bash
python -m gaokaollm_bench.data_gen.major_probe_llm_review \
  --input gaokaollm_bench/outputs/major_probe_review_candidates.json \
  --output gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json \
  --per-item \
  --concurrency 10 \
  --batch-size 10
```

先试跑 1 条：

```bash
python -m gaokaollm_bench.data_gen.major_probe_llm_review \
  --input gaokaollm_bench/outputs/major_probe_review_candidates.json \
  --output gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.preview.json \
  --per-item \
  --concurrency 1 \
  --limit 1
```

### 4.3 从审校结果生成最终专业树

```bash
python -m gaokaollm_bench.data_gen.major_tree_finalize_from_reviews \
  --base-tree gaokaollm_bench/sample_data/major_tree_observed_full.json \
  --reviews gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json \
  --output gaokaollm_bench/outputs/major_tree_final_reviewed.json \
  --audit-output gaokaollm_bench/outputs/major_tree_final_reviewed_audit.json
```

## 5. 真实 DB 冰山画像生成

依赖：PostgreSQL 配置可用，`app.core.db_pg` 能连接真实库。

### 5.1 省份放宽：坚持不出省

```bash
python -m gaokaollm_bench.data_gen.generate_personas \
  --persona-shape volunteer_set \
  --relaxation province \
  --province 浙江 \
  --count 10 \
  --score-min 520 \
  --score-max 700 \
  --score-step 1 \
  --candidates-per-score 120 \
  --recommendation-threshold 3 \
  --output gaokaollm_bench/sample_data/iceberg_personas_real_db_10.json
```

### 5.2 专业放宽：去除专业限制

```bash
python -m gaokaollm_bench.data_gen.generate_personas \
  --persona-shape volunteer_set \
  --relaxation major_any \
  --strict-major 临床医学 \
  --major-relax-scope province \
  --province 浙江 \
  --count 10 \
  --score-min 520 \
  --score-max 700 \
  --score-step 1 \
  --candidates-per-score 120 \
  --recommendation-threshold 3 \
  --output gaokaollm_bench/sample_data/iceberg_personas_major_any_real_db_10.json
```

### 5.3 专业放宽：医学技术类

```bash
python -m gaokaollm_bench.data_gen.generate_personas \
  --persona-shape volunteer_set \
  --relaxation major_clinical_to_medtech \
  --strict-major 临床医学 \
  --target-major-clusters medical_technology \
  --major-relax-scope province \
  --province 浙江 \
  --count 10 \
  --score-min 520 \
  --score-max 700 \
  --score-step 1 \
  --candidates-per-score 120 \
  --recommendation-threshold 3 \
  --output gaokaollm_bench/sample_data/iceberg_personas_major_medtech_real_db_10.json
```

### 5.4 专业树逐级放宽：推荐主路径

Stage 4 默认使用 embedding + probe 找相邻 3 个 level-1 大类，Stage 5 为去除专业限制。当前浙江省内临床医学场景在默认质量过滤、每校最多 2 个志愿、阈值 10 的条件下通常不足量；若要稳定生成每例 10 个志愿，推荐先使用 `--major-relax-scope national`。

```bash
python -m gaokaollm_bench.data_gen.generate_personas \
  --persona-shape volunteer_set \
  --relaxation major_hierarchy \
  --strict-major 临床医学 \
  --major-tree gaokaollm_bench/outputs/major_tree_final_reviewed.json \
  --neighbor-probe gaokaollm_bench/outputs/major_training_probe/best_probe.pt \
  --neighbor-label-map gaokaollm_bench/outputs/major_training_probe/label_map.json \
  --neighbor-count 3 \
  --neighbor-category-level 1 \
  --major-relax-scope national \
  --province 浙江 \
  --count 10 \
  --score-min 520 \
  --score-max 700 \
  --score-step 1 \
  --candidates-per-score 120 \
  --recommendation-threshold 10 \
  --max-volunteers-per-case 10 \
  --max-volunteers-per-school 2 \
  --output gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json
```

如果当前机器没有 embedding API，手工指定 Stage 4 的 probe 邻近叶子簇，绕过实时 probe：

```bash
python -m gaokaollm_bench.data_gen.generate_personas \
  --persona-shape volunteer_set \
  --relaxation major_hierarchy \
  --strict-major 临床医学 \
  --major-tree gaokaollm_bench/outputs/major_tree_final_reviewed.json \
  --neighbor-clusters computer_science law_politics finance_accounting \
  --neighbor-count 3 \
  --source-major-cluster medical_clinical \
  --major-relax-scope national \
  --province 浙江 \
  --count 10 \
  --score-min 520 \
  --score-max 700 \
  --score-step 1 \
  --candidates-per-score 120 \
  --recommendation-threshold 10 \
  --max-volunteers-per-case 10 \
  --max-volunteers-per-school 2 \
  --output gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_manual_neighbors_10.json
```

如果想禁用 Stage 4 probe 邻居，只保留 Stage 1-3 和 Stage 5：

```bash
python -m gaokaollm_bench.data_gen.generate_personas \
  --persona-shape volunteer_set \
  --relaxation major_hierarchy \
  --strict-major 临床医学 \
  --no-probe-neighbors \
  --major-tree gaokaollm_bench/outputs/major_tree_final_reviewed.json \
  --major-relax-scope province \
  --province 浙江 \
  --count 10 \
  --recommendation-threshold 10 \
  --max-volunteers-per-case 10 \
  --output gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_no_probe_10.json
```

## 6. 沙盒与评价器

当前沙盒和评价器主要通过测试用例运行。完整 Phase 4 沙盒测试：

```bash
python -m pytest gaokaollm_bench/tests/test_phase4.py -q
```

完整 Phase 5 评价器测试：

```bash
python -m pytest gaokaollm_bench/tests/test_phase5.py -q
```

如需在代码中接入真实被测系统，需要实现：

```python
from gaokaollm_bench.sandbox.base_target import BaseTargetAgent


class MyTargetAgent(BaseTargetAgent):
    async def chat(self, user_input: str) -> tuple[str, dict]:
        ...
```

然后调用：

```python
from gaokaollm_bench.sandbox.arena import run_episode

transcript = await run_episode(
    persona,
    target=MyTargetAgent(),
    max_turns=6,
    simulator_llm_client=simulator_llm,
    output_dir="gaokaollm_bench/outputs/transcripts",
)
```

事实裁判：

```python
from gaokaollm_bench.evaluator.deterministic_judge import check_hallucination

hallucination_rate = await check_hallucination(transcript, db_pool)
```

LLM 过程裁判：

```python
from gaokaollm_bench.evaluator.llm_as_a_judge import evaluate_process

report = await evaluate_process(transcript, transcript.persona, judge_llm)
```

## 7. 常见问题

### 7.1 找不到 `gaokaollm_bench`

不要这样运行：

```bash
python gaokaollm_bench/tests/test_real_db_generator_cli.py
```

改用：

```bash
python -m pytest gaokaollm_bench/tests/test_real_db_generator_cli.py -q
```

或临时设置：

```bash
PYTHONPATH=. python gaokaollm_bench/tests/test_real_db_generator_cli.py
```

### 7.2 无独显能不能跑 probe

可以。当前 probe 是 4096 输入维度的线性层，CPU 可推理。需要安装 CPU 版 PyTorch：

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 7.3 probe 推理和 Stage 4 有什么外部依赖

probe 本身只需要 CPU PyTorch；但要把原始专业文本转成 embedding，需要 `.env` 中配置：

```text
OPENAI_API_KEY=...
EMBEDDING_MODEL=...
OPENAI_BASE_URL=...
```

若无法调用 embedding API，可在 persona 生成命令中使用 `--neighbor-clusters` 手动指定 Stage 4 邻近叶子簇。

### 7.4 LLM 审校脚本没有中间输出

使用 `--per-item --concurrency 10` 时，每个 item 独立调用，更容易观察进度和失败位置。先用 `--limit 1` 试跑可以快速确认 API、模型名和 SSL 环境是否正常。

### 7.5 Git Bash 下 OpenAI/httpx 报 SSL_CERT_FILE 不存在

如果看到类似错误：

```text
FileNotFoundError: [Errno 2] No such file or directory
ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"])
```

说明当前 shell 中的 `SSL_CERT_FILE` 指向了不存在的证书文件。`gaokao_pg` 的 Git Bash conda hook 已修正为：

```bash
${CONDA_PREFIX}/Library/ssl/cacert.pem
```

重新打开终端或重新激活环境：

```bash
conda deactivate
conda activate gaokao_pg
```

临时修复也可以直接执行：

```bash
export SSL_CERT_FILE="$CONDA_PREFIX/Library/ssl/cacert.pem"
unset REQUESTS_CA_BUNDLE
```

代码侧的 `OpenAIEmbeddingClient` 也会在创建 OpenAI client 前清理坏的 `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`，并在 conda 证书存在时自动指向有效证书。
