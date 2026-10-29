# PAIR-SV Project Progress Report

**Reporting cutoff:** 20 July 2026, through tracker record R49  
**Scope:** the current GRCh38 multisample PAIR-SV project. Earlier single-sample DeepSV work remains preserved as historical context and is not presented as evidence for this report.  
**Status:** intermediate validation completed; final 40/5/5 experiment is not complete; internal-test evaluation has not been opened.

## Technical summary

PAIR-SV is a candidate-genotyping system for genomic deletions. It asks whether a specific individual carries a preselected, sequence-resolved deletion candidate, rather than attempting whole-genome discovery. The system combines evidence from both deletion breakpoints, candidate REF/ALT sequence context, selected read sequences from the individual, and scalar read-support features.

The project successfully established a leakage-audited 50-person GRCh38 data design, verified remote indexed CRAM extraction, generated a strict 100,000-row manifest, and completed a controlled Train15 comparison using 15 training people and five validation people. In that frozen one-seed snapshot, full PAIR-SV (M4) obtained validation F1 **0.8062**, compared with **0.7991** for the dual-breakpoint image baseline (M0) and **0.7980** for image plus scalar features (M2). A paired row bootstrap supported a small M4 advantage over M0 and M2. The multimodal branches measurably affected predictions when zeroed.

This is encouraging but not a final success claim. The evidence is from model selection on a fixed validation cohort, one seed, and a row-level bootstrap that does not fully account for candidate-locus reuse. The 40-person training set, three-seed replication, candidate-cluster uncertainty, and untouched five-person internal test are still outstanding. The project has therefore produced a scientifically defensible **intermediate validation result**, not a completed final experiment or a production SV caller.

## 1. Research question and original trajectory

The project began from a practical limitation of image-only deletion classifiers: a deletion has two breakpoints, an allele hypothesis, and sample-specific read evidence, but a single pileup image represents only part of that information. The central question was whether a dual-breakpoint CNN could gain useful signal from three additional branches:

1. candidate-level GRCh38 REF/ALT sequence representations;
2. selected read-sequence representations from the individual being genotyped; and
3. scalar summaries of conventional deletion evidence.

The original multisample plan targeted 100 unrelated 1000 Genomes individuals. The execution plan was subsequently revised for available compute, while keeping the architecture and scientific success threshold intact. The active plan became:

| Design element | Current committed design |
|---|---|
| Cohort | 50 unrelated 1000 Genomes/IGSR individuals |
| Final split | 40 train / 5 validation / 5 untouched internal test |
| Target examples | approximately 1,000 positives and 1,000 matched negatives per person; approximately 100,000 rows |
| Reference | GRCh38 only, using the exact CRAM decoding FASTA |
| Labels | HGSVC2/PanGenie sequence-resolved deletion genotypes; explicitly treated as silver labels |
| Primary negative | same candidate locus in another person with confident 0/0 genotype |
| Final success threshold | mean internal-test F1 >= 0.72 across three seeds, consistent direction, improvement over M0, branch dependence, and no leakage |

The reduction from 100 to 50 people was a compute-scheduling decision, not an attempt to lower the final performance threshold. The final test cohort was deliberately held back from architecture selection and has not been used for model metrics.

## 2. Data sources, label policy, and why same-site negatives matter

The project used public, versioned resources chosen to be coordinate-compatible with GRCh38:

- the 1000 Genomes/IGSR NYGC high-coverage approximately 30x CRAM collection and CRAI indexes;
- `GRCh38_full_analysis_set_plus_decoy_hla.fa` for CRAM decoding;
- the HGSVC2 PanGenie genotype callset `pangenie_merged_bi_nosnvs.vcf.gz`;
- official high-coverage sequence-index metadata for verified sample-to-CRAM mappings; and
- later, frozen HyenaDNA encoders for candidate and read embeddings.

The inclusion rules were deliberately strict. Positive rows require a valid sequence-resolved GRCh38 deletion of 50--10,000 bp, non-missing genotype 0/1 or 1/1, GQ >=20, a valid REF/ALT representation, and selected site-quality requirements. Same-site negative rows require non-missing 0/0, GQ >=20, callability, no conflicting overlapping deletion call, and adequate read coverage confirmed during extraction. GQ and label provenance are retained for quality control but excluded from model inputs.

