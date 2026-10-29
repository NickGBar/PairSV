# Public Release Boundary

## Scope

The `PairSV` branch is intended to be a complete public source and documentation release. The target GitHub repository is public. This file records the deliberate boundary between reproducible source material and generated sample-level or security-sensitive artifacts.

## Included

- all Python and shell source code in the project checkout;
- all PAIR-SV library modules and historical single-sample implementation files;
- all Kaggle kernel source files and `kernel-metadata.json` configurations;
- the audited private Kaggle code-dataset source payload, without private outputs;
- all project, progress, research, handoff, and methodological Markdown documents;
- requirements and packaging configuration;
- local unit and smoke tests;
- aggregate controlled Train15 metric, subgroup, bootstrap, and ablation CSV files;
- manuscript and supplement source, compiled PDFs, publication tables, figures, rendered page previews, bibliography, and audit;
- checksums and row/failure summaries already recorded in the progress ledger and reports.

## Excluded from the public branch

| Artifact class | Reason | Reconstruction or traceability |
|---|---|---|
| Kaggle API credentials, tokens, environment files, private keys | Security-sensitive | Never required in source; configure through Kaggle/GitHub secret storage |
| BAM/CRAM, BAI/CRAI, reference FASTA downloads | Very large upstream genomic data | Public source locations and exact GRCh38 reference are recorded in project documents and scripts |
| Downloaded PanGenie/HGSVC2 genotype VCF | Large upstream genotype resource | Official URL and filtering code are committed |
| Sample-candidate manifests and candidate catalogs | Sample-level derived experiment artifacts | Deterministically rebuilt by `scripts/build_pairsv_manifest.py`; counts, policy, and audit are recorded |
| Extraction and embedding HDF5 stores | Sample-level derived tensors, tens to hundreds of MB per shard | Rebuilt by committed extraction/embedding runners; schemas and SHA-256 checksums are in the ledger |
| Model checkpoints | Derived from sample-level training data and previously stored only in private artifacts | Rebuilt by committed runners; aggregate metrics and parameter counts are published |
| Raw kernel logs and output directories | May contain transient URLs, local paths, sample-level rows, or redundant large data | Scientific runtime, failure, and checksum facts are transcribed into `multisample_progress.md` |
| `.DS_Store`, Python bytecode, test caches, LaTeX intermediates | Machine-specific and not source material | Regenerated automatically |

These exclusions are explicit and are not accidental omissions. No code or documentation file is excluded by this policy.

## Continuation without private outputs

A new developer can run local synthetic/unit tests immediately after installing dependencies. Reproducing the full biological experiment additionally requires the public GRCh38 reference, PanGenie callset, and remote 1000 Genomes CRAM/CRAI inputs. The code retrieves or reads those resources using the verified official indexes. Cloud execution requires the developer’s own private Kaggle credentials and private artifact storage.

The exact scientific state can be understood without private tensors from:

1. `multisample_project.md` — committed protocol and gates;
2. `multisample_progress.md` — terminal job ledger and artifact checksums;
3. `reports/PAIR_SV_project_progress_report.md` — full narrative history;
4. `reports/*.csv` — aggregate controlled results;
5. `paper/` — manuscript, supplement, tables, figures, and audit;
6. `kaggle/*/source/` — exact cloud runner sources.

## Internal-test isolation

No internal-test metric, prediction, checkpoint selection, or model-tuning result is included because the internal test has not been evaluated. Public documentation may describe the committed split policy, but it must not present internal-test outcomes until the final experiment is frozen and executed once.
