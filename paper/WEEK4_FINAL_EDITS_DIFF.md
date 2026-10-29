# Week 4 — final pre-submission edits: diff summary and verification

**Date:** 2026-08-08
**Canonical manuscript:** 604 lines, sha256 `3624d02eeee4c722a2459a1d3567d887a0c5be235298a46af9a1d48ba3b82bfe`
(previous: `186e2186…5259`) — regenerated via `paper/merge_manuscript.py`
**Frozen report:** `84f571b6…b3d1`, unchanged. No evaluation run. No test computed.
**Edits applied:** 14 (1 required correctness fix, 1 calibration fix, 1 factual addition, 11 editorial)

---

## 1. Diff — every changed sentence

### Q1 — internal contradiction (required)

**§15.10**

- **Before:** "…in which case neither number alone should be treated as decisive and the population-level cohort (§15.12) is the more reliable arbiter."
- **After:** "…in which case neither number alone should be treated as decisive."

*Reason:* the deleted clause contradicted the D8 sentence in the following paragraph ("the cohort is labelled with PanGenie truth, not with either GIAB callset, so it is not a clean arbiter between them"). The cohort cannot arbitrate between two GIAB callsets. The following paragraph still supplies the cohort data point with its correct limitation.

### C1 + O6 — implied test removed, factual relations substituted

**§15.12, "Effect on the paper's earlier claims"**

- **Before:** "The cohort **strengthens** §15.1-15.2 (the added branches beyond M2 contribute little; M2 and M4 are **now shown indistinguishable** on recall across 30 people), leaves §15.5-15.6 untouched, and **materially weakens** the specific reading in §15.3 … — that asymmetry does not survive contact with a population sample."
- **After:** "The cohort is **consistent with** §15.1-15.2: M2 and M4 **differ on cohort recall by 0.000176, far inside the between-person spread**. It **does not bear on** §15.5-15.6. It **supersedes** the reading in §15.3 that M4's calibration transfers less faithfully than M2's; that asymmetry is not present across 30 people."

*Reason:* "shown indistinguishable" implies an equivalence test that was not pre-specified or run. "strengthens"/"materially weakens" are evaluative; "consistent with"/"does not bear on"/"supersedes" are the factual relations, and "supersedes" matches the label already used in §15.3.

### R4 — operating trade-off (new sentence, frozen numbers only)

**§15.12, added after the F1 paragraph**

> "The operating trade-off the filter represents at this threshold is the following. Across the 30 people, the models remove 7.2-7.3% of Manta PASS DEL candidates (filtered-candidate rate 0.0719 for M2, 0.0725 for M4, 0.0732 for M0) and retain 94.5-94.7% of the labelled positive deletions (recall 0.9453-0.9473). F1 does not express this trade, because at 88.3% prevalence the recall term dominates it."

*Values:* all read from the frozen report — `filtered_candidate_rate` macro means 0.0732 / 0.0719 / 0.0725 (range 7.19-7.32%, stated as 7.2-7.3%) and `recall` macro means 0.9453-0.9473 (94.5-94.7%).
*Wording check:* the words "improvement", "benefit", "gain" and "success" do not appear in this paragraph — verified programmatically.

### Editorial corrections (11)

| ID | Section | Before | After |
|---|---|---|---|
| **O1** | §15.2 | "…is therefore small on the metrics the deployment criterion is written in. **We report that rather than constructing an after-the-fact case for M4.**" | Second sentence deleted |
| **O2 / N1** | §10 | "Two distinct ablation designs were used, and their results **must not be conflated** — this is a central methodological point, **not a footnote**:" | "Two distinct ablation designs were used. Their results measure different things and are reported separately:" |
| **O3** | §15.7 | "**Readers should not conflate** 'PAIR-SV needs threshold recalibration…' (true, expected, and handled) with 'PAIR-SV's ranking ability degrades…' (not supported by the ROC-AUC evidence)." | "Threshold recalibration was needed when moving from curated pairs to real candidates. Ranking, measured by ROC-AUC, did not degrade (0.75-0.76)." |
| **O4** | §15.8 | "**Stated in the Introduction and repeated here because it is easy to lose track of across many tables of numbers:** PAIR-SV is evaluated exclusively…" | "As stated in the Introduction: PAIR-SV is evaluated exclusively…" |
| **O5** | §15.12 | "**We flag this** as a limitation of the evaluation's truth source **with a real equity dimension** (§16), not as a demonstrated model deficiency, and **we do not attempt to correct for it post hoc** — doing so would require changing the labelling rules after seeing results." | "This is a limitation of the truth source (§16). The evidence does not separate it from a property of the classifier. The labelling rules were not changed after the result was seen." |
| **O7** | §15.3 | "The subsection is kept because the interpretation was reasonable on the evidence then available, and **because the paper's point is what happened to it**." | "The subsection is kept because the interpretation was drawn from the evidence available at the time and is superseded by §15.12." |
| **O8** | §16 | "**The result is reported as measured;** labelling rules and thresholds were not adjusted by ancestry after seeing it." | "Labelling rules and thresholds were not adjusted by ancestry after this result was seen." |
| **O9a** | §15.2 | "The differences are small, and we did not pre-specify or run a test for them, so we report the direction and not a significance claim." | "The differences are small; the direction is reported without a significance claim (§15.12)." |
| **O9b** | §18 | "M4 was highest in all three external evaluations. **We did not pre-specify a test for that difference and do not claim significance for it,** and M4 remains the predefined primary model…" | "M4 was highest in all three external evaluations; no test for that difference was pre-specified (§15.12). M4 remains the predefined primary model…" |
| **O10** | §18 | "**Evaluation design.** A single external genome, evaluated once under a fixed protocol, supported a conclusion that thirty genomes did not reproduce." | "**Evaluation design.** The HG002 conclusion was not reproduced by the 30-person cohort." |
| **N2** | §9.2 heading | "Internal one-shot test (**the headline result** — accessed exactly once, §7)" | "Internal one-shot test (**the controlled-benchmark result** — accessed exactly once, §7)" |

