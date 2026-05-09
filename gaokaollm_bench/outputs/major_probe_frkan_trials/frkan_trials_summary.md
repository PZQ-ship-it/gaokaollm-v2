# Major Probe FR-KAN Trials

Promotion gate: Macro-F1 > 0.6862 and Accuracy >= 0.7088.

| Trial | Protocol | Runs | Grid | LR | Epochs | Macro-F1 Mean | Macro-F1 Std | Accuracy Mean | Top-3 Mean | Promotion Candidate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| baseline_mlp_h256_sqrt_fair | fair_probe | 3 | 5 | 0.0010 | 100 | 0.6862 | 0.0239 | 0.7068 | 0.8554 | no |
| frkan_g3_fair | fair_probe | 3 | 3 | 0.0010 | 100 | 0.5113 | 0.0350 | 0.6024 | 0.7490 | no |
| frkan_g5_fair | fair_probe | 3 | 5 | 0.0010 | 100 | 0.4814 | 0.0195 | 0.5723 | 0.7289 | no |
| frkan_g7_fair | fair_probe | 3 | 7 | 0.0010 | 100 | 0.4653 | 0.0110 | 0.5462 | 0.7209 | no |
| frkan_g5_paper_lr2e5_e5 | paper_suggested | 3 | 5 | 0.0000 | 5 | 0.4156 | 0.0088 | 0.5000 | 0.7048 | no |

## Conclusion

No FR-KAN trial passes the dual gate; keep the current MLP default unless a later protocol changes the evidence.
