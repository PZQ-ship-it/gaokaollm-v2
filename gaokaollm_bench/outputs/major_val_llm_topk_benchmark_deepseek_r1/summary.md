# 专业树 Top-k 候选池与 LLM 重标注评估

本报告只评估专业层级本体 clean validation set，不运行 Agent/Benchmark。

## Top-k 候选池上限

| 指标 | 数值 |
|---|---:|
| hit@1 | 0.7108 |
| hit@3 | 0.8554 |
| hit@5 | 0.9217 |
| hit@10 | 0.9819 |

## LLM 评估结果

| 方案 | Accuracy | Macro-F1 | changed | corrected | regressed | invalid |
|---|---:|---:|---:|---:|---:|---:|
| candidate_top5_full | 0.6566 | 0.6393 | 37 | 11 | 20 | 0 |
| candidate_top10_full | 0.6928 | 0.6653 | 30 | 11 | 14 | 0 |
| direct_llm_full | 0.6325 | 0.5310 | 38 | 9 | 22 | 0 |
| candidate_top5_threshold_0.20 | 0.7169 | 0.7136 | 1 | 1 | 0 | 0 |
| candidate_top5_threshold_0.35 | 0.7048 | 0.6597 | 10 | 3 | 4 | 0 |
| candidate_top5_threshold_0.50 | 0.6988 | 0.6377 | 17 | 6 | 8 | 0 |
| candidate_top5_threshold_0.65 | 0.7048 | 0.6743 | 25 | 10 | 11 | 0 |
| candidate_top10_threshold_0.20 | 0.7169 | 0.7136 | 1 | 1 | 0 | 0 |
| candidate_top10_threshold_0.35 | 0.7108 | 0.6634 | 10 | 4 | 4 | 0 |
| candidate_top10_threshold_0.50 | 0.7048 | 0.6348 | 17 | 7 | 8 | 0 |
| candidate_top10_threshold_0.65 | 0.7108 | 0.6718 | 25 | 11 | 11 | 0 |

## 低置信区间

| 阈值 | 审校数 | 错误数 | 错误且 gold@5 | 错误且 gold@10 |
|---:|---:|---:|---:|---:|
| 0.20 | 1 | 1 | 1 | 1 |
| 0.35 | 21 | 10 | 4 | 8 |
| 0.50 | 37 | 15 | 9 | 13 |
| 0.65 | 75 | 31 | 19 | 28 |

## 推荐论文口径

- 推荐区间：candidate_top5_threshold_0.20，Accuracy=0.7169，Macro-F1=0.7136。
- 若 Macro-F1 未超过 MLP 单模型，应写作候选池与审校机制分析，不包装为自动重标注全面提升。
