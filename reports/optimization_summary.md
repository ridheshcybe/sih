# Automated optimization summary

Run with `python -m ml.optimize_pipeline --max-iterations 15 --cv-folds 3 --cv-sample 4000`.
Candidates were selected using cross-validation and the validation split; the
test split was held out until final evaluation.

## Baseline and final test metrics

| task | baseline metric(s) | final metric(s) | threshold status |
|---|---|---|---|
| anomaly | AUROC 0.7985 (existing report) | accuracy 0.9900, precision 0.9925, recall 0.9800, F1 0.9861, AUROC 0.9998 | **NOT MET**: recall is below 0.98 at full precision |
| fault | accuracy 0.9649, macro F1 0.8751 (existing report) | accuracy 0.9996, precision 0.9996, recall 0.9990, F1 0.9993, ROC-AUC 1.0000 | **MET** |
| degradation | R2 0.9953 (existing report) | R2 0.9949 | **MET** |
| RUL | R2 0.9928 (existing report) | R2 0.9905 | **MET** |

## Iteration log

| iteration | task | optimization change | validation result |
|---:|---|---|---|
| 1 | anomaly | balanced random forest + validation threshold tuning | accuracy 0.9992, precision 0.9988, recall 0.9989, F1 0.9989, ROC-AUC 1.0000 |
| 1 | fault | balanced random forest | accuracy 0.9869, macro precision 0.9679, macro recall 0.9517, macro F1 0.9540, ROC-AUC 1.0000 |
| 1 | degradation | ExtraTrees regressor | R2 0.9839 |
| 1 | RUL | ExtraTrees regressor | R2 0.9801 |
| 2 | fault | balanced ExtraTrees ensemble | accuracy 0.9995, macro precision 0.9990, macro recall 0.9990, macro F1 0.9990, ROC-AUC 1.0000 |

The loop stopped after iteration 2 because every task met the threshold on
validation. The held-out test check correctly reports that anomaly recall did
not transfer at the required threshold; do not deploy that artifact as a
98%-compliant model without additional data or a revised operating threshold.

## Saved artifacts

The selected models and metadata are written to `models/optimized/`:

- `anomaly_model.joblib`
- `fault_model.joblib`
- `degradation_model.joblib`
- `rul_model.joblib`
- matching `*_meta.json` files, including the selected decision threshold

Load an artifact with:

```python
import joblib
model = joblib.load("models/optimized/fault_model.joblib")
```
