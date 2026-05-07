# Major Probe Architecture Trials

Promotion gate: Macro-F1 > 0.6862 and Accuracy >= 0.7088.

| Architecture | Runs | Macro-F1 Mean | Macro-F1 Std | Accuracy Mean | Top-3 Mean | Epoch Mean | Promotion Candidate |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline_mlp_h256_l1_do0p1_sqrt | 3 | 0.6862 | 0.0239 | 0.7068 | 0.8554 | 41.0000 | no |
| deep_mlp_h256_l2_do0p1_sqrt | 3 | 0.6541 | 0.0023 | 0.6908 | 0.8474 | 43.0000 | no |
| residual_mlp_h256_b2_do0p1_sqrt | 3 | 0.6420 | 0.0149 | 0.6787 | 0.8133 | 14.0000 | no |
| deep_mlp_h384_l2_do0p15_sqrt | 3 | 0.6417 | 0.0091 | 0.6767 | 0.8474 | 35.6667 | no |
| residual_mlp_h384_b2_do0p15_sqrt | 3 | 0.6386 | 0.0181 | 0.6787 | 0.8092 | 28.0000 | no |
| deep_mlp_h256_l3_do0p15_sqrt | 3 | 0.6018 | 0.0254 | 0.6486 | 0.8052 | 53.3333 | no |

## Conclusion

No architecture passes the dual gate; under this strict protocol, deeper probe capacity is not yet a default-model replacement.