---

## 2. Verification results

| # | Check | Result |
|---|---|---|
| 1 | Canonical manuscript regenerated via `merge_manuscript.py` | **PASS** — 604 lines, sha256 `3624d02e…2bfe` |
| 2 | **Pass 2 quantitative verification (complete rerun)** | **PASS** — 20/20 scalar claims match the frozen report (now including the three filtered-candidate-rate values used by R4); §15.12 tables 57/57 cells, **0 mismatches**; aggregates 135,993 / 30,740 / 0.9378 verified |
| 3 | **Pass 3 claim-calibration rescan** | **PASS** — all 11 targeted phrasings now return 0 occurrences; valid technical uses retained unchanged (demonstrat 2, generaliz 3, validated 4, robust 4, superior 1, reliable 3, reproduce 6, typical 1) |
| 4 | D3 and D8 intact | **PASS** — all 5 marker sentences present |
| 5 | `[ref]` placeholders | **PASS** — 12, unchanged |
| 6 | Frozen evaluation checksum | **PASS** — `84f571b6…b3d1`, unchanged |
| 7 | Diff summary | This document |

### R4 numeric confirmation

| Quantity | Frozen report | Manuscript |
|---|---|---|
| filtered-candidate rate M0 / M2 / M4 | 0.0732 / 0.0719 / 0.0725 | identical |
| Range as percentage | 7.19-7.32% | "7.2-7.3%" |
| Recall M0-M2 range | 0.9453-0.9473 | "94.5-94.7%" |

### Forbidden designations — all 0

`best model`, `M4 is superior`, `M4 performs best`, `preferred model`, `clinically validated`, `deployment ready`.

### No new evaluative language introduced

`clearly`, `promising`, `compelling` — 0 occurrences. `improvement` (3), `benefit` (3) and `success` (8) occur only in pre-existing text, each checked individually: they are either denials ("No evidence was found that fusion preferentially benefits short deletions"), tied to the §9.2 bootstrap CI ("measurable improvement over M0 … without adding statistically supported improvement"), the label of the pre-registered decision rule ("strong success bar"), or extraction success counts. None is an evaluative claim about the cohort result.

---

## 3. One deviation from the audit's stated target

The audit proposed reducing the "no test was pre-specified" disclaimer from 4 occurrences to 2. **Three remain, and this is correct.** The three are distinct claims, not repetitions:

| Line | Claim it qualifies |
|---|---|
| L50 (Abstract) | M4's specificity direction across the three external evaluations |
| L419 (§13) | **D3** — whether the HG002 M2-M4 difference itself was nonzero |
| L529 (§15.12) | M4's specificity direction on the cohort |

L50 and L529 are the same claim in abstract and body, which is the normal abstract/body pair. L419 qualifies a different claim entirely and was added as D3 in the previous pass. Removing it would delete the D3 distinction. The audit's target of 2 was set before D3 existed.

---

## 4. Unresolved (carried forward, unchanged by this pass)

1. `[ref]` × 12 unresolved; `byrska-bishop2022` and `[ebert2021, ebler2022]` not expanded to full citations; `pbsv` has no primary publication and should be cited as software.
2. CSV-Filter (2024) unread — literature audit U3.
3. samplot-ML pairing statistics unverified — literature audit U1; the §3 comparison remains qualitative.
4. Figure 8 not renumbered; prose supports promotion to Figure 3 but the figure, filenames and cross-references are unchanged.

---

## 5. Verdict

**Scientific consistency: PASS.** The internal contradiction identified as Q1 in the pre-submission audit is resolved. No quantitative value in the manuscript differs from the frozen report. No scientific claim, number, tier, threshold, evaluation definition or computational artifact was modified. All changes were to prose.
