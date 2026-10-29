# Evaluating a deletion-candidate classifier across 30 genomes: a single-genome result that did not replicate

**Canonical merged manuscript source — generated file, do not edit directly.**
Regenerate with `python3 paper/merge_manuscript.py` after editing any of the
four section drafts (`intro_related_work_v1_draft.md` §1-3,
`methods_v1_draft.md` §4-8, `results_v1_draft.md` §9-14,
`discussion_limitations_conclusion_v1_draft.md` §15-18). Substantive prose is
concatenated verbatim; only each draft's own status preamble is stripped in
favour of this shared block.

**Overall status (Week 3 complete, all eight evidence tiers reported).** Every
results section is filled from real, checksummed, frozen artifacts. The
untouched 30-person external cohort (evidence tier 8) has been evaluated
exactly once under the frozen protocol and is reported in §15.12; its source
report is `manta_poc/cohort_final_evaluation_report.json`
(sha256 `84f571b617025597b12d1caf55bb0ce3b18b0f021fbc58cf30e6798a0538b3d1`),
with the pre-evaluation state frozen beforehand in
`manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json`
(sha256 `3a670e207d8f3bb99a695e05c3755349fd934685b0c1ff402cfbf5d771403942`).
All §15.12 numbers were extracted programmatically by
`paper/extract_cohort_numbers.py`; none was transcribed by hand.

**Remaining open items:**

- **§3 Related Work** — no `[ref]` placeholder remains; `[software-ref]` (pbsv)
  and `[giab-v5.0q-release]` mark sources that are software and a data release
  rather than articles.
- One known erratum in a **descriptive** field of the cohort report, documented
  in `manta_poc/COHORT_EVALUATION_ERRATUM.md`. It feeds no metric and no
  reported result depends on it.

All ten manuscript figures are built reproducibly by `paper/build_figures.py`
from frozen source tables, including Figure 8, which verifies the cohort
report's SHA-256 before plotting any value.

---

## 1. Abstract

Methods that filter structural-variant calls are commonly validated on a single well-characterised genome. That practice assumes a result obtained on one individual describes how the method behaves across people. We tested that assumption on our own method.

PAIR-SV verifies deletion candidates produced by Manta. It scores a candidate using a dual-breakpoint pileup image, and in its larger variants adds candidate REF/ALT sequence context from a frozen genomic language model, read-level embeddings, and 17 scalar read-support features. Five nested variants (M0-M4) share one image encoder and differ only in which evidence branches are active. Training uses same-site matched pairs across 40 individuals: each locus contributes a positive row in a carrier and a confidently-genotyped reference row in a different person.

We evaluated at four levels, kept separate throughout: a controlled internal test on curated pairs, a 5-person development study on real Manta output that fixed a deployment threshold targeting 95% recall, one untouched genome (GIAB HG002), and an untouched 30-person cohort with six individuals per continental superpopulation, screened for relatedness against all earlier cohorts. The last two were each opened exactly once, with thresholds, metric definitions, subgroup definitions and sample inclusion fixed and checksummed beforehand.

On the 30-person cohort, macro-averaged recall at the frozen threshold was 0.9453 (M0), 0.9473 (M2) and 0.9471 (M4); specificity was 0.2167, 0.2216 and 0.2253. **None of the three models reached the pre-specified 95% recall target.** The shortfall was small and consistent across people: the between-person standard deviation was about 0.006, with all 30 individuals between 0.928 and 0.962. All three models scored lower F1 than accepting every Manta call (0.9223-0.9238 against 0.9378), which follows from 88.3% positive prevalence and is why F1 is not used as a headline metric for this tier.

On HG002, M2 had been the only model above the 95% target (0.9551) and M4 had fallen 1.7 points below it (0.9327). We had read that as a difference between the models. **It did not persist across the cohort:** M2 and M4 differ there in macro-averaged recall by 0.000176, roughly thirty-five times smaller than the between-person standard deviation. The HG002 ordering reflected that individual's candidate population. M4 had the highest specificity in all three external evaluations; we did not pre-specify a test for that difference and make no claim of significance for it, and M4 remains the primary model by prior specification rather than by these results.

The study's main contribution is therefore about evaluation rather than about model ranking: a frozen single-genome evaluation was sufficient to support a conclusion that thirty genomes did not reproduce, and a parallel comparison in the same pipeline shows post-hoc zero-ablation overstating each modality's contribution by 5-10x relative to retrained branch-removal.

Two limitations bound the scope. Specificity for the six African-ancestry individuals was 0.174-0.183, against 0.223-0.243 for the other four superpopulations, a pattern consistent with a representation effect in the genotype panel supplying the truth labels, though the analysis does not establish a cause. And the frozen threshold, while transferring consistently between people, sits below the recall it was calibrated to reach. PAIR-SV verifies candidates a caller has already produced; it does not recover deletions the caller missed, and we make no claim of clinical or deployment validity.

## 2. Introduction

Structural variant (SV) discovery from short-read whole-genome sequencing remains a two-stage problem in practice: a caller such as Manta [chen2016manta] generates candidate breakpoints from split-read, discordant-pair, and local-assembly evidence, and a second stage — often manual curation, hard filtering thresholds, or population-frequency heuristics — decides which candidates to trust. Deletions are the best-studied SV class for this problem, but callers still over-generate: a substantial fraction of PASS-filtered Manta deletion candidates do not correspond to a real variant at the queried locus, and the rate varies by length, breakpoint complexity, and local sequence context. This candidate-verification step is distinct from, and frequently conflated with, variant *discovery* — a classifier that successfully rejects false candidates cannot recover true deletions the upstream caller never proposed in the first place, and a paper reporting classifier performance without holding these two questions apart risks overstating what has been shown.

A second question sits behind the first, and it is the one this paper ends up being about. Methods of this kind are routinely validated on a single well-characterised genome — most often GIAB HG002. That practice assumes a conclusion drawn from one external genome represents how the method behaves across people. We set out to test our own method that way, and then to check the assumption by repeating the evaluation on thirty untouched individuals. The check did not confirm it.

PAIR-SV is a candidate-aware classifier for exactly this verification step. It takes a Manta deletion candidate (chromosome, breakpoints, genotype call) plus a specific individual's aligned reads and produces a probability that the candidate is a true deletion in that individual. Its architecture is a five-model ladder (M0 through M4, §6) that incrementally adds evidence: M0 uses only a dual-breakpoint pileup image; M1 adds the candidate's REF/ALT sequence context via a pretrained genomic language model (HyenaDNA); M2 adds seventeen scalar read-support features; M3 adds embedded read-level evidence; M4 fuses all three additional branches on top of the shared image encoder. The ladder is trained with *same-site matched supervision* (§5): the same candidate locus is a positive example in one individual who carries the deletion and a confidently-labeled negative example in another who does not. Within a pair, the genomic context is held constant and only the person-specific read evidence differs. This pairing requires training data spanning several individuals; §3 describes prior work that also learns from same-site examples across people.

This paper reports four progressively less controlled, more realistic layers of evidence for whether this architecture, and specifically the added evidence beyond the image-only M0 baseline, produces a measurable and *transferable* improvement:

1. **A fully controlled, held-out internal test** (§9.2) on curated same-site candidate pairs from 5 people never used in training or model selection, drawn from the same 50-person cohort used to train and validate the model. This isolates architecture quality from any distribution-shift question.
2. **A realistic-candidate development study** on 5 additional people's actual whole-genome Manta output (§11-12), used to characterize how models trained on curated pairs behave on Manta's real, unfiltered, highly imbalanced candidate stream, and to develop and validate a threshold-calibration procedure (leave-one-person-out, targeting ~95% recall) before any untouched data is examined.
3. **A single untouched external individual, GIAB HG002** (§13-14), evaluated exactly once against an independent, assembly-based truth set (GIAB v5.0q), with the calibration procedure from (2) applied unmodified — the first out-of-sample test in this study.
4. **A 30-person untouched external cohort** balanced across five continental superpopulations (§15.12), evaluated exactly once, to test whether the single-person HG002 result generalizes across ancestry, or whether it reflects properties specific to one person's variant profile. It does not: the HG002 recall ordering between M2 and M4 is not reproduced across 30 people (§15.12).

M4 is not consistently ahead of the simpler variants. On the internal test it is statistically indistinguishable from M2 (§9.2). On the 5-person POC the three models fall within 0.212-0.240 specificity at the 95%-recall operating point (§12). On HG002, M4 had the highest specificity of the three and was 1.7 points below the 95% recall target that M2 met; across 30 people that recall ordering does not persist (§15.12).

**Contributions.**

- We show, on our own pre-registered result, that a single-genome external evaluation can support a model-level conclusion that a population sample does not reproduce. On GIAB HG002, M2 was the only variant to reach the pre-specified 95% recall target and M4 fell 1.7 points below it. Across 30 untouched people that ordering does not persist (§15.12).
- We report a frozen, checksummed, one-shot evaluation protocol over eight separated evidence tiers, in which thresholds, metric definitions, subgroup definitions and sample inclusion are fixed before any label is opened. We report the resulting operating point as a miss: none of the three models reached the 95% recall target on the cohort.
- We measure a second evaluation artefact in the same pipeline: post-hoc zero-ablation overstates each modality's marginal contribution by 5-10x relative to retrained branch-removal.
- We describe a candidate-verification architecture and a deliberately constructed, balanced same-site matched-pair training design, together with quantified probes for residual locus-level shortcuts. Same-site supervision across individuals is not itself new (§3); what we add is the explicit construction and the shortcut measurement.

## 3. Related Work

**Structural variant callers.** Manta [chen2016manta], DELLY [rausch2012delly], LUMPY [layer2014lumpy], and long-read callers (Sniffles [sedlazeck2018sniffles], pbsv [software-ref]) represent the first stage of the two-stage pipeline this paper's classifier sits downstream of. This paper does not propose a new caller and does not compare against DELLY or other callers as alternative candidate sources (per the mission's own scope discipline) — PAIR-SV is evaluated exclusively as a post-hoc filter of Manta's own candidates, and any claim about PAIR-SV's performance should be read as conditional on Manta's candidate-generation recall, not as an independent measure of total deletion-detection recall (§13's explicit separation of Manta's own end-to-end recall from PAIR-SV's candidate-filtering performance is the paper's concrete instantiation of this point).

**Learned SV genotyping and filtering.** Two prior methods sit closest to this work. DeepSVFilter [liu2021deepsvfilter] filters a caller's short-read SV candidates using a CNN over a three-channel image encoding read depth, discordant pairs and split reads. Its positives are calls overlapping a truth set and its negatives are calls absent from it, so positives and negatives occupy unrelated loci; its deletion model was trained on HG002. Samplot-ML [belyeu2021samplot] classifies putative deletions from Samplot renderings using a ResNet-like network, with genotype-class labels (0/0, 0/1, 1/1) drawn from the 1000 Genomes phase-3 integrated SV map [sudmant2015sv] across many individuals. Because it genotypes catalogued sites in many people, the same site carries different labels in different individuals; the authors describe this as arising from the genotyping formulation, exclude direct relatives of their test individuals, and note that some sites still appear in both training and test. Cue [popic2023cue] converts alignments to images and predicts SV type, genotype and locus, but it discovers SVs rather than verifying a separate caller's candidates, so it addresses a different task. CSV-Filter [xia2024csvfilter] addresses the same filtering task for both short and long reads, encoding CIGAR strings as grayscale images and classifying them with a ResNet-50 pair pre-trained by self-supervision. Its positives are taken from the GIAB HG002 high-confidence callset and its negatives are generated synthetically from a length distribution, so positives and negatives again occupy unrelated loci; training and internal testing both use HG002.

**We therefore do not claim that same-site supervision across individuals is new.** Samplot-ML already learns from same-site, differently-labelled examples across many people. What PAIR-SV adds relative to this line of work is narrower: (a) the matched pairing is constructed deliberately and balanced by design — each locus contributes one positive row in a carrier and one confidently-genotyped reference row in a different individual, gated on genotype quality, callability and conflict exclusion — and residual locus-level shortcuts are then measured directly rather than assumed absent (§8); and (b) a ladder isolating each added evidence type's marginal contribution under both post-hoc and retrained ablation. We are not aware of prior SV work that quantifies a locus-memorisation shortcut in this way, though we have not reviewed the field exhaustively.

**Genomic sequence language models.** HyenaDNA [nguyen2023hyenadna] and related long-context genomic sequence models are used here purely as a fixed pretrained feature extractor for candidate REF/ALT sequence (M1/M4) and read sequence (M3/M4) embeddings — this paper does not fine-tune HyenaDNA and makes no claim about sequence-model architecture superiority; it treats the embedding as one evidence source among several and measures its marginal contribution empirically (§10), finding it modest and largely redundant with the scalar read-support branch.

