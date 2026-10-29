# Week 4 — focused literature audit: prior image/CNN SV classifiers and same-site supervision

**Date:** 2026-08-08
**Question:** does prior work already perform same-site matched positive/negative supervision comparable to PAIR-SV, and must the novelty claim be narrowed?
**Method:** primary sources read where accessible (peer-reviewed methods sections, PMC open-access full text). Bibliographic metadata verified against PubMed/publisher records. **No citation below was written from memory without a lookup.**
**Headline answer: yes — the novelty claim must be narrowed. See §4.**

---

## 1. Comparison table

| Paper | Year | Task | Representation | Model | Supervision | Same-site matched? | Comparable to PAIR-SV? | Exact relevance |
|---|---|---|---|---|---|---|---|---|
| **DeepSVFilter** (Liu, Huang, Wang & Wang) | 2021 | Filter candidate SVs from short reads (DEL, DUP) | 3-channel image: read depth, discordant read pairs, split reads; binary 255/0 encoding | Transfer-learned CNNs (Inception-ResNet v2, MobileNet v1/v2, NASNet-A, PNASNet-5) | Positives = caller calls with ≥90% reciprocal overlap with a truth set; negatives = caller calls **absent** from the truth set, plus (for DUP) randomly sampled genomic regions | **No.** Positives and negatives come from unrelated loci | **Closest prior work by task**, but supervision differs fundamentally | The nearest neighbour to PAIR-SV: same task (post-hoc filtering of a caller's candidates), same modality (short-read pileup-style image + CNN), deletion-inclusive. Trained on **HG002** (deletions); DUP model adds NA12878 — i.e. one-to-two individuals |
| **Samplot / samplot-ML** (Belyeu, Chowdhury, Brown, Pedersen, Cormier, Quinlan & Layer) | 2021 | Genotype/filter putative deletions; automated removal of false positives | Samplot rendering: split reads, discordant pairs, coverage anomalies, colour-coded alignment types | ResNet-like CNN | **Genotype classes** (0/0, 0/1, 1/1). Positives from the GRCh38 liftover of the 1000 Genomes phase-3 integrated SV map; additional negatives sampled from regions known to confuse callers | **Effectively yes, but incidental.** Training spans many 1000G individuals, so the same deletion site carries different genotypes in different people. The authors describe this as occurring naturally, not as a constructed matched-pair design | **Yes — this is the critical case** | Trains across many individuals with genotype labels, so same-site/different-label examples arise. Direct relatives of test individuals were excluded; the authors explicitly acknowledge residual distant relatedness and that "some SVs in the test set also appeared in the training set" |
| **Cue** (Popic, Rohlicek, Cunial et al.) | 2023 | SV **discovery** and genotyping (a caller, not a filter) | Alignments converted to images encoding SV-informative signals | Stacked-hourglass CNN predicting type, genotype and locus | Learned from data incl. synthetic SVs; predicts SV type/genotype/position | Not applicable in PAIR-SV's sense | **No** — different task | Establishes image+CNN as mainstream for SV analysis, but Cue *proposes* SVs rather than verifying a caller's existing candidates. Not a competitor to PAIR-SV's framing |
| **CSV-Filter** | 2024 | Filter SVs for both short and long reads | Image encoding of alignment data | CNN with self-supervised pre-training | Not read in full — see §5 uncertainty | Not established | Probably not, unverified | A more recent filtering method in the same family; its supervision scheme was **not** verified for this audit and remains an open item |
| **NPSV-deep** | 2024 | Genotype SVs in short-read data | Not verified in detail | Deep learning | Notes that population-scale SV datasets contain groups of similar/overlapping SVs | Not established | **No** — genotyping, not candidate filtering | Relevant to the population-scale framing but a different task |
| **DeepSVP** | 2022 | SV **prioritisation** using genotype + phenotype ontology | Not image-based | Deep learning over ontology/phenotype features | Positives = causative variants with disease phenotype; negatives = benign/unrelated pathogenic | No | **No** — clinical prioritisation, not caller-candidate verification | Different problem entirely; listed to bound the search |

---

## 2. Established facts (from the primary sources)

**F1.** DeepSVFilter defines negatives as caller calls *absent from the truth set*, plus random regions for duplications. Positives are caller calls with ≥90% reciprocal overlap with truth. **Positives and negatives therefore occupy different genomic loci by construction.** (Methods, *Briefings in Bioinformatics* 2021.)

**F2.** DeepSVFilter's deletion model was trained on **HG002** at 60× Illumina coverage; the tandem-duplication model used HG002 and NA12878, with candidates from Delly, LUMPY and Manta.

**F3.** samplot-ML's labels are **genotype classes** (0/0, 0/1, 1/1), not true/false-call labels, drawn from the GRCh38 liftover of the 1000 Genomes phase-3 integrated SV map, and the short-read model was trained across **many 1000 Genomes individuals**.

**F4.** samplot-ML excluded individuals present in, or directly related to, its test individuals (NA12878, NA12891, NA12892, HG00512, HG00513, HG00731, HG00732, NA19238, NA19239). The authors state that distantly related individuals remain and that, given shared ancestral history, **some SVs in the test set also appeared in the training set**.

**F5.** Because samplot-ML genotypes the same catalogued deletion sites across many individuals, the same site does carry different genotype labels in different people. The paper presents this as a natural consequence of the genotyping formulation, not as a deliberately constructed matched-pair design.

**F6.** Cue performs SV discovery and genotyping — it predicts type, genotype and locus from images — rather than verifying candidates produced by a separate caller.

---

## 3. My inference about comparability (clearly separated from the facts above)

**I1.** DeepSVFilter is the closest prior work *by task* but is **not** comparable in supervision. Its negatives are drawn from different loci than its positives, so a model can in principle exploit locus-level cues (mappability, repeat context, region difficulty) that correlate with being a false call. PAIR-SV's matched design removes that particular shortcut by construction. This is an inference about what the design permits, not a claim that DeepSVFilter demonstrably exploits it — no experiment in either paper tests that.

**I2.** samplot-ML **is** substantively comparable on the specific axis PAIR-SV claims as novel. Training a CNN on image representations across many individuals, with genotype labels at catalogued sites, necessarily produces cases where one site is 0/0 in one person and 0/1/1/1 in another. Functionally, that is same-site, different-individual, different-label supervision. The difference from PAIR-SV is one of **deliberateness and control**, not of whether such examples exist:

- PAIR-SV *constructs* the pairing explicitly (12,272 same-site candidate pairs, exactly 50,000/50,000 balanced, with each locus contributing both a positive and a confidently-genotyped negative row), and gates it on genotype quality, callability and conflict exclusion.
- samplot-ML obtains such cases *incidentally* from the genotyping formulation, without balancing, pairing, or (per F4) fully excluding site-level overlap between train and test.

**I3.** PAIR-SV's genuinely distinct methodological element is therefore **not** "same-site supervision exists" but "same-site supervision is deliberately constructed, balanced, and then *tested* for residual locus shortcuts." The leakage probes in §8 (metadata-only AUC 0.575 against a pre-registered 0.65 ceiling; allele-frequency-only AUC 0.500/0.501; train-locus prior applied to validation AUC 0.531) quantify what samplot-ML acknowledges qualitatively but does not measure. I could not find any prior SV paper that quantifies a locus-memorisation shortcut in this way — but see U2.

**I4.** Relevant to Narrative B rather than to novelty: **the closest prior filtering work is itself HG002-centric.** DeepSVFilter's deletion model is trained on HG002 (F2), and GIAB HG002 is a standard evaluation genome across this literature. That is precisely the single-genome dependence PAIR-SV's 30-person cohort result cautions against. This *supports* Narrative B's framing without requiring any claim that prior work is wrong — and it should be stated carefully, since DeepSVFilter used HG002 for *training*, whereas our critique concerns single-genome *evaluation*. Conflating those two would be unfair to that paper.

---

## 4. Does PAIR-SV's novelty claim need to be narrowed? **Yes.**

The current wording in §3 of the manuscript is:

> "PAIR-SV's contribution relative to this line of work is (a) explicit same-site matched supervision across many individuals rather than single-sample training, and (b) a systematic ladder isolating the marginal contribution of each added evidence type…"

Clause (a) is **not defensible as written**. "Same-site matched supervision across many individuals rather than single-sample training" reads as a claim of priority over multi-individual same-site learning, and samplot-ML (F3, F5) already trains across many individuals in a way that yields same-site, differently-labelled examples. The contrast with "single-sample training" is fair against DeepSVFilter (F2) but false against samplot-ML.

**Minimum honest narrowing:**

> PAIR-SV's contribution relative to this line of work is (a) a *deliberately constructed and balanced* same-site matched-pair design — each candidate locus contributes both a positive row in a carrier and a confidently-genotyped reference row in a different individual — together with explicit, quantified probes for residual locus-level shortcuts, rather than same-site examples arising incidentally from a genotyping formulation; and (b) a systematic ladder isolating each evidence type's marginal contribution under both post-hoc and retrained ablation.

The claim that must be dropped entirely is any implication that multi-individual, same-site learning is itself new. It is not.

**What this does not affect.** The evaluation-methodology contribution — Narrative B — is untouched by this literature. None of the papers surveyed performs a pre-registered, checksummed, one-shot evaluation on an untouched, relatedness-screened, superpopulation-balanced 30-person cohort, nor reports a single-genome model-ordering result being overturned by a population sample. Narrative B remains fully defensible and is now, in my judgement, clearly the stronger of the paper's two candidate contributions.

---

## 5. Unresolved uncertainty

**U1.** **samplot-ML's exact pairing statistics are unverified.** I established that same-site/different-genotype examples occur, but not how frequently, nor whether any balancing was applied. A reviewer familiar with that paper could reasonably push further. Resolving this would require reading the samplot-ML training-set construction code or the supplementary material; the Genome Biology full text was behind a redirect/auth wall for two access routes, and PMC gave the methods summary quoted above rather than the full construction detail.

**U2.** **I cannot prove a negative.** My claim that no prior SV work quantifies a locus-memorisation shortcut (I3) rests on a targeted search that returned nothing relevant, not on exhaustive review. It should be stated in the manuscript as "we are not aware of" rather than "no prior work does."

**U3.** **CSV-Filter (2024) unread.** A recent, directly-adjacent filtering method whose supervision scheme was not verified. This is the most likely source of a surprise and should be read before submission.

**U4.** **Long-read and graph-based methods not surveyed.** The audit was scoped to short-read image/CNN methods. If the paper's related-work section claims anything about the broader SV-classification field, that scope limit must be stated.

**U5.** **`pbsv` still has no identifiable primary publication** (carried over from the Week 4 audit). It should be cited as software, not as an article.

---

## 6. Verified bibliographic metadata

Ready to cite. Each was confirmed against a publisher or PubMed record during this audit.

| Key | Full citation | Verified via |
|---|---|---|
| liu2021deepsvfilter | Liu Y, Huang Y, Wang G, Wang Y. A deep learning approach for filtering structural variants in short read sequencing data. *Briefings in Bioinformatics*. 2021;22(4):bbaa370. doi:10.1093/bib/bbaa370. PMID: 33378767 | PubMed record + publisher full text |
| belyeu2021samplot | Belyeu JR, Chowdhury M, Brown J, Pedersen BS, Cormier MJ, Quinlan AR, Layer RM. Samplot: a platform for structural variant visual validation and automated filtering. *Genome Biology*. 2021;22:161. doi:10.1186/s13059-021-02380-5. PMID: 34034781 | PubMed record + PMC full text |
| popic2023cue | Popic V, Rohlicek C, Cunial F, et al. Cue: a deep-learning framework for structural variant discovery and genotyping. *Nature Methods*. 2023;20:559-568. doi:10.1038/s41592-023-01799-x | Publisher record |

**Not yet verified — do not cite until checked:** CSV-Filter (*Bioinformatics* 2024;40(9):btae539), NPSV-deep (*Bioinformatics* 2024;40(3):btae129), DeepSVP (*Bioinformatics* 2022;38(6):1677). Metadata appeared in search results but was not confirmed against the publisher record, and their methods were not read.

**Still outstanding from the Week 4 audit** (unchanged, not re-verified here): Manta, DELLY, LUMPY/smoove, Sniffles, pbsv, HyenaDNA, NIST v0.6, GIAB v5.0q release, Truvari, DeepVariant, PanGenie/HGSVC2, 1000G NYGC high-coverage.

---

## Sources

- [A deep learning approach for filtering structural variants in short read sequencing data — PubMed](https://pubmed.ncbi.nlm.nih.gov/33378767/)
- [A deep learning approach for filtering structural variants in short read sequencing data — Briefings in Bioinformatics](https://academic.oup.com/bib/article/22/4/bbaa370/6055714)
- [Samplot: a platform for structural variant visual validation and automated filtering — PubMed](https://pubmed.ncbi.nlm.nih.gov/34034781/)
- [Samplot: a platform for structural variant visual validation and automated filtering — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8145817)
- [Cue: a deep-learning framework for structural variant discovery and genotyping — Nature Methods](https://www.nature.com/articles/s41592-023-01799-x)
- [CSV-Filter — Bioinformatics](https://academic.oup.com/bioinformatics/article/40/9/btae539/7750355)
- [NPSV-deep — Bioinformatics](https://academic.oup.com/bioinformatics/article/40/3/btae129/7623007)
- [DeepSVP — Bioinformatics](https://academic.oup.com/bioinformatics/article/38/6/1677/6482742)
