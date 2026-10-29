# Post-cohort manuscript integration — audit

**Date:** 2026-08-08 (Week 3 → Week 4 boundary)
**Scope:** integrating the completed one-shot 30-person cohort evaluation into the manuscript.
**Pipeline reruns:** none. See the confirmation at the end.

---

## 1. Artifacts frozen

| Artifact | SHA-256 | Note |
|---|---|---|
| `manta_poc/cohort_final_evaluation_report.json` | `84f571b617025597b12d1caf55bb0ce3b18b0f021fbc58cf30e6798a0538b3d1` | The one-shot result. Verified byte-identical on cluster and in-repo; `.sha256` sidecar written. |
| `manta_poc/cohort_evaluate.py` | `6c9afb37c0822ab31fd0bf2964e5d0eb878fe2eea042347f122cb3d49b1edac9` | Checksummed *before* first execution; ran once, unmodified. |
| `manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json` | `3a670e207d8f3bb99a695e05c3755349fd934685b0c1ff402cfbf5d771403942` | Pre-evaluation state, frozen before the run. |
| `manta_poc/COHORT_ONESHOT_EXECUTION_RECORD.md` | — | Execution record, preserved unchanged. |
| `manta_poc/COHORT_EVALUATION_ERRATUM.md` | — | Known erratum, §6 below. |

## 2. Sections updated

| Section | File | Change |
|---|---|---|
| §15.12 | `discussion_limitations_conclusion_v1_draft.md` | Placeholder **replaced** with full cohort results: primary table (9 metrics × M0/M2/M4, mean ± SD), recall range across people, superpopulation table, candidate accounting, explicit HG002 v5.0q and v0.6 comparison, explicit statement that no model reaches 95% recall, explicit statement that the HG002 M2-vs-M4 ordering does not replicate, and an explicit restatement that M4 remains the predefined primary model. |
| §16 Limitations | same | Cohort-dependent placeholder bullet **replaced** by two evidenced bullets: the AFR specificity gap (equity-relevant, attributed to truth-panel representation rather than model deficiency, with that uncertainty stated) and the frozen threshold undershooting its recall target at population scale. Truth-source bullet's stale "(pending)" on v0.6 removed. |
| §15.11 | same | Cross-reference `§TODO` → `§15.12`, plus a one-line forward pointer that the answer came back person-specific. |
| §18 Conclusion | same | "(pending completion)" removed; rewritten to state the cohort answer, the 95%-target miss, the surviving specificity ordering, and the methodological lesson about n=1 external validation. |
| Draft status header + sourcing note | same | Updated to record that all cohort-dependent sections are filled and that no cohort number was hand-transcribed. |
| §9-14 status line, evidence-tier index row 8 | `results_v1_draft.md` | Tier 8 changed from "in progress" to complete, with the frozen report and pre-evaluation manifest cited. |
| §2 Introduction (layer 4), Contributions | `intro_related_work_v1_draft.md` | `§TODO` → `§15.12`; contribution bullet rewritten to state the non-replication and the 95% miss. |
| §1 Abstract skeleton | same | Skeleton updated so it no longer implies the HG002 ordering is the paper's external headline; now carries a population-scale bullet. **Still a skeleton by design.** |
| §3 Related Work | same | `§TODO` → `§13` for the v0.6 sensitivity pass. |
| Canonical manuscript | `PAIR_SV_v1_manuscript.md` | Regenerated (540 lines) from the four drafts by the new `paper/merge_manuscript.py`, so it can no longer drift from them by hand-editing. |

## 3. Figures regenerated

All ten rebuilt by `paper/build_figures.py` from frozen sources.

- **Figure 8 replaced.** The zero-value placeholder (`fig8_cohort_per_person_placeholder.png`, deleted) is now `fig8_cohort_per_person.png`: two stacked panels (recall, specificity) × 30 people × M0/M2/M4, with dotted macro-average reference lines, the 0.95 target line, and superpopulation bands. Every value is read from the frozen report; the function **verifies the report's SHA-256 and aborts if it does not match**, so the figure cannot be silently regenerated from an altered or re-run evaluation. No hand-entered values.
- A missing `numpy` import in `build_figures.py`, surfaced by the new figure, was fixed.

**Numeric verification of Figure 8** (independent recomputation from the report):

- macro-average of the plotted per-person bars == the report's `macro_mean`, for all 2 metrics × 3 models, to < 1e-12 (12/12 pass)
- recomputed SD == the report's `macro_sd`, same tolerance (12/12 pass)
- 30 unique bars per series; superpopulation groups 6/6/6/6/6
- all plotted values inside the drawn axis limits; 0.95 target line above all three macro means

## 4. Exact source artifact for every newly inserted result

