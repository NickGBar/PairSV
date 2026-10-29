# PAIR-SV frozen external-evaluation protocol

**Status: FROZEN as of 2026-08-04, before any external CRAM has been downloaded or any external label has been opened.** Nothing in this document may change after external processing begins. Any change required after that point is itself a reportable event (see "Escalation triggers" in `paper/PUBLICATION_LEDGER.md`), not a silent edit.

This protocol governs Week 2-3 of the publication mission (`paper/PUBLICATION_LEDGER.md`). It reuses, unchanged, every frozen artifact from the 5-person realistic Manta POC (gate 2 + gate 3 + Phase F, decisions 0029-0041) plus the newly-frozen seed-ensemble deployment thresholds (`manta_poc/truvari_gate2/phase_f/phaseF_deployment_thresholds_FROZEN.json`).

---

## 1. External cohort requirements

- Must not overlap the 50-person controlled Train40/val/internal-test cohort.
- Must not overlap the 5-person realistic Manta POC (HG00108, HG01912, HG00736, HG00436, HG02601).
- **Truth source resolved and frozen (see `manta_poc/EXTERNAL_TRUTH_SOURCE_DECISION.md`, decision 0044):**
  - **PRIMARY:** GIAB HG002, `HG002_GRCh38_v5.0q_stvar.vcf.gz` + `HG002_GRCh38_v5.0q_stvar.benchmark.bed` (GRCh38-native, assembly-based via dipcall on the T2T-HG002-Q100-v1.1 diploid assembly). MD5-verified against NIST's own `checksum.md5`. Formally a Draft release — reported as such, not hidden.
  - **SECONDARY/sensitivity:** GIAB NIST SV v0.6 Tier1, `HG002_SVs_Tier1_v0.6.vcf.gz` + `HG002_SVs_Tier1_v0.6.bed` (GRCh37-native, no liftover). Run as a fully separate pipeline pass against a GRCh37-aligned HG002 CRAM/reference. Results reported separately, never pooled with the primary.
- Person is the statistical unit throughout. Candidate rows are never treated as independent biological samples, and candidate-row bootstrap is never used as a substitute for person-level generalization.

## 2. Frozen software/data versions (byte-identical to the 5-person POC, no exceptions)

| Component | Frozen value |
|---|---|
| Manta | version 1.6.0, container `quay.io/biocontainers/manta`, digest `sha256:48d0c2464fa0129935438c5cddec5f67c4b3d65e8f7a647f95164ee51662cc70` |
| Reference genome | GRCh38_full_analysis_set_plus_decoy_hla.fa, sha256 `3b103f4742abfd54938fb0333e19ad067635c8eb86f1dbf0ce44b165c4292b50` |
| Truvari | version 5.4.0, params: `--refdist 500 --pctseq 0.7 --pctsize 0.7 --pctovl 0.0 --sizemin 50 --sizefilt 30 --sizemax 50000 --pick single` |
| HyenaDNA | `LongSafari/hyenadna-small-32k-seqlen-hf` @ revision `8fe770c78eb13fe33bf81501612faeddf4d6f331`, CUDA + bfloat16 (original scripts, unmodified) |
| Checkpoints | `kaggle/deepsv-ms-train40-ckpt-seed{1,2,3}/output-v1/pairsv_train40_seed{20260720,20260721,20260722}_{M0,M2,M4}.pt` — verified against `reports/train40/frozen_checkpoint_checksums.json` before use |
| Extraction code | `deepsv/multisample/extraction.py` (`Candidate`, `RemoteCramSession`, `extract_example_from_reads`, `build_candidate_refalt_tokens`) verbatim |
| Embedding code | `scripts/embed_pairsv_refalt.py`, `scripts/embed_pairsv_reads.py` verbatim |
| Deployment thresholds | M0=0.697741, M2=0.695706, M4=0.730540 (mean-of-3-seeds ensemble probability), from `manta_poc/truvari_gate2/phase_f/phaseF_deployment_thresholds_FROZEN.json` — selected on the 5 POC people ONLY, never touched by external data |

## 3. Candidate inclusion rules (frozen, identical to the 5-person POC)

