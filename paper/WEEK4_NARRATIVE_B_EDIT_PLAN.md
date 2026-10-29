# Week 4 — Narrative B edit plan

**Date:** 2026-08-08
**Framing:** Narrative B — "one genome is not enough"
**Contribution framing:** C1 (evaluation-methodology)
**Edit target:** the four canonical source drafts. The merged `PAIR_SV_v1_manuscript.md` is regenerated, never edited directly.
**Constraint:** no frozen number, threshold, checkpoint, dataset, cohort, evaluation definition, statistical test or metric is altered or added.

Change types: **F** = factual correction, **I** = interpretive rewrite, **S** = stylistic (Orwell pass).

---

## Term audit (grounded counts, not estimates)

Occurrences of flagged evaluative terms across the four drafts before editing:

| Term | Count | Locations |
|---|---|---|
| conservative | 3 | results:145, results:185, discussion:83 |
| model-specific | 1 | discussion:19 |
| superior | 2 | intro:40, discussion:135 |
| robust | 3 | results:76, discussion:31, discussion:108 |
| validated | 3 | intro:42, discussion:35, discussion:47 |
| generaliz* | 3 | intro:22, discussion:53, methods:76 |
| novel | 1 | discussion:47 |
| demonstrat* | 4 | results:64, results:229, discussion:100, discussion:135 |
| striking | 5 | intro:9, intro:22, discussion:79, discussion:117, discussion:135 |
| prove/proven | 8 | intro, results, discussion (several are "improve"/"approve" substrings — checked individually) |
| "best model" / "achieved 95" / "reached the target" | 0 | — |

Not every occurrence is wrong. Each is classified individually below or in the final audit; terms used to *deny* a claim ("we do not claim to have demonstrated…") are retained.

---

## §1 Abstract — *(new, written last per Part 9)*

**1. Current:** structured skeleton, architecture-first.
**2. Problem:** Part 9 requires the Abstract to open with the evaluation problem, not the architecture, and to carry the negative result explicitly.
**3. Replacement:** new Abstract in seven parts (problem → method → what was evaluated → cohort result → what happened to the HG002 interpretation → contribution → limitation).
**4. Evidence:** cohort report `84f571b6…b3d1`; HG002 reports.
**5. Type:** I + S.

## §2 Introduction

**2a — central question.**
**1. Current:** the Introduction motivates PAIR-SV as an architecture and lists four evidence layers.
**2. Problem:** under Narrative B the paper's question is an evaluation question. The architecture is the instrument, not the subject.
**3. Replacement:** add an explicit framing paragraph asking whether a conclusion drawn from one external genome represents model behaviour across people; keep the architecture description but subordinate it.
**4. Evidence:** the HG002-vs-cohort contrast (§13, §15.12).
**5. Type:** I.

**2b — "striking" (intro:9, intro:22) and "superior" (intro:40).**
**1. Current:** "the most striking single result"; "makes no claim about sequence-model architecture superiority".
**2. Problem:** "striking" is an evaluative adjective inflating a result; the "superiority" use is a denial and is acceptable.
**3. Replacement:** delete "striking"; state the measurement instead. Retain intro:40.
**4. Evidence:** n/a — stylistic.
**5. Type:** S.

**2c — contributions block.**
**1. Current:** four bullets, one claiming "explicit same-site matched supervision across many individuals rather than single-sample training".
**2. Problem:** the literature audit established that samplot-ML already trains across many individuals with genotype labels at shared sites. The contrast with "single-sample training" is false against that paper.
**3. Replacement:** contribution statement C1 (evaluation-methodology framing); same-site design appears as a narrowly worded fourth item with no priority claim.
**4. Evidence:** `WEEK4_LITERATURE_AUDIT.md` F3, F5, §4.
**5. Type:** F (the claim is incorrect as written).

## §3 Related Work

**3a — novelty claim.**
**1. Current:** "PAIR-SV's contribution relative to this line of work is (a) explicit same-site matched supervision across many individuals rather than single-sample training…"
**2. Problem:** not defensible. samplot-ML's genotype-class labels across many 1000 Genomes individuals already yield same-site, differently-labelled examples.
**3. Replacement:** narrowed wording — deliberate construction of balanced matched pairs, plus quantified probes for residual locus shortcuts, rather than same-site examples arising incidentally from a genotyping formulation. No priority claim.
**4. Evidence:** literature audit F1-F5, I2, I3, §4.
**5. Type:** F.

