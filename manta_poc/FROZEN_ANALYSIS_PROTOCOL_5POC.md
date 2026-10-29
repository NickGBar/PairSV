# Frozen analysis protocol — 5-person realistic-benchmark POC

Written and frozen **before** inspecting any gate-2/gate-3 results on
HG01912, HG00736, HG00436, or HG02601. Nothing in this document may be
changed after any of those four samples' results are observed. Any
amendment after that point requires an explicit SkillLayer decision record
that supersedes this one and states what was already known when the change
was made.

## Scope

Five development POC samples: HG00108 (done), HG01912, HG00736, HG00436,
HG02601. These are pipeline-construction samples, not the final external
test cohort. PAIR-SV v1 and its frozen internal-test result are never
touched or revisited by anything in this protocol.

## 1. Per-person reporting

Every metric below is computed **separately per person**, using that
person's own Manta candidates and gate-2 labels. Results across the 5
people are reported side by side, never pooled into a single merged table
of rows before scoring. This directly serves item 5 below.

## 2. Baseline

"Accept-all Manta candidates" (predict positive for every PASS DEL
candidate, unconditionally) is the practical baseline every model must be
compared against, per person.

## 3. Metrics (per person, per model, per seed, at the model's frozen
   validation-selected threshold — natural labeled prevalence, no rebalancing)

- Specificity
- Balanced accuracy
- MCC
- ROC-AUC
- PR-AUC
- Precision at fixed recall — evaluated at recall = 0.99, 0.95, 0.90
  (probability threshold chosen post-hoc per person/model/seed from that
  person's own ROC/PR curve solely to hit the target recall; this is a
  curve read-off, not a refit of the model or its frozen threshold)
- Negatives removed at 99%, 95%, 90% positive recall — i.e. of that
  person's known_negative candidates, what fraction fall below the
  probability threshold that achieves each recall target on positives

These are always reported alongside precision/recall/F1 (already computed
in gate 3), not in place of them.

## 4. Leave-one-person-out (LOPO) calibration — development-only

For each of the 5 POC people held out in turn:
- Fit threshold/calibration **only** on the other 4 POC people's labeled
  candidates (positive + known_negative).
- Evaluate that calibration on the held-out person's labeled candidates.
- Repeat for all 5 held-out choices.

This is explicitly a development-only diagnostic: it never touches the
frozen internal-test set, never touches PAIR-SV v1, and its output is not a
new frozen threshold for any future external cohort — any final external
evaluation must fit calibration (if any) on its own held-out development
data, never on these 5 POC people.

## 5. No pooled-random-split evaluation

Candidates from different people are never concatenated into one pool and
then row-randomly split into train/eval. All splits in this protocol are by
whole person (LOPO) or single-person (per-person metrics), never row-level
random splits across people.

## 6. Unknown handling

Unknown-class candidates (gate-2) are scored by every model/seed exactly
like labeled candidates, but are excluded from every metric in sections 3
and 4 above. Only their predicted-positive rate is reported, per person,
outside the supervised-metrics tables.

## 7. M4 precision gate

Before any fine-grained comparison that involves M4 (e.g. comparing M4's
specificity or calibration against M0/M2, or the candidate-cluster
bootstrap comparisons already run for HG00108 gate 3), M4 must first be
re-run on HG00108 in the original CUDA/bfloat16 environment (matching the
frozen training/internal-test kernels exactly), to quantify whether the
float32-on-MPS deviation used for the HG00108 gate-3 smoke test materially
changed M4's outputs. Until that re-run is done and compared, M4's
gate-3/gate-4 numbers on HG00108 are provisional; M0 and M2 have no such
caveat since they never depended on the HyenaDNA embedding step.

## Frozen Manta configuration (unchanged from HG00108, decisions 0016–0018)

- Manta 1.6.0, container digest
  `sha256:48d0c2464fa0129935438c5cddec5f67c4b3d65e8f7a647f95164ee51662cc70`
- Reference: `manta_poc/reference/GRCh38_full.fa` (same file, same SHA-256)
- `configManta.py --bam=<sample.cram> --referenceFasta=<ref> --runDir=<...>`
  (no `--callRegions` — whole genome)
- `runWorkflow.py -m local -j 4 -g 5`
- CRAM version checked via magic-byte HEAD/range request before download,
  same as HG00108 (decision 0017); transcode to v3.0 only if the original is
  v3.1, otherwise direct byte-for-byte download
- Same Truvari v5.4.0 gate-2 parameters, same PanGenie source/thresholds
  (decision 0019)
- Same frozen M0/M2/M4 checkpoints, norm_stats, thresholds (decision 0020)

## What this protocol does not decide yet

Whether/how any recalibration informs a future PAIR-SV v2 is explicitly out
of scope here — this protocol only governs how the 5 POC people's gate-3/
gate-4 results are measured and reported, not what modeling decision (if
any) follows from them.
