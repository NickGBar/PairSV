# External cohort identification (Week 2 item 1-3)

## Finding: GIAB HG002 was already the pre-planned external benchmark

`multisample_project.md` §4 (written before this session, before the 5-person Manta POC existed) already specifies:

> GIAB **HG002** (GRCh38, matching Illumina short-read alignment), not in training. Used **once**, after the final architecture is chosen. Never for architecture selection. Report internal 1000G test and external GIAB **separately** — no mixing.

with the exact source path already recorded:

> External benchmark | GIAB HG002 `ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/HG002_NA24385_son/NIST_SV_v0.6/` + HG002 Illumina GRCh38 CRAM | **independent** evaluation only

This matches the publication mission's explicit preference ("Prefer GIAB HG002 with high-confidence assembly-based SV truth as one strong independent benchmark") almost exactly, and predates it — this was not an ad hoc choice, it was designed in from the start of the multisample project.

## Overlap check (Week 2 item 3) — PASSED

- HG002 (NA24385) is a GIAB/Coriell Ashkenazi-trio sample, entirely separate from the 1000 Genomes Project.
- The 50-person controlled benchmark (Train40/val/internal-test) and the 5-person realistic Manta POC (HG00108, HG01912, HG00736, HG00436, HG02601) are both drawn from 1000 Genomes NYGC 30x alignments (`multisample_project.md` §3: "1000G NYGC 30× alignments (3,202)").
- **No overlap is possible by construction** — different source projects entirely. No further de-duplication check needed beyond confirming this (done here).

## Truth-set version choice — needs one concrete decision, made here

Two live candidate GIAB HG002 SV truth sets exist:

| Version | Path | Type | Coordinate system | Maturity |
|---|---|---|---|---|
| NIST SV v0.6 | `.../AshkenazimTrio/HG002_NA24385_son/NIST_SV_v0.6/` | Union of 68 callsets, 19 callers, 4 technologies | GRCh37-native (GRCh38 requires liftover, though this project's own CRAM is GRCh38-aligned) | Mature, widely used, already what this project pre-planned |
| T2T-HG002 assembly-based (v1.1 assembly, draft SV benchmark e.g. `defrabbV0.019-20241113`, or the newer v5.0q small+SV release) | `.../AshkenazimTrio/analysis/NIST_HG002_DraftBenchmark_defrabbV0.019-20241113/` or `.../HG002_NA24385_son/v5.0q/` | Assembly-based (T2T diploid assembly), matches the mission's stated preference for "assembly-based SV truth" | GRCh38-native | Newer, methodologically stronger, but some releases are explicitly labeled "Draft" |

**Recommendation:** use the T2T-assembly-based GRCh38-native benchmark as primary (methodologically matches "assembly-based" as the mission explicitly asks for, and avoids a GRCh37→GRCh38 liftover step that would itself need validation). Fall back to NIST SV v0.6 (with liftover) only if the assembly-based release turns out to be unsuitable for genome-wide deletion benchmarking specifically (e.g. if it's scoped too narrowly, or still too immature/draft for a publication-grade external validation claim).

This determination requires actually fetching and inspecting the current directory listing and README on the NCBI FTP server (or its mirrors) at execution time — the exact current filename/version was not pinned to full certainty in this research pass (NCBI's FTP over HTTPS returned inconsistent directory listings during this session's research; a direct `curl`/`wget`/`rsync` against the FTP server, or the AWS S3 mirror `s3://giab`, will be more reliable than HTTPS scraping and should be the first action of Week 2 execution).

## Secondary cohort (mission item "plus a separate untouched cohort of new independent CRAMs where feasible")

Not yet identified. Candidates to consider in Week 2:
- Additional unrelated 1000 Genomes NYGC samples never touched by this project (would need explicit exclusion-list cross-check against both the 50-person controlled cohort and the 5-person POC before selection) — but these would only have PanGenie silver-standard labels, not independent truth, so they'd add realistic-Manta-style POC breadth rather than a second true external validation.
- A second GIAB trio member (HG003/HG004, the AJ parents) or a different GIAB sample (e.g. HG005 Han Chinese, if a comparable SV benchmark exists for it) would give genuine ancestry diversity in the external evaluation beyond HG002 alone.
- This is explicitly marked "where feasible" in the mission brief — not a hard requirement. Given the 6-week timeline, HG002 alone may be sufficient for Week 2-3; a second person/cohort is a stretch goal, not a blocker.

## Immediate next action for Week 2 execution (next session)

1. On the cluster (or locally), directly query the NCBI FTP server for HG002's current directory structure (`curl -s ftp://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/HG002_NA24385_son/` or the S3 mirror) rather than relying on HTTPS scraping.
2. Pin the exact SV truth VCF + confidence-region BED filename and compute/verify their checksums before download.
3. Identify and download the HG002 GRCh38 CRAM (same NYGC-alignment convention as the other 5 people, if available, for pipeline consistency).
4. Run the frozen external-evaluation protocol (`manta_poc/EXTERNAL_EVAL_PROTOCOL_FROZEN.md`) end to end.
