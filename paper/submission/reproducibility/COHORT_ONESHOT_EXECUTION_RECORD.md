# 30-person cohort — one-shot evaluation execution record

**Executed:** 2026-08-08
**Command:**

```
source ~/miniconda3/etc/profile.d/conda.sh && conda activate deepsv2_new \
  && cd /scratch/igorno-deepsv_poc/pairsv_parity/manta_poc \
  && python3 cohort_evaluate.py
```

**Outcome:** completed successfully on its **first execution**, with **no
modification to the script** after checksumming. Exit status success; no
exception, no retry, no partial run.

## Frozen artifact checksums (verified identical on cluster and in-repo)

| Artifact | SHA-256 |
|---|---|
| `cohort_final_evaluation_report.json` | `84f571b617025597b12d1caf55bb0ce3b18b0f021fbc58cf30e6798a0538b3d1` |
| `cohort_evaluate.py` (checksummed *before* first run) | `6c9afb37c0822ab31fd0bf2964e5d0eb878fe2eea042347f122cb3d49b1edac9` |
| `COHORT_PRE_EVALUATION_MANIFEST.json` (frozen *before* the run) | `3a670e207d8f3bb99a695e05c3755349fd934685b0c1ff402cfbf5d771403942` |

## Captured console output

**Disclosure — the full stdout of the run was not captured to a file.** The
evaluation was invoked over an interactive SSH session with the output piped
through `tail -20`, so only the final 20 lines were returned to the caller,
and no `tee`/redirect wrote a complete log to disk. A search of the cluster
(`/scratch/igorno-deepsv_poc`) confirms no evaluation log file exists. What
follows is therefore the **complete captured tail, verbatim and unaltered** —
not a full transcript, and not a reconstruction. The per-sample lines that
scrolled past before this tail were of the identical `"<SAMPLE>: evaluated"`
form emitted once per person by the script's own loop.

```
HG00739: evaluated
HG00742: evaluated
HG01048: evaluated
HG01051: evaluated
HG01054: evaluated
HG01058: evaluated
HG01914: evaluated
HG01958: evaluated
HG01985: evaluated
HG01988: evaluated
HG01990: evaluated
HG02009: evaluated
HG02603: evaluated
HG02648: evaluated
HG02651: evaluated
HG02654: evaluated
HG02657: evaluated
HG02660: evaluated
wrote /scratch/igorno-deepsv_poc/pairsv_parity/manta_poc/cohort_final_evaluation_report.json
sha256 84f571b617025597b12d1caf55bb0ce3b18b0f021fbc58cf30e6798a0538b3d1
```

That the run covered all 30 people is independently verifiable from the
report itself, which records `n_people: 30` and carries a complete
`per_person` block with one entry per cohort member — this does not depend on
the console output.

**This record is preserved unchanged.** The evaluator has not been re-run and
must not be, regardless of the erratum documented in
`COHORT_EVALUATION_ERRATUM.md`.

## Process note for future one-shot runs

A one-shot, non-repeatable execution should be invoked under `tee` (or as a
batch job with an `--output` log) so the complete stdout is preserved at run
time. Piping through `tail` is irreversible for a run that by protocol cannot
be repeated. Recorded here as a process lesson rather than corrected after
the fact, since re-running to produce a fuller log is exactly what the
one-shot discipline forbids.