**GIAB benchmarking practice.** The Genome in a Bottle Consortium's HG002 truth sets — the mature, GRCh37-native NIST SV v0.6 [zook2020giabsv] and the newer, GRCh38-native, assembly-based v5.0q Draft release [giab-v5.0q-release] — are widely used reference truth sets for SV caller benchmarking; comparisons in this paper use Truvari [english2022truvari]. This paper uses v5.0q as its primary external truth source because it is GRCh38-native (matching every other stage of this pipeline, avoiding a liftover step) and because the two differ in construction: v5.0q is derived by dipcall from a diploid assembly, whereas v0.6 was built as a consensus of read-based callers. We do not treat either construction as the more accurate one. The paper explicitly flags its Draft, not-yet-peer-reviewed status (§13, §16) and reporting the mature v0.6 as a separate, never-pooled sensitivity analysis (§13) precisely because the two callsets have different, non-interchangeable limitations (v5.0q: Draft/less field-validated; v0.6: GRCh37-only, self-reported ≤50% genome-wide SV coverage with an easier-SV bias).


---

*Sourcing note: this file contains structural/positioning prose only; every specific number referenced (e.g., "5-10x" ablation overstatement, "21-24%" specificity, "25-32%" HG002 specificity) is sourced from and must remain consistent with `results_v1_draft.md` §9-14.*

---

## Verified references

Each entry below was checked against a PubMed or publisher record. No unresolved `[ref]` placeholder remains in this section.

- **[chen2016manta]** Chen X, Schulz-Trieglaff O, Shaw R, Barnes B, Schlesinger F, Källberg M, Cox AJ, Kruglyak S, Saunders CT. Manta: rapid detection of structural variants and indels for germline and cancer sequencing applications. *Bioinformatics.* 2016;32(8):1220-2. doi:10.1093/bioinformatics/btv710. PMID: 26647377
- **[english2022truvari]** English AC, Menon VK, Gibbs RA, Metcalf GA, Sedlazeck FJ. Truvari: refined structural variant comparison preserves allelic diversity. *Genome Biology.* 2022;23:271. doi:10.1186/s13059-022-02840-6. PMID: 36575487
- **[nguyen2023hyenadna]** Nguyen E, Poli M, Faizi M, Thomas A, Wornow M, Birch-Sykes C, Massaroli S, Patel A, Rabideau C, Bengio Y, Ermon S, Ré C, Baccus S. HyenaDNA: long-range genomic sequence modeling at single nucleotide resolution. *Advances in Neural Information Processing Systems 36* (NeurIPS 2023):43177-43201
- **[zook2020giabsv]** Zook JM, Hansen NF, Olson ND, Chapman L, Mullikin JC, Xiao C, Sherry S, Koren S, Phillippy AM, Boutros PC, Sahraeian SME, Huang V, Rouette A, Alexander N, Mason CE, Hajirasouliha I, Ricketts C, Lee J, Tearle R, Fiddes IT, Martinez Barrio A, Wala J, Carroll A, Ghaffari N, Rodriguez OL, Bashir A, Jackman S, Farrell JJ, Wenger AM, Alkan C, Soylev A, Schatz MC, Garg S, Church G, Marschall T, Chen K, Fan X, English AC, Rosenfeld JA, Zhou W, Mills RE, Sage JM, Davis JR, Kaiser MD, Oliver JS, Catalano AP, Chaisson MJP, Spies N, Sedlazeck FJ, Salit M. A robust benchmark for detection of germline large deletions and insertions. *Nature Biotechnology.* 2020;38(11):1347-1355. doi:10.1038/s41587-020-0538-8. PMID: 32541955
- **[liu2021deepsvfilter]** Liu Y, Huang Y, Wang G, Wang Y. A deep learning approach for filtering structural variants in short read sequencing data. *Briefings in Bioinformatics.* 2021;22(4):bbaa370. doi:10.1093/bib/bbaa370. PMID: 33378767
- **[belyeu2021samplot]** Belyeu JR, Chowdhury M, Brown J, Pedersen BS, Cormier MJ, Quinlan AR, Layer RM. Samplot: a platform for structural variant visual validation and automated filtering. *Genome Biology.* 2021;22:161. doi:10.1186/s13059-021-02380-5. PMID: 34034781
- **[popic2023cue]** Popic V, Rohlicek C, Cunial F, et al. Cue: a deep-learning framework for structural variant discovery and genotyping. *Nature Methods.* 2023;20:559-568. doi:10.1038/s41592-023-01799-x
- **[xia2024csvfilter]** Xia Z, Xiang W, Wang Q, Li X, Li Y, Gao J, Tang T, Yang C, Cui Y. CSV-Filter: a deep learning-based comprehensive structural variant filtering method for both short and long reads. *Bioinformatics.* 2024;40(9):btae539. doi:10.1093/bioinformatics/btae539
- **[ebert2021]** Ebert P, Audano PA, Zhu Q, Rodriguez-Martin B, Porubsky D, et al. Haplotype-resolved diverse human genomes and integrated analysis of structural variation. *Science.* 2021;372(6537):eabf7117. doi:10.1126/science.abf7117. PMID: 33632895
- **[rausch2012delly]** Rausch T, Zichner T, Schlattl A, Stütz AM, Benes V, Korbel JO. DELLY: structural variant discovery by integrated paired-end and split-read analysis. *Bioinformatics.* 2012;28(18):i333-i339. doi:10.1093/bioinformatics/bts378. PMID: 22962449
- **[layer2014lumpy]** Layer RM, Chiang C, Quinlan AR, Hall IM. LUMPY: a probabilistic framework for structural variant discovery. *Genome Biology.* 2014;15(6):R84. doi:10.1186/gb-2014-15-6-r84. PMID: 24970577
- **[sedlazeck2018sniffles]** Sedlazeck FJ, Rescheneder P, Smolka M, Fang H, Nattestad M, von Haeseler A, Schatz MC. Accurate detection of complex structural variations using single-molecule sequencing. *Nature Methods.* 2018;15(6):461-468. doi:10.1038/s41592-018-0001-7. PMID: 29713083
- **[byrska-bishop2022]** Byrska-Bishop M, Evani US, Zhao X, Basile AO, Abel HJ, Regier AA, Corvelo A, Clarke WE, Musunuri R, Nagulapalli K, Fairley S, Runnels A, Winterkorn L, Lowy E, Flicek P, Germer S, Brand H, Hall IM, Talkowski ME, Narzisi G, Zody MC. High-coverage whole-genome sequencing of the expanded 1000 Genomes Project cohort including 602 trios. *Cell.* 2022;185(18):3426-3440.e19. doi:10.1016/j.cell.2022.08.004. PMID: 36055201
- **[sudmant2015sv]** Sudmant PH, Rausch T, Gardner EJ, Handsaker RE, Abyzov A, Huddleston J, Zhang Y, Ye K, et al.; 1000 Genomes Project Consortium. An integrated map of structural variation in 2,504 human genomes. *Nature.* 2015;526(7571):75-81. doi:10.1038/nature15394. PMID: 26432246
- **[ebler2022]** Ebler J, Ebert P, Clarke WE, Rausch T, Audano PA, Houwaart T, Mao Y, Korbel JO, Eichler EE, Zody MC, Dilthey AT, Marschall T. Pangenome-based genome inference allows efficient and accurate genotyping across a wide spectrum of variant classes. *Nature Genetics.* 2022;54(4):518-525. doi:10.1038/s41588-022-01043-w. PMID: 35410384

**Non-article sources.** `[giab-v5.0q-release]` is a NIST data release, not a peer-reviewed publication, and must be cited with its version and access date; §15.10's Draft-status argument depends on this distinction. `[software-ref]` marks pbsv, for which no primary publication was identified; it should be cited as software.

**Still unresolved.** No primary publication was identified for `smoove`, so it was removed from the callers sentence rather than attributed to the LUMPY paper. The `≤50% genome-wide SV coverage` figure in this section is quoted from the v0.6 release README, not from [zook2020giabsv]; it needs a release-level citation of the kind used for `[giab-v5.0q-release]`, which has not been added. `byrska-bishop2022` is cited in §4 and its entry below is complete apart from the full author list.

---

## 4. Controlled multisample dataset

Candidate deletions and their same-site negatives were drawn from 50 unrelated individuals sequenced to high coverage (30x) by the expanded 1000 Genomes Project NYGC alignment set [byrska-bishop2022], aligned to GRCh38. Silver-standard genotype labels came from the HGSVC2 PanGenie-derived pangenome genotyping resource [ebert2021, ebler2022] (`pangenie_merged_bi_nosnvs.vcf.gz`, 3,202 samples).

The 50 people were split by person, before any extraction, into 40 train / 5 validation / 5 internal-test, with no person appearing in more than one split:

- Train (40): HG00096, HG00097, HG00099, HG00100, HG00101, HG00102, HG00103, HG00105, HG00403, HG00404, HG00406, HG00407, HG00409, HG00410, HG00419, HG00421, HG00551, HG00553, HG00554, HG00637, HG00638, HG00640, HG00641, HG00731, HG01583, HG01586, HG01589, HG01593, HG01879, HG01880, HG01882, HG01883, HG01885, HG01886, HG01889, HG01890, HG02490, HG02491, HG02493, HG02494.
- Validation (5): HG00106, HG00422, HG00732, HG01894, HG02597.
- Internal test (5, held untouched until one evaluation — see §7): HG00107, HG00428, HG00734, HG01896, HG02600.

A strict manifest of 100,000 sample-candidate rows (50,000 positive / 50,000 negative, exactly balanced by construction) was built from 12,272 same-site candidate pairs across the 50 people, gated on: schema/GT/GQ/FILTER validity, callability, genotype-conflict exclusion, coordinate consistency, and person-split integrity (`multisample_progress.md` R14). Positives require a non-missing 0/1 or 1/1 genotype with GQ>=20; negatives require a callable, conflict-free, non-missing 0/0 genotype at the identical locus in a different person (see §5). Deletions are sequence-resolved, 50-10,000bp, on autosomes only, with unambiguous GRCh38 coordinates.

CRAM feature extraction was run per shard (8 shards of 10,000 rows for train, one shard of 10,000 rows for validation, drawing 5 people per shard). Extraction succeeded for 79,801/80,000 attempted training rows (199 failures, 0.25%; class balance in the successful set: 39,842 positive / 39,959 negative) and 9,981/10,000 validation rows (19 failures, 0.19%). The internal-test extraction (§7) succeeded for 9,978 rows. Failures are retained as an explicit accounting category (`CandidateExtractionError`, predominantly empty reads at one or both breakpoints), never silently dropped.

Each successful row contains two `(6,64,128)` uint8 breakpoint pileup images, up to 48 selected read tokens per breakpoint with masks, 17 scalar read-support features, and deduplicated 1,024bp candidate REF/ALT sequence context. The six image channels encode base identity, base quality, mapping quality, strand, alignment state, and alternate-allele evidence. Sample identity, population label, split assignment, genotype quality, allele frequency, negative-type, source shard, and read-name hash are excluded from every model input tensor by construction (see §8 for the metadata-leakage check that verifies this exclusion is effective).

The Train40 snapshot is checksummed end to end: each of the 8 training shards has an independent SHA-256, and the full snapshot has a content fingerprint SHA-256 (`916bbcbdd54d5e34a345be2449373bef621b8cbb8e0ccfd53821b866215a1d33`, `train40_snapshot.json`) computed before any model saw the data.

| Dataset composition | Value |
|---|---|
| Total people | 50 (40 train / 5 validation / 5 internal test), person-disjoint |
| Strict manifest | 100,000 sample-candidate rows, 50,000/50,000 balanced by construction, 12,272 same-site candidate pairs |
| Train extraction | 79,801/80,000 successful (0.25% failure); 39,842 positive / 39,959 negative |
| Validation extraction | 9,981/10,000 successful (0.19% failure) |
| Internal-test extraction | 9,978 successful (§7) |
| Deletion length range | 50-10,000bp, sequence-resolved, autosomal |
| Snapshot integrity | per-shard + whole-snapshot SHA-256 fingerprint, computed pre-training |


![Figure 1. Study design and cohort separation.](figures/fig1_study_design_cohort_separation.png)

**Figure 1. Study design and cohort separation.** Four person-disjoint evidence tiers: a 50-person controlled benchmark (40 train / 5 validation / 5 internal test), a 5-person realistic-candidate development study, GIAB HG002, and the untouched 30-person cohort (6 per continental superpopulation). Membership and family IDs were screened so that no person or family appears in more than one tier.

## 5. Same-site matched supervision

The central design choice of the dataset is that a candidate deletion's genomic locus (chromosome, coordinates, REF/ALT sequence context) is never unique to its label. Each same-site candidate pair places the identical locus twice in the manifest: once as a positive row (an individual with a confident 0/1 or 1/1 genotype at that site) and once as a negative row (a different individual with a confident, callable, conflict-free 0/0 genotype at the same site). The candidate REF/ALT sequence context and coordinate representation are therefore held constant within a matched pair — only the person-specific read evidence (the two breakpoint pileups, the selected reads, and the 17 scalar support features) differs between the positive and negative row of a pair.

