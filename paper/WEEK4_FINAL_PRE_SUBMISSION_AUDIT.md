# Week 4 — final pre-submission audit

**Date:** 2026-08-08
**Manuscript audited:** `paper/PAIR_SV_v1_manuscript.md`, 602 lines, sha256 `186e21864e9729cef266954611b54e8dc039489f4ad7236d3524b3b592c75259`
**Quantitative source of truth:** `manta_poc/cohort_final_evaluation_report.json`, sha256 `84f571b617025597b12d1caf55bb0ce3b18b0f021fbc58cf30e6798a0538b3d1` (verified unchanged)
**Edits applied in this pass:** none. Every item below is a proposal.
**Evaluations run:** none. No statistical test computed.

**Overall verdict: PASS for scientific consistency, with one internal contradiction (Q1) that must be resolved before submission.**

---

## 1. Quantitative verification (Pass 2)

Every cohort-derived number asserted in the manuscript was compared programmatically against the frozen report.

### Scalar claims — 17/17 verified

| Claim | Manuscript | Frozen report | Status |
|---|---|---|---|
| Recall M0 / M2 / M4 | 0.9453 / 0.9473 / 0.9471 | identical | OK |
| Recall SD M0 / M2 / M4 | 0.0065 / 0.0063 / 0.0062 | identical | OK |
| Specificity M0 / M2 / M4 | 0.2167 / 0.2216 / 0.2253 | identical | OK |
| Specificity SD M4 | 0.0302 | identical | OK |
| F1 M0 / M2 / M4 | 0.9223 / 0.9237 / 0.9238 | identical | OK |
| ROC-AUC M4 | 0.7616 | identical | OK |
| MCC M4 | 0.2106 | identical | OK |
| Recall range across people | 0.9276-0.9620 | identical | OK |

### Aggregate and derived claims — all verified

| Claim | Manuscript | Recomputed from report | Status |
|---|---|---|---|
| Manta PASS DEL | 135,993 | 135,993 | OK |
| Labelled scored | 102,758 | 102,758 | OK |
| Unknown | 30,740 (22.6%) | 30,740 (22.6%) | OK |
| Accept-all prevalence / F1 | 0.8832 / 0.9378 | 0.8832 / 0.9378 | OK |
| M2-M4 recall gap | 0.000176 | 0.000176 | OK |
| "thirty-five times smaller than the SD" | — | SD/gap = 35.1 | OK |
| Extraction failures | 128 (0.0968%) | matches pre-evaluation manifest | OK |
| §15.12 tables, cell by cell | 57 cells | 57/57 | **0 mismatches** |

### Superpopulation and HG002 cross-checks

| Claim | Manuscript | Computed | Status |
|---|---|---|---|
| AFR specificity range | 0.174-0.183 | 0.1736-0.1834 | OK (rounding) |
| Other superpopulations | 0.223-0.243 | 0.2227-0.2430 | OK (rounding) |
| Recall across all groups | 0.942-0.949 | 0.9423-0.9493 | OK |
| HG002 v5.0q recall M0/M2/M4 | 0.9486 / 0.9551 / 0.9327 | identical | OK |
| HG002 v5.0q specificity M0/M2/M4 | 0.2739 / 0.2500 / 0.3217 | identical | OK |
| "M4 fell 2.2 points below" | 2.2 | 2.23 | OK |
| v0.6 recall M0/M2/M4 | 0.9742 / 0.9795 / 0.9654 | identical | OK |

**No quantitative mismatch was found anywhere in the manuscript.**

---

## 2. Narrative consistency (Pass 1)

The manuscript carries one central narrative, stated at L52: *"The study's main contribution is therefore about evaluation rather than about model ranking."* The C1 framing is present in the Abstract, Introduction contributions, §13 transition, §15.12 and §18. No architecture-superiority or matched-supervision-novelty thesis competes with it: §3 states explicitly that same-site supervision across individuals is not claimed as new, and the Contributions repeat that qualification.

