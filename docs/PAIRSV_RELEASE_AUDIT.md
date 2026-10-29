# PAIR-SV GitHub Release Audit

**Audit date:** 20 July 2026  
**Target:** `aayushkrm/AlignSSL-SV`, branch `PairSV`  
**Target visibility at audit time:** public

## Scope result

The release index contained 190 tracked files before adding this audit. It included 91 Python files, 24 Markdown files, 25 JSON configuration files, nine CSV tables, 18 publication figure files, 48 Kaggle kernel-source files, the package requirements, and `setup.py`. After this audit is included, the branch contains 191 tracked files.

Directory-level inventory before this audit:

| Area | Tracked files | Content |
|---|---:|---|
| `kaggle/` | 62 | kernel sources, metadata, and audited code payload |
| `paper/` | 45 | manuscript, supplement, PDFs, figures, tables, bibliography, previews, audit |
| `deepsv/` | 35 | historical and PAIR-SV library code |
| `scripts/` | 17 | local data, embedding, model, inference, and report runners |
| `reports/` | 9 | controlled aggregate results and project reports |
| `docs/` | 9 before this audit | design research, schemas, manifest audit, handoff, release boundary |
| `tests/` | 2 | multisample pipeline and M0--M4 model tests |
| repository root | 11 | README, plans, progress ledgers, requirements, packaging, and historical note |

## Completeness checks

- `git ls-files -o --exclude-standard` returned no files: every nonignored workspace file was staged.
- All existing tracked historical files remain in the branch.
- All files under every `kaggle/*/source/` directory are included.
- All PAIR-SV code under `deepsv/multisample/`, `deepsv/models/`, and `scripts/` is included.
- All project/progress Markdown files, reports, manuscript sources, publication PDFs, figures, tables, bibliography, and page previews are included.
- `requirements.txt`, `setup.py`, Kaggle metadata, and dataset metadata are included.
- The largest included file was 636,151 bytes; no GitHub large-file limit is approached.

## Security and public-data checks

The staged release was searched for:

- GitHub and AWS token formats;
- Kaggle credential variables;
- private-key headers;
- authorization headers;
- signed URL query parameters.

No matching credential or signed-URL material was found. `.DS_Store`, bytecode, test caches, local environments, keys, `.env` files, and `kaggle.json` are ignored.

Because the target is public, generated sample-level data remain excluded. This includes alignments, downloaded genotype VCFs, sample-candidate manifests, extraction and embedding HDF5 stores, model checkpoints, and raw kernel output directories. `docs/PUBLIC_RELEASE_BOUNDARY.md` records the reason and reconstruction path. No source code or documentation is excluded by that boundary.

## Validation

The exact focused validation command was:

```bash
PYTHONPATH=/opt/miniconda3/lib/python3.13/site-packages \
  /Users/nikolai/Experiment/.venv/bin/python -m pytest -q \
  tests/test_pairsv_multisample.py tests/test_pairsv_model.py
```

Result: **18 passed in 1.81 seconds**.

The split runtime was used only for local validation because the available PyTorch virtual environment lacked `h5py`, while the base Python environment supplied compatible `pytest` and `h5py`. A fresh clone should instead install the complete committed `requirements.txt` into one isolated environment.

## Scientific boundary

- The controlled Train15 aggregate results are included.
- The internal-test cohort has not been evaluated.
- No internal-test predictions or metrics are present.
- The branch documentation consistently identifies the current result as intermediate validation rather than a final 40/5/5 outcome.

## Commit-message audit

The release commit uses a standard concise subject and contains no co-author, sign-off, generated-by, AI-assistance, or other attribution trailer.