This is a deliberate attempt to reduce the value of locus memorization as a shortcut: a model that only learned "this genomic coordinate is usually a real deletion" cannot separate the two rows of a same-site pair, since they share that coordinate. It does not eliminate every locus-related shortcut (e.g. the model still sees the reference and hypothesized-alternate sequence context, which is locus-determined), which is why the leakage probes in §8 test residual locus/metadata signal directly rather than relying on the same-site design alone as proof.

## 6. PAIR-SV architecture

PAIR-SV frames deletion verification as binary classification of a pre-selected, sequence-resolved candidate, not variant discovery. Five nested variants share a tied dual-breakpoint image encoder and differ only in which additional evidence branches are active, isolating each modality's marginal contribution under an otherwise identical architecture, optimizer, and training protocol:

| Variant | Images | Candidate REF/ALT | Sample reads | Scalars | Parameters (frozen, seed 20260720) |
|---|:---:|:---:|:---:|:---:|---:|
| M0 | yes | no | no | no | 287,618 |
| M1 | yes | yes | no | no | 487,300 |
| M2 | yes | no | no | yes | 323,110 |
| M3 | yes | no | yes | no | 420,740 |
| M4 | yes | yes | yes | yes | 622,374 |

The tied image encoder processes the left- and right-breakpoint pileups with shared convolutional weights, producing paired features plus their absolute difference and elementwise product. Candidate context (M1, M4) uses the 1,024bp REF and hypothesized-ALT sequence, encoded by a frozen HyenaDNA model (`LongSafari/hyenadna-small-32k-seqlen-hf`, pinned revision `8fe770c78eb13fe33bf81501612faeddf4d6f331`, 3,277,568 parameters) into REF, ALT, ALT-REF, |ALT-REF|, and junction embeddings (each 256-dimensional, 1,280-dimensional total). Sample reads (M3, M4) select up to 48 reads per breakpoint, tokenize to 128 bases, encode with the same frozen HyenaDNA model, and mask-aware mean-pool per side to a 768-dimensional left/right/|left-right| representation. The 17 scalar features (M2, M4) summarize clipping and split-read support, discordant-pair evidence, depth, mapping and base quality, insert-size anomaly, breakpoint balance, and log deletion length. Fusion is residual and late: additional branches are added on top of the image path in a way that preserves the image-only forward pass at initialization, so any measured gain reflects learned use of the added evidence rather than a change in the model's starting point.


![Figure 2. The M0-M4 evidence ladder.](figures/fig2_architecture_ladder.png)

**Figure 2. The M0-M4 evidence ladder.** Five nested variants share one tied dual-breakpoint image encoder and differ only in which evidence branches are active. Parameter counts are from the frozen seed-20260720 checkpoints. Fusion is residual and late, so each added branch preserves the image-only forward pass at initialization.

All 5 variants were trained with 3 independent seeds (20260720, 20260721, 20260722), 5 epochs, AdamW (learning rate 2×10⁻⁴, weight decay 10⁻⁴), batch size 16, mixed precision, cross-entropy loss — identical across variants and seeds, so that differences in outcome are attributable to the evidence branches, not to protocol variation. Per-model training time was ~2,400-2,470s per seed on the training infrastructure used.

## 7. Training and frozen evaluation protocol

Normalization statistics (scalar feature mean/std, candidate/read embedding mean/std) were fit on training people only, never on validation or test data. For each (model, seed), the checkpoint and decision threshold were selected by validation-set F1 across the 5 training epochs — this makes the validation-set numbers reported in §9 model-selection evidence, not an unbiased held-out estimate, and they are reported as such rather than conflated with the internal-test result.

Every frozen artifact — 15 checkpoints (5 models × 3 seeds), normalization statistics, decision thresholds, and the training/evaluation code itself (`deepsv/models/pairsv.py`, `deepsv/multisample/dataset.py`) — was checksummed (SHA-256) and locked (`reports/train40/frozen_checkpoint_checksums.json`) before the internal test was touched.

**The internal test was accessed exactly once.** All 5 models × 3 seeds were scored against the 5 held-out test people in a single pass (`evaluate_test_predictions.py`), joining predictions with labels for the first time only after every upstream artifact (checkpoints, thresholds, normalization, matching parameters, evaluation code) was already frozen. No threshold, feature, checkpoint, or hyperparameter was touched after this evaluation. The internal test remains permanently closed to further model development for PAIR-SV v1; a v2 model (if built) would be evaluated only on a new, separate cohort, never against this test set.

## 8. Leakage and quality-control checks

Three probes were run on the strict 100,000-row manifest before any model training, to test whether label information leaks through channels other than genuine read evidence:

| Probe | Result | Interpretation |
|---|---|---|
| Metadata-only classifier (identity/source-file-adjacent fields) AUC | 0.57484 | Below the pre-registered 0.65 ceiling — some residual signal exists in incidental metadata, but far from label-determining |
| Allele-frequency-only classifier AUC (train) | 0.50001 | Indistinguishable from chance |
| Allele-frequency-only classifier AUC (validation) | 0.50056 | Indistinguishable from chance |
| Train-locus prior applied to validation rows, AUC | 0.53066 | Modest — a classifier that only memorized which loci were positive in training generalizes only weakly to validation, consistent with the same-site design (§5) limiting but not eliminating locus shortcuts |

These checks gate every downstream result: had any probe exceeded its pre-registered ceiling, the manifest itself (not just a model) would have required revision before proceeding to training. All four passed their pre-registered thresholds.

Model input tensors exclude, by construction, sample identity, population label, split assignment, genotype quality, allele frequency, negative-type flag, source shard/file, and read-name hash (§4) — the metadata-probe result above is the direct empirical check that this exclusion is effective, not merely declared.

---

*Sourcing note for reviewers/co-authors: every number in this document traces to a specific file under version control — `train40_snapshot.json` (dataset composition, checksums), `reports/train40/` (training-time/validation metrics, frozen checkpoint checksums), `reports/test_evaluation/` (internal-test results, referenced in §7 but reported in §9, not drafted here), and `multisample_progress.md` (leakage-probe run log, entry R14). No number here was estimated, rounded from memory, or carried over from the Train15 interim report.*

---

## Evidence-tier index

This manuscript reports evidence at eight progressively less controlled, more realistic tiers. They are never pooled or averaged into a single headline number — each answers a different question, and conflating them (e.g., quoting a controlled-benchmark F1 as if it were the external-validation result) would misrepresent what has actually been shown. This index exists specifically so no tier's result can be mistaken for another's.

| # | Tier | People | Candidate source | Truth source | Section | Status |
|---|---|---|---|---|---|---|
| 1 | Controlled validation | 5 val (of 50) | curated same-site pairs | PanGenie silver-standard | §9.1 | complete — **not** an unbiased estimate (used for model/threshold selection) |
| 2 | Untouched internal test | 5 test (of 50), never used for selection | curated same-site pairs | PanGenie silver-standard | §9.2 | complete — the controlled-benchmark headline result, accessed exactly once |
| 3 | Retrained ablations | same 5 test | curated same-site pairs | PanGenie silver-standard | §10 | complete — retrained branch-removal vs. post-hoc zero-ablation, both reported |
| 4 | Realistic-candidate development POC | 5 (HG00108/HG01912/HG00736/HG00436/HG02601), excluded from every other tier | real whole-genome Manta output | two-pass PanGenie (carrier + reference-check) | §11 | complete — characterizes curated-vs-real calibration shift |
| 5 | Frozen LOPO calibration | same 5 | real Manta output | same two-pass PanGenie | §12 | complete — the threshold-selection procedure later frozen and reused unmodified in tiers 6-8 |
| 6 | Untouched HG002 external validation (primary) | 1 (HG002), never used elsewhere | real whole-genome Manta output | GIAB v5.0q GRCh38 (Draft, assembly-based) | §13 | complete — opened exactly once |
| 7 | HG002 sensitivity pass (secondary) | HG002, separate GRCh37 alignment/pipeline | real whole-genome Manta output | NIST SV v0.6 Tier1 GRCh37 (mature, incomplete) | §13 | complete — **never pooled** with tier 6; reported as agreement/disagreement, not averaged |
| 8 | Untouched multi-person external cohort | 30 (6 per superpopulation), never used elsewhere | real whole-genome Manta output | two-pass PanGenie | §15.12 | **complete — opened exactly once**; all 30 selected people completed the pipeline with no replacement, pre-evaluation state frozen in `manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json`, result in `manta_poc/cohort_final_evaluation_report.json` (sha256 `84f571b6…b3d1`) |

Tiers 1-3 use the same 50-person controlled cohort (disjoint train/val/test splits) and curated same-site candidate pairs — they measure architecture quality in isolation from any real-world candidate-distribution shift. Tiers 4-5 introduce real, unfiltered Manta output for the first time, on people still excluded from every controlled-benchmark split, and exist specifically to characterize and correct for the resulting calibration shift (§15.7) before any untouched data is examined. Tiers 6-8 are the actual untouched external evidence: single-person (6-7) and population-level (8), primary-truth-source (6) and sensitivity-analysis (7), all using the tier-5 calibration procedure completely unmodified.

---

## 9. Controlled benchmark results

### 9.1 Validation-time model selection (not an unbiased estimate — see §7)

Across 3 seeds, validation F1 was closely clustered across all 5 variants (0.8113-0.8161 mean), with M4 highest and M3 lowest:

| Model | F1 (mean±sd) | ROC-AUC (mean) | PR-AUC (mean) | MCC (mean) |
|---|---|---|---|---|
| M0 | 0.8130±0.0020 | 0.8972 | 0.9075 | 0.6148 |
| M1 | 0.8135±0.0023 | 0.8997 | 0.9088 | 0.6133 |
| M2 | 0.8121±0.0020 | 0.8994 | 0.9091 | 0.6144 |
| M3 | 0.8142±0.0020 | 0.8982 | 0.9075 | 0.6120 |
| M4 | 0.8146±0.0008 | 0.9011 | 0.9097 | 0.6162 |

This is model-selection evidence (checkpoint/threshold chosen by validation F1, §7) — reported for completeness, not as the headline result.

### 9.2 Internal one-shot test (the controlled-benchmark result — accessed exactly once, §7)

3-seed mean, 5 models, 9,978 test rows (5 held-out people: HG00107, HG00428, HG00734, HG01896, HG02600):

| Model | Precision | Recall | F1 | ROC-AUC | PR-AUC | MCC |
|---|---|---|---|---|---|---|
| M0 | 0.7770±0.0220 | 0.8502±0.0253 | **0.81127**±0.0044 | 0.8982 | 0.9063 | 0.6091 |
| M1 | 0.7760±0.0035 | 0.8523±0.0071 | **0.81233**±0.0030 | 0.8996 | 0.9073 | 0.6100 |
| M2 | 0.7905±0.0088 | 0.8414±0.0083 | **0.81506**±0.0017 | 0.9012 | 0.9087 | 0.6203 |
| M3 | 0.7709±0.0070 | 0.8589±0.0033 | **0.81248**±0.0025 | 0.8991 | 0.9068 | 0.6083 |
| M4 | 0.7831±0.0073 | 0.8523±0.0109 | **0.81613**±0.0014 | 0.9018 | 0.9083 | 0.6194 |

M4 has the highest mean F1, ROC-AUC, and MCC; M2 is a close second and has the highest mean precision. **M0's cross-seed F1 standard deviation (0.0044) is markedly higher than every fusion variant's (0.0014-0.0030)** — the image-only baseline is less stable across random seeds than any variant with additional evidence branches, a secondary but notable finding in its own right.


![Figure 3. Controlled benchmark: validation-time selection versus the untouched internal test.](figures/fig3_controlled_and_internal_test.png)

**Figure 3. Controlled benchmark: validation-time selection versus the untouched internal test.** F1 as 3-seed mean with standard deviation, for all five variants. Validation numbers (left) were used to select checkpoints and thresholds and are not an unbiased estimate; the internal test (right) was opened once.

**Candidate-cluster bootstrap** (2,000 resamples, 4,260 unique candidate clusters — not row-level, since candidates recur across the same-site design; this is the statistically appropriate unit given §5):

| Comparison | ΔF1 (mean) | 95% CI | Win proportion | Conclusion |
|---|---|---|---|---|
| M4 − M0 | +0.00490 | [+0.00139, +0.00832] | 0.997 | **excludes zero** |
| M2 − M0 | +0.00379 | [+0.00097, +0.00674] | 0.9955 | **excludes zero** |
| M1 − M0 | +0.00110 | [−0.00151, +0.00385] | 0.786 | crosses zero |
| M3 − M0 | +0.00121 | [−0.00184, +0.00425] | 0.7885 | crosses zero |
| M4 − M2 | +0.00106 | [−0.00227, +0.00433] | 0.741 | crosses zero |

