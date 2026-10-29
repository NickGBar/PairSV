# Week 4 — scientific consistency audit and final framing pass

**Date:** 2026-08-08
**Audited artifact:** `paper/PAIR_SV_v1_manuscript.md` (540 lines, regenerated from four drafts)
**Authoritative evidence:** `manta_poc/cohort_final_evaluation_report.json` (`84f571b6…b3d1`), `manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json` (`3a670e20…3942`), `manta_poc/hg002_external/hg002_final_evaluation_report.json`, `manta_poc/hg002_v0.6_external/hg002_v0.6_final_evaluation_report.json`
**Manuscript modified during this audit:** **no.** This document proposes corrections; it does not apply them.

---

## Part 1 — Scientific consistency audit

### Reference table: specificity across every tier (frozen values)

Several stale claims below turn on this comparison, so it is stated once here.

| Tier | M0 | M2 | M4 |
|---|---|---|---|
| 5-person POC (LOPO, §12) | \~0.212-0.240 across models | | |
| HG002 v5.0q (§13) | 0.2739 | 0.2500 | 0.3217 |
| HG002 v0.6 (§13) | 0.1675 | 0.1626 | 0.2167 |
| **30-person cohort (§15.12)** | **0.2167** | **0.2216** | **0.2253** |

The cohort sits essentially *on* the POC estimate. **v5.0q is the high outlier, not the POC the conservative one.**

### Stale / pre-cohort claims

**S1 — §13, "Honest reporting of a genuine, non-tuned finding" paragraph (line ~344)**
*Category: HG002 result implied to generalize; specificity inference now contradicted.*
> "Specificity at the frozen threshold (25-32%) is directionally **higher than** the 5-person POC's LOPO estimate (21-24%, §12), suggesting the earlier POC-scale estimate was not overoptimistic, if anything conservative"

**Evidence:** cohort specificity is 0.2167/0.2216/0.2253 — statistically on top of the POC's 0.212-0.240, not above it. Across 30 people the POC estimate was *accurate*, and v5.0q's 0.25-0.32 was the outlier.
**Minimum correction:** keep the factual comparison, delete the inference. Replace "suggesting the earlier POC-scale estimate was not overoptimistic, if anything conservative" with a forward pointer: "§15.12 shows the 30-person cohort lands on the POC estimate (0.217-0.225), identifying this v5.0q figure as the high outlier among the three tiers rather than the POC as conservative." This is the single most important correction in the audit — the current wording draws a generalizing conclusion from n=1 that n=30 refutes.

**S2 — §15.2 heading and body (line ~412)**
*Category: written pre-cohort; also an internal arithmetic error.*
> "Four independent pieces of evidence — one statistical test on curated pairs, one development-POC calibration study, and the untouched external result — all point the same direction"

**Evidence:** the sentence enumerates **three** items while claiming four (pre-existing error), and the cohort now adds a genuine fourth. Also "no evaluation layer showing a decisive, reproducible M4 advantage over M2" is now too strong in one respect: M4's *specificity* lead is reproducible across three evaluations (§15.12), even though it is small and does not extend to recall.
**Minimum correction:** fix the count to four and enumerate them (controlled bootstrap; POC LOPO; HG002; 30-person cohort). Qualify the claim to its true scope: no layer shows a decisive M4 advantage **on recall or F1**, while M4's specificity lead is small but directionally reproducible. Do not overstate the specificity lead as a performance win.

**S3 — §15.3, entire subsection (heading + body)**
*Category: describes an HG002-specific effect in general, model-level language.*
> "### 15.3 Why M2 alone met the frozen 95% recall criterion on HG002, and M4 did not … What happened on HG002 is model-specific: M4's probability distribution shifted enough … M2's threshold transferred more faithfully."

**Evidence:** across 30 people M2 and M4 differ in macro recall by 0.000176, ~35× smaller than the between-person SD (0.0062). "Model-specific" is exactly the wrong characterisation; the effect was **person-specific**.
**Minimum correction:** retain the subsection (the HG002 numbers are real and must stay reported) but change "is model-specific" to "appeared model-specific when only HG002 was available", and append one sentence: "§15.12 shows this ordering does not replicate across 30 people; the effect was person-specific, and the mechanistic speculation below should be read as superseded." The existing hypothesis paragraph should be explicitly marked as superseded rather than deleted — deleting it would hide that the paper once entertained it.