Same-site negatives are the most important design decision. A positive individual and a negative individual may share the same `candidate_id`, chromosome, coordinates, and REF/ALT sequence representation. The model must therefore respond to the individual-specific pileups, read sequences, and scalar evidence rather than simply learning that a genomic locus is often a deletion. This is a stronger genotype-level control than using random genomic negatives, although it does not eliminate every residual locus-related correlation.

## 3. What was implemented

### 3.1 Production data pipeline

The project implemented reusable multisample code under `deepsv/multisample/` and associated runner scripts. The production extractor:

- uses remote indexed CRAM access rather than downloading complete alignments;
- validates the exact GRCh38 reference;
- fetches both breakpoint regions with bounded retries, exponential backoff, timeout handling, and CRAM reopening after transport failure;
- records failed candidates explicitly instead of writing silent all-zero replacements;
- creates left and right breakpoint pileups, selected read tokens/masks, scalar features, and candidate-level REF/ALT tensors;
- deduplicates candidate REF/ALT context by candidate ID;
- writes chunked HDF5 shards with stable row identifiers, success/failure flags, failure reasons, and checksums; and
- keeps sample ID, population, split, GQ, allele frequency, negative type, source filename, and read-name hash out of model tensors.

The primary tensor schema is:

| Artifact | Stored shape / design |
|---|---|
| Breakpoint images | `(2, 6, 64, 128)` uint8 per row |
| Read tokens | `(2, 48, 128)` per row |
| Read masks | `(2, 48)` per row |
| Scalar evidence | 17 float features per row |
| Candidate REF/ALT | `(2, 1024)` tokens, deduplicated by candidate ID |
| Candidate embedding | five 256-dimensional representations, 1,280 dimensions total |
| Read embedding | 768-dimensional mask-aware pooled representation |

The 17 scalar features cover left/right soft clips, split and supplementary evidence, discordant pairs, reference-spanning reads, candidate ALT-support count, inside/flank depth, depth ratio, mapping and base quality, insert-size statistics, left/right evidence balance, and log deletion length.

### 3.2 Model ladder

The following controlled variants were implemented and smoke-tested:

| Model | Inputs |
|---|---|
| M0 | left/right breakpoint pileups with tied CNN encoders |
| M1 | M0 + candidate REF/ALT representation |
| M2 | M0 + scalar evidence |
| M3 | M0 + pooled sample-specific read embeddings |
| M4 / PAIR-SV | M0 + candidate REF/ALT + reads + scalars, with residual late fusion |

M4 uses one identity-at-initialization mechanism so that the image-only path is preserved at initialization. The model smoke gate verified finite forward values and losses, non-zero finite gradients, loader alignment, branch effects on logits, and rapid learning of a synthetic oracle signal. This prevented interpreting an implementation defect as a biological or architectural null result.

### 3.3 Private Kaggle packaging and execution

Only audited source packages were uploaded to a private Kaggle dataset. The export process explicitly checked that payloads contained no credentials, tokens, private keys, alignments, VCFs, HDF5 shards, sample outputs, signed URLs, or unrelated files. The private code dataset evolved through versions as runners and embedding code were added. No project data were made public.

## 4. Stage-by-stage execution and results

### 4.1 Stage 0: source audit and feasibility

The initial source audit established that the public GRCh38 reference, high-coverage CRAMs, and PanGenie callset were compatible. The filtered candidate catalog contained approximately **34,402** deletion loci. Before the per-person cap, there were roughly 8,000--10,000 deletion-positive genotypes per person and abundant same-site 0/0 negatives.

The first audit run was only partially successful because the VCF reader and pedigree path were not yet robust. A corrected second run downloaded and indexed the needed VCF data and established a go decision. This was a data-access implementation issue, not evidence against the scientific design.

### 4.2 Mandatory CRAM proof of concept

The remote-CRAM proof of concept used HG01879 and HG00096, with 60 balanced sample-candidate rows. Both CRAMs opened against the exact GRCh38 reference. Both breakpoint windows contained reads for all 60 examples. The observed average evidence separated positives from same-site negatives:

