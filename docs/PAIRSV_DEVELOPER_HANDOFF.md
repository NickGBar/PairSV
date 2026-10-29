# PAIR-SV Developer Handoff

## Purpose

This document is the shortest reliable path from a fresh clone to the current PAIR-SV development checkpoint. It complements the full plan in `multisample_project.md`, the execution ledger in `multisample_progress.md`, and the narrative report in `reports/PAIR_SV_project_progress_report.md`.

## Current checkpoint

- Experiment design: 50 unrelated 1000 Genomes individuals on GRCh38.
- Frozen split: 40 train, five validation, five untouched internal test.
- Strict manifest: 100,000 balanced sample-candidate rows.
- Controlled intermediate snapshot: 15 train people / five validation people.
- Successful rows: 29,924 train and 9,981 validation.
- Validation extraction failure rate: 19 / 10,000 = 0.19%.
- Best controlled one-seed validation result: M4 F1 0.8062.
- Final internal-test evaluation: not performed.

The authoritative controlled metrics are in `reports/pairsv_train15_main_metrics.csv`; the bootstrap and intervention outputs are in the adjacent CSV files. Preliminary metrics recorded before the controlled rerun are historical only.

## Environment

```bash
git clone --branch PairSV https://github.com/aayushkrm/AlignSSL-SV.git
cd AlignSSL-SV
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest -q tests/test_pairsv_multisample.py tests/test_pairsv_model.py
```

GPU runners may need a platform-specific PyTorch wheel. Use a small import and forward/backward smoke test before starting a long kernel. Previous failures showed that P100 CUDA compute capability and `torchvision` binary operators cannot be inferred safely from package version strings alone.

## Authoritative code paths

| Purpose | File or module |
|---|---|
| Manifest construction and matching | `scripts/build_pairsv_manifest.py`, `deepsv/multisample/manifest.py` |
| Remote CRAM extraction | `scripts/extract_pairsv_shard.py`, `deepsv/multisample/extraction.py` |
| HDF5 schema and writer | `deepsv/multisample/storage.py` |
| Training loader and alignment checks | `deepsv/multisample/dataset.py` |
| QC gates and reports | `deepsv/multisample/qc.py` |
| Candidate REF/ALT construction | `deepsv/data/refalt.py` |
| Candidate embeddings | `scripts/embed_pairsv_refalt.py` |
| Read embeddings | `scripts/embed_pairsv_reads.py` |
| M0--M4 architectures | `deepsv/models/pairsv.py` |
| Controlled report generation | `scripts/build_pairsv_train15_report.py` |
| Paper figures | `scripts/build_pairsv_paper_figures.py` |
| Exact Kaggle jobs | `kaggle/*/source/` |

The copy under `kaggle/deepsv-pairsv-code/` is the audited code-dataset payload used by the private Kaggle workflows. Keep it synchronized when production code changes.

## Data contracts

### Manifest

Each row has a stable row ID, sample ID, candidate ID, label, split, genotype QC fields, coordinates, population and source fields for audit. Only the approved tensor whitelist is exposed to a model. The model must never receive sample ID, population, GQ, AF, negative type, split, or source filename.

### Extraction tensors

- pileups: `(N, 2, 6, 64, 128)`, `uint8`;
- selected read tokens: `(N, 2, 48, 128)`;
- read masks: `(N, 2, 48)`;
- scalar features: `(N, 17)` and finite;
- candidate sequence reference: deduplicated REF/ALT key;
- explicit extraction success flag and failure reason.

Candidate-level REF/ALT representations are identical for the same candidate across people. Pileups, selected reads, and scalar evidence remain sample-specific.

### Embeddings

- read representation: one aligned 768-dimensional vector per successful row;
- candidate representation: five 256-dimensional REF/ALT-derived vectors per deduplicated candidate in the committed schema;
- row/candidate identifiers must match extraction artifacts exactly before training.

## Production sequence

1. Rebuild the strict manifest using the official 1000 Genomes sequence index and PanGenie VCF.
2. Run the deterministic validation subset and full validation shard before any new extractor version is fanned out.
3. Extract independent five-person train shards. A failed shard must not invalidate completed shards.
4. Audit checksums, schema, finite values, non-empty evidence, balance, coordinate identity, sample-specific differences, GQ, and failure rate for every shard.
5. Deduplicate and embed candidate REF/ALT contexts; then embed selected reads.
6. Join stores through stable row and candidate IDs. Do not rely on row position without identifier equality checks.
7. Run the M0--M4 forward/backward/oracle smoke gate after any model or loader change.
8. Train only on the frozen person split. Fit normalization on train people only.
9. Freeze architecture and threshold policy after three-seed train/validation analysis.
10. Open the internal test exactly once.

The exact Kaggle metadata and runner for every completed or prepared stage is committed under `kaggle/`. Update `multisample_progress.md` only after a kernel reaches a terminal state and its artifacts have been retrieved and audited.

## Known failures and lessons

- The first strict manifest failed the precommitted metadata-leakage gate because allele-frequency distributions separated labels too well. Matching was rebuilt before extraction.
- Early local runs lacked `pysam`; environment import checks are now required.
- One extractor expected a CRAI column that was absent from an intermediate table; input schema validation was added.
- A train shard stopped making progress during remote access; transport retries, reopening, and progress logs are necessary.
- P100 and `torchvision::nms` incompatibilities caused cloud failures unrelated to architecture quality.
- Some downloaded shard outputs were zero-byte files; file existence is not completion. Validate size, checksum, and HDF5 openability.
- The first M0 run did not save aligned predictions or the full metric set; it was superseded by the controlled M0/M2/M4 rerun.
- The first article PDF was a Markdown dump with missing figures and references; the Tectonic-built LaTeX package and visual audit supersede it.

See `reports/PAIR_SV_project_progress_report.md` for causes, fixes, and scientific impact.

## Reproducibility checklist before new training

- [ ] GRCh38 reference checksum matches the validated reference.
- [ ] Strict manifest is the leakage-audited version.
- [ ] No train/validation/test person overlap.
- [ ] No internal-test rows or metrics were opened.
- [ ] Successful extraction failure rate is below 1% per shard.
- [ ] Extraction, read embedding, and candidate embedding IDs align exactly.
- [ ] Scalar values and all embeddings are finite.
- [ ] Model input dictionary contains only the whitelist.
- [ ] M0 and M4 use identical rows, sampling, seed policy, metrics, and threshold selection.
- [ ] Each epoch saves a checkpoint, aligned validation predictions, metrics, and runtime.

## Final completion criteria

The project is not complete until all 40 training people are processed, M0 and final PAIR-SV are trained across three seeds, the architecture and threshold policy are frozen, candidate-cluster-aware paired bootstrap is reported, and one untouched five-person test evaluation meets the precommitted scientific criteria. The target must not be lowered after results are observed.