**S4 — §15.4, entire subsection**
*Category: M4 framed purely as a specificity-for-recall trade, without cohort evidence.*
> "### 15.4 Why M4's higher specificity does not compensate for missing the recall target … A model that trades recall for specificity has not found a better point on the same curve"

**Evidence:** on the cohort M4's specificity lead comes with **no recall penalty** (M4 recall 0.9471 vs M2 0.9473). The "trade" framing was true of HG002 and is not true at population scale.
**Minimum correction:** keep the principle (a specificity gain does not substitute for a pre-registered recall target — this remains correct and important), but scope it: retitle to "…on HG002" and add: "On the 30-person cohort this trade does not appear — M4's specificity lead costs no recall relative to M2 (§15.12) — so the argument below applies to the HG002 result specifically, not to M4 in general." Also note that on the cohort *all three* models miss the target, so the argument no longer distinguishes between models.

**S5 — §15.11 (line ~450)**
*Category: correctly updated, but one clause still reads as pre-cohort.*
> "balanced across five continental superpopulations specifically to probe whether the HG002 finding (M2 meets the recall target, M4 does not) is a property of the model or a property of this one person."

**Evidence:** already followed by the added sentence "§15.12 reports the answer: it was a property of this one person." **No correction required.** Listed here only to record that it was checked and is consistent.

**S6 — §14, Error and subgroup analysis**
*Category: cohort described as absent; scope now understated.*
> "Both subgroup analyses show the same qualitative pattern independently derived on two different cohorts and two different truth sources (PanGenie 5-person POC vs GIAB v5.0q HG002)"

**Evidence:** there are now **three** cohorts and the 30-person cohort's length and breakpoint-error subgroups exist in the frozen report (`per_person.*.<model>.length_subgroups`, `breakpoint_error_subgroups`). The section also cites only HG002's extraction-failure rate.
**Minimum correction:** extend to three cohorts, and add the cohort's extraction-failure rate (128/132,196 = 0.0968%) alongside HG002's 5/4,761. If the per-person subgroup tables are to be summarised, they must be extracted programmatically, not typed.

**S7 — §17 Reproducibility (line ~3 of §17)**
*Category: describes cohort artifacts as not yet existing.*
> "The equivalent multi-cohort and v0.6 manifests will be added once those passes complete."

**Evidence:** both passes are complete. The cohort's pre-evaluation manifest exists and is checksummed; a v0.6 artifact manifest does **not** yet exist.
**Minimum correction:** state precisely what exists — `COHORT_PRE_EVALUATION_MANIFEST.json` (`3a670e20…`), `cohort_final_evaluation_report.json` (`84f571b6…`), `cohort_evaluate.py` (`6c9afb37…`), `COHORT_ONESHOT_EXECUTION_RECORD.md`, `COHORT_EVALUATION_ERRATUM.md` — and keep an explicit, honest note that a full end-to-end v0.6 artifact manifest comparable to the HG002 v5.0q one has **not** been produced. Do not claim parity that does not exist.

**S8 — §1 Abstract skeleton**
*Category: pre-cohort framing in the skeleton (already partially updated).*
**Evidence:** skeleton item (5) still presents the HG002 M2-only-clears finding without immediately flagging non-replication; item (7) is serviceable.
**Minimum correction:** superseded by the Abstract in Part 3 below, which replaces the skeleton entirely.

**S9 — §15.12 (new section) — under-stated finding, not a stale claim**
*Category: F1 treated without the prevalence caveat being drawn to its conclusion.*
> "The accept-all-Manta baseline, macro-averaged over people, has prevalence 0.8832 and F1 0.9378."

**Evidence:** the models' F1 is 0.9223-0.9238 — **lower than the accept-all baseline's 0.9378**. The manuscript states both numbers but never says this plainly, so a reader can miss that the models lose on F1.
**Minimum correction:** add one explicit sentence: "All three models therefore score *lower* F1 than indiscriminately accepting every Manta call (0.9223-0.9238 vs 0.9378) — the arithmetic consequence of trading recall for specificity at 88.3% prevalence, and the concrete vindication of §11's warning that F1 is not a meaningful discriminator in this regime." Reporting this is required by the project's own no-hiding-negative-findings rule.

### Categories checked and found clean

