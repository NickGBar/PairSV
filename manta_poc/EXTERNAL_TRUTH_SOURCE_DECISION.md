# External truth-source decision — GIAB HG002 SV benchmark

**Status: FROZEN as of 2026-08-04, before any HG002 model result has been opened or evaluated.** This document supersedes the version-selection ambiguity left open in `manta_poc/EXTERNAL_COHORT_IDENTIFICATION.md`. It was produced entirely from direct `curl` queries against `https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/HG002_NA24385_son/` (raw Apache directory listings and file contents), not from AI-summarized web search, per the requirement to inspect the official listings directly.

---

## 1. Every plausible GRCh38-native assembly-based candidate found

Only one GRCh38-native, genome-wide SV benchmark package exists for HG002 on the official GIAB FTP: **v5.0q**. (CMRG_v1.00 is GRCh38-native and assembly-based but restricted to challenging medically-relevant genes, not genome-wide — considered separately below, not as a primary candidate.)

### v5.0q — `.../HG002_NA24385_son/v5.0q/`

| Field | Value |
|---|---|
| Exact directory | `https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/HG002_NA24385_son/v5.0q/` (also mirrored at `.../latest/`, confirming it is the current release pointer as of 2026-08-04) |
| Truth VCF (GRCh38) | `HG002_GRCh38_v5.0q_stvar.vcf.gz` (48,040,012 bytes) + `.tbi` |
| Benchmark BED (GRCh38) | `HG002_GRCh38_v5.0q_stvar.benchmark.bed` (230,609 bytes) |
| Exclusion stats | `HG002_GRCh38_v5.0q_stvar.exclusion_stats.txt` |
| Release/version identifier | v5.0q (dated 2026-03-02 for benchmark files; README updated 2026-07-17) |
| Release or Draft status | **Explicitly self-labeled "Draft"** — README title is literally "v5.0q GIAB HG002 Assembly-Based Small & Structural Variant **Draft** Sets"; internal filename `NIST_HG002_DraftBenchmark_defrabbV0.020-20250117_README.md`; LIMITATIONS section states "generated using a new assembly-based approach which is under active development, therefore benchmarking results generated using these benchmarks should be carefully evaluated" and "As these benchmark sets are a work in progress we appreciate and welcome feedback." Not yet peer-reviewed ("We plan to publish this work soon"). |
| Assembly | Built from the **T2T HG002 Q100 v1.1 diploid assembly** via `dipcall` (assembly-to-reference alignment-based variant calling) run through NIST's `defrabb` pipeline — genuinely assembly-based, matching the mission's stated preference. Also available natively for GRCh37 and CHM13v2.0 (not used here). |
| Truth VCF availability | Yes, GRCh38-native, no liftover |
| Confident/benchmark BED availability | Yes, `HG002_GRCh38_v5.0q_stvar.benchmark.bed`, explicitly designed as a paired VCF+BED for accuracy benchmarking |
| Checksums | **Yes, official NIST-provided** `checksum.md5` covering every file in the release. Verified locally: `HG002_GRCh38_v5.0q_stvar.vcf.gz` MD5 `34dbeeac5eb3fc09e94c5cb8cfe9e24f` — **matches exactly**. Same for `.benchmark.bed` (`55fc11c80ff376c0a8da99d0c69004f3`) and `.exclusion_stats.txt` (`92bdc427ad4fb4c1e7954d715e276e43`) — **both match exactly**. |
| README and intended benchmarking use | Comprehensive (`NIST_HG002_v5.0q_variant-benchmarksets_README.md`, 334 lines). Explicitly recommends **Truvari with `--refine`** for SV comparison (the same tool family, `truvari bench`, already frozen throughout this project) and gives the exact command template. Explicitly states the VCF+BED pair is "intended to be used... to benchmark accuracy of small and structural variant calls," designed for both TP/FP/FN classification. |
| DEL count >=50bp | **16,625** PASS/unfiltered (FILTER `.`/`HET1`/`HET2`, excluding `GAP`-flagged records) DEL records with `\|SVLEN\|>=50`, counted directly from the downloaded, checksum-verified VCF (39,081 total DEL records at any size; most below 50bp are small-variant-scale deletions co-included in this combined smvar+stvar VCF). |
| FP and FN evaluation | Yes — the benchmark BED defines confident regions in which the truth VCF is asserted comprehensive, the standard GIAB design for symmetric FP/FN assessment (candidate calls outside a truth match within the BED = FP; truth variants inside the BED with no matching candidate = FN). |

### CMRG_v1.00 (considered, not selected as primary)

GRCh38-native, assembly-based, but scoped to challenging medically-relevant genes only (a curated gene list), not a genome-wide deletion benchmark. Retained as a possible future subgroup/stratification source (mission Week 4 item 1: "difficult genomic regions where reliable annotations are available"), not as the primary external truth source.

---

## 2. Mature comparator — GIAB NIST SV v0.6

