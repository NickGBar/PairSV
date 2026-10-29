# PAIR-SV Train15 interim report

## Abstract

This interim validation experiment evaluates PAIR-SV on a frozen multisample snapshot of 15 training individuals and five validation individuals (29,924 and 9,981 successful sample–candidate examples). It is **not** the final 40/5/5 experiment and no internal-test person was accessed. Controlled fixed-seed M0, M2 and M4 runs use identical examples, five epochs, train-only normalization and validation-only threshold selection. M4 has the highest F1, but its margin over M2 is small; conclusions therefore remain cautious.

## Motivation, data and split

The question is whether paired breakpoint images benefit from sample-specific read support and candidate-aware REF/ALT representation. Positives are PanGenie GT 0/1 or 1/1 high-quality sequence-resolved deletions; negatives are same-site callable 0/0 genotypes. This design holds the candidate locus fixed across people and tests genotype-specific evidence. The person split is frozen: 15 train and five validation individuals here; internal test remains untouched.

## Extraction, QC and protocol

Each example has two `(6,64,128)` pileups, selected read sequences, 17 scalar support features and deduplicated GRCh38 REF/ALT context. Validation extraction passed 9,981/10,000 rows (0.19% failure); train shards used for this snapshot passed their QC. No sample ID, population, GQ, AF, negative type, source filename or split is passed to the model. M0 uses images, M2 adds scalars, and M4 adds REF/ALT and read embeddings. All three models were retrained with seed 20260720, five epochs, identical rows and a threshold maximizing validation F1.

## Main results

| model   |   validation_loss |   threshold |   precision |   recall |     f1 |   roc_auc |   pr_auc |    mcc |   tn |   fp |   fn |   tp |   epochs |   training_seconds |   parameters |
|:--------|------------------:|------------:|------------:|---------:|-------:|----------:|---------:|-------:|-----:|-----:|-----:|-----:|---------:|-------------------:|-------------:|
| M0      |            0.4261 |       0.415 |      0.7609 |   0.8413 | 0.7991 |    0.8836 |   0.8947 | 0.5807 | 3678 | 1318 |  791 | 4194 |        5 |            1065.28 |       287618 |
| M2      |            0.4242 |       0.445 |      0.7591 |   0.8411 | 0.798  |    0.8844 |   0.8954 | 0.578  | 3665 | 1331 |  792 | 4193 |        5 |            1025.04 |       323110 |
| M4      |            0.4102 |       0.435 |      0.7668 |   0.8497 | 0.8062 |    0.8914 |   0.9003 | 0.5954 | 3708 | 1288 |  749 | 4236 |        5 |            1044.46 |       622374 |

The controlled M4 F1 advantage over M2 is small. Bootstrap intervals below should not be read as final-test inference; rows are paired observations and candidate reuse limits independence.

## Paired bootstrap (1,000 row resamples)

| comparison   |   n_bootstrap |   f1_difference |   f1_ci_low |   f1_ci_high |   f1_win_proportion |   pr_auc_difference |
|:-------------|--------------:|----------------:|------------:|-------------:|--------------------:|--------------------:|
| M2 − M0      |          1000 |         -0.001  |     -0.005  |       0.0034 |               0.35  |              0.0008 |
| M4 − M0      |          1000 |          0.007  |      0.0016 |       0.0124 |               0.995 |              0.0056 |
| M4 − M2      |          1000 |          0.0081 |      0.0029 |       0.0138 |               1     |              0.0049 |

## Branch dependence

| intervention      |   validation_loss |   threshold |   precision |   recall |     f1 |   roc_auc |   pr_auc |    mcc |   tn |   fp |   fn |   tp |   f1_change |   roc_auc_change |   pr_auc_change |   mean_abs_logit_change |   changed_binary_predictions |
|:------------------|------------------:|------------:|------------:|---------:|-------:|----------:|---------:|-------:|-----:|-----:|-----:|-----:|------------:|-----------------:|----------------:|------------------------:|-----------------------------:|
| candidate_zero    |            0.419  |       0.435 |      0.7375 |   0.8736 | 0.7998 |    0.8894 |   0.8988 | 0.5731 | 3446 | 1550 |  630 | 4355 |     -0.0063 |          -0.002  |         -0.0015 |                  0.164  |                       0.0486 |
| read_zero         |            0.425  |       0.435 |      0.7509 |   0.8514 | 0.798  |    0.8832 |   0.8938 | 0.5746 | 3588 | 1408 |  741 | 4244 |     -0.0082 |          -0.0082 |         -0.0065 |                  0.1745 |                       0.0549 |
| scalar_zero       |            0.4416 |       0.435 |      0.7314 |   0.86   | 0.7905 |    0.8756 |   0.8842 | 0.5534 | 3422 | 1574 |  698 | 4287 |     -0.0156 |          -0.0158 |         -0.0161 |                  0.3291 |                       0.0815 |
| candidate_shuffle |            0.4221 |       0.435 |      0.767  |   0.8367 | 0.8003 |    0.885  |   0.8946 | 0.5855 | 3729 | 1267 |  814 | 4171 |     -0.0058 |          -0.0064 |         -0.0056 |                  0.2046 |                       0.0555 |
| read_shuffle      |            0.4057 |       0.435 |      0.7716 |   0.8568 | 0.812  |    0.8952 |   0.9038 | 0.6074 | 3732 | 1264 |  714 | 4271 |      0.0058 |           0.0039 |          0.0035 |                  0.2362 |                       0.077  |
| scalar_shuffle    |            0.3639 |       0.435 |      0.7833 |   0.9091 | 0.8415 |    0.9247 |   0.9291 | 0.6667 | 3742 | 1254 |  453 | 4532 |      0.0354 |           0.0333 |          0.0288 |                  0.3634 |                       0.115  |

Zero ablations remove an encoded branch; shuffle ablations break row correspondence. Non-zero logit and prediction changes demonstrate that M4 uses the branches. A shuffled read branch can occasionally improve a finite validation realization; that is not evidence that reads are harmful.

## Subgroups

Subgroup counts and metrics are in `pairsv_train15_subgroup_metrics.csv`. Small GT 1/1 or per-person strata require caution. The same-site-negatives row is an all-negative slice, so binary precision/recall/F1 are undefined there (reported as NaN); `specificity` (TN/(TN+FP)) is the informative metric for that row: M0 0.736, M2 0.734, M4 0.742. The short-deletion comparison is shown in the figure.

## Limitations and interim conclusion

Multisample dual-breakpoint models reach validation F1 around 0.80. Scalar read support is useful relative to controlled M0. Full PAIR-SV uses its additional branches and may improve short-deletion recall, but it has not yet shown a convincing overall advantage over M2. Remaining work: audit/recover all remaining shards, finish 40-person training, run three seeds, freeze threshold policy, evaluate once on the untouched five-person internal test, and perform cluster-aware inference. The final success target remains mean internal-test F1 ≥0.72 with consistent three-seed direction and multimodal dependence.