| Category audited | Finding |
|---|---|
| Claims that the 95% target was achieved | **None.** Every mention of the cohort states the miss. §12's POC "0.9500 macro recall" refers to the LOPO target-setting procedure, which is correct in context. |
| Cohort described as pending / in progress | **None remaining.** All `§TODO` markers resolved; evidence-tier row 8 marked complete. |
| Accidental pooling of v5.0q / v0.6 / cohort | **None.** Tier index row 7 and §13 both state "never pooled" explicitly; §15.12 compares tiers without averaging them. Wording is sound. |
| Resource claims based on POC data | **None in the manuscript.** All resource estimates live in `manta_poc/MULTICOHORT_RESOURCE_ESTIMATE.md`, which is an internal planning document and not part of the manuscript. |
| Post-hoc model selection | **None.** §13, §15.12 and §18 each state explicitly that no model is selected on results and that M4 remains predefined primary. Language is consistent. |
| F1 as primary in the balanced controlled tier (§9) | **Legitimate.** §9 uses a 1:1 by-construction design where F1 is appropriate; §11 already warns it is not appropriate at 83-90% prevalence. Only §15.12 needs the explicit statement in S9. |

**Total stale//incorrect claims requiring correction: 7** (S1, S2, S3, S4, S6, S7, S9). S5 verified clean; S8 is superseded by the new Abstract.

**Severity ranking:** S1 (a generalizing inference the cohort refutes) > S3 ≈ S4 (person-specific effects described in model-level language) > S9 (a negative finding present but not stated) > S2 (scope overreach plus a counting error) > S6, S7 (completeness/accuracy of scope and provenance).

---

## Part 2 — Three candidate central narratives

All three are consistent with the frozen evidence. They differ in what is placed at the centre.

### Narrative A — "Evidence-ladder honesty: multimodal gains are small and largely redundant"

*Central claim:* a systematic M0→M4 ladder with same-site matched supervision shows that added evidence branches beyond an image+scalar baseline contribute little; retrained ablation shows post-hoc zero-ablation overstates modality importance 5-10×.

*Strengths:* supported by the most independent evidence (controlled bootstrap, retrained ablation, POC, HG002, cohort all agree); the 5-10× ablation-methodology result is genuinely novel and reusable; makes no claim the data cannot bear.
*Weaknesses:* it is essentially a negative architectural result, and it under-uses the study's most distinctive asset — the 30-person untouched cohort. The ablation finding, though solid, is a methods contribution in a paper framed as an SV-filtering paper.

### Narrative B — "One genome is not enough: a single-genome result overturned by a 30-genome cohort"

*Central claim:* rigorous single-genome external validation (GIAB HG002, frozen, one-shot) produced a striking, publishable-looking model-ordering result — M2 clears the pre-specified 95% recall target, M4 misses it by 2.2 points — which a 30-person untouched cohort then shows does not replicate (macro recall difference 0.000176, ~35× smaller than the between-person SD). The paper's contribution is the *demonstration*, not merely the assertion, that n=1 external validation is insufficient for model-level claims.

*Strengths:* this is the study's most distinctive and most defensible finding, and it is quantified rather than asserted. It is self-critical in a way that is scientifically credible — the overturned claim is our own, and the counterfactual is explicit ("had we stopped at n=1 we would have published it"). It reframes an apparently negative result (all models miss the target) into a methodological contribution that transfers well beyond SV calling. The frozen, pre-registered, checksummed protocol is exactly what makes the demonstration airtight.
*Weaknesses:* it foregrounds a methodological lesson over a performance claim, which some venues read as a weaker contribution. It requires the reader to accept that PAIR-SV's absolute performance is modest.

### Narrative C — "A calibrated Manta deletion filter, characterised across 31 genomes and two truth sources"

*Central claim:* PAIR-SV removes ~22% of false Manta deletion candidates while retaining ~94.7% of true ones at a threshold calibrated once and never retuned, with performance characterised across 31 untouched genomes, five superpopulations and two independent truth sources.

*Strengths:* most conventional framing, easiest to position as a usable tool; the transfer consistency (SD 0.006 across 30 people) is a real and quotable strength.
*Weaknesses:* **it is the framing most at risk of overstating the work.** The headline operating point *misses* its own pre-registered target; specificity of ~22% is modest; and F1 is below the accept-all baseline. Presenting this as a deployable filter would require soft-pedalling the target miss and the AFR specificity gap — precisely the optimisation-toward-the-best-looking-result that the integrity rule forbids.

### Recommended narrative: **B**, with A as the supporting architectural result

**Reasoning.** B is the only framing whose central claim is *strengthened* rather than weakened by every awkward result in the study. The 95% target miss, the modest specificity, the v5.0q/v0.6 disagreement and the AFR gap are all liabilities under C and largely irrelevant under A — but under B they are precisely the evidence: they demonstrate how much apparent signal a single genome can manufacture and how a population sample disciplines it. B also uses the study's genuinely scarce asset (a 30-person untouched, relatedness-screened, superpopulation-balanced cohort evaluated exactly once under a pre-registered protocol), which is far harder to obtain than another architecture variant.

