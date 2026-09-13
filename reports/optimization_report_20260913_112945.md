# Automated ML optimization report

- Target threshold: **0.98**
- Iterations run: **2**
- Runtime: **391.7s**

## Final test metrics

| task | accuracy | precision | recall | f1 | roc_auc | pass |
|---|---|---|---|---|---|---|
| anomaly | 0.9900 | 0.9925 | 0.9800 | 0.9861 | 0.9998 | NO |
| fault | 0.9996 | 0.9996 | 0.9990 | 0.9993 | 1.0000 | YES |
| degradation | 0.9949 | 0.0035 | YES |
| rul | 0.9905 | 5.6479 | YES |

## Iteration log

| iteration | task | change | validation metrics | CV metrics |
|---:|---|---|---|---|
| 1 | anomaly | `rf_balanced_binary` | accuracy=0.9992, precision=0.9988, recall=0.9989, f1=0.9989, roc_auc=1.0000 | accuracy=0.9950, precision=0.9950, recall=0.9950, f1=0.9950, roc_auc=0.9998 |
| 1 | fault | `rf_balanced_multiclass` | accuracy=0.9869, precision=0.9679, recall=0.9517, f1=0.9540, roc_auc=1.0000 | accuracy=0.9987, precision=0.9988, recall=0.9988, f1=0.9987, roc_auc=1.0000 |
| 1 | degradation | `extra_trees_regressor` | r2=0.9839, mae=0.0049 | r2=0.9920 |
| 1 | rul | `extra_trees_regressor` | r2=0.9801, mae=6.1432 | r2=0.9901 |
| 2 | fault | `extra_trees_balanced_multiclass` | accuracy=0.9995, precision=0.9990, recall=0.9990, f1=0.9990, roc_auc=1.0000 | accuracy=0.9985, precision=0.9985, recall=0.9985, f1=0.9985, roc_auc=1.0000 |

## Artifacts

Models and metadata are saved in `models/optimized/`.
The test set is held out from candidate selection; inspect the `pass` column before deployment.
