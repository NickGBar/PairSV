# PAIR-SV 50-person manifest v2 audit

**Audit date:** 2026-07-19 UTC  
**Artifact:** `kaggle/deepsv-ms-manifest50/output/sample_candidate_manifest.tsv`  
**SHA-256:** `07c4a3afc26c40beea29af16fd6c311b1e56554ddaab62bc90111eb86b087935`  
**Verdict:** **FAIL the final production label gate; rebuild required before extraction.**

This is a targeted audit of the completed v2 artifact. It does not repeat
source discovery, person selection, callset discovery, or the CRAM POC.

## Verified strengths

- 100,000 rows across 50 people.
- Frozen 40/5/5 person split: 80,000 train rows, 10,000 validation rows,
  10,000 untouched internal-test rows.
- Exactly 50,000 positives and 50,000 same-site negatives.
- Exactly 1,000 rows per class per person.
- Selected-row GQ minimum is 20; zero selected rows have GQ below policy.
- Selected GQ p05/p50/p95 is 36/10,000/10,000 for positives and
  34/10,000/10,000 for negatives.
- 9,143 unique candidate IDs; 2,348 candidate IDs occur with both labels in
  different sample-candidate records.
- All 50 CRAM URLs were taken from the already verified official sequence
  index mapping; they were not reconstructed from filename templates.

## Blocking gaps

1. Exact GT is not stored, so the final requirement of positive GT in
   {0/1, 1/1} and negative GT=0/0 is not auditable from the artifact.
2. PanGenie site FILTER policy is not applied or stored.
3. Genotype callability and conflicting overlapping deletion checks are not
   applied or stored.
4. The catalog uses `rec.stop` mixed with sequence-length filtering. As a
   result, 10,159 selected rows have a stored deletion length outside
   50-10,000 bp even though the earlier `len(REF)-len(ALT)` filter passed.
5. REF alleles are not validated against the exact GRCh38 decoding reference,
   and no reference-allele hash is stored.
6. Selection is deterministic round-robin, but it does not rank the
   highest-confidence calls within each stratum.
7. Negatives are not matched on GQ bucket or local callability and are not
   screened for overlapping carried deletions.
8. Repeat/mappability annotation is unavailable and was not explicitly marked
   as unavailable in each row.

## Corrective implementation

`scripts/build_pairsv_manifest.py` implements schema `pairsv-manifest-v3`:

- strict biallelic, sequence-resolved pure-deletion normalization;
- exact diploid GT states and GQ>=20;
- selected FILTER rule (`PASS` or unfiltered `.` only), recorded in QC;
- confidence-ranked proportional chromosome/length/AF stratification;
- explicit `annotation_unavailable` repeat bucket;
- same-split same-site negative candidates matched on chromosome, length, AF,
  and GQ buckets;
- rejection of 0/0 loci overlapping another carried GQ>=20 deletion;
- official-index-derived CRAM and CRAI URLs;
- versioned stable row IDs, exact 0-based half-open coordinates, REF/ALT
  hashes, frozen shards, and a fail-fast manifest audit.

Production extraction remains gated until the v3 Kaggle kernel completes and
its `manifest_audit.passed` field is true.
