# Major Probe Academic Ablation Summary

## Aggregates

| Group | Runs | Macro-F1 Mean | Macro-F1 Std | Accuracy Mean | Accuracy Std | Top-3 Mean | Top-3 Std |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw__mlp__sqrt_balanced | 3 | 0.6862 | 0.0195 | 0.7068 | 0.0057 | 0.8554 | 0.0098 |
| raw__mlp__none | 3 | 0.6795 | 0.0136 | 0.7088 | 0.0057 | 0.8474 | 0.0102 |
| raw__linear__sqrt_balanced | 3 | 0.6109 | 0.0025 | 0.6888 | 0.0028 | 0.8454 | 0.0057 |
| raw__linear__none | 3 | 0.5552 | 0.0024 | 0.6566 | 0.0000 | 0.8594 | 0.0028 |

## Runs

| Run | Group | Macro-F1 | Accuracy | Top-3 | Epoch | Model | Hidden | Class Weight | Seed |
|---|---|---:|---:|---:|---:|---|---:|---|---:|
| raw_linear_none_s42 | raw__linear__none | 0.5530 | 0.6566 | 0.8614 | 64 | linear | 256 | none | 42 |
| raw_linear_none_s43 | raw__linear__none | 0.5541 | 0.6566 | 0.8614 | 76 | linear | 256 | none | 43 |
| raw_linear_none_s44 | raw__linear__none | 0.5584 | 0.6566 | 0.8554 | 75 | linear | 256 | none | 44 |
| raw_linear_sqrt_balanced_s42 | raw__linear__sqrt_balanced | 0.6074 | 0.6867 | 0.8494 | 80 | linear | 256 | sqrt_balanced | 42 |
| raw_linear_sqrt_balanced_s43 | raw__linear__sqrt_balanced | 0.6123 | 0.6928 | 0.8373 | 76 | linear | 256 | sqrt_balanced | 43 |
| raw_linear_sqrt_balanced_s44 | raw__linear__sqrt_balanced | 0.6131 | 0.6867 | 0.8494 | 80 | linear | 256 | sqrt_balanced | 44 |
| raw_mlp_h256_none_s42 | raw__mlp__none | 0.6866 | 0.7169 | 0.8434 | 79 | mlp | 256 | none | 42 |
| raw_mlp_h256_none_s43 | raw__mlp__none | 0.6914 | 0.7048 | 0.8614 | 69 | mlp | 256 | none | 43 |
| raw_mlp_h256_none_s44 | raw__mlp__none | 0.6604 | 0.7048 | 0.8373 | 47 | mlp | 256 | none | 44 |
| raw_mlp_h256_sqrt_balanced_s42 | raw__mlp__sqrt_balanced | 0.7081 | 0.7108 | 0.8554 | 32 | mlp | 256 | sqrt_balanced | 42 |
| raw_mlp_h256_sqrt_balanced_s43 | raw__mlp__sqrt_balanced | 0.6897 | 0.7108 | 0.8675 | 40 | mlp | 256 | sqrt_balanced | 43 |
| raw_mlp_h256_sqrt_balanced_s44 | raw__mlp__sqrt_balanced | 0.6607 | 0.6988 | 0.8434 | 51 | mlp | 256 | sqrt_balanced | 44 |