| Feature | Positive | Same-site 0/0 negative |
|---|---:|---:|
| Inside/flank depth ratio | 0.68 | 0.92 |
| Soft clips | 106 | 49 |
| Split reads / SA | 32 | 5.7 |
| Discordant pairs | 52 | 11 |
| Mean MAPQ | 43 | 51 |

The interpretation is narrow but important: at the same candidate locus, different individuals showed different sample-specific evidence. This passed the remote-access and genotype-evidence feasibility gate. It did **not** prove model performance.

### 4.3 Manifest construction and leakage gate

An early 50-person manifest structurally met its row-count and label rules, but failed a metadata leakage probe. The metadata-only ROC-AUC was **0.68977**, above the precommitted 0.65 threshold; allele frequency alone had AUC **0.68589**. This was a genuine scientific failure, not an infrastructure failure. The extractor was not launched from that manifest.

The cause was insufficiently tight matching: high-frequency positive loci were easier to identify from metadata because confident callable 0/0 support was not equally represented. The corrective action was to require split-local positive/0/0 pairability, use continuous allele-frequency matching, and apply deterministic length, chromosome, and GQ tie-breaks. The resulting strict v4 manifest passed:

| Strict-manifest result | Value |
|---|---:|
| Rows | 100,000 |
| Class balance | 50,000 positive / 50,000 negative |
| People | 50 |
| Unique candidate loci | 14,597 |
| Same-site candidates | 12,272 |
| Metadata-only ROC-AUC | 0.57484 |
| AF-only AUC, train / validation | 0.50001 / 0.50056 |
| Train-locus-prior to validation AUC | 0.53066 |

This episode materially improved the validity of the study. It is also an important warning: balanced classes alone are not adequate protection against label or locus shortcuts.

### 4.4 Validation extraction: subset gate and full shard

Before the full validation shard, a deterministic 40-row subset included short, medium, and long deletions, heterozygous and homozygous-alt positives, and same-site negatives. It passed tensor shapes, finite scalars, non-empty reads/images, same-site coordinate identity, sample-specific evidence difference, and model-whitelist checks.

The full validation shard then processed the five validation people:

| Full shard-0 metric | Result |
|---|---:|
| Planned rows | 10,000; 5,000 positive / 5,000 negative |
| Successful rows | 9,981 |
| Explicit failures | 19 / 10,000 = 0.19% |
| Failure types | 15 empty breakpoint-read; 4 inadequate flank coverage |
| Wall time | 4,093.94 s (68.23 min) |
| Throughput | 2.438 examples/s |
| HDF5 size | 63 MB |
| Same-candidate positive/negative coordinate-identical pairs | 3,412 |

The full shard passed schema, finite-value, non-empty-tensor, GQ, split, class-balance, coordinate, whitelist, and visual-QC gates. The HDF5 checksum was independently verified. The failure rate remained below the precommitted 1% threshold. No failed inputs were silently filled with model-ready zeros.

### 4.5 Train15 extraction and frozen embeddings

Three audited train shards supplied the first 15 training people. Their successful rows totalled **29,924**. The validation cohort contributed **9,981** successful rows. Candidate REF/ALT embeddings were deduplicated across **11,200** train candidates; read embeddings aligned exactly to all 29,924 successful train rows. Validation candidate embeddings had five finite `(4,289, 256)` representations, and validation read embeddings were finite `(9,981, 768)` mask-aware pools with positive selected-read counts.

Alignment checks established one-to-one correspondence between source shard row identifiers and embedding rows. This was essential because a misalignment would create a silent label or sample-evidence error.

## 5. Controlled Train15 results

### 5.1 Why earlier model values were not accepted as the main conclusion

The first M0 runner produced a preliminary fixed-threshold F1 of 0.79476 but did not save row-aligned logits or the full metric set. M2 and an early M4 run used richer outputs and different threshold handling. It would have been a methodological mistake to compare these heterogeneous results as if they were controlled.

The project therefore reran M0, M2, and M4 on one exact frozen snapshot with the same rows, seed, five-epoch policy, training normalisation, metric implementation, and validation-F1 threshold selection. This R47 controlled run is the authoritative result for the interim report. The preliminary values remain in the ledger as historical artifacts but are not used for model-comparison claims.

### 5.2 Controlled metrics