B additionally carries the two supporting results without strain: A's ablation-methodology finding (post-hoc zero-ablation overstates 5-10×) is the same *kind* of claim — a warning that a cheap evaluation shortcut produces inflated conclusions — so A and B reinforce each other under one thesis: **cheap evaluation shortcuts, whether post-hoc ablation or single-genome validation, systematically overstate what has been shown.** That is a coherent, defensible, and genuinely useful paper.

What B must not claim: that PAIR-SV is a validated deployable filter, or that M4 is the better model. Neither is supported.

---

## Part 3 — Abstract (final draft)

> Short-read structural-variant callers over-generate deletion candidates: a substantial fraction of PASS-filtered Manta deletion calls do not correspond to a real variant, and deciding which to trust is normally left to manual curation or hard filters. We present PAIR-SV, a candidate-aware classifier that verifies Manta deletion candidates using *same-site matched supervision* — the same locus appears as a positive example in one individual and a confidently-genotyped negative in another, so that person-specific read evidence, rather than genomic context, carries the label. PAIR-SV is a five-model ladder (M0-M4) that incrementally adds candidate REF/ALT sequence context, read-level embeddings from a frozen genomic language model, and 17 scalar read-support features on top of a dual-breakpoint pileup-image encoder, trained across 40 individuals and evaluated under a pre-registered, checksummed protocol.
>
> We report evaluations at increasing external rigour, never pooled. On an untouched internal test of curated same-site pairs, the full model M4 exceeds an image-only baseline by a small but statistically supported margin (ΔF1 +0.0049, 95% CI [+0.0014, +0.0083]), while a scalar-only variant M2 captures most of that gain and M4 does not significantly exceed M2. On real Manta output from five development individuals, a leave-one-person-out procedure fixes a deployment threshold targeting 95% recall. Applying that threshold, frozen and never retuned, to the GIAB HG002 genome — opened exactly once — M2 was the only model to reach the 95% recall target (0.9551) while M4 fell short (0.9327) with the highest specificity (0.3217).
>
> To test whether that model-ordering result generalises, we evaluated an untouched 30-person cohort (six per continental superpopulation, screened for relatedness against all prior cohorts), also exactly once, with the evaluation script checksummed before execution. **It does not replicate.** Across 30 individuals, M2 and M4 differ in macro-averaged recall by 0.000176 — roughly thirty-five times smaller than the between-person standard deviation (0.0062) — so the HG002 ordering reflected that individual's candidate population, not the models. Two results do hold: **no model reaches the pre-specified 95% recall target** (M0 0.9453, M2 0.9473, M4 0.9471, mean ± SD ≈ 0.006 across people), and M4 retains the highest specificity (0.2253 vs 0.2216 and 0.2167), the same direction observed on both HG002 truth sets. Specificity is modest throughout, and all three models score lower F1 than indiscriminately accepting every Manta call — the expected arithmetic at 88.3% candidate prevalence, and the reason F1 is not used as a primary measure here.
>
> Two limitations qualify these results. The frozen threshold transfers with high person-to-person consistency (recall range 0.928-0.962 across all 30 individuals) but sits slightly below the recall it was calibrated to reach, so a deployment claiming ~95% recall would overstate what it delivers on unseen genomes. Specificity is markedly lower for the African-ancestry group (0.174-0.183) than for the other four superpopulations (0.223-0.243); we attribute this most plausibly to weaker representation of African-ancestry haplotypes in the genotype panel supplying the truth labels rather than to the classifier itself, but our evidence cannot separate the two.
>
> The broader finding is methodological. A rigorously frozen, honestly reported single-genome external validation was sufficient to produce a striking model-ordering claim that thirty genomes then overturned; a parallel comparison shows post-hoc zero-ablation overstates each modality's marginal contribution by 5-10× relative to retrained branch-removal. Cheap evaluation shortcuts — one external genome, one ablation pass — systematically overstate what has been demonstrated. PAIR-SV verifies candidates a caller has already produced; it does not discover deletions the caller missed, and all recall figures reported here are conditional on Manta having generated the candidate.