| Field | Value |
|---|---|
| Exact directory | `https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/HG002_NA24385_son/NIST_SV_v0.6/` |
| Truth VCF | `HG002_SVs_Tier1_v0.6.vcf.gz` (25,738,211 bytes) + `.tbi` |
| Tier 1 high-confidence BED | `HG002_SVs_Tier1_v0.6.bed` (725,960 bytes) — "defines regions in which HG002_SVs_Tier1_v0.6.vcf.gz should contain close to 100% of true insertions and deletions >=50bp" (verbatim from README) |
| Coordinate system | **GRCh37-native.** README states explicitly: "GRCh38 callsets are under development" (as of this README) — no native GRCh38 version was ever released for v0.6. |
| Checksums | **None provided by NIST for this release** (no `checksum.md5` in the v0.6 directory, unlike v5.0q). Locally computed after download for our own provenance: `HG002_SVs_Tier1_v0.6.vcf.gz` MD5 `78bceed7edda5c4ae373f5e4c31f72cd` (self-computed, not an NIST-issued reference value — recorded here as the value future re-downloads must match). |
| Maturity | Published 2018-2020, described in a preprint (doi:10.1101/664623), used extensively across the field for years — genuinely mature, in contrast to v5.0q's Draft status. |
| Known, self-reported limitation | README states verbatim: "it likely only includes 50% or less of the total SVs in the genome, **and is likely biased towards easier SVs**." Complex/ambiguous SVs are explicitly moved to a separate Tier 2 (not comprehensive, not usable for symmetric FP/FN the way Tier 1 is). |
| DEL count >=50bp | **5,464** PASS-filter DEL records with `\|SVLEN\|>=50`, counted directly from the downloaded VCF (out of 74,012 total union candidate records, 12,745 PASS). Roughly **1/3 as many usable truth deletions as v5.0q**, consistent with v0.6's own stated <=50% genome-wide SV coverage and easier-SV bias. |
| FP and FN evaluation | Yes — this is exactly why the Tier 1 BED was introduced in v0.6 ("New to v0.6, we have defined high-confidence regions to accompany the Tier 1 calls... enable users to assess FPs as well as FNs"). |

---

## 3-6. Decision

**Per the mission's own stated rule (item 4):** *"Select a GRCh38-native benchmark as primary only if it contains a versioned, documented, checksum-verifiable truth VCF plus benchmark BED suitable for FP and FN evaluation."*

v5.0q satisfies every listed technical criterion:
- versioned — yes (v5.0q, dated, with a `latest/` pointer confirming currency)
- documented — yes (334-line README, explicit methodology section, explicit Truvari usage instructions)
- checksum-verifiable — yes, **and independently verified in this session** (3/3 files matched NIST's own published MD5s exactly)
- truth VCF + benchmark BED suitable for FP/FN — yes, by explicit design and README statement

**Decision: v5.0q (GRCh38, native) is selected as the PRIMARY external truth source.**

Per mission item 7, GIAB NIST SV v0.6 (GRCh37, native, Tier 1 VCF + Tier 1 BED, **no liftover**) is selected as the **secondary / sensitivity benchmark**, run as a fully separate pipeline pass against a GRCh37-aligned HG002 alignment and GRCh37 reference — never mixed coordinate systems, never a self-created liftover of either benchmark, per item 6's explicit prohibition.

Item 6 (do not use dbVar-remapped GRCh38 calls alone for specificity/FP benchmarking) is satisfied by construction — neither selected source is a dbVar remap; v5.0q is natively generated in GRCh38 coordinates directly from the assembly-to-GRCh38 `dipcall` alignment, not remapped from another assembly's calls.

---

## 7. Rationale, limitations, and the two-benchmark design

**Rationale:** v5.0q is native to the same reference (GRCh38) already used throughout every stage of this project — the frozen Manta pipeline, gate 2/3, and Phase F all operate on GRCh38 coordinates. Using v5.0q as primary avoids introducing a liftover step (itself a source of coordinate error for structural variants specifically, which are exactly the class of variant most sensitive to liftover artifacts) into the primary result. It is also methodologically the more rigorous design (assembly-based, includes previously-inaccessible difficult regions) and has ~3x more usable DEL>=50bp truth records than v0.6, giving a materially more powerful test of recall (false-negative sensitivity) specifically.

**Known limitations of the PRIMARY (v5.0q) benchmark — to be stated explicitly in the manuscript, not hidden:**
- Formally a Draft release, not yet peer-reviewed, explicitly flagged by NIST as "under active development."
- New assembly-based methodology with less multi-year field validation than v0.6.
- NIST's own guidance recommends curating a subset of putative FPs/FNs to check whether disagreements are comparison-tool artifacts, benchmark errors, or genuine representation differences — this project will follow that guidance rather than treating every mismatch as a genuine PAIR-SV error.

**Known limitations of the SECONDARY (v0.6) benchmark:**
- Self-reported to cover "50% or less" of true genome-wide SVs, with a bias toward "easier" SVs — likely to overstate specificity/precision relative to the true difficulty of the task, since a large share of genuinely hard true deletions are absent from its truth set entirely (silently reducing the effective FN-detection power, not eliminating FPs).
- GRCh37-native — requires a GRCh37-aligned HG002 CRAM/reference for its own pipeline pass, entirely separate infrastructure from the GRCh38 pipeline used everywhere else in this project.
- No NIST-issued checksum for this specific release (self-computed and recorded for our own provenance instead).

**Two-benchmark design:** results from v5.0q (primary) and v0.6 (secondary/sensitivity) will be reported **separately, never pooled**, exactly as the frozen protocol already requires for every other cross-cohort comparison in this project. Agreement between the two would strengthen confidence in the external result; disagreement would itself be a reportable, honestly-discussed finding (consistent with the mission's hard constraint against hiding negative or inconvenient results).

---

*Files retained locally under `/private/tmp/.../scratchpad/giab_hg002/` this session for verification; not yet copied into the permanent artifact tree — that happens at Week 2 execution time, alongside the actual HG002 CRAM download, per `manta_poc/EXTERNAL_EVAL_PROTOCOL_FROZEN.md`. No HG002 model inference or evaluation has been performed. This document resolves the truth-source choice only.*
