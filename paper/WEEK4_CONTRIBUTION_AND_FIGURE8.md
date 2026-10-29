# Week 4 — revised contribution statement, Figure 8 transition, and change list

**Date:** 2026-08-08
**Depends on:** `WEEK4_LITERATURE_AUDIT.md` (completed), `WEEK4_SCIENTIFIC_CONSISTENCY_AUDIT.md` (approved)
**Framing adopted:** Narrative B — "one genome is not enough"
**Canonical manuscript modified:** **no.** Nothing below has been applied.

---

## Part 3 — Three candidate contribution statements

All three are constrained by the literature audit: **no claim of priority over multi-individual same-site learning**, since samplot-ML already trains across many individuals with genotype labels at shared sites. All three also avoid the five forbidden claims (M4 best; deployment-validated; cohort proves superiority; 95% target achieved; HG002 M2 advantage generalises).

### C1 — Evaluation-methodology contribution *(most defensible)*

> **Contributions.** (1) We show, on our own pre-registered result, that rigorous single-genome external validation can produce a model-level conclusion that does not survive a population sample: on GIAB HG002 the scalar-augmented M2 was the only variant to reach the pre-specified 95% recall target while the full fusion model M4 missed it by 2.2 points, yet across 30 untouched individuals the two differ in macro-averaged recall by 0.000176 — roughly thirty-five times smaller than the between-person standard deviation. (2) We provide a frozen, checksummed, one-shot evaluation protocol spanning eight explicitly separated evidence tiers, in which thresholds, metric definitions, subgroup definitions and sample inclusion are all fixed before any label is opened, and we report the resulting operating point as a miss: no model reaches the 95% recall target on the cohort. (3) We quantify a parallel evaluation artefact — post-hoc zero-ablation overstates each modality's marginal contribution by 5-10× relative to retrained branch-removal. (4) We release a candidate-verification architecture and a deliberately constructed, balanced same-site matched-pair training design with explicit, quantified probes for residual locus-level shortcuts.

**Why most defensible.** Every clause is a statement about *what was done and observed*, verifiable against frozen artifacts. The central claim is self-critical — the overturned result is ours — which is the hardest kind for a reviewer to attack, since the paper is not asking for credit for a performance win. It survives the literature audit intact: nothing in the surveyed prior work performs this evaluation. It also survives the awkward results (target miss, modest specificity, AFR gap, v5.0q/v0.6 disagreement), because under this framing those are evidence rather than liabilities.

**Attack surface.** A reviewer may say the methodological point is already known in principle ("of course n=1 is insufficient"). The rebuttal is that it is rarely *demonstrated* with a pre-registered protocol on the same pipeline, and that the closest prior filtering work is itself trained on a single genome (DeepSVFilter, HG002) — but the paper must make the demonstration, not the assertion, the contribution.

### C2 — Matched-supervision + evaluation, balanced *(defensible, but with one exposed flank)*

> **Contributions.** (1) A deliberately constructed, balanced same-site matched-pair supervision design for multi-individual SV candidate verification — each locus contributes a positive row in a carrier and a confidently-genotyped reference row in a different individual — combined with explicit, quantified leakage probes showing residual locus-level signal is far below a pre-registered ceiling. (2) A five-model evidence ladder isolating each modality's marginal contribution under both post-hoc and retrained ablation, showing the former overstates by 5-10×. (3) An eight-tier frozen evaluation culminating in a 30-person untouched cohort, which shows that a single-genome model-ordering result does not replicate and that no model reaches the pre-specified recall target.

