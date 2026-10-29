# Cohort evaluation — erratum (secondary accounting field only)

**Date:** 2026-08-08
**Applies to:** `manta_poc/cohort_final_evaluation_report.json`
(sha256 `84f571b617025597b12d1caf55bb0ce3b18b0f021fbc58cf30e6798a0538b3d1`)

## The error

The report's per-person `candidate_accounting.n_extraction_failures` field is
computed by a flawed expression in `cohort_evaluate.py`. Summed over the
cohort it yields **67**, which is wrong.

The authoritative value, computed directly from the primary artifacts
(count of `extraction_precheck_status == "ok"` rows in each person's
`gate3_candidate_manifest.json`, minus the row count of that person's
`pairsv_shard_<SAMPLE>_gate3.h5`), is:

| Quantity | Value |
|---|---|
| Total eligible for extraction | 132,196 |
| Total rows successfully extracted into shards | 132,068 |
| **True extraction failures** | **128** |
| **True extraction failure rate** | **0.0968%** |

128 is also the value independently recorded in
`COHORT_PRE_EVALUATION_MANIFEST.json`, which was frozen *before* the
evaluation ran, and it matches the per-sample `CandidateExtractionError`
counts printed in the gate3 logs.

## Why the report was not re-run to correct it

`n_extraction_failures` is a **descriptive accounting field only**. It is not
an input to any metric: every reported metric is computed from the merged
predictions-and-labels frame, which is built from the prediction CSVs and the
labelled manifest rows, and never consults this field. All recall,
specificity, precision, F1, balanced-accuracy, MCC, ROC-AUC, PR-AUC,
filtered-candidate-rate, subgroup and superpopulation numbers are therefore
**unaffected**.

Re-running the evaluation after its results have been seen would violate the
one-shot discipline that governs this entire external-validation tier — the
whole point of checksumming the script before execution is that it is not
adjusted once an outcome is visible. Correcting a descriptive field by
re-running would trade a real methodological guarantee for a cosmetic fix.
The error is therefore recorded here and the original report left exactly as
it was produced.

## Related, and not an error

The report's `n_labelled_candidates_scored` totals 102,758, while the
pre-evaluation manifest's `total_confidently_labelled_candidates` totals
103,481 — a difference of 723. Both are correct; they count different things.
The manifest figure is gate2's `labeled_for_M0_M2_M4` (positive +
known_negative among *all* Manta PASS DEL calls), whereas the report counts
labelled candidates that actually reached scoring, i.e. after the predefined
50-10,000bp length precheck and after extraction failures. The 723
difference is the expected, predefined attrition between those two points.