The frozen snapshot contains 29,924 successful training rows from 15 people and 9,981 successful validation rows from five different people. All models were one-seed, maximum-five-epoch runs using seed 20260720, AdamW, mixed precision, train-only normalization, and a threshold selected on validation F1.

| Model | Val. loss | Threshold | Precision | Recall | F1 | ROC-AUC | PR-AUC | MCC | TN/FP/FN/TP | Parameters | Training time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| M0: images | 0.4261 | 0.415 | 0.7609 | 0.8413 | 0.7991 | 0.8836 | 0.8947 | 0.5807 | 3678 / 1318 / 791 / 4194 | 287,618 | 1,065 s |
| M2: images + scalars | 0.4242 | 0.445 | 0.7591 | 0.8411 | 0.7980 | 0.8844 | 0.8954 | 0.5780 | 3665 / 1331 / 792 / 4193 | 323,110 | 1,025 s |
| M4: full PAIR-SV | 0.4102 | 0.435 | 0.7668 | 0.8497 | 0.8062 | 0.8914 | 0.9003 | 0.5954 | 3708 / 1288 / 749 / 4236 | 622,374 | 1,044 s |

The primary descriptive finding is that M4 had the best values across the reported summary metrics in this one controlled validation run. M2 alone did not improve F1 over M0. The results do not show that every added modality independently improves performance; rather, they suggest that the full fused system performs modestly better than either M0 or the image-plus-scalar subset on this snapshot.

### 5.3 Paired bootstrap comparison

The validation predictions were row-aligned, so paired row bootstrap comparisons were possible. One thousand resamples gave:

| Comparison | Observed F1 difference | 95% paired row-bootstrap CI | Win proportion | Interpretation |
|---|---:|---|---:|---|
| M4 - M0 | +0.00697 | +0.00164 to +0.01238 | 0.995 | small positive support |
| M4 - M2 | +0.00815 | +0.00292 to +0.01381 | 1.000 | small positive support |
| M2 - M0 | -0.00096 | -0.00499 to +0.00337 | 0.350 | inconclusive |

The confidence intervals are useful but limited. They resample rows, while candidate loci can recur across people. The intervals therefore should not be read as fully independent-locus uncertainty. Candidate-cluster bootstrap is a required final-stage analysis.

### 5.4 Subgroup and branch-dependence findings

The short-deletion subgroup (50--200 bp) had recall 0.8211 for M0, 0.8193 for M2, and 0.8344 for M4. This is an encouraging direction, but it is an exploratory one-seed subgroup result, not a final claim.

For M4, zeroing a branch on saved validation inputs changed logits and lowered F1:

| M4 intervention | F1 | F1 change from full M4 | ROC-AUC change | PR-AUC change | Changed binary predictions |
|---|---:|---:|---:|---:|---:|
| Full M4 | 0.8062 | -- | -- | -- | -- |
| Candidate branch zeroed | 0.7998 | -0.0063 | -0.0020 | -0.0015 | 4.86% |
| Read branch zeroed | 0.7980 | -0.0082 | -0.0082 | -0.0065 | 5.49% |
| Scalar branch zeroed | 0.7905 | -0.0156 | -0.0158 | -0.0161 | 8.15% |

These ablations show that the trained model uses every added branch. They do not identify a causal biological importance ranking, because zeroing a branch creates out-of-distribution inputs. Shuffle ablations were also run, but they were unstable: shuffling read or scalar vectors unexpectedly improved finite-snapshot performance. Those results are reported as inconclusive rather than as proof that a branch is harmful.

## 6. Failures, drawbacks, and corrections

The project encountered multiple failures. They should be separated into scientific failures, implementation defects, infrastructure failures, and delivery/reporting defects.

### 6.1 Scientific and methodological failures

| Incident | Why it failed | Correction and lesson |
|---|---|---|
| Initial strict manifest failed metadata leakage gate | Allele-frequency composition allowed metadata to identify labels; metadata-only AUC 0.68977 exceeded the 0.65 gate | Rebuilt matching using common positive/0/0 support and continuous AF matching. Never allow a structurally valid manifest to proceed without direct leakage probes. |
| Preliminary M0 could not support a controlled comparison | It omitted logits, ROC/PR/MCC, stratified results, and validation-threshold artifact | Recovered the issue by running controlled M0/M2/M4 with the same snapshot and row-aligned predictions. Preserve prediction artifacts from the first model run. |
| Shuffle branch ablations were unstable | Shuffling destroys row correspondence and can exploit chance/calibration behavior rather than model reliance | Treat shuffles as diagnostics only; use zero ablation cautiously and add more robust intervention designs later. |
| Row bootstrap understates locus dependence | Sample-candidate rows are not fully independent if candidate loci recur | Do candidate-cluster bootstrap in the final experiment; do not overstate interim CI evidence. |