Two residual designations partially compete, both minor:

| ID | Location | Issue | Proposal |
|---|---|---|---|
| **N1** | L250, §10 | "their results **must not be conflated** — this is a central methodological point, not a footnote" | A second "central" designation, plus "not a footnote" is meta-commentary. Propose: "Two distinct ablation designs were used. Their results measure different things and are reported separately:" |
| **N2** | L216, §9.2 heading | "Internal one-shot test (the headline result — accessed exactly once, §7)" | "Headline" here means headline *of the controlled tier*, but reads as the paper's headline under C1. Propose: "Internal one-shot test (the controlled-benchmark result — accessed exactly once, §7)" |

---

## 3. Claim calibration (Pass 3)

All occurrences of the flagged vocabulary were classified individually. **Valid technical uses were not marked for deletion.**

| Term | Count | VALID | NEEDS QUALIFICATION | STALE |
|---|---|---|---|---|
| demonstrat* | 3 | 3 (all denials: "does not demonstrate", "not a demonstrated mechanism", "not a demonstrated model deficiency") | 0 | 0 |
| generaliz* | 3 | 3 (the question under test; a technical statement about a locus-prior classifier; a limitation) | 0 | 0 |
| validated | 4 | 4 (2 describe the practice being critiqued; 2 are "field-validated" describing truth-set maturity) | 0 | 0 |
| robust | 3 | 3 (2 = robustness to input perturbation; 1 = "robust median/MAD scaling", a method name) | 0 | 0 |
| superior | 1 | 1 (denial: "makes no claim about … superiority") | 0 | 0 |
| best | 1 | 1 ("best-studied SV class" — a property of the field, not of our models) | 0 | 0 |
| significan* | 6 | 6 (4 explicit denials; 2 refer to the §9.2 bootstrap CI, which was a real pre-specified analysis) | 0 | 0 |
| typical | 1 | 1 ("typical insert size" — technical) | 0 | 0 |
| reproduce | 6 | 6 (all describe non-replication accurately) | 0 | 0 |
| **reliable** | 4 | 3 | **1 — see Q1** | 0 |
| **"now shown indistinguishable"** | 1 | 0 | **1 — see C1 below** | 0 |

### Items needing qualification

**Q1 — internal contradiction (the one issue that must be fixed).**
§15.10 contains two statements that cannot both stand:

- L487: *"…in which case neither number alone should be treated as decisive and the population-level cohort (§15.12) is the more reliable arbiter."*
- L489: *"…the cohort is labelled with PanGenie truth, not with either GIAB callset, so it is not a clean arbiter between them."*

The first was written before the D8 truth-source qualification was added; the second is the D8 text. **Proposed minimum fix** — change L487 to: *"…in which case neither number alone should be treated as decisive."* Delete the arbiter clause. The following paragraph then supplies the cohort data point with its correct limitation.

**C1 — implied test where none was run.**
L548: *"M2 and M4 are now shown indistinguishable on recall across 30 people"*. "Shown indistinguishable" implies a test of equivalence. None was pre-specified or run. **Proposed:** *"M2 and M4 differ on cohort recall by 0.000176, far inside the between-person spread"*.

---

## 4. Orwell-style editorial findings (Pass 4)

Each item gives the original, the replacement, and the reason. None applied.