- Source: Manta's own `diploidSV.vcf.gz`, records with `FILTER=PASS` and `INFO/SVTYPE=DEL`.
- Original Manta coordinates (`POS`+`END`/`SVLEN`) used as model input throughout — never recentered or replaced by truth coordinates.
- Candidate length bound for model extraction: 50-10,000bp (the `Candidate` dataclass's hard bound). Records outside this range are tracked as `failed_length_outside_50_10000bp_candidate_bound`, not silently dropped.
- Truvari's own `sizemax=50000` separately excludes >50kb records from 3-class labeling (`excluded_size_gt50kb` bucket) — distinct from the 10kb model-input bound.

## 4. Pipeline execution order (strict — no step may be reordered or skipped)

```
CRAM
  -> Manta whole-genome (frozen config, same digest)
  -> Truvari 3-class truth matching (Positive / Known-negative / Unknown; two-pass, carrier and 0/0 truth NEVER pooled)
  -> candidate manifest (original Manta coordinates + gate-2 label)
  -> CRAM feature extraction (images/scalars/read-tokens/refalt-tokens)
  -> HyenaDNA embedding (CUDA/bfloat16, original scripts)
  -> frozen M0/M2/M4 inference, all 3 seeds
  -> ensemble (mean probability across 3 seeds)
  -> apply frozen deployment threshold (per model, from step 2 above)
  -> hash all predictions (SHA-256) and write the hash to disk
  -> ONLY THEN: join against external truth labels and compute metrics
```

No threshold, feature, model, matching parameter, or exclusion rule may be tuned after this last step. If a result looks wrong, it is reported as-is with an honest failure-mode discussion, not corrected by revisiting an earlier step.

## 5. Metrics (primary and secondary)

**Primary:** specificity at the frozen ~95% recall operating point (the deployment thresholds from §2), reported **per person**, then macro mean + standard deviation across people. Pooled-row metrics are secondary only, never primary.

**Secondary, per person and macro-aggregated:**
- actual recall, precision, F1, balanced accuracy, MCC, ROC-AUC, PR-AUC
- filtered-candidate rate (fraction of ALL Manta PASS DEL candidates, including Unknown, rejected by the threshold)
- Positive / Known-negative / Unknown counts
- extraction failure rate (with failure-reason breakdown, never silently dropped)

**Baseline:** accept-all-Manta baseline computed and reported alongside, same convention as Phase F (`manta_poc/truvari_gate2/phase_f/PHASE_F_REPORT.md` §3): recall=1, specificity=0, precision=prevalence, MCC reported as mathematically-undefined-by-construction with the sklearn 0.0 convention noted explicitly.

## 6. Subgroup definitions (frozen, identical structure to Phase F)

- Length: 50-200bp, 200-1000bp, 1000-10,000bp — full metrics (both classes present).
- Breakpoint-error (Positive-only): exact (0bp), 1-10bp, 11-50bp, 51-100bp, >100bp — recall + score distribution, not F1.
- Genotype (Positive-only, where supported by the external truth source): 0/1, 1/1 — recall + score distribution, not F1.
- Ancestry / superpopulation — only if external cohort sample size permits meaningful subgroup counts; not forced.
- Unknown candidates: NEVER included in any supervised metric. Score distribution + predicted-positive rate only.

## 7. Failure handling

- Any CRAM download, Manta run, extraction, embedding, or scoring failure is recorded with its failure reason and reported in the final results — never hidden, never silently retried into a different outcome without a note.
- Environment differences from the POC (e.g. different cluster, different GPU) are recorded in an environment manifest, following the same convention as `manta_poc/truvari_gate2/phase_f/environment_manifest.json`.

## 8. Explicit non-negotiables (carried from the mission's hard constraints)

- The frozen internal 5-person controlled test is never reopened.
- The 5-person realistic POC is never used as, or presented as, this external test.
- v1 (checkpoints, thresholds, normalization, features) is never modified based on what the external results show.
- M0 vs M2 vs M4 is never chosen after seeing external performance — M4 remains the predefined primary model, M0/M2 remain mandatory baselines, all three are reported.
- If the external result is weaker than the 5-person POC, it is reported honestly as a degradation, not corrected by re-touching v1.

---

## ADDENDUM (appended 2026-08-04, before any HG002 CRAM download or processing — an authorized pre-execution amendment, not a post-hoc change; the freeze in the document header still governs everything from the moment HG002 processing actually begins)

### 9. Benchmark-region rule

Primary evaluation (v5.0q) includes a candidate **only if both of its deletion breakpoints fall inside the `HG002_GRCh38_v5.0q_stvar.benchmark.bed` regions**. A candidate with one or both breakpoints outside the BED, or straddling a BED boundary, is **excluded from primary supervised metrics and reported separately** — it is never labeled a false positive, because the benchmark BED is precisely the region where v5.0q asserts truth-VCF comprehensiveness; outside it, absence of a truth match carries no evidentiary weight.

### 10. External labels (v5.0q primary pass — single-truth-VCF design, distinct from the 5-person POC's two-pass PanGenie design)

Unlike the 5-person POC (which used PanGenie's genotype-based carrier/reference truth split), v5.0q supplies one truth VCF + one confident-region BED — the standard GIAB design. Labeling is a **single** Truvari bench pass, not two:

```
truvari bench -b <v5.0q DEL>=50bp truth subset> -c <Manta PASS DEL> \
              --includebed HG002_GRCh38_v5.0q_stvar.benchmark.bed \
              -f <GRCh38 reference> -o <outdir> \
              --refdist 500 --pctseq 0.7 --pctsize 0.7 --pctovl 0.0 \
              --sizemin 50 --sizefilt 30 --sizemax 50000 --pick single
```

(Same frozen Truvari params as §2/§3 — only the truth source and the explicit `--includebed` differ from the 5-person POC's invocation.)

- **`tp-comp` (Manta PASS DEL matched to a v5.0q truth deletion) → Positive.**
- **`fp` that survives the independently-computed both-breakpoints-inside-BED check (§9) → Known negative** (inside the confident region, no truth match — a genuine, not merely unlabeled, absence).
- **Any candidate failing the both-breakpoints-inside-BED check (§9), regardless of Truvari's own tp/fp assignment → Unknown/excluded**, reported in its own bucket (`excluded_outside_or_crossing_benchmark_bed`), never merged into Known negative.
- Truth coordinates are never used as model input at any point — original Manta coordinates only (§3, unchanged).

The secondary/sensitivity pass (v0.6, GRCh37, no liftover) uses the same single-truth-VCF logic against `HG002_SVs_Tier1_v0.6.bed`, run as an entirely separate pipeline invocation against a GRCh37-aligned HG002 CRAM+reference, never mixed with the primary's GRCh38 candidates or labels.

### 11. Scope — length subgroup tiers (supersedes §6's flat length list for HG002 reporting)

| Range | Role |
|---|---|
| 50-200bp | **Primary** length subgroup |
| 200-1000bp | Secondary |
| 1000-10,000bp | Exploratory |
| >10,000bp | **Unsupported by PAIR-SV v1** — predefined exclusion (matches the `Candidate` dataclass's own 50-10,000bp hard bound, §3), reported as a count only, never scored |

### 12. Separate evaluation levels — do not conflate caller recall with filter precision

Two distinct numbers must be reported side by side and never merged into one headline claim:

1. **Manta end-to-end truth recall**: of all v5.0q truth deletions (>=50bp, DEL, inside the benchmark BED), what fraction were called by Manta at all (PASS DEL, any Truvari match, before PAIR-SV ever sees them)? This is a property of Manta, not PAIR-SV.
2. **PAIR-SV as a filter of Manta's own candidate set**: of the candidates Manta already produced, how well does PAIR-SV separate Positive from Known-negative (the primary/secondary metrics in §5)? PAIR-SV is evaluated **only** on this second question. The manuscript and every report must state explicitly that **PAIR-SV cannot recover a true deletion that Manta itself never candidated** — a low Manta end-to-end recall is not a PAIR-SV failure, and a high PAIR-SV filtering specificity does not imply high whole-pipeline (Manta+PAIR-SV) sensitivity to all true deletions in the genome.

---

*This protocol must be read together with `paper/PUBLICATION_LEDGER.md` for escalation triggers and overall mission status.*