**Interpretation, precisely stated:** M4 and M2 both significantly exceed the image-only baseline M0. **M4 does not significantly exceed M2** (CI crosses zero) — the scalar read-support branch alone captures most of the measurable improvement over M0; adding candidate-sequence and read-embedding evidence on top of it (the difference between M2 and M4) does not demonstrate a further, statistically supported gain on this test set. Single-modality-addition variants M1 (candidate sequence only) and M3 (read embeddings only) do not significantly exceed M0 alone.

**50-200bp length-restricted candidate-cluster bootstrap** (2,798 clusters): M4 − M0 ΔF1 +0.00351, 95% CI [−0.00051, +0.00782], win proportion 0.948 — **borderline, does not clear the 95% threshold**. No evidence that fusion (M4) helps disproportionately on short deletions specifically, contrary to a plausible a priori hypothesis that short-deletion pileups might benefit most from additional sequence/read evidence.

**Leave-one-person-out stability** (F1 mean with each of the 5 test people excluded in turn): all 5 models are stable, standard deviation across the 5 leave-one-out estimates ranging 0.0013-0.0024 model, indicating the headline result does not hinge on any single test person.

**Same-site-negative specificity** (test set, frozen threshold): M2 highest (0.7775 mean), M3 lowest (0.7455 mean) — the scalar branch (present in M2 and M4) is specifically associated with better same-site-negative rejection, consistent with §10's branch-dependence finding.

## 10. Ablation methodology and results

Two distinct ablation designs were used. Their results measure different things and are reported separately:

1. **Post-hoc perturbation** (zero and shuffle) of a single frozen M4 checkpoint's inputs at inference time, no retraining. Cheap, but the model was never trained to be robust to the perturbed distribution, so effect sizes can be inflated by pushing the model out of its training distribution rather than by removing genuine information content.
2. **Retrained branch-removal** — M4_NO_CANDIDATE, M4_NO_READ, M4_NO_SCALAR: the corresponding branch structurally removed from the architecture and the model retrained from scratch with the same protocol (3 seeds, 5 epochs) as every other variant. This measures the branch's marginal contribution when the rest of the network is allowed to compensate, which is what actually matters for an architecture decision.

### 10.1 Post-hoc zero-ablation (single frozen M4 checkpoint, validation set, 3 seeds)

| Intervention | ΔF1 (mean) | ΔROC-AUC | ΔPR-AUC |
|---|---|---|---|
| candidate_zero | −0.00543±0.0014 | −0.0041 | −0.0025 |
| read_zero | −0.00751±0.0021 | −0.0069 | −0.0049 |
| scalar_zero | **−0.01002**±0.0017 | −0.0106 | −0.0103 |

Scalar zeroing produces the largest drop; shuffle interventions were directionally unstable (e.g. `scalar_shuffle` *increased* F1 by +0.0301 in the single-seed diagnostic run investigating the `mean_abs_insert_size` pathology — see the Discussion/Limitations section for the scalar-normalization defect this anomaly led to identifying) and are not treated as reliable ablation evidence.

### 10.2 Retrained branch-removal (validation set, 3 seeds — the methodologically preferred design)

| Variant | ΔF1 vs full M4 (mean) |
|---|---|
| M4_NO_CANDIDATE | −0.00107 |
| M4_NO_READ | −0.00072 |
| M4_NO_SCALAR | −0.00151 |

### 10.3 Post-hoc zero-ablation overstates branch importance by ~5-10x relative to retrained removal

Directly comparing the two designs' F1 drops for the same three branches:

| Branch | Post-hoc zero ΔF1 | Retrained-removal ΔF1 | Ratio (overstatement) |
|---|---|---|---|
| Candidate | −0.00543 | −0.00107 | **5.1x** |
| Read | −0.00751 | −0.00072 | **10.5x** |
| Scalar | −0.01002 | −0.00151 | **6.6x** |


![Figure 4. Post-hoc zero-ablation compared with retrained branch-removal.](figures/fig4_zero_ablation_vs_retrained.png)

**Figure 4. Post-hoc zero-ablation compared with retrained branch-removal.** ΔF1 for removing each of the three added branches, measured two ways. Annotations give the ratio between the two designs: post-hoc zeroing yields drops 5.1x (candidate), 10.5x (read) and 6.6x (scalar) larger than retraining the model without that branch.

This is the primary ablation finding: **naive post-hoc zero-ablation overstates each modality's true marginal contribution by roughly 5-10x** relative to a properly retrained branch-removal control. The retrained-removal numbers themselves are small (0.07-0.15 F1 percentage points per branch) — consistent with the branches being **largely redundant with each other rather than strongly additive**, and consistent with §9.2's finding that M4 does not significantly exceed M2 on the internal test. Neither ablation design provides evidence that any single added modality is strictly necessary; each contributes a small, measurable, but individually modest amount, and removing any one is largely compensated for by the rest of the network.

No evidence was found (§9.2, 50-200bp bootstrap) that fusion (M4) preferentially benefits short (50-200bp) deletions specifically, despite this being a plausible a priori hypothesis for why additional sequence/read evidence might matter most.

---

## 11. Realistic Manta-candidate benchmark (5-person development POC)

**This is a development POC result, not the final external validation.** It uses 5 people (HG00108, HG00436, HG00736, HG01912, HG02601) whose PanGenie-based truth was already available during model/threshold development (Phase F, decisions 0037-0041) — they are explicitly excluded as an external test set (see §7 and the hard constraints in `paper/PUBLICATION_LEDGER.md`). Its purpose here is to characterize how the controlled-benchmark models behave on **realistic, unfiltered Manta candidates** (as opposed to the curated same-site pairs of §9) and to validate the LOPO calibration procedure that is then applied, unmodified, to the untouched external cohort in §13.

Manta was run whole-genome on each of the 5 people and its PASS DEL candidates were matched against two-pass PanGenie truth (carrier and reference-check Truvari passes; positive / known_negative / unknown labels — see `manta_poc/truvari_gate2/gate2_pipeline.py`). Candidate composition:

| person | positive | known_negative | unknown | confidently-labeled fraction |
|---|---|---|---|---|
| HG00108 | 2,957 | 326 | 867 | 0.791 |
| HG00436 | 2,936 | 347 | 886 | 0.788 |
| HG00736 | 2,945 | 375 | 847 | 0.797 |
| HG01912 | 3,011 | 629 | 1,278 | 0.740 |
| HG02601 | 3,026 | 339 | 903 | 0.788 |

