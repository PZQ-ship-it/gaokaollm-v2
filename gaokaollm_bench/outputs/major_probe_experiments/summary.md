| rank | name | macro_f1 | accuracy | val_loss | epoch | model | lr | wd | class_weight |
|---|---|---|---|---|---|---|---|---|---|
| 1 | mlp_h256_d0.1_lr1e-3_wd1e-4_balanced | 0.7588 | 0.7711 | 0.8274 | 38 | mlp | 0.0010 | 0.0001 | balanced |
| 2 | mlp_h512_d0.2_lr5e-4_wd1e-4_balanced | 0.7328 | 0.7470 | 0.8239 | 59 | mlp | 0.0005 | 0.0001 | balanced |
| 3 | linear_lr1e-3_wd1e-4_balanced | 0.7098 | 0.7470 | 0.8860 | 96 | linear | 0.0010 | 0.0001 | balanced |
| 4 | linear_lr1e-3_wd1e-4_sqrt_balanced | 0.6929 | 0.7530 | 0.8593 | 100 | linear | 0.0010 | 0.0001 | sqrt_balanced |
| 5 | linear_lr1e-3_wd1e-4 | 0.6657 | 0.7590 | 0.8399 | 156 | linear | 0.0010 | 0.0001 | none |
| 6 | linear_lr1e-3_wd1e-5 | 0.6657 | 0.7590 | 0.8399 | 156 | linear | 0.0010 | 0.0000 | none |
| 7 | baseline_linear_macro | 0.6446 | 0.7530 | 0.8888 | 96 | linear | 0.0010 | 0.0000 | none |
| 8 | linear_lr5e-4_wd1e-4 | 0.6226 | 0.7470 | 0.9141 | 160 | linear | 0.0005 | 0.0001 | none |