### 6.2 Implementation and infrastructure failures

| Incident | Immediate cause | Scientific impact | Resolution |
|---|---|---|---|
| Initial stage-0 VCF/pedigree access failed | Remote VCF reading and a pedigree filename assumption were not robust | None; label counts not accepted | Download/index the VCF and use verified official sample resources. |
| Strict-manifest kernel v1 failed before processing labels | `pysam` was missing from the Kaggle CPU image | None | Add a fail-fast dependency installation. |
| Strict-manifest kernel v2 rejected all CRAM mappings | Parser required a CRAI column absent from the official sequence index | None | Preserve exact official CRAM URLs and apply the POC-verified companion `.crai` policy; do not guess CRAM filenames. |
| Train-shard1 v1 stalled | No completed-person checkpoint was published for more than 90 minutes | None; no usable partial artifact | Relaunch in a clean session; add future checkpoint/logging behavior. |
| Initial embedding kernels failed on Tesla P100 | Installed PyTorch build lacked `sm_60` kernels | None; no forward pass processed data | Use a P100-compatible PyTorch path. |
| Second embedding attempt failed during imports | `torchvision` and `Transformers` ABI mismatch around `torchvision::nms` | None | Use compatible dependency handling; v3 embeddings passed. |
| Shards 5 and 6 completed but local HDF5 recovery was unreliable | Kaggle CLI retrieval created or replaced local files with zero bytes | Their publisher metrics/manifests exist, but fresh local HDF5 QC cannot be claimed | Preserve publisher checksums; recover artifacts before using these shards in science claims. |
| Early article PDF failed publication QC | It was a short Markdown wrapper with literal Markdown, missing figures/tables/bibliography, and incorrect audit assumptions | None for model result; reporting package was not accepted | Rebuild a real LaTeX article, generate original figures, render every page, and audit it. |

### 6.3 Process mistakes and how they changed the work

Several process errors were corrected rather than hidden:

1. **Starting with a leakage-prone negative-matching policy.** The early strict manifest passed label and coordinate rules but failed the more important metadata test. The project stopped fan-out rather than rationalising the leak.
2. **Insufficient artifact requirements in the first M0 runner.** The initial M0 result was useful as a smoke signal but was not comparable to M2/M4. The project explicitly superseded it with a controlled run instead of retroactively treating it as a baseline.
3. **Assuming Kaggle environments were binary-compatible.** The P100 GPU, PyTorch, and torchvision failures showed that declared package versions alone were insufficient. Compatibility needs a minimal real forward pass before long jobs are launched.
4. **Insufficient observability in long embedding jobs.** The Train15 read-embedding job produced little external progress while active. It was allowed to finish because compute activity suggested progress, but future runners should write periodic checkpoints and chunk-level progress logs.
5. **Treating document existence as document completion.** The first article PDF existed but failed visual and publication-quality checks. The correction pass required full source, generated figures, tables, rendered bibliography, PNG review of every page, and an audit based on actual `pdfinfo` output.

## 7. What has been achieved

The following outcomes are verified by saved artifacts and checksums:

- A strict, balanced 50-person, 100,000-row GRCh38 manifest with passed label, coordinate, split, and metadata-leakage gates.
- A production remote-CRAM extractor with 0.19% validation-shard failure rate and explicit failure categories.
- Demonstration that same-site positive and 0/0 negative individuals show different read evidence at identical candidate coordinates.
- HDF5 storage, schema validation, tensor whitelisting, candidate deduplication, and exact embedding-row alignment for Train15.
- Smoke-tested implementations of M0 through M4, including a full multimodal PAIR-SV model.
- A frozen Train15 controlled comparison with traceable predictions, metrics, bootstrap results, and branch ablations.
- A publication-quality intermediate manuscript, supplement, figures, bibliographic audit, Markdown companion article, and Russian summary.

