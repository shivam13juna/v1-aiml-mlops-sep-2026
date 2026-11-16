# Hotel cancellation models for the Model Registry class

Two trained models that predict whether a hotel booking will be cancelled, plus the bookings used to check
them after release. The class registers these files in the SageMaker Model Registry; nothing here needs to
be trained again.

| Path | What it is |
|---|---|
| `models/v1/model.tar.gz` | Version 1: XGBoost, 100 trees of depth 4 |
| `models/v2/model.tar.gz` | Version 2: XGBoost, 300 trees of depth 6, cancellations weighted 3x |
| `data/live.csv` | 1,000 bookings that arrived in August 2017, in the models' input format |
| `data/live_labels.csv` | Whether each of those 1,000 bookings was really cancelled (1) or not (0) |
| `data/encoding.json` | The 29 input columns in order, and the number each text value became |

## How the models were trained

Both were trained by SageMaker training jobs with the built-in XGBoost container `sagemaker-xgboost:1.7-1`
on one `ml.m5.large`, each archive holding one file named `xgboost-model`.

| | v1 | v2 |
|---|---|---|
| Hyperparameters | max_depth 4, num_round 100 | max_depth 6, num_round 300, scale_pos_weight 3 |
| Shared | objective binary:logistic, eta 0.1, tree_method hist, seed 0 | same |
| Validation AUC | 0.8817 | 0.9028 |
| sha256 of model.tar.gz | `95eb395d605f936169edcaf224e980f1d5638fbb29f3e5c028cfc76f4b6274d5` | `936e1c724ade1af5f5a9b53d3960265e76c18e904e2a3b794228d846e5f3700f` |

Training rows are bookings arriving before June 2017 (103,505), validation rows those arriving in June and
July 2017 (10,960). `reservation_status` and `reservation_status_date` were left out, because they record how
a booking ended. Input format: CSV, no header, the 29 columns of `data/encoding.json` in that order, text values
replaced by their numbers (a value not seen in training is -1), missing `children`, `agent` and `company` as 0.
The model returns one probability of cancellation per row.

## Data

Built from the hotel booking demand datasets: Nuno Antonio, Ana de Almeida, Luis Nunes, "Hotel booking demand
datasets", *Data in Brief* 22 (2019) 41-49, https://doi.org/10.1016/j.dib.2018.11.126, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The rows here are re-encoded; the original files
were not otherwise changed.