**Compliance notes.** Every quantitative value traces to a frozen artifact via `paper/extract_cohort_numbers.py` or the cited HG002 reports. The 30-person cohort is described as a pre-registered test of a specific question (it was), while the AFR specificity gap and the specificity ordering are presented as **observations**, not as predefined hypotheses — neither was pre-specified. No model is selected or recommended; M4 remains the predefined primary model.

---

## Part 4 — Figure 8 placement recommendation

**Recommendation: promote it, conditional on adopting Narrative B. Do not move it yet.**

**Scientific argument.** Under Narrative B the paper's central claim is the *contrast* between one genome and thirty. Figure 8 is the only figure that renders that contrast as evidence: 30 people × 3 models × 2 metrics, with the 0.95 target line drawn and the macro-averages overlaid. The reader can see in a single panel (a) that the three models' recall distributions are interleaved rather than separated, which *is* the non-replication result, and (b) that the target line sits above essentially every bar, which *is* the target-miss result. Both of the paper's two surviving quantitative findings are visible simultaneously. A figure carrying the central claim should not appear tenth.

Its current position also creates a specific misreading risk: §13's HG002 result appears with figure support (Figure 7) hundreds of lines before the cohort evidence that qualifies it. A reader who skims figures encounters the overturned claim illustrated and the overturning evidence not yet seen.

**Proposed destination.** Renumber to **Figure 3**, immediately after Figure 2 (the M0-M4 architecture ladder) and *before* the controlled-benchmark results figure. Rationale: Figures 1-2 establish design and architecture; a new Figure 3 then states the principal external outcome up front, after which §9-13 can be read as the evidence chain leading to it. This is the standard "principal result early" arrangement and it matches how the paper now argues.

**Surrounding text that must change if promoted:**
1. §2 Introduction, layer-4 paragraph — add a forward reference ("Figure 3") where the cohort is introduced.
2. The figure caption must become self-contained: state that the threshold was frozen on five development individuals and never retuned, that the evaluation was one-shot, that dotted lines are macro-averages over people, and that no model reaches the 0.95 line.
3. §15.12 must change from introducing the figure to referring back to it.
4. All subsequent figure numbers shift (old 3→4 … old 7→8, old 9→10, old 10→11); `build_figures.py` output filenames and every in-text cross-reference need updating together.
5. §13 should gain a forward pointer to the promoted figure at the point where the HG002 M2/M4 ordering is first reported, so the qualification is visible where the claim is made.

**Argument against promotion, recorded for balance.** If reviewers push the paper toward Narrative C (a tool paper), the principal figure should instead be the recall/specificity operating-point figure, and Figure 8 belongs in Results. The promotion decision is therefore *contingent on the narrative decision* and should be taken together with it, not separately.

---

## Part 5 — Literature pass: unresolved references

12 `[ref]` placeholders and 1 partially-specified citation. **No citations were invented.** For each, the claim needing support and the required source type are identified. Candidate primary papers are listed **only where I have specific recall of them**, and every one is marked as requiring verification against the actual bibliographic record before submission — the risk of a misremembered year or venue is real and unacceptable in a reference list.

| # | Location | Claim requiring citation | Source type needed | Candidate (must verify) |
|---|---|---|---|---|
| 1 | §2, §3 | Manta as the caller whose candidates are filtered | Primary tool paper | Chen et al., *Bioinformatics*, 2016 — "Manta: rapid detection of structural variants and indels" |
| 2 | §3 | DELLY as a representative alternative caller | Primary tool paper | Rausch et al., *Bioinformatics*, 2012 |
| 3 | §3 | LUMPY/smoove as a representative alternative caller | Primary tool paper (+ smoove is a separate toolkit, may need its own reference or a software citation) | Layer et al., *Genome Biology*, 2014 |
| 4 | §3 | Sniffles as a long-read caller | Primary tool paper | Sedlazeck et al., *Nature Methods*, 2018 |
| 5 | §3 | pbsv as a long-read caller | **No primary paper known to exist** — likely requires a software/repository citation rather than an article | — |
| 6 | §3 | HyenaDNA as the frozen sequence encoder | Primary model paper | Nguyen et al., NeurIPS 2023 — "HyenaDNA: long-range genomic sequence modeling at single nucleotide resolution" |
| 7 | §3 | NIST SV v0.6 as the mature GRCh37 truth set | Primary benchmark paper | Zook et al., *Nature Biotechnology*, 2020 — GIAB SV benchmark |
| 8 | §3 | GIAB v5.0q Draft release | **Draft, likely no peer-reviewed paper** — cite the NIST release/FTP with version and access date; must not be cited as if peer-reviewed (§15.10 depends on this distinction) | — |
| 9 | §3 | Truvari as the SV comparison tool | Primary tool paper | English et al., *Genome Biology*, 2022 |
| 10 | §3 | "prior CNN-pileup-image classifiers for SV genotyping/filtering" — currently a bracketed *space for* text, not a placeholder tag | **Literature search required.** This is the paper's related-work positioning claim and the one genuine gap: the novelty argument for same-site matched supervision depends on establishing what prior work did | — |
| 11 | §3 | DeepVariant as the pileup-image analogy | Primary paper | Poplin et al., *Nature Biotechnology*, 2018 |
| 12 | §3 | Conformal-prediction / person-level calibration under distribution shift | Review or representative primary papers | — |
| 13 | §4 | `[ebert2021, ebler2022]` — PanGenie and HGSVC2 resource | Two primary papers, keys present but not resolved to full citations | Ebert et al., *Science*, 2021 (HGSVC2); Ebler et al., *Nature Genetics*, 2022 (PanGenie) |
| 14 | §4 | `[byrska-bishop2022]` — 1000 Genomes NYGC high-coverage set | Primary paper, key present, not resolved | Byrska-Bishop et al., *Cell*, 2022 |