| ID | Location | Original | Proposed | Reason |
|---|---|---|---|---|
| **O1** | L445, §15.2 | "We report that rather than constructing an after-the-fact case for M4." | *(delete the sentence)* | Meta-commentary defending against a suspicion the reader has not raised. The preceding sentence already states the measurement |
| **O2** | L250, §10 | "**must not be conflated** — this is a central methodological point, not a footnote" | "Their results measure different things and are reported separately:" | Instruction to the reader plus self-assessment of importance |
| **O3** | L471, §15.7 | "Readers should not conflate 'PAIR-SV needs threshold recalibration…' with 'PAIR-SV's ranking ability degrades…'" | "Threshold recalibration was needed when moving from curated pairs to real candidates. Ranking, measured by ROC-AUC, did not degrade (0.75-0.76)." | Tells the reader how to interpret rather than stating the two results |
| **O4** | L475, §15.8 | "Stated in the Introduction and repeated here because it is easy to lose track of across many tables of numbers:" | "As stated in the Introduction:" | Meta-commentary about the paper's own readability |
| **O5** | L546, §15.12 | "We flag this as a limitation of the evaluation's truth source with a real equity dimension (§16), not as a demonstrated model deficiency" | "This is a limitation of the truth source (§16). The evidence does not separate it from a property of the classifier." | "We flag", "real equity dimension" — evaluative framing; the §16 bullet already states the consequence |
| **O6** | L548, §15.12 | "The cohort strengthens §15.1-15.2 …, leaves §15.5-15.6 untouched, and materially weakens the specific reading in §15.3" | "The cohort is consistent with §15.1-15.2, does not bear on §15.5-15.6, and supersedes the reading in §15.3" | "strengthens" / "materially weakens" are evaluative; "supersedes" is the factual relation and matches the §15.3 label |
| **O7** | L453, §15.3 | "…because the interpretation was reasonable on the evidence then available, and because the paper's point is what happened to it." | "…because the interpretation was drawn from the evidence available at the time and is superseded by §15.12." | Second clause is authorial commentary on the paper's purpose |
| **O8** | L565, §16 | "The result is reported as measured; labelling rules and thresholds were not adjusted by ancestry after seeing it." | "Labelling rules and thresholds were not adjusted by ancestry after this result was seen." | "reported as measured" is a claim about the authors' conduct rather than about the result |
| **O9** | throughout | The disclaimer "we did not pre-specify a test … make no claim of significance" appears 4× (L50, L443, L527, L594) | Retain in the Abstract (L50) and §15.12 (L527). Replace in §15.2 and §18 with a cross-reference | Repetition of the same disclaimer; two instances carry the evidentiary function, four do not |
| **O10** | L52 / L592 | "a frozen single-genome evaluation was **sufficient to support** a conclusion that thirty genomes did not reproduce" (Abstract and §18) | Retain one; in §18 replace with "The HG002 conclusion was not reproduced by the 30-person cohort." | Same statement in two places with the same evidentiary function |

---

## 5. Reviewer attack surface (Pass 5)

The five strongest technically defensible criticisms, and whether the manuscript already answers them.

| # | Criticism | Already addressed? | Proposed minimum addition |
|---|---|---|---|
| **R1** | **PanGenie is the truth source for the principal result.** The cohort's positives, known-negatives and Unknowns all come from a silver-standard genotype panel, not from an assembly-based benchmark. The headline non-replication is therefore a statement about behaviour under PanGenie labels | **Yes, fully.** §15.9 carries a dedicated paragraph, §15.12 opens with a **Truth source** frame, §16 has a bullet. The wording states the dependency without calling PanGenie weak | None |
| **R2** | **"Did not replicate" ≠ "there was no effect."** The cohort shows the HG002 difference does not persist; it does not establish that the HG002 difference was sampling variation | **Yes.** Stated in both §13 and §15.12: no test of whether the HG002 difference was nonzero was pre-specified, and none is run | None |
| **R3** | **No model reaches the 95% recall target.** A filter that misses its own pre-registered criterion | **Yes.** Stated in the Abstract, §15.12, §16 and §18, each time with the measured values and without mitigation | None |
| **R4** | **F1 below accept-all at 88.3% prevalence.** A reviewer may read this as the filter being worse than doing nothing | **Partly.** §15.12 gives the numbers and the prevalence explanation. What is not stated is the quantity the filter actually improves | **Propose one sentence in §15.12:** "At the frozen threshold the models remove 7.2-7.3% of candidates (filtered-candidate rate 0.0719-0.0732) while retaining 94.5-94.7% of true deletions; F1 does not express this trade because it is dominated by the recall term at this prevalence." All values are already in the frozen report |
| **R5** | **AFR specificity gap with no established cause.** A reviewer may object either that the cause is unproven, or that the paper does too little about it | **Yes.** §16 states the measurement first, gives the consequence, marks the panel-representation account as interpretation, and states that no ancestry-specific adjustment was made | None |