**3b — empty related-work placeholder.**
**1. Current:** "[Space for: prior CNN-pileup-image classifiers…]".
**2. Problem:** the positioning claim rests on related work that is not described.
**3. Replacement:** describe DeepSVFilter (closest by task; positives and negatives from unrelated loci; deletion model trained on HG002), samplot-ML (genotype-class labels across many individuals; same-site examples arise naturally; direct relatives excluded but residual site overlap acknowledged), Cue (discovery and genotyping — different task). Cite the three verified references.
**4. Evidence:** verified metadata table, literature audit §6.
**5. Type:** F.

**3c — "we are not aware of" hedge.**
**1. Current:** no such hedge exists.
**2. Problem:** the claim that no prior work quantifies a locus-memorisation shortcut rests on a targeted search, not exhaustive review (uncertainty U2).
**3. Replacement:** phrase as "we are not aware of" wherever this is asserted.
**4. Evidence:** literature audit U2.
**5. Type:** F.

## §13 Untouched external validation (HG002)

**13a — the "conservative" inference (results:185). Highest priority.**
**1. Current:** "Specificity at the frozen threshold (25-32%) is directionally **higher than** the 5-person POC's LOPO estimate (21-24%, §12), suggesting the earlier POC-scale estimate was not overoptimistic, if anything conservative".
**2. Problem:** this generalises from one genome. The cohort refutes it: cohort specificity is 0.2167/0.2216/0.2253, which sits on the POC range 0.212-0.240. v5.0q is the outlier, not the POC.
**3. Replacement:** report the comparison, drop the inference, and add the cohort-supported reading — the cohort specificity range (≈0.217-0.225) is broadly consistent with the POC estimate, and the v5.0q values are higher than both, so v5.0q appears as the high-specificity outlier among the three tiers.
**4. Evidence:** cohort report `primary_macro_averaged_over_people.specificity`; §12 Phase F; §13 v5.0q table.
**5. Type:** F.

**13b — Figure 8 transition (Part 8).**
**1. Current:** §13 ends with the HG002 subgroup analyses; the cohort appears only much later.
**2. Problem:** the reader meets the HG002 model ordering with no signal that it was later tested and not replicated.
**3. Replacement:** insert the transition drafted in `WEEK4_CONTRIBUTION_AND_FIGURE8.md` — observation → interpretation entertained → independent cohort test → non-replication — stating explicitly that the cohort tested generalisability and was not a post-hoc model search. Reference the figure under its current number (8); renumbering is deferred.
**4. Evidence:** cohort selection manifest (deterministic, pre-Manta), pre-evaluation manifest (checksummed before labels opened), cohort report.
**5. Type:** I.

**13c — "demonstrated mechanism" wording (results:229).**
**1. Current:** "though this is offered as a hypothesis, not a demonstrated mechanism".
**2. Problem:** none. This is a denial and correctly separates hypothesis from result.
**3. Replacement:** retain.
**5. Type:** none.

**13d — results:145 "conservative".**
**1. Current:** appears in the §12 LOPO decision-rule discussion ("At the conservative 99%-recall setting…").
**2. Problem:** none — "conservative" here describes a threshold setting, not an estimate quality.
**3. Replacement:** retain.
**5. Type:** none.

## §14 Error and subgroup analysis

**1. Current:** "two different cohorts and two different truth sources (PanGenie 5-person POC vs GIAB v5.0q HG002)"; extraction-failure rate cited for HG002 only.
**2. Problem:** three cohorts now exist; the cohort's extraction accounting is omitted.
**3. Replacement:** extend to three cohorts; add the cohort extraction-failure rate (128 of 132,196 eligible, 0.0968%) beside HG002's 5 of 4,761.
**4. Evidence:** `COHORT_PRE_EVALUATION_MANIFEST.json` `cohort_totals`; erratum document.
**5. Type:** F.

## §15.2 Recurrence of M2/M4 near-equivalence

**1. Current:** "Four independent pieces of evidence — one statistical test on curated pairs, one development-POC calibration study, and the untouched external result — all point the same direction"; and "never reaches the bar of clearly outperforming the simpler scalar-augmented model".
**2. Problem:** (i) three items are listed while four are claimed — an arithmetic error predating the cohort; (ii) the cohort adds a genuine fourth; (iii) the blanket claim is now too broad — M4's specificity was highest in all three external evaluations, though the differences are small and were not tested for significance.
**3. Replacement:** enumerate four items (controlled bootstrap; POC LOPO; HG002; 30-person cohort). Restrict the equivalence claim to recall and F1. State the specificity direction as an observation, with no significance claim.
**4. Evidence:** §9.2 bootstrap; §12; §13; §15.12.
**5. Type:** F + I.

## §15.3 Why M2 alone met the criterion on HG002