Every number inserted into §15.12 and §16 was produced by
`paper/extract_cohort_numbers.py`, which verifies source SHA-256 before
reading and writes both a machine-readable sidecar
(`paper/cohort_numbers_for_manuscript.json`) and a prose-ready fragment
(`paper/cohort_15_12_fragment.md`). Nothing was transcribed by hand.

| Inserted result | Source artifact | Path within artifact |
|---|---|---|
| Recall / specificity / precision / F1 / balanced accuracy / MCC / ROC-AUC / PR-AUC / filtered-candidate rate, mean ± SD, M0/M2/M4 | `cohort_final_evaluation_report.json` | `primary_macro_averaged_over_people.<metric>.<model>.{macro_mean,macro_sd}` |
| Recall range across people | same | `primary_macro_averaged_over_people.recall.<model>.{min,max}` |
| Superpopulation recall/specificity table | same | `by_superpopulation.<POP>.metrics.<model>.<metric>` |
| Manta PASS DEL (135,993), labelled scored (102,758), Unknown (30,740 / 22.6%) | same | summed over `candidate_accounting.*` |
| Accept-all-Manta baseline (prevalence 0.8832, F1 0.9378) | same | macro of `per_person.*.accept_all_manta_baseline` |
| **Extraction failures (128, 0.0968%)** | `COHORT_PRE_EVALUATION_MANIFEST.json` | `cohort_totals.total_extraction_failures` — **deliberately not** taken from the report's known-bad field (§6) |
| M2−M4 recall gap (0.000176) | `cohort_final_evaluation_report.json` | computed from the two `macro_mean` values |
| HG002 v5.0q comparison figures | `hg002_final_evaluation_report.json` | `results_by_model.<model>.primary_at_frozen_threshold` |
| HG002 v0.6 comparison figures | `hg002_v0.6_final_evaluation_report.json` | same path |

**Independent post-hoc check:** the rendered manuscript's §15.12 tables were
parsed back out of `PAIR_SV_v1_manuscript.md` and compared cell-by-cell to the
frozen report — **57/57 table cells match, 0 mismatches**, plus 6 prose-level
scalar claims verified (135,993 / 102,758 / 30,740 / the 0.000176 gap / no
model reaching 0.95 / M4 highest specificity).

## 5. Remaining manuscript placeholders

| Placeholder | Status | Why it remains |
|---|---|---|
| **§1 Abstract** | Structured skeleton | Deliberately written last, so it summarises the finished paper. Content updated to reflect the cohort, but it is not yet prose. |
| **§3 Related Work `[ref]` tags** | Unresolved citations | Structural claims are final; a literature pass is still required. Bracketed tags must not be read as verified citations. |
| — | — | **No cohort-dependent placeholder remains.** Every placeholder that was blocked on cohort completion has been filled. |

## 6. Known erratum

The cohort report's descriptive field `candidate_accounting.*.n_extraction_failures`
sums to **67**, which is **incorrect**. The authoritative extraction accounting is
**128 failures (0.0968% of 132,196 eligible)**, independently confirmed three ways:
the pre-evaluation manifest (frozen *before* the run), the per-sample
`CandidateExtractionError` counts in the gate3 logs, and a direct recount of
manifest-eligible rows minus shard rows.

**This field feeds no metric.** Every reported metric is computed from the merged
predictions-and-labels frame, which never consults it. All recall, specificity,
precision, F1, balanced-accuracy, MCC, ROC-AUC, PR-AUC, filtered-candidate-rate,
subgroup and superpopulation values are unaffected.

The evaluator was **not** re-run to correct it. Adjusting a checksummed one-shot
script after its results are visible would trade a real methodological guarantee
for a cosmetic fix. The manuscript therefore cites the manifest's 128, not the
report's 67. Full detail in `manta_poc/COHORT_EVALUATION_ERRATUM.md`, which also
explains the related, non-erroneous 723-candidate difference between the report's
scored count (102,758) and the manifest's labelled count (103,481) — predefined
length-precheck and extraction attrition, both figures correct.

## 7. Confirmation: no scientific pipeline was rerun

During this phase the following were **not** executed, modified, or re-derived:

- the cohort evaluator (`cohort_evaluate.py`) — ran exactly once, before this phase
- Manta, gate2/Truvari, gate3 extraction, HyenaDNA embedding, ensemble scoring
- model checkpoints, seeds, normalization statistics, deployment thresholds
- cohort membership, sample inclusion/exclusion, labels, truth sources
- metric or subgroup definitions

No model training, threshold tuning, label inspection, cohort change, or
exploratory metric optimisation was performed. **No model was selected or
promoted on the basis of the cohort results**: M4 remains the predefined primary
model and M0/M2 the mandatory baselines, exactly as pre-specified, despite M4
leading on specificity, ROC-AUC and MCC while being statistically
indistinguishable from M2 on recall.

Work in this phase was confined to: reading frozen artifacts, extracting their
values programmatically, writing manuscript prose, regenerating figures from
those frozen artifacts, and verifying the result.