The following outcomes have **not** been achieved and must not be claimed:

- Completion of all 40 training people under fully recovered/audited artifacts.
- Three-seed replication for M0 and M4.
- Candidate-cluster bootstrap or a full unseen-locus protocol result.
- Any internal-test metric or final test threshold decision.
- External GIAB evaluation.
- Proof that PAIR-SV meets the final mean internal-test F1 >=0.72 criterion.
- Proof of superiority over external SV callers, whose data, technology, discovery protocol, and benchmark design differ.

## 8. Current scientific interpretation

The strongest honest interpretation is:

> On a frozen, leakage-audited Train15/validation snapshot, dual-breakpoint image models achieved F1 near 0.80. Full PAIR-SV achieved a modest but row-bootstrap-supported validation improvement over the image-only baseline, and the candidate, read, and scalar branches all affected trained-model predictions. This is sufficient motivation to continue the planned final experiment, but insufficient to claim final generalisation or clinical/production utility.

The result is more favourable than an architectural null: M4 outperformed M0 and M2 in the controlled run, and branch ablations were non-zero. It is also more cautious than a decisive win: the gain is small, M2 alone did not beat M0, one seed was used, and the uncertainty calculation does not yet fully model repeated loci.

## 9. Remaining trajectory and decision gates

The next scientifically valid trajectory is already defined:

1. Recover or independently retrieve and audit HDF5 outputs for completed shards 5 and 6; do not use them until their local checksum/schema audit is complete.
2. Retrieve and audit any remaining train extraction shards, keeping each artifact independent.
3. Generate candidate and read embeddings for each accepted shard, with chunk-level logging and resumable checkpoints.
4. Complete the 40-person training set without touching the five internal-test people.
5. Freeze architecture and decision-threshold policy using training and validation only.
6. Train M0 and final M4 across three seeds on the final 40-person training set.
7. Run paired bootstrap and candidate-cluster bootstrap on validation/final results.
8. Perform exactly one evaluation of the untouched five-person internal-test cohort.
9. Only then assess the precommitted final threshold: mean internal-test F1 >=0.72, consistent three-seed direction, baseline improvement, short-deletion or hard-negative benefit, and measurable branch dependence.

The project should stop and investigate rather than proceed if any of the following reappear: a label or split leak, row/embedding alignment failure, reference mismatch, extraction failure above 1% after retry, corrupted unrecoverable outputs, or a repeated unexplained infrastructure failure.

## 10. Deliverables and traceability

The main evidence artifacts are retained locally:

- project plan and ledger: `multisample_project.md`, `multisample_progress.md`;
- controlled metrics: `reports/pairsv_train15_main_metrics.csv`;
- aligned bootstrap results: `reports/pairsv_train15_bootstrap.csv`;
- branch interventions: `reports/pairsv_train15_ablations.csv`;
- subgroup metrics: `reports/pairsv_train15_subgroup_metrics.csv`;
- controlled interim report: `reports/PAIR_SV_Train15_interim_report.md`;
- full article: `paper/PAIR_SV_Train15_article_draft.pdf` and `paper/PAIR_SV_Train15_full_article.md`;
- supplementary material: `paper/PAIR_SV_Train15_supplementary.pdf`; and
- final publication audit: `paper/final_audit.md`.

The controlled metrics, prediction, and ablation artifacts have recorded SHA-256 values in the tracker and manuscript audit. The report deliberately does not include private credentials, signed URLs, full alignments, or internal-test artifacts.

## Final outcome at the reporting cutoff

The PAIR-SV project is **partially successful and scientifically interpretable at the intermediate-validation stage**. It solved the core feasibility problems: labels, same-site negatives, remote CRAM access, multimodal tensor generation, embedding alignment, leakage auditing, and controlled model comparison. It also identified and corrected real problems in manifest matching, runner observability, GPU dependency compatibility, artifact completeness, and publication quality.

The best current result is M4 validation F1 **0.8062** on the frozen Train15 snapshot, a **+0.00697** paired-row-bootstrap-supported F1 difference over M0. This is promising evidence that the full multimodal representation may help. It is not yet the final answer to the original scientific question because the final cohort, multi-seed replication, cluster-aware inference, and untouched internal-test evaluation remain incomplete.