**Two further criticisms not in the requested list but present:**

- **R6 — "n=1 is insufficient" is a known principle.** The manuscript demonstrates it on a pre-registered protocol rather than asserting it, and §3 notes that the closest prior filtering method was trained on a single genome. No text change proposed; this is a discussion-with-reviewers matter, not a manuscript defect.
- **R7 — M4's specificity direction is consistent across three evaluations but untested.** The manuscript reports the direction and declines significance four times (O9). The position is defensible; adding a test now would violate the protocol.

---

## 6. Unresolved issues

1. **Q1 is a genuine internal contradiction** between §15.10's "more reliable arbiter" and the D8 sentence "not a clean arbiter". This is the only defect in the manuscript that a careful reader would catch as an inconsistency rather than a matter of taste.
2. **`[ref]` placeholders: 12, unresolved.** Three citations verified (`liu2021deepsvfilter`, `belyeu2021samplot`, `popic2023cue`); `byrska-bishop2022` and `[ebert2021, ebler2022]` remain unresolved to full citations. `pbsv` has no identifiable primary publication and should be cited as software.
3. **CSV-Filter (2024) unread** (literature audit U3). A directly adjacent filtering method whose supervision scheme is unverified.
4. **samplot-ML pairing statistics unverified** (U1). The §3 comparison is deliberately qualitative as a result.
5. **Figure 8 not renumbered.** Prose supports promotion to Figure 3; the figure, filenames and cross-references have not been changed.
6. **Abstract and §18 both state the non-replication and the target miss.** This is intentional duplication (abstract vs conclusion), not flagged as a defect, but O10 proposes trimming one repeated formulation.

---

## 7. Summary of proposed edits

**14 proposals, none applied.** One is a required correctness fix; the rest are editorial.

| Priority | ID | Type |
|---|---|---|
| **Required** | Q1 | Internal contradiction, §15.10 |
| High | C1 | Implies an equivalence test that was not run |
| Medium | O1-O8 | Meta-commentary, evaluative framing, reader instruction |
| Medium | R4 | One factual sentence giving the trade F1 obscures |
| Low | N1, N2 | Competing "central"/"headline" designations |
| Low | O9, O10 | Repetition without distinct evidentiary function |

---

## 8. Final verdict

| Dimension | Result |
|---|---|
| Quantitative consistency with frozen report | **PASS** — 17/17 scalar claims, 57/57 table cells, all aggregates and HG002/v0.6 cross-checks; 0 mismatches |
| Frozen artifacts unmodified | **PASS** — report checksum unchanged; no evaluation run; no test computed |
| Single central narrative (C1) | **PASS** — with two minor competing designations (N1, N2) |
| Claim calibration | **PASS** — 29 of 31 flagged occurrences valid; 2 need qualification (Q1, C1) |
| Evidence-tier separation | **PASS** — no pooling of v5.0q, v0.6, POC and cohort |
| Negative results stated plainly | **PASS** — target miss, F1 below baseline, AFR gap all present without mitigation |
| Novelty claims bounded by the literature audit | **PASS** — §3 and Contributions both disclaim priority on same-site supervision |
| M4 designation | **PASS** — "predefined primary" only; no "best", "superior" or "preferred" |
| Significance claims | **PASS** — no significance asserted where no test was pre-specified |
| **Internal consistency** | **FAIL on one item (Q1)** — must be fixed before submission |

**Scientific consistency: PASS**, conditional on resolving Q1. No quantitative error exists in the manuscript. The remaining items are editorial and do not affect what the paper claims.