HG01912 (ACB/AFR) shows a visibly larger known-negative/unknown fraction, consistent with a known population effect (more divergence from a European-reference-derived panel, more sites outside PanGenie's coverage) rather than a processing anomaly.

**Accept-all-Manta baseline** (label every PASS DEL positive — the naive floor any model must beat): recall=1, specificity=0 by construction; precision/F1 are already high (0.83-0.90 precision, 0.90-0.95 F1) purely because prevalence is high, which is why **F1 is not a useful discriminator here** — a model must be judged on how much it can shrink specificity's floor while holding recall near-fixed, which is exactly what §11's LOPO calibration (below) measures, not on F1 alone.

**Frozen-threshold transfer** (applying the Train40-controlled-benchmark operating point unmodified to Manta candidates): specificity collapses to 4-7% (predicted-positive rate 98-99%) across all three models and all three seeds, while ROC-AUC stays stable at 0.75-0.76. The controlled-benchmark threshold does not transfer to the realistic candidate distribution — but the underlying ranking remains informative (ROC-AUC well above chance), meaning the threshold, not the model's discrimination, is what needs recalibrating for this distribution shift.


![Figure 5. Threshold transfer from curated pairs to real Manta candidates.](figures/fig5_calibration_shift.png)

**Figure 5. Threshold transfer from curated pairs to real Manta candidates.** Applying the controlled-benchmark operating point unmodified to real candidates drives specificity to 4-7%; leave-one-person-out recalibration on the 5-person development study restores it to 21-24% at the ~95% recall target. ROC-AUC is stable across both settings.

## 12. Person-level LOPO calibration — the primary POC-scale result

Leave-one-person-out (LOPO): a threshold is selected on 4 of the 5 people (holding macro recall at a target level across their pooled positives), then applied unmodified to the 5th, held-out person. Repeated for all 5 held-out people × 3 models (M0/M2/M4) × 3 seeds × 3 target recall levels (99/95/90%) — 135 total folds.

**Primary operating point: 95% target recall**

| model | seed | recall macro (worst fold) | specificity macro (range) |
|---|---|---|---|
| M0 | mean of 3 seeds | 0.9497 (0.9415 worst) | 0.224 (0.182-0.264) |
| M2 | mean of 3 seeds | 0.9500 (0.9416 worst) | 0.222 (0.182-0.264) |
| M4 | mean of 3 seeds | 0.9500 (0.9415 worst) | 0.222 (0.175-0.295) |

All 45 held-out folds (5 people × 9 model×seed combinations) hold macro recall within 0.9415-0.9504 of the 0.95 target and **none falls to specificity ≤ 0.10** — a threshold selected on 4 people transfers to the 5th without failure in every fold tested. At the conservative 99%-recall setting specificity drops to 5-7% (0/45 folds exceed the 0.10 floor); at the more aggressive 90%-recall setting specificity rises to 35-38% — a monotonic, gap-free recall/specificity trade-off consistent with a stable, content-driven ranking rather than noise.


![Figure 6. Leave-one-person-out calibration on the 5-person development study.](figures/fig6_lopo_recall_specificity.png)

**Figure 6. Leave-one-person-out calibration on the 5-person development study.** Macro recall against macro specificity at the 95% target, one point per frozen seed and model. The dashed line marks the 95% recall target used to select the deployment thresholds.

**Decision-rule check against the predefined Phase F criteria (all satisfied, not marginally):**

| criterion | threshold | worst observed | status |
|---|---|---|---|
| macro held-out recall | ≥ 0.93 | 0.9496 | met |
| macro specificity | ≥ 0.20 | 0.2124 | met |
| people with specificity > 0.10 | ≥ 4/5 | 5/5 (all 9 combos) | met |
| individual-person held-out recall | ≥ 0.90 | 0.9415 | met |
| ROC-AUC above chance | — | 0.748-0.764 | met |

This did not reach the "strong success" bar of the pre-registered decision rule (30-40% specificity at ~95% recall; the label is the rule's own) — actual macro specificity is 21-24%, below that bar. **Verdict: 0.4A** — calibration without retraining is sufficient; PAIR-SV v1 at a properly recalibrated (not frozen-controlled-benchmark) threshold removes roughly a fifth to a quarter of false Manta candidates while retaining ~95% of true deletions, a modest but real and person-transferable signal (5 people spanning AFR/AMR/EAS/SAS ancestry).

M0, M2, and M4 perform near-identically at this operating point (macro specificity 0.212-0.240) — the pairwise M0-vs-fusion difference in sign is inconsistent across seeds, i.e. **no model shows a reproducible advantage over the others at POC scale (n=5 people)**, consistent with §9.2/§10's finding that added modalities contribute only a small, largely redundant increment over the image+scalar baseline.

**Subgroup behavior at the frozen threshold:** ROC-AUC is stable across length buckets (0.70-0.78 for 50-200bp, 200-1000bp, and 1000-10,000bp candidates — no single length range drives performance). Among true positives, acceptance rate/confidence degrades monotonically as breakpoint error from the PanGenie-truth coordinate grows (99.5% accepted at exact match down to 88.8% beyond 100bp error), and heterozygous genotypes are accepted slightly less often than homozygous-alt (98.4% vs 99.6%) — both patterns are content-consistent, not artifacts of noise. Unknown-class candidates (sites PanGenie did not genotype, never used in supervised metrics) receive predicted-positive rates (93-95%) nearly as high as confirmed positives, consistent with them being ungenotyped rather than rejected sites.

This 5-person result establishes that the LOPO calibration procedure is well-behaved and transfers reliably between people — it is the basis for §13's untouched-external-cohort evaluation, where the same procedure (unmodified) is applied once to GIAB HG002 and is not itself re-tuned there.

## 13. Untouched external validation (GIAB HG002) — the frozen, one-shot result

**This section reports the single, frozen evaluation of PAIR-SV v1 against GIAB HG002, opened exactly once, per `manta_poc/EXTERNAL_EVAL_PROTOCOL_FROZEN.md` (base protocol + ADDENDUM, decision 0046) and executed end to end without any post-hoc tuning of thresholds, matching parameters, candidate filters, models, or feature processing.** HG002 is a person never seen during model development, threshold calibration (§12), or the internal one-shot test (§9.2), and was untouched until this evaluation.

**Pipeline.** Whole-genome Manta 1.6.0 (identical frozen container digest to every other sample in this project) was run on `HG002.GRCh38.60x.1.bam` (GIAB/NHGRI, Illumina, 60x, Novoalign, 126,230,242,948 bytes, self-computed SHA256 `e2cb894b...cf77f26`, chosen for platform consistency with all 6 prior samples). The first Manta attempt failed `configManta`'s contig-set validation in 33s (the BAM's 2,580 contigs, while a strict subset of this project's 3,366-contig reference, are not an *exact* match, and Manta requires exact equality) — fixed, and reported here rather than hidden, by extracting a subset reference containing exactly the BAM's contig set via `samtools faidx` (verified byte-identical contig names to the BAM header; same GRCh38 sequences, only the extra ALT/HLA/decoy contigs the BAM's own aligner never used are omitted). The resubmitted run completed successfully: exit code 0, elapsed 1,962s, 6,613 raw DEL records in `diploidSV.vcf.gz` (SHA256 `5af8c0fb...b914540b`).

Manta's PASS DEL candidates were matched against GIAB v5.0q GRCh38 truth (assembly-based, dipcall on the T2T-HG002-Q100-v1.1 diploid assembly; **Draft status, not yet peer-reviewed** — stated explicitly here per the mission's truth-source constraint) using the frozen Truvari 5.4.0 parameters (identical to every other Truvari pass in this project) plus the ADDENDUM's benchmark-region rule (candidate included only if both deletion breakpoints fall inside the v5.0q confident-region BED). Manta's own end-to-end recall against v5.0q truth in benchmark regions was 42.7% (4,333/10,143 truth deletions matched) — reported here as a separate evaluation level per ADDENDUM §12, **not to be confused with or conflated with PAIR-SV's performance as a filter of Manta's own candidates below**, which is a categorically different question (can PAIR-SV distinguish Manta's true from false candidates, not can Manta find every truth deletion in the first place).

**Candidate composition** (5,461 total Manta PASS DEL): **4,333 positive** (Truvari-matched), **512 known_negative** (unmatched, fully inside benchmark regions), **616 excluded** (outside/crossing benchmark-region boundaries, per the benchmark-region rule — never treated as false positives). Of the 4,845 confidently-labeled candidates, 84 fell outside the predefined 50-10,000bp scope tier (`unsupported_length_gt_10000bp`, per ADDENDUM §11) and were excluded from scoring; extraction succeeded for 4,756/4,761 eligible candidates (99.9%; 5 `CandidateExtractionError` failures, reported not hidden).

**Accept-all-Manta baseline** (label every PASS DEL positive): prevalence 0.903, recall=1, specificity=0 by construction, F1=0.949 — again a high but uninformative floor, per §11's F1 caveat.

**Primary result — specificity at the frozen ~95%-recall deployment threshold** (3-seed-ensembled probability, threshold frozen in Week 1 from the 5-person POC, applied here completely unmodified):

| model | recall | specificity | precision | F1 | balanced acc. | MCC | ROC-AUC | PR-AUC | filtered-candidate rate |
|---|---|---|---|---|---|---|---|---|---|
| M0 | 0.9486 | **0.2739** | 0.9242 | 0.9362 | 0.6112 | 0.2528 | 0.7906 | 0.9713 | 0.0730 |
| M2 | **0.9551** | 0.2500 | 0.9224 | 0.9385 | 0.6025 | 0.2463 | 0.7889 | 0.9703 | 0.0648 |
| M4 | 0.9327 | **0.3217** | 0.9278 | 0.9302 | 0.6272 | 0.2604 | 0.7865 | 0.9698 | 0.0919 |

**At the frozen threshold:** M2 is the only model that clears the ~95% recall target on this external cohort (0.9551); M0 comes close (0.9486); **M4 falls short of the 95% target (0.9327)** while achieving the highest specificity of the three (0.3217 vs 0.2739/0.2500). This is the opposite ordering from the 5-person POC's LOPO calibration (§12), where M0/M2/M4 were statistically indistinguishable (specificity 0.212-0.240 for all three) — on untouched external data, M4's higher specificity comes with a recall cost that the frozen threshold (calibrated on the 5-person POC, not retuned here) does not fully compensate for. Per the mission's hard constraint, **no model is selected or preferred based on this result, and no threshold is retuned** — all three are reported as run. Specificity at the frozen threshold is 0.2500-0.3217 here, against 0.212-0.240 for the 5-person POC (§12). The two use different truth sources (PanGenie vs GIAB v5.0q) and are not directly comparable in absolute terms. The 30-person cohort later measured 0.2167-0.2253 (§15.12), which is broadly consistent with the POC range. Against those two tiers, the v5.0q values reported here are the higher ones, and v5.0q appears as the high-specificity outlier among the three. We draw no conclusion from this section alone about whether the POC estimate was optimistic or pessimistic; that comparison requires more than one external genome.


![Figure 7. HG002 recall and specificity at the frozen threshold, under two truth sources.](figures/fig7_hg002_recall_specificity.png)

**Figure 7. HG002 recall and specificity at the frozen threshold, under two truth sources.** GIAB v5.0q (primary) and NIST SV v0.6 (secondary sensitivity pass). The two are never pooled; they are plotted together only for visual comparison. The dashed line marks the 95% recall target.

**Length subgroups** (per ADDENDUM §11 scope tiers):

| bucket | model | recall | specificity | ROC-AUC | n |
|---|---|---|---|---|---|
| 50-200bp (primary) | M0 | 0.9247 | 0.2830 | 0.7368 | 2,503 |
| 50-200bp (primary) | M2 | 0.9329 | 0.2830 | 0.7397 | 2,503 |
| 50-200bp (primary) | M4 | 0.8905 | 0.3762 | 0.7353 | 2,503 |
| 200-1000bp (secondary) | M0 | 0.9908 | 0.1776 | 0.8666 | 1,626 |
| 200-1000bp (secondary) | M2 | 0.9921 | 0.1776 | 0.8647 | 1,626 |
| 200-1000bp (secondary) | M4 | 0.9868 | 0.1589 | 0.8631 | 1,626 |
| 1000-10000bp (exploratory) | M0 | 0.9282 | 0.4524 | 0.8065 | 627 |
| 1000-10000bp (exploratory) | M2 | 0.9419 | 0.1905 | 0.7796 | 627 |
| 1000-10000bp (exploratory) | M4 | 0.9504 | 0.3333 | 0.7951 | 627 |

Recall/specificity/ROC-AUC vary meaningfully by length bucket (specificity is consistently lowest in the 200-1000bp range across all three models — the hardest region to reject known negatives in) but no bucket collapses to chance-level ROC-AUC (all buckets 0.74-0.87) — consistent with §11's finding on the 5-person POC that no single length range drives performance.

**Breakpoint-error subgroups** (positive class only, Truvari's own StartDistance/EndDistance from `tp-comp.vcf.gz`, M4 shown; M0/M2 show the same monotonic pattern, see `manta_poc/hg002_external/hg002_final_evaluation_report.json` for all three):

| bucket | n | accepted rate | median score |
|---|---|---|---|
| exact_0bp | 3,397 | 0.952 | 0.992 |
| 1-10bp | 546 | 0.918 | 0.980 |
| 11-50bp | 203 | 0.833 | 0.950 |
| 51-100bp | 70 | 0.729 | 0.869 |
| >100bp | 80 | 0.637 | 0.803 |

Same monotonic degradation pattern as the 5-person POC (§11's breakpoint-error subgroup) — acceptance/confidence falls as the Manta candidate's breakpoints diverge further from the matched truth coordinate, replicated on external data.


**Secondary/sensitivity pass (NIST SV v0.6, GRCh37) — completed, reported separately, never pooled with the primary v5.0q result above.**

Run as an entirely separate pipeline pass: a native GRCh37 HG002 alignment (`HG002.hs37d5.60x.1.bam`, same NHGRI Illumina 300X AJtrio Novoalign 60x series as the primary GRCh38 BAM, aligned to `hs37d5` — the exact reference the README documents Novoalign as having used), Manta run against the unmodified `hs37d5.fa` reference (contigs matched exactly on the first attempt, no subset-reference workaround needed this time), and Truvari matched against NIST SV v0.6 Tier1 truth using this project's own frozen parameters (not the v0.6 README's own suggested `-r 2000`, for metric-definition consistency with every other pass in this project — a deliberate, documented choice). Same frozen M0/M2/M4 checkpoints, seed-ensemble procedure, and deployment thresholds as the primary pass; predictions hashed before any label was loaded.

Candidate composition (5,385 total Manta PASS DEL): 3,008 positive, 232 known_negative, 2,145 excluded by the benchmark-region rule. Manta's own end-to-end recall against v0.6 truth in benchmark regions was 71.6% (3,008/4,199 truth deletions matched) — markedly higher than the 42.7% observed against v5.0q, consistent with v0.6's documented bias toward easier, better-supported SVs (§15.10). Extraction succeeded for 3,183/3,184 eligible candidates (99.97%).

**Primary result at the frozen threshold:**

| model | recall | specificity | precision | F1 | balanced acc. | MCC | ROC-AUC | filtered-candidate rate |
|---|---|---|---|---|---|---|---|---|
| M0 | 0.9742 | 0.1675 | 0.9450 | 0.9594 | 0.5708 | 0.1887 | 0.7397 | 0.0349 |
| M2 | **0.9795** | 0.1626 | 0.9450 | 0.9619 | 0.5710 | 0.2051 | 0.7414 | 0.0295 |
| M4 | 0.9654 | **0.2167** | 0.9476 | 0.9564 | 0.5911 | 0.2121 | 0.7432 | 0.0462 |

**The v0.6 pattern differs from v5.0q.** The two are reported separately, per the evidence-tier index. On v5.0q, only M2 cleared the 95% recall target and M4 fell short (§13). On v0.6, **all three models clear ~95%+ recall** (M0 97.4%, M2 98.0%, M4 96.5%), and M4 again has the highest specificity (0.2167) but this time without missing the recall target. Absolute specificity is lower across the board on v0.6 than on v5.0q (16-22% vs. 25-32%) — plausibly because v0.6's easier-SV-biased truth set makes its "known negative" candidates (Manta PASS DEL calls with no v0.6 truth match) systematically harder to distinguish from true positives than v5.0q's known negatives, though this is offered as a hypothesis, not a demonstrated mechanism. The two truth sources agree that M4 achieves the highest specificity of the three models, but disagree on whether that comes bundled with a recall shortfall — a genuine, non-trivial discrepancy between a Draft assembly-based benchmark and a mature-but-incomplete read-support benchmark, reported honestly rather than resolved in favor of either.

Length subgroups and breakpoint-error subgroups show the same qualitative patterns already established on v5.0q and the 5-person POC (ROC-AUC stable across length buckets, 0.63-0.81; breakpoint-error acceptance rate degrades monotonically with distance from the matched truth coordinate) — full tables in `manta_poc/hg002_v0.6_external/hg002_v0.6_final_evaluation_report.json`.

**From one genome to thirty.**

The ordering above invites a model-level reading: that M2's calibration transfers more faithfully than M4's, and that the fusion model is the more fragile of the two under distribution shift. We entertained that reading. §15.3 records it.

It rests on one genome. Recall, specificity, and the gap between them are properties of one individual's candidate population — HG002's variant profile, its sequencing run, and the few thousand deletions Manta proposed in it. Nothing in this section separates "M4's threshold transfers less well than M2's" from "M4's threshold transferred less well on this person." More analysis of HG002 cannot settle it. More people can.

The 30-person cohort (§15.12) was assembled to settle it. Its membership, purpose and protocol were fixed in advance: the cohort was selected deterministically before any Manta run, six people per continental superpopulation, screened for relatedness against every earlier cohort in this study; the deployment thresholds were the frozen values used here and were not retuned; and the evaluation script, metric definitions, subgroup definitions and sample inclusion were checksummed before any cohort label was opened. The cohort tested a pre-stated question about generalisation across people. It was not a search for a model that scored better, and no model was selected, promoted or re-ranked on its result.

The ordering did not replicate. Across 30 people, M2 and M4 differ in macro-averaged recall by 0.000176, against a between-person standard deviation of 0.0062 (Figure 8).

![Figure 8. Per-person performance on the untouched 30-person cohort.](figures/fig8_cohort_per_person.png)

**Figure 8. Per-person performance on the untouched 30-person cohort.** Recall (top) and specificity (bottom) for M0, M2 and M4 on each of the 30 individuals, at the deployment threshold calibrated once on the 5-person development study and not retuned. Dotted lines are macro-averages over people; the dashed line in the upper panel is the pre-specified 0.95 recall target, which no model reaches. Background bands group individuals by continental superpopulation. Values are read from the frozen evaluation report, whose SHA-256 is verified before plotting.

Two statements should be kept apart here. The cohort shows that the HG002 recall difference between M2 and M4 does not persist at cohort scale. It does not establish that the HG002 difference was itself sampling variation rather than a real difference on that individual. We did not pre-specify a test of whether the HG002 M2-M4 difference was nonzero, and we do not run one now. What the cohort licenses is a statement about generalisation across people, not a retrospective verdict on the single-genome measurement. Two results did carry over: no model reached the pre-specified 95% recall target, and M4 had the highest specificity, as on both HG002 truth sets. §15.12 reports the cohort in full. §15.3 and §15.4 are kept, and marked, as the interpretation the cohort superseded.

**Provenance:** every number above traces to `manta_poc/hg002_external/hg002_final_evaluation_report.json`, `hg002_gate2_classification_report.json`, `hg002_gate3_predictions_ensembled_LABEL_BLIND.csv` (+ `.sha256`, hashed *before* any label was loaded — `hg002_gate3_predictions_ensembled_LABEL_BLIND.csv.sha256`, `hg002_gate3_predictions_per_seed_LABEL_BLIND.csv.sha256`), `HG002_wgs_exit_code.txt`, `HG002_diploidSV_sha256.txt`, `HG002_bam_sha256.txt`, and `truvari_v5.0q_primary_summary.json`. This evaluation was opened exactly once; per the mission's hard constraints, it will not be reopened, rescored, or used to select between M0/M2/M4 or to modify v1.

## 14. Error and subgroup analysis

![Figure 9. Acceptance rate against breakpoint error.](figures/fig9_breakpoint_error.png)

**Figure 9. Acceptance rate against breakpoint error.** For true-positive candidates, the fraction accepted at the frozen threshold as a function of the distance between the Manta breakpoints and the matched truth coordinate, shown for both HG002 truth sources.

Phase F subgroup CSVs (5-person POC, `manta_poc/truvari_gate2/phase_f/phaseF_6a_length_subgroups.csv`, `phaseF_6b_positive_only_subgroups.csv`, `phaseF_6c_known_negative_summary.csv`, `phaseF_6d_unknown_summary.csv`) are described in §11-12 above. The external (HG002) subgroup breakdown is now complete and reported in §13 above (length tiers per the ADDENDUM §11 primary/secondary/exploratory scheme; breakpoint-error buckets from Truvari's own StartDistance/EndDistance). The same qualitative pattern appears on three cohorts and two truth sources (PanGenie 5-person POC; GIAB v5.0q HG002; PanGenie 30-person cohort): no single length range drives performance, and acceptance rate falls as breakpoint distance from the matched truth coordinate grows. The pattern recurs across cohorts rather than being confined to one truth source. Extraction-failure rates are low throughout: HG002, 5 of 4,761 eligible candidates (0.1%); the 30-person cohort, 128 of 132,196 eligible candidates (0.0968%); the 5-person POC was not tabulated per person in Phase F.

---

*Sourcing note: every number in §9-10 traces to `reports/train40/three_seed_aggregate.csv`, `reports/train40/ablations_aggregate.csv`, `reports/train40/ablations_per_seed.csv`, `reports/test_evaluation/three_seed_aggregate.csv`, `reports/test_evaluation/candidate_cluster_bootstrap.csv`, `reports/test_evaluation/candidate_cluster_bootstrap_50_200bp.csv`, `reports/test_evaluation/leave_one_person_out.csv`, and `reports/test_evaluation/subgroup_metrics.csv`. No number is estimated or carried over from the Train15 interim report. Every number in §11-12 traces to `manta_poc/truvari_gate2/phase_f/PHASE_F_REPORT.md` and its accompanying `phaseF_*.csv` files (decisions 0037-0041) — a 5-person development POC, explicitly distinct from and not to be pooled with the untouched HG002 external evaluation in §13-14. Every number in §13-14's HG002 portion traces to `manta_poc/hg002_external/hg002_final_evaluation_report.json` and its cited provenance files, generated by `manta_poc/hg002_evaluate.py`, run exactly once.*

---

## 15. Discussion

### 15.1 Why M4 led on the controlled internal test, and why that lead is not what it first appears

On the internal one-shot test (§9.2), M4 had the highest mean F1 (0.81613), ROC-AUC, and MCC of the five variants, and the candidate-cluster bootstrap confirmed M4−M0 excludes zero (+0.00490, 95% CI [0.00139, 0.00832]). Read at face value, this looks like a clean win for the full multimodal architecture. Two things complicate that reading. First, M2−M0 *also* excludes zero (+0.00379, CI [0.00097, 0.00674]) — the scalar-only branch alone captures most of the measurable gain. Second, and more directly: M4−M2 does *not* exclude zero (+0.00106, CI [−0.00227, 0.00433]). M4's absolute F1 is highest, but the model that is statistically distinguishable from the image-only baseline is "image + scalar read-support features," not "image + scalar + candidate-sequence + read embeddings." M4's extra two branches (candidate REF/ALT sequence via HyenaDNA, embedded read sequence) add measurable numeric improvement on this specific test set without adding *statistically supported* improvement over M2 specifically.

### 15.2 M2 and M4 are close in each of the four measurements

M2 and M4 are close on recall and F1 in each of the four measurements below. The measurements are not directly comparable to one another: they use different candidate populations and, in two cases, different truth sources. The candidate-cluster bootstrap on curated pairs gives M4-M2 ΔF1 +0.00106, 95% CI [-0.00227, +0.00433] (§9.2). The 5-person LOPO calibration gives macro specificity 0.212-0.240 for all three models, with the M0-vs-fusion difference changing sign across seeds (§12). The HG002 evaluation is reported in §13, the 30-person cohort in §15.12.

On recall and F1, no layer separates M4 from M2. Specificity behaves differently: M4 was the highest of the three in all three external evaluations — HG002 v5.0q 0.3217, v0.6 0.2167, cohort 0.2253. The differences are small; the direction is reported without a significance claim (§15.12).

The marginal value of M4's two extra branches beyond M2 is therefore small on the metrics the deployment criterion is written in.

### 15.3 The HG002 recall ordering, and the interpretation we drew from it before the cohort

**Observation.** At the frozen deployment threshold, calibrated once on the 5-person POC and not retuned, recall on HG002 was 0.9551 for M2, 0.9486 for M0 and 0.9327 for M4. M2 was the only one above the 95% target. The calibration procedure itself was working: the same method held recall within 0.9415-0.9504 across 45 leave-one-out folds in the development study (§12).

**Interpretation we drew at the time, now superseded.** We read this as a property of the models: that M4's score distribution shifted more than M2's on a new candidate population, so its fixed threshold landed near 93% recall rather than 95%. We speculated that M4's extra branches might make its scores more sensitive to the read-length, coverage or breakpoint-complexity profile of HG002's sequencing run. We flagged this as a hypothesis rather than a finding.

**What the cohort showed.** The reading does not survive 30 people. Macro-averaged recall is 0.9473 for M2 and 0.9471 for M4, a difference far inside the between-person spread (§15.12 gives the figures). The HG002 ordering was specific to that person, not to the models. The subsection is kept because the interpretation was drawn from the evidence available at the time and is superseded by §15.12.

### 15.4 On HG002, a specificity gain did not substitute for the missed recall target

At the frozen threshold on HG002, M4 had the highest specificity of the three models (0.3217, against 0.2739 for M0 and 0.2500 for M2) and the lowest recall (0.9327). The deployment criterion fixes recall at approximately 95% first, with specificity maximised subject to that constraint (§12). Under that criterion the two quantities are not interchangeable: a model with higher specificity and lower recall sits at a different point on the curve than the one the rule specifies, not at a better one. In a clinical or production deletion-filtering context, the cost of missing a true deletion (a false negative under M4's looser recall) is generally treated as more severe than retaining a few more false candidates for downstream manual review (the cost paid by M0/M2's lower specificity) — which is precisely why the recall target was fixed as the primary constraint rather than left to float. Reporting M4's higher specificity without this framing would overstate what the HG002 result shows.

This argument is scoped to HG002. On the 30-person cohort the trade does not appear: M4's specificity is the highest of the three (0.2253) and its recall equals M2's to within 0.0002 (§15.12). There, all three models fall below the 95% target by a similar margin, so the argument no longer separates them. What survives is the principle — a specificity gain does not substitute for a pre-registered recall target — not its HG002 instance.

### 15.5 Modality redundancy

The retrained branch-removal ablation (§10.2) found small, individually modest ΔF1 for removing each branch from M4 (candidate: −0.00107, read: −0.00072, scalar: −0.00151 F1), all much smaller than a naive reading of the post-hoc zero-ablation numbers would suggest (§15.6). Combined with 15.1-15.2's finding that M2 alone captures most of M4's measurable advantage over M0, the coherent picture is that the three added evidence types (candidate sequence, read embeddings, scalar read-support features) carry substantially overlapping information about the same underlying signal — whether a candidate is well-supported by the reads at that locus — rather than each contributing an independent, additive slice of evidence. This is a specific, falsifiable architectural claim, not merely a restatement that "more features didn't help much."

### 15.6 Zero-ablation overestimates branch importance by 5-10x relative to retrained removal

Directly quantified in §10.3: post-hoc zero-ablation overstates each branch's true marginal contribution by 5.1x (candidate), 10.5x (read), and 6.6x (scalar) relative to a properly retrained branch-removal control. The mechanism is straightforward once stated: zeroing an input at inference time pushes the model outside the distribution it was trained on, and the resulting performance drop conflates "this input carries important information" with "this model was never trained to be robust to this input being absent." A retrained-removal ablation, by construction, lets the rest of the network compensate during training — which is the actually relevant question for an architecture decision (should this branch exist at all), as opposed to a robustness question (what happens if this branch's sensor fails at inference time). This paper treats post-hoc zero-ablation as informative only as an upper bound on importance, never as a point estimate, and recommends the same discipline for future work in this area — a naive single zero-ablation pass, common in the literature, risks systematically overstating every modality's individual value.

### 15.7 Calibration shift between curated candidates and real Manta candidates

The controlled benchmark (§9) trains and tests on curated same-site candidate *pairs* — by construction, close to 1:1 positive:negative, drawn from a matched-supervision design. Real Manta output (§11) is nothing like this: prevalence is 83-90% positive per person in the 5-POC realistic study, and the frozen-threshold-transfer experiment (§11) showed specificity collapsing to 4-7% when the controlled-benchmark's own operating threshold was applied unmodified to real candidates — even though the underlying ranking (ROC-AUC ~0.75-0.76) remained informative. This is a textbook prevalence/covariate-shift problem: the model's *discrimination* transfers reasonably well, but its *calibration* (the mapping from score to a specific recall/specificity trade-off) does not, because the score distribution the threshold was tuned against no longer matches the deployment distribution. The LOPO calibration procedure (§12) exists specifically to correct for this, and it does. What §15.3 and §15.12 add is that a threshold calibrated this way can still land slightly off its target on a new population: across 30 people the frozen threshold held recall between 0.928 and 0.962, consistently, but below the 0.95 it was set for. Threshold recalibration was needed when moving from curated pairs to real candidates. Ranking, measured by ROC-AUC, did not degrade (0.75-0.76).

### 15.8 Candidate verification is not variant discovery

As stated in the Introduction: PAIR-SV is evaluated exclusively on its ability to separate Manta's true candidates from Manta's false candidates. It has no mechanism to propose a deletion Manta did not already candidate, and no experiment in this paper measures that capacity. Every recall number reported for PAIR-SV (§9-14) is *conditional* on Manta having generated the candidate in the first place. This is why §13 explicitly reports Manta's own end-to-end recall against v5.0q truth (42.7% of truth deletions in benchmark regions were matched by *any* Manta PASS DEL candidate) as a separate, non-comparable number from PAIR-SV's candidate-filtering recall (93-96% at the frozen threshold, §13) — the two numbers answer different questions and must never be multiplied together or presented as a single end-to-end sensitivity figure without careful qualification, since a naive product would understate PAIR-SV's actual filtering quality while overstating what fraction of the genome's true deletions the full Manta+PAIR-SV pipeline actually recovers.

### 15.9 Limitations of PanGenie-derived Known-negative and Unknown labels

The 5-person realistic-candidate development study (§11-12) uses PanGenie genotypes as silver-standard truth, not GIAB-grade ground truth (a distinction maintained throughout this project, `multisample_project.md` §2). A "Known negative" label there means Truvari found no truth match for a Manta candidate whose locus was confidently genotyped 0/0 by the two-pass PanGenie carrier/reference-check design — it is only as reliable as PanGenie's own genotyping accuracy at that locus, which varies with local mappability, panel composition, and population representation (HG01912/ACB's markedly higher known-negative/unknown fraction in §11 is itself evidence of this population-dependent variability). "Unknown" candidates (sites PanGenie did not confidently genotype either way) are never used in any supervised metric in this project (§11 explicitly), and their high predicted-positive rate (93-95% at the frozen threshold, per Phase F's own subgroup breakdown) is reported descriptively, not as evidence about PAIR-SV's accuracy on unlabeled sites.

The same truth source labels the 30-person cohort (§15.12), and this bears directly on the study's principal result. The cohort's positives, known-negatives and Unknown classes are all derived from two-pass PanGenie genotypes, not from an assembly-based or otherwise independent standard. The cohort-level conclusions in §15.12 — including the non-replication of the HG002 recall ordering and the shortfall against the 95% recall target — are therefore conclusions about model behaviour as measured against this truth source. PanGenie genotypes short-read samples against a haplotype-resolved panel; the HGSVC2 panel used here comprises 64 haplotypes from 32 genomes spanning the 1000 Genomes superpopulations [ebert2021]. Its reported genotype concordance is lower in repetitive (STR/VNTR) regions than in non-repetitive ones [ebler2022]. We are not aware of a published characterisation of how its accuracy depends on the ancestry composition of the panel; the interpretation offered for the AFR pattern in §16 is ours and is not supported by a documented property of the genotyper. PanGenie is not a weak label set, but it is not GIAB-grade ground truth either. Replication of the cohort result against a stronger independent truth standard was not established here, and would require a population-scale benchmark of a kind that does not currently exist at 30-person scale. Readers should read §15.12 with that dependency attached.

### 15.10 The Draft status of GIAB v5.0q

The primary external truth source (§13) is formally a Draft release, not yet peer-reviewed, built via a still-actively-developed assembly-based pipeline (`manta_poc/EXTERNAL_TRUTH_SOURCE_DECISION.md`). NIST's own README states results using it "should be carefully evaluated." This project selected it over the mature, peer-reviewed v0.6 specifically because it is GRCh38-native (avoiding a liftover step) and assembly-based (methodologically stronger for a new benchmark), while explicitly committing to running v0.6 as a separate sensitivity pass precisely to characterize whether the two truth sources' results agree in direction, given their non-overlapping limitation profiles (Draft/less field-validated vs. GRCh37-only, with the release documentation reporting ≤50% genome-wide SV coverage and a bias towards easier SVs).

**The v0.6 sensitivity pass is now complete (§13), and the two truth sources do *not* fully agree.** Both agree that M4 achieves the highest specificity of the three models. They disagree on the practical consequence: on v5.0q, M4's higher specificity comes bundled with missing the pre-specified 95% recall target (only M2 clears it); on v0.6, all three models clear ~95%+ recall, so M4's higher specificity is "free" in the sense of not costing the recall target. Two non-exclusive readings are offered, neither preferred over the other by this analysis: (a) v0.6's own easier-SV bias makes its "known negative" candidates easier to reject without also rejecting true positives, so the recall/specificity trade-off it exposes is systematically gentler than the trade-off on the harder, more complete v5.0q truth set — meaning v5.0q's result should be weighted more heavily as the more demanding, and therefore more informative, test; or (b) the discrepancy reflects genuine truth-set-specific noise in a single-person evaluation (§15.11), in which case neither number alone should be treated as decisive. This project does not adjudicate between (a) and (b) here — doing so would require evidence this paper does not have — and treats the disagreement itself, not a resolution of it, as the reportable finding.

The 30-person cohort adds one further data point, which we record as suggestive and not decisive. Cohort specificity is 0.2167-0.2253 (§15.12), close to the 5-person POC range (0.212-0.240) and to v0.6 (0.1626-0.2167), and below v5.0q (0.2500-0.3217). Among the tiers measured, v5.0q is the one with the highest specificity. That is consistent with reading (a), but it does not establish it: the cohort is labelled with PanGenie truth, not with either GIAB callset, so it is not a clean arbiter between them.

### 15.11 HG002 is one person

Every number in §13 describes PAIR-SV's behavior on a single individual's genome. However carefully the evaluation was frozen and executed exactly once, a single person cannot establish that a result generalizes across human genetic diversity — ancestry-linked structural variant profiles, coverage/library-prep idiosyncrasies specific to one sequencing run, and simple sampling noise in a candidate set of a few thousand deletions are all confounded with "the true population-level performance of PAIR-SV" when n=1. This is the explicit motivation for the 30-person untouched external cohort (§15.12), balanced across five continental superpopulations specifically to probe whether the HG002 finding (M2 meets the recall target, M4 does not) is a property of the model or a property of this one person. **§15.12 reports the answer: it was a property of this one person.**

### 15.12 The role of the 30-person cohort as transfer evidence

The 30-person untouched external cohort was evaluated exactly once under the frozen protocol, with the evaluation script checksummed before it was ever executed and the full pre-evaluation state (sample inclusion, prediction hashes, Truvari label hashes, extraction accounting, metric and subgroup definitions) frozen in `manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json` beforehand. All 30 originally-selected people completed the pipeline; none was dropped and no replacement was triggered, so the balanced design (6 per superpopulation, zero relatedness) is intact. Primary aggregation is per-person macro-averaging over the 30 independent people — candidate rows are never treated as independent samples (§9.2's reasoning).

**Primary results at the frozen deployment threshold** (macro-averaged over 30 people, mean ± SD across people):

| metric | M0 | M2 | M4 |
|---|---|---|---|
| Recall @ frozen threshold | 0.9453 ± 0.0065 | 0.9473 ± 0.0063 | 0.9471 ± 0.0062 |
| Specificity | 0.2167 ± 0.0310 | 0.2216 ± 0.0310 | 0.2253 ± 0.0302 |
| Precision | 0.9008 ± 0.0236 | 0.9015 ± 0.0234 | 0.9019 ± 0.0234 |
| F1 | 0.9223 ± 0.0125 | 0.9237 ± 0.0124 | 0.9238 ± 0.0126 |
| Balanced accuracy | 0.5810 ± 0.0141 | 0.5844 ± 0.0140 | 0.5862 ± 0.0141 |
| MCC | 0.1967 ± 0.0232 | 0.2068 ± 0.0223 | 0.2106 ± 0.0246 |
| ROC-AUC | 0.7534 ± 0.0216 | 0.7481 ± 0.0220 | 0.7616 ± 0.0233 |
| PR-AUC | 0.9552 ± 0.0143 | 0.9535 ± 0.0148 | 0.9568 ± 0.0146 |
| Filtered-candidate rate | 0.0732 ± 0.0076 | 0.0719 ± 0.0075 | 0.0725 ± 0.0070 |

Recall range across the 30 people: M0 0.9276-0.9620, M2 0.9295-0.9610, M4 0.9279-0.9617.

**Truth source.** The cohort is labelled with two-pass PanGenie genotypes, the same silver-standard source used for the 5-person development study (§11) and not the assembly-based GIAB truth used for HG002 (§13). Every number in this subsection is a measurement against that source; see §15.9 for what this bounds.


Per-person values for all 30 individuals are shown in Figure 8 (§13).

**Cohort scale and candidate accounting:** 135,993 Manta PASS DEL candidates across the 30 people; 102,758 confidently-labelled candidates scored; 30,740 Unknown (22.6% of all candidates), never converted into negatives and never entering any supervised metric; 128 extraction failures (0.0968% of 132,196 eligible candidates). The accept-all-Manta baseline, macro-averaged over people, has prevalence 0.8832 and F1 0.9378.

**All three models score lower F1 than accepting every Manta call:** 0.9223 (M0), 0.9237 (M2) and 0.9238 (M4), against the baseline's 0.9378. This follows from the prevalence. At 88.3% positives, a rule that keeps every candidate holds recall at 1.0, and the recall term dominates F1; a classifier that removes false candidates at the cost of some true ones therefore scores lower on F1 while trading recall for specificity. It is the reason F1 is not used as a headline metric for this tier, and the same reason §11 gave when the pattern first appeared on the 5-person POC. The quantity the deployment criterion is written in is recall at a fixed threshold, with specificity maximised subject to it.

The operating trade-off the filter represents at this threshold is the following. Across the 30 people, the models remove 7.2-7.3% of Manta PASS DEL candidates (filtered-candidate rate 0.0719 for M2, 0.0725 for M4, 0.0732 for M0) and retain 94.5-94.7% of the labelled positive deletions (recall 0.9453-0.9473). F1 does not express this trade, because at 88.3% prevalence the recall term dominates it.

**No model reaches the predefined 95% recall target on this cohort.** All three land just below it (0.9453-0.9473), and the shortfall is small but consistent rather than driven by outlying individuals — the between-person standard deviation is only ~0.006 and every one of the 30 people falls in a narrow 0.928-0.962 band. The threshold calibrated once on five development people transfers to thirty untouched people with consistent person-to-person recall, and lands below its intended target. The threshold was not retuned after the target was missed.

**The HG002 M2-versus-M4 recall ordering does not replicate at cohort scale.** On HG002 v5.0q (§13), M2 was the only model above the 95% target (0.9551) while M4 fell 1.7 points below it (0.9327). §15.11 flagged this as possibly person-specific. Across 30 people, the macro-averaged recall difference between M2 and M4 is **0.000176**, roughly thirty-five times smaller than the between-person standard deviation (0.0062). The two models are, at population scale, indistinguishable on recall. The v5.0q ordering was therefore a property of that one individual's candidate population, not a property of the models — the confound §15.11 identified.

Two claims must be kept apart. The cohort shows that the M2-M4 recall difference seen on HG002 does not persist across 30 people. It does not establish that the HG002 difference was sampling variation rather than a real difference on that individual. No test of whether the HG002 M2-M4 difference was nonzero was pre-specified, and none is run here. The cohort supports a statement about generalisation across people; it does not retrospectively adjudicate the single-genome measurement. This is a concrete, quantified argument against drawing architectural conclusions from single-genome external validation, and it applies as much to our own v5.0q result as to anyone else's.

**The specificity ordering is the same in all three external evaluations.** M4 has the highest specificity of the three models on the cohort (0.2253, against 0.2216 for M2 and 0.2167 for M0), as it did on HG002 v5.0q (0.3217) and NIST v0.6 (0.2167). That is three evaluations, two truth sources and thirty-one people, with the direction the same each time. M4 also has the highest ROC-AUC (0.7616), MCC (0.2106) and balanced accuracy on the cohort. The differences are small, and we did not pre-specify a test for them, so we report the direction and make no claim of statistical significance. M4 remains the predefined primary model; it is not selected here on the basis of these numbers.

**Absolute specificity sits at the low end of the range seen elsewhere:** 0.217-0.225 on the cohort, against 0.212-0.240 for the 5-person POC LOPO estimate (§12), 0.250-0.322 on HG002 v5.0q, and 0.163-0.217 on v0.6. The cohort figure sits closest to the POC estimate and below the v5.0q figure. Among the tiers measured, v5.0q has the highest specificity. §13 reports the same comparison and draws no conclusion from it on its own; thirty people are what allow the comparison to be made at all.

**Superpopulation breakdown** (macro over the 6 people in each group):

| superpopulation | metric | M0 | M2 | M4 |
|---|---|---|---|---|
| AFR (n=6) | recall | 0.9467 ± 0.0052 | 0.9493 ± 0.0044 | 0.9483 ± 0.0043 |
| AFR (n=6) | specificity | 0.1736 ± 0.0165 | 0.1783 ± 0.0201 | 0.1834 ± 0.0172 |
| AMR (n=6) | recall | 0.9437 ± 0.0119 | 0.9451 ± 0.0111 | 0.9458 ± 0.0112 |
| AMR (n=6) | specificity | 0.2268 ± 0.0339 | 0.2372 ± 0.0347 | 0.2430 ± 0.0271 |
| EAS (n=6) | recall | 0.9423 ± 0.0044 | 0.9457 ± 0.0044 | 0.9459 ± 0.0040 |
| EAS (n=6) | specificity | 0.2347 ± 0.0114 | 0.2405 ± 0.0172 | 0.2310 ± 0.0193 |
| EUR (n=6) | recall | 0.9458 ± 0.0045 | 0.9478 ± 0.0048 | 0.9468 ± 0.0047 |
| EUR (n=6) | specificity | 0.2255 ± 0.0226 | 0.2240 ± 0.0171 | 0.2315 ± 0.0232 |
| SAS (n=6) | recall | 0.9480 ± 0.0038 | 0.9487 ± 0.0051 | 0.9489 ± 0.0053 |
| SAS (n=6) | specificity | 0.2227 ± 0.0254 | 0.2278 ± 0.0192 | 0.2376 ± 0.0242 |

Recall is essentially flat across ancestry (0.942-0.949 for every superpopulation and model), but **specificity is markedly lower for the AFR group (0.174-0.183) than for the other four (0.223-0.243)** — a gap of roughly five specificity points that is large relative to the within-group spread and consistent in the same direction for all three models. This is the same population effect already visible in §11's candidate composition, where HG01912 (ACB/AFR) showed a distinctly higher known-negative and Unknown fraction, and it is visible again in this cohort's own composition (the AFR people carry the largest Unknown fractions). The most likely reading is that it reflects the PanGenie truth panel's weaker representation of African-ancestry haplotypes rather than a property of PAIR-SV itself: where the panel genotypes fewer sites confidently, the "Known negative" set that remains is enriched for genuinely difficult calls. This is a limitation of the truth source (§16). The evidence does not separate it from a property of the classifier. The labelling rules were not changed after the result was seen.

**Effect on the paper's earlier claims.** The cohort is consistent with §15.1-15.2: M2 and M4 differ on cohort recall by 0.000176, far inside the between-person spread. It does not bear on §15.5-15.6. It supersedes the reading in §15.3 that M4's calibration transfers less faithfully than M2's; that asymmetry is not present across 30 people. §15.4's argument stands as a matter of principle (a specificity gain does not substitute for a missed pre-registered recall target), but its concrete instance on HG002 turns out to have been person-specific, and on the cohort all three models miss the target by a similar margin.

Per the standing constraint, **none of this is used to select or promote a model.** M4 remains the predefined primary model and M0/M2 the mandatory baselines, exactly as pre-specified, irrespective of the fact that M4 leads on specificity, ROC-AUC and MCC here while being statistically indistinguishable from M2 on recall. Reporting a reproducible directional advantage is not the same as retrospectively choosing a winner, and PAIR-SV v1 is not modified in any way on the strength of these results.

### 15.13 The `mean_abs_insert_size` defect: a diagnosed but unfixed limitation of the frozen v1 scalar branch

![Figure 10. Scalar-feature normalization and the `mean_abs_insert_size` outlier.](figures/fig10_scalar_outlier_mechanism.png)

**Figure 10. Scalar-feature normalization and the `mean_abs_insert_size` outlier.** Schematic of the frozen train-set z-score applied to the 17 scalar read-support features. A single heavy-tailed feature reaches |z| ≈ 33 on affected rows; because the branch applies row-wise LayerNorm across all 17 features jointly, that outlier inflates the row's normalization scale and compresses the remaining features. No clamping is applied in v1.

Post-hoc ablation diagnostics (§10.1) found that `scalar_shuffle` *increased* validation F1 by +0.0301 in a single-seed diagnostic run — the opposite direction from every other ablation intervention, and inconsistent with the scalar branch containing net-positive signal. Root-cause investigation (SkillLayer decision 0012) found the cause: `mean_abs_insert_size` is an extremely heavy-tailed, non-label-informative feature (maximum value 37.4 million against a typical insert size of a few hundred base pairs; among the 10.9% of rows exceeding 100,000, the positive-label rate is 0.503 versus 0.496 for normal rows — essentially no discriminative signal). After the project's standard global z-scoring, this one feature reaches a z-score of approximately 33 for affected rows. Because the scalar branch applies row-wise LayerNorm across all 17 scalar features jointly, this single extreme outlier inflates the affected row's normalization standard deviation by roughly 2.3x (measured: 2.52 vs. 1.10 without the outlier present), which crushes the other 16 — genuinely informative — features toward zero for those rows. Shuffling the scalar vector across rows decouples the outlier from its original row and avoids this crushing effect, which is why shuffling *helped* rather than hurt: an anomalous ablation result that, once traced to its mechanism, turned out to be diagnostic of a real defect rather than evidence against the scalar branch's value. **This defect was found, root-caused, and documented but deliberately not fixed in any checkpoint used for this paper's frozen results** — per the mission's hard constraint against modifying v1 after any test data (internal or external) is opened, and because the defect was identified from validation-set diagnostics, not training-set inspection, its fix belongs to a v2 iteration, not a silent patch to v1. Candidate fixes (dropping the feature, log1p transform, percentile clipping, robust median/MAD scaling) were prototyped as isolated single-seed diagnostic training runs, explicitly logged as v2-candidate exploration and never applied to any checkpoint whose predictions appear in this paper's results tables. This is listed as a concrete, well-understood item for v2 (§18), not a vague direction for future work.

## 16. Limitations

- **Single-caller scope.** PAIR-SV is trained and evaluated exclusively as a filter of Manta's candidates. No claim is made, or supported by any experiment here, about its behavior as a filter for DELLY, LUMPY, or long-read callers' candidates.
- **Deletion-only.** No other SV class (insertion, duplication, inversion, translocation) is addressed.
- **Length scope.** The frozen `Candidate` extraction pipeline supports 50-10,000bp deletions; larger events are a predefined, reported exclusion (§13's `unsupported_length_gt_10000bp` bucket), not a silent gap.
- **Truth-source dependence.** Every reported metric is only as reliable as its underlying truth source — PanGenie silver-standard genotypes for the development POC (§15.9), Draft-status v5.0q for the primary external test (§15.10), and mature-but-incomplete v0.6 for the sensitivity pass (§15.10). The 30-person cohort relies on the same two-pass PanGenie silver-standard truth as the development POC, with the ancestry-dependent representation gap noted below.
- **The principal cohort result rests on PanGenie truth.** The 30-person cohort's labels come from two-pass PanGenie genotypes, not from an assembly-based standard. The conclusions in §15.12 hold with respect to that truth source. Whether they hold against a stronger independent standard at population scale was not tested here (§15.9).
- **`mean_abs_insert_size` defect** (§15.13) — diagnosed, unfixed in v1 by design, carried forward as an explicit v2 item.
- **Single-person external primary result.** §15.11's limitation, now bounded by the 30-person cohort (§15.12), which did not reproduce the HG002 M2-over-M4 recall ordering.
- **Specificity is lower for the AFR group.** On the 30-person cohort, specificity for the six AFR people is 0.174-0.183 across M0/M2/M4, against 0.223-0.243 for AMR, EAS, EUR and SAS. Recall is flat across all five groups (0.942-0.949). The AFR people also carry the largest Unknown fractions, as HG01912 (ACB) did in §11. The consequence for a reader is that the measured benefit of the filter is smaller for these six individuals than for the other 24. As an interpretation, the pattern is consistent with a panel-representation effect — fewer African-ancestry haplotypes in the genotype panel that supplies the truth labels — but the analysis does not establish a cause, and the evidence here cannot separate a property of the truth source from a property of the classifier. Labelling rules and thresholds were not adjusted by ancestry after this result was seen.
- **The frozen operating point undershoots its recall target at population scale.** No model reached the pre-specified 95% recall on the 30-person cohort (0.9453-0.9473, §15.12). The miss is small and highly consistent across people (SD ~0.006), so it is a property of where the threshold sits, not of unstable transfer — but a deployment claiming ~95% recall would be overstating what this frozen threshold actually delivers on unseen people.

## 17. Reproducibility and Data Availability

**Code.** All model, training, extraction, embedding, and evaluation code referenced in this paper is versioned in this repository. Frozen checkpoints are checksum-verified against `reports/train40/frozen_checkpoint_checksums.json` before every use; the full artifact chain for the HG002 external evaluation is checksummed end-to-end in `manta_poc/hg002_external/HG002_v5.0q_FINAL_ARTIFACT_MANIFEST.json` (1,083 SHA-256-hashed entries spanning raw input BAM through final evaluation report, including the one failed Manta attempt and its documented fix). The 30-person cohort's artifacts are: `manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json` (sha256 `3a670e20…3942`, frozen before the evaluation ran, covering sample inclusion, prediction hashes, Truvari label hashes, extraction accounting, and the metric and subgroup definitions); `manta_poc/cohort_evaluate.py` (sha256 `6c9afb37…dac9`, checksummed before first execution); `manta_poc/cohort_final_evaluation_report.json` (sha256 `84f571b6…b3d1`); `manta_poc/COHORT_ONESHOT_EXECUTION_RECORD.md`; and `manta_poc/COHORT_EVALUATION_ERRATUM.md`. No end-to-end artifact manifest comparable to the HG002 v5.0q one was produced for the v0.6 sensitivity pass. We state this rather than imply parity that does not exist.

**Data.** GRCh38 reference: `GRCh38_full_analysis_set_plus_decoy_hla.fa` (1000 Genomes technical reference FTP, checksum recorded). GRCh37/hs37d5 reference: from the 1000 Genomes phase2 technical reference FTP, checksum recorded. GIAB HG002 truth: v5.0q (primary, official NIST MD5-verified) and NIST SV v0.6 (secondary, self-computed checksum, no official MD5 exists for this release). PanGenie silver-standard genotypes: HGSVC2 release v1.0. All source URLs, sizes, and checksums are recorded in the corresponding provenance JSON alongside each pipeline stage's output, not only summarized in prose.

**Frozen protocol documents**, which any reproduction attempt should follow in the order specified: `manta_poc/EXTERNAL_EVAL_PROTOCOL_FROZEN.md` (base + ADDENDUM), `manta_poc/EXTERNAL_TRUTH_SOURCE_DECISION.md`, `manta_poc/multicohort_30_selection_manifest.json` (cohort selection, checksummed before any Manta run per decision 0049).

**Randomness and seeds.** All controlled-benchmark and internal-test results use exactly 3 fixed seeds (20260720, 20260721, 20260722), reported individually and as 3-seed means throughout; no cherry-picked single-seed result is reported as a headline number anywhere in §9-14.

**What is not yet reproducible from this draft alone:** the 30-person multi-cohort's raw CRAM inputs are third-party 1000 Genomes data (publicly available at the recorded URLs, not redistributed here); GIAB HG002 raw sequencing data is likewise public but not redistributed. Only derived artifacts (candidate tables, extracted features, predictions, evaluation reports) are versioned in this repository's own tree.

## 18. Conclusion

PAIR-SV verifies deletion candidates that Manta has already proposed. It does not find deletions Manta missed, and every recall figure here is conditional on Manta having produced the candidate.

We evaluated it at four levels: a controlled internal test on curated same-site pairs, a 5-person development study on real Manta output, one untouched external genome, and an untouched 30-person cohort. The last two were each opened exactly once, under thresholds and metric definitions fixed beforehand.

Three results should be separated, because they answer different questions.

**Performance.** At the frozen threshold, the cohort macro-averaged recall was 0.9453 (M0), 0.9473 (M2) and 0.9471 (M4), with specificity 0.2167, 0.2216 and 0.2253. None of the three reached the pre-specified 95% recall target. The shortfall is small and consistent: the between-person standard deviation is about 0.006, and all 30 people fall between 0.928 and 0.962. A deployment quoting ~95% recall from this threshold would overstate what it delivers on unseen people.

**Generalisation.** On HG002, M2 was the only model above the 95% target and M4 fell 1.7 points below it. We read that as a difference between the models. Across 30 people the same two models differ in macro recall by 0.000176, against a between-person standard deviation of 0.0062. The ordering was a property of that individual. Had we stopped at one genome, we would have reported it as a model-level result.

**Evaluation design.** The HG002 conclusion was not reproduced by the 30-person cohort. A separate comparison points the same way: post-hoc zero-ablation overstated each branch's marginal contribution by 5-10x relative to retrained branch-removal. Both are cases of a cheap evaluation shortcut producing a larger apparent effect than a more expensive one.

What the cohort does not show is that the models are poor. It shows that the strongest model-level reading available from one genome did not hold across people. The specificity ordering did hold: M4 was highest in all three external evaluations; no test for that difference was pre-specified (§15.12). M4 remains the predefined primary model for reasons fixed before any external data was opened, not because of these numbers.

Two limitations bound the scope. Specificity for the six AFR people was 0.174-0.183, against 0.223-0.243 for the other four superpopulations; this is consistent with a panel-representation effect in the truth source, though the analysis does not establish a cause. And the frozen threshold, while transferring consistently between people, sits slightly below the recall it was calibrated to reach. We make no claim of clinical or deployment validity.

*Sourcing note: every specific number in this file is drawn from and must remain byte-consistent with `results_v1_draft.md` §9-14 and the underlying frozen JSON/CSV artifacts it cites. §15.10 (v0.6 sensitivity pass) and §15.12 + the cohort-dependent bullets of §16 (30-person cohort) are now complete and filled from real frozen results. All §15.12 values were extracted programmatically by `paper/extract_cohort_numbers.py`, which verifies the source report's SHA-256 before reading it; the machine-readable extraction is preserved at `paper/cohort_numbers_for_manuscript.json`. No cohort number in this file was typed by hand.*

---

*Merge provenance: generated by `paper/merge_manuscript.py` from the four section drafts listed in the header. Substantive prose is concatenated verbatim; no number was altered, rounded, or re-derived during the merge. Every value in §9-14 traces to the frozen JSON/CSV artifacts cited in those sections, and every cohort value in §15.12 traces to `manta_poc/cohort_final_evaluation_report.json` via `paper/extract_cohort_numbers.py`.*
