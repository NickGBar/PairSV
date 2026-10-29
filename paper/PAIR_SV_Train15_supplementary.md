# PAIR-SV Train15 interim study: supplementary material

The publication-form supplement is available as [PDF](PAIR_SV_Train15_supplementary.pdf) and [LaTeX source](PAIR_SV_Train15_supplementary.tex). It documents the frozen Train15/validation comparison (29,924 successful training rows from 15 people; 9,981 successful validation rows from five distinct people). No internal-test person, input, prediction or metric was accessed.

It contains:

- the strict GRCh38 label and deterministic manifest rules;
- the complete table of 17 scalar read-support features;
- HDF5 extraction tensor schema, QC gates and explicit failure rate;
- fixed controlled-training configuration;
- length and genotype subgroup tables and five-person validation F1;
- zero and shuffle intervention results, with the row-bootstrap limitation;
- checksums for controlled metrics, aligned predictions and ablations; and
- the remaining scientific limitations and final-evaluation boundary.

Authoritative numerical inputs are [main metrics](../reports/pairsv_train15_main_metrics.csv), [paired bootstrap](../reports/pairsv_train15_bootstrap.csv), [ablations](../reports/pairsv_train15_ablations.csv), and [subgroups](../reports/pairsv_train15_subgroup_metrics.csv).