**1. Current:** heading "Why M2 alone met the frozen 95% recall criterion on HG002, and M4 did not"; body: "What happened on HG002 is **model-specific**: M4's probability distribution shifted… M2's threshold transferred more faithfully."
**2. Problem:** "model-specific" is the exact inversion of what 30 people show. Macro recall differs by 0.000176, against a between-person SD of 0.0062.
**3. Replacement:** retitle to mark it as the HG002 observation. Rewrite the body as: observation (the HG002 numbers), then the interpretation entertained at the time, then the cohort outcome. Keep the mechanistic speculation but label it superseded — do not delete it, per the instruction not to hide superseded interpretations.
**4. Evidence:** cohort report recall macro means and SDs.
**5. Type:** F + I.

## §15.4 Why M4's higher specificity does not compensate

**1. Current:** frames M4 as trading recall for specificity, in general terms.
**2. Problem:** on the cohort M4's specificity is highest *and* its recall equals M2's (0.9471 vs 0.9473). There is no trade at population scale. The principle is sound; its instance was person-specific.
**3. Replacement:** scope the section to HG002; retain the principle (a specificity gain does not substitute for a pre-registered recall target); add that on the cohort the trade does not appear and all three models miss the target, so the argument no longer separates models.
**4. Evidence:** cohort report recall and specificity macro means.
**5. Type:** I.

## §15.12 Cohort as transfer evidence

**1. Current:** reports accept-all prevalence 0.8832 and F1 0.9378 in the accounting paragraph; model F1 appears only in the table.
**2. Problem:** the reader is left to notice unaided that all three models score lower F1 than accepting every call. That is an unfavourable result and must be stated plainly.
**3. Replacement:** state it directly — model F1 0.9223-0.9238 against accept-all 0.9378 — and give the reason: 88.3% positive prevalence plus a threshold that trades recall for specificity. State that F1 is not used as a headline metric for this tier.
**4. Evidence:** cohort report per-model F1 macro means; accept-all baseline macro.
**5. Type:** F (adds a required negative result).

**15.12b — evaluative language.** Replace "the most reproducible model-level signal in the study" and similar with the measurement and its scope. **Type:** S.

## §15.10 v5.0q vs v0.6

**1. Current:** offers two readings, prefers neither.
**2. Problem:** the cohort adds a third data point that mildly favours reading (a). It is not decisive — the cohort uses PanGenie truth, not GIAB — so it must be labelled suggestive.
**3. Replacement:** add one sentence recording the cohort specificity range and marking the inference as suggestive, not conclusive. Keep the refusal to adjudicate.
**4. Evidence:** cohort specificity; audit ambiguity item 2.
**5. Type:** I.

## §16 Limitations

**1. Current:** AFR bullet says "The most plausible explanation is weaker PanGenie panel representation… rather than a deficiency of PAIR-SV itself".
**2. Problem:** close to a causal claim. The instruction requires "consistent with a panel-representation effect".
**3. Replacement:** state the measurement first (AFR specificity 0.174-0.183 vs 0.223-0.243 elsewhere; recall flat), then say the pattern is consistent with a panel-representation effect and that the analysis does not establish a cause.
**4. Evidence:** cohort `by_superpopulation`.
**5. Type:** F (removes an unsupported causal implication).

## §17 Reproducibility

**1. Current:** "The equivalent multi-cohort and v0.6 manifests will be added once those passes complete."
**2. Problem:** the cohort artifacts exist; no v0.6 artifact manifest exists.
**3. Replacement:** list the cohort artifacts with checksums, and state plainly that no end-to-end v0.6 artifact manifest comparable to the HG002 one was produced.
**4. Evidence:** the five cohort artifact files and their recorded hashes.
**5. Type:** F.

## §18 Conclusion

**1. Current:** long paragraph; contains "striking", "superior"-adjacent phrasing, and leads with the architecture finding.
**2. Problem:** must be coherent with Narrative B and must separate performance, generalisation and evaluation design. Also must not imply deployment readiness.
**3. Replacement:** restructure into short paragraphs: what was measured; what did not generalise; what the study contributes; what it does not claim. Remove evaluative adjectives. Keep the counterfactual ("had we stopped at one genome") as a plain statement.
**4. Evidence:** as for §15.12.
**5. Type:** I + S.

---

## Explicitly out of scope

- No change to any frozen number, threshold, checkpoint, dataset, cohort membership, or evaluation definition.
- No new statistical test, significance claim, or metric.
- No renaming or moving of Figure 8 (Part 8 covers prose only).
- No `[ref]` removed; the bracketed citation placeholders are preserved for the outstanding literature pass.
- §4-8 (Methods) unchanged except where a cross-reference breaks.