**Distinguishing literature-derived from own results.** No claim in §3 currently attributes a numerical result to prior literature; all numbers in §3 are cross-references to this project's own §9-14. That separation is clean and should be preserved when citations are filled in.

**Highest-priority gap: item 10.** Everything else is a lookup. Item 10 requires an actual literature search to establish whether same-site matched supervision across individuals is genuinely novel, and the paper's contribution framing depends on the answer. If prior work has done something equivalent, the contribution claim in §2 must be narrowed accordingly. **This should be resolved before the contribution wording is finalised, not after.**

---

## Remaining scientific ambiguity

1. **AFR specificity gap — mechanism unresolved.** The paper attributes it to truth-panel representation rather than model behaviour. The evidence is consistent with that (AFR people carry the largest Unknown fractions) but does not establish it. Distinguishing the two would require a truth source with different ancestry coverage — out of scope for v1, and the paper says so. The claim as written is appropriately hedged; the ambiguity is real and should not be resolved rhetorically.

2. **v5.0q vs v0.6 disagreement — unadjudicated by design.** §15.10 offers two non-exclusive readings and prefers neither. The cohort adds indirect evidence (cohort specificity sits near the POC and v0.6 values, below v5.0q's), which mildly favours reading (a) — that v5.0q's higher specificity is the outlier. This is worth *noting* in §15.10 as a third data point, but it is not decisive: the cohort uses PanGenie truth, not GIAB, so it is not a clean arbiter between two GIAB callsets. Recommend adding one sentence, explicitly labelled as suggestive rather than conclusive.

3. **Why the frozen threshold undershoots by ~0.4 points.** The miss is small (0.9453-0.9473 vs 0.95) and highly consistent, which suggests a systematic offset between the 5-person calibration population and the 30-person target population rather than noise. The paper does not explain it, and cannot without re-opening calibration — which is forbidden. Recommend stating explicitly that the cause is uncharacterised and is a v2 question.

4. **Whether M4's specificity lead is statistically supported at cohort scale.** M4 leads on specificity across all three evaluations (direction reproducible), but the paper does not report a paired significance test across the 30 people. The frozen report contains per-person values, so a paired test **could** be computed from existing artifacts without re-running any pipeline stage. **However**, computing a new statistic after seeing results risks reading as post-hoc analysis. Recommendation: either declare it explicitly as a post-hoc descriptive test, or state the limitation plainly ("direction is consistent across three evaluations; we do not claim statistical significance for the cohort-scale specificity difference"). The second is safer and is what the current text effectively does.

---

## Summary

- **Stale/incorrect claims found: 7** (S1, S2, S3, S4, S6, S7, S9); 1 verified clean (S5); 1 superseded (S8).
- **Six categories audited clean:** achieved-target claims, pending-cohort language, truth-source pooling, POC-based resource claims, post-hoc model selection, and F1-as-primary in the balanced tier.
- **Recommended central narrative: B** — "one genome is not enough", with A's ablation-methodology result as the supporting finding under a single thesis that cheap evaluation shortcuts overstate what has been shown.
- **Figure 8: promote to Figure 3**, contingent on adopting Narrative B, with the five listed text changes. Not moved.
- **Manuscript unmodified.** No pipeline stage, model, threshold, label, or cohort membership was touched during this audit.