**Why less defensible than C1.** Clause (1) invites exactly the challenge the literature audit surfaced. samplot-ML already trains across many individuals where the same site carries different genotype labels; our advantage is deliberateness, balance and shortcut-quantification, not the existence of same-site examples. That distinction is real but subtle, and a reviewer who knows samplot-ML well may read clause (1) as overclaiming even in its narrowed form. It also requires uncertainty **U1** (samplot-ML's exact pairing statistics) to be resolved before submission.

### C3 — Architecture-and-modality contribution *(least defensible)*

> **Contributions.** A multimodal candidate-verification architecture combining pileup images, genomic-language-model sequence embeddings and read-support features, evaluated across 31 untouched genomes and two truth sources, with a systematic ablation showing the added modalities are largely redundant.

**Why least defensible.** The architecture's own result is that its extra branches contribute little; leading with the architecture invites the reviewer to conclude the paper's main object is unnecessary by its own evidence. It also under-uses the cohort — the study's scarcest asset — and puts the most weight on the part of the work most similar to prior art (image+CNN SV filtering, per DeepSVFilter and samplot-ML). It is not dishonest, but it is the weakest reading of the same evidence.

### Ranking against a skeptical reviewer

**C1 > C2 > C3.**

**Recommended: C1.** It is the only framing where the literature audit's narrowing costs nothing — C1 makes no priority claim about same-site supervision at all, mentioning the design as a fourth-position engineering contribution rather than the headline. C1 also aligns exactly with Narrative B, and its central claim is quantified from frozen artifacts rather than argued.

If reviewers demand a methods-novelty claim, **C2 is the fallback**, but only after U1 and U3 are resolved.

---

## Part 4 — Proposed Results transition for Figure 8 promotion

Drafted, **not applied.** This is the text that would carry the reader from the HG002 observation to the cohort test if Figure 8 becomes Figure 3. Its job is to make the logical chain explicit and to foreclose the misreading that the cohort was run to find a better model.

> **Proposed insertion — end of §13, immediately after the HG002 primary-result table and its "Honest reporting" paragraph:**
>
> The ordering just described is striking, and it is the kind of result that invites a model-level interpretation: that M2's calibration transfers more faithfully than M4's, and that the full fusion architecture is the more fragile of the two under distribution shift. We considered exactly that interpretation, and §15.3 records it as the hypothesis we entertained.
>
> It is, however, an interpretation drawn from a single genome. Recall, specificity and the gap between them are all properties of one individual's candidate population — of HG002's variant profile, its sequencing run, and the few thousand deletions Manta proposed in it. Nothing in this section can distinguish "M4's threshold transfers less well than M2's" from "M4's threshold transferred less well *on this person*." That ambiguity is not resolvable with more analysis of HG002; it requires more people.
>
> The 30-person cohort reported in §15.12 was assembled to resolve it. Its purpose, membership and evaluation protocol were fixed in advance: the cohort was selected deterministically before any Manta run (six individuals per continental superpopulation, screened for relatedness against every prior cohort in this study), the deployment thresholds were the same frozen values used here and were never retuned, and the evaluation script, metric definitions, subgroup definitions and sample inclusion were all checksummed before a single cohort label was opened. **The cohort was therefore a confirmatory test of a specific, pre-stated generalisation question — does the HG002 model ordering hold across people? — and not a search for a model that performs better.** No model was selected, promoted or re-ranked on the basis of its result; M4 remains the predefined primary model and M0/M2 the mandatory baselines throughout, exactly as pre-specified.
>
> The answer is that the ordering does not hold. Across 30 individuals, M2 and M4 differ in macro-averaged recall by 0.000176 — roughly thirty-five times smaller than the between-person standard deviation of 0.0062 — so the two models are indistinguishable on recall at population scale (Figure 3). The HG002 ordering reflected that individual, not the architecture. Two findings do survive the move from one genome to thirty, and both are visible in the same figure: **no model reaches the pre-specified 95% recall target** on the cohort, and M4 retains the highest specificity, as it does on both HG002 truth sets. §15.12 reports the full result; §15.3 and §15.4 are retained, and explicitly marked, as the interpretation that the cohort superseded.

**Notes on this draft.**
- It names the confirmatory intent in bold and gives the concrete pre-registration facts that back it up, which is the specific defence against a post-hoc-selection reading.
- It preserves §15.3/§15.4 rather than deleting them, consistent with audit items S3/S4 — the paper should show what it once believed.
- It introduces no new number: 0.000176, 0.0062, and the 95%/specificity statements all already exist in frozen artifacts and §15.12.
- It refers to "Figure 3", so it is only valid **if** the promotion happens; the current-numbering variant would say "Figure 8".

---

## Part 5 — Manuscript locations that must change

Nothing below has been applied. Grouped by whether the change is required by the audit, by the literature findings, or by the figure promotion.

### A. Required by the approved consistency audit (7 items)

| # | Location | Change |
|---|---|---|
| A1 | §13, "Honest reporting…" paragraph | **S1 (highest priority):** delete the inference that the POC estimate was "if anything conservative"; replace with a forward pointer noting the cohort lands on the POC estimate, identifying v5.0q as the high outlier |
| A2 | §15.2 body | **S2:** fix "Four independent pieces" to enumerate four (controlled bootstrap; POC LOPO; HG002; cohort); qualify "no decisive M4 advantage" to recall/F1, acknowledging the small but reproducible specificity direction |
| A3 | §15.3 heading + body | **S3:** "is model-specific" → "appeared model-specific when only HG002 was available"; append supersession sentence pointing to §15.12; mark the mechanistic speculation as superseded, do not delete |
| A4 | §15.4 heading + body | **S4:** scope to HG002; add that on the cohort M4's specificity lead costs no recall, and that all three models miss the target |
| A5 | §14 | **S6:** extend "two cohorts" → three; add cohort extraction-failure rate (128/132,196 = 0.0968%) alongside HG002's 5/4,761 |
| A6 | §17, Code paragraph | **S7:** replace "will be added once those passes complete" with the actual cohort artifact list and checksums; state honestly that no end-to-end v0.6 artifact manifest exists |
| A7 | §15.12, accounting paragraph | **S9:** state plainly that all three models score *lower* F1 than the accept-all baseline (0.9223-0.9238 vs 0.9378) and why |

### B. Required by the literature audit (4 items)

| # | Location | Change |
|---|---|---|
| B1 | §3, "Learned SV genotyping and filtering" | **Narrow the novelty claim** per literature audit §4. Remove "rather than single-sample training" as a general contrast; replace clause (a) with the deliberate-construction + quantified-shortcut-probe wording |
| B2 | §3, same paragraph | Replace the bracketed "[Space for: prior CNN-pileup-image classifiers…]" with actual related work: DeepSVFilter (task-closest, different supervision), samplot-ML (multi-individual genotype labels, same-site examples arise incidentally), Cue (discovery/genotyping, different task). Use the three verified citations |
| B3 | §3 and/or §15 | Add the "we are not aware of" hedge for the locus-shortcut-quantification claim (uncertainty U2) — never "no prior work does" |
| B4 | Contributions block (§2) | Replace with **C1** |

### C. Conditional on Figure 8 promotion (5 items, from the Week 4 audit)

| # | Location | Change |
|---|---|---|
| C1 | §13 end | Insert the Part 4 transition above |
| C2 | §2 Introduction, layer-4 paragraph | Add forward reference to the promoted figure |
| C3 | Figure caption | Make self-contained: frozen threshold, one-shot, dotted = macro-averages, no model reaches 0.95 |
| C4 | §15.12 | Change from introducing the figure to referring back to it |
| C5 | `build_figures.py` + all cross-references | Renumber old 3→4 … 7→8, 9→10, 10→11; update output filenames and every in-text reference together |

### D. Blocked — must not be written yet

| # | Item | Blocker |
|---|---|---|
| D1 | Final Abstract | Drafted in the consistency audit, but its contribution sentence must be reconciled with C1 before insertion |
| D2 | §3 citations 1-9, 11-14 | Bibliographic verification outstanding (Manta, DELLY, LUMPY, Sniffles, pbsv, HyenaDNA, v0.6, v5.0q release, Truvari, DeepVariant, PanGenie/HGSVC2, NYGC) |
| D3 | Any statement about CSV-Filter | Uncertainty U3 — paper unread |
| D4 | Precise samplot-ML pairing comparison | Uncertainty U1 — exact statistics unverified; keep the comparison qualitative until resolved |

---

## Summary

- **Literature audit: complete.** Three primary sources read and verified; the decisive finding is that samplot-ML already trains across many individuals with genotype labels at shared sites.
- **Novelty claim: must be narrowed.** "Same-site matched supervision across many individuals rather than single-sample training" is not defensible; deliberate construction + quantified shortcut probes is.
- **Recommended contribution: C1**, the evaluation-methodology framing — the only one that costs nothing under the narrowing and aligns with Narrative B.
- **Figure 8 transition: drafted**, explicitly framing the cohort as confirmatory of a pre-stated generalisation question, not a model search.
- **16 manuscript locations identified** (7 audit, 4 literature, 5 figure-conditional), plus 4 blocked items.
- **No manuscript, pipeline, artifact, metric or test was modified or introduced.**
