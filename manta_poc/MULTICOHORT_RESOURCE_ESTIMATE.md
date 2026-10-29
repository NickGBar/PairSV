# Multi-person cohort (30 people) — cluster resource estimate

**Purpose:** Week 3 mission Part 4 item 1 — produced *before* launching any cohort sample, using this project's own directly-measured per-sample costs (HG002's just-completed run, and the 5-person realistic-POC's Manta/download history), not generic assumptions.

---

## 1. Download volume

30 people selected (`manta_poc/multicohort_30_selection_manifest.json`), CRAM sizes fetched via HTTP HEAD from `https://ftp.sra.ebi.ac.uk/...` (NYGC 30x high-coverage collection):

| Metric | Value |
|---|---|
| Total CRAM download volume | **480.3 GB** (30 people, ~16.0 GB average per person — 30x-coverage CRAMs, much smaller than HG002's 126GB 60x BAM) |
| Host | `ftp.sra.ebi.ac.uk` — the same host already used for all 5 realistic-POC CRAM downloads this project has run; **not** the `ftp-trace.ncbi.nlm.nih.gov` host that throttled HG002's single-connection download to ~250-300KB/s |

**UPDATE (2-person dry run result, decision 0050): single-connection throughput on `ftp.sra.ebi.ac.uk` is ALSO severely throttled** — observed ~250KB/s (HG00109, ETA 17-34h) and ~660KB/s (HG00110, ETA ~6h15m) on the first dry-run attempt. This is not host-specific; per-connection rate-limiting appears to be a general property of these genomics FTP mirrors, not a one-off. **Corrected and now the frozen default for all 30 people:** the same 16-way parallel byte-range chunked download already proven on the HG002 BAMs. Single-connection download must not be used again for this cohort.

**UPDATE 2 (running 3 parallel-chunk jobs concurrently): aggregate throughput does NOT scale with concurrent jobs.** With the hs37d5 BAM download (16 chunks) and both corrected dry-run downloads (16 chunks each) running simultaneously, per-job rates dropped to ~2.2MB/s (HG00109), ~1.6MB/s (HG00110), ~8.3MB/s (hs37d5 BAM) — summing to ~12.1MB/s, essentially identical to the ~12-14MB/s a *single* parallel-chunked job achieved alone. **This points to a shared cluster/network egress ceiling (~12-14MB/s total), not a per-job or per-host limit** — running more concurrent downloads splits the same pipe rather than adding capacity. Practical consequence for Phase 2: launching more people concurrently does not slow any individual download down further than the shared ceiling already implies, but it also does not shorten total cohort download wall-clock — **at a ~13MB/s aggregate ceiling, the full 480GB cohort download takes ~10.25h of wall-clock no matter how many people are launched at once.** This is still comfortably within the six-week deadline (and the per-person Manta/extraction/embedding stages can begin as soon as that person's own download completes, so total pipeline wall-clock is not download-time plus everything-else in series for every person — only for whichever finishes last).

## 2. Temporary disk use

Peak per-person temporary footprint (during parallel-chunk download, before parts are deleted post-concatenation): ≈2× the CRAM size ≈ 32GB/person. If several people download concurrently, peak aggregate temp use scales with concurrency — even at all 30 simultaneous (unrealistic, batches will be smaller) that's ≈960GB, **2.1% of the 46TB free** on `/beegfs/scratch`. Not a constraint at any realistic batch size.

## 3. Permanent artifact size

Measured directly from HG002's completed run (`du -sh` on the cluster):

| Component | HG002 measured size |
|---|---|
| Manta output directory (`results/<SAMPLE>_wgs/`, incl. workspace/stats/logs) | 66 MB |
| gate2/gate3/embeddings/predictions/evaluation (`<sample>_external/` or equivalent) | 91 MB |
| **Total per person** | **≈157 MB** |

30 people × 157MB ≈ **4.7 GB** permanent artifacts. Combined with the 480GB raw CRAMs (which may or may not be retained long-term — the 5 POC people's CRAMs were kept for the 30-day workspace retention window, not deleted immediately), **total footprint ≈485GB, 1.05% of the 46TB free space.** Storage is not a constraint at this cohort size.

## 4. Manta CPU-hours

Observed whole-genome Manta runtimes on this cluster (16 cores/job, `amd_256M` partition), from actual completed runs:

| Sample | Elapsed | Outcome |
|---|---|---|
| HG002 (job 1570058) | 1,962s (32.7 min) | success — notably fast, possibly favorable node/queue conditions |
| HG00736 | 22,326s (6.2h) | success |
| HG02601 | 26,597s (7.4h) | success |

**Range observed: 33 min to 7.4 hours per person.** Using the two POC successes as the more representative planning baseline (~6.8h average) and 16 cores: **~109 CPU-hours/person**, **≈3,270 CPU-hours for 30 people**. If HG002's fast runtime turns out to be more typical for this cohort (plausible — cluster load varies), the true figure could be substantially lower. The 2-person dry run (Part 4 item 2) will narrow this range before the full batch launches.

**Concurrency ceiling found (Phase 2, 8-person batch):** submitting 8 jobs at 16 cores each hit a hard SLURM association CPU limit (`AssocGrpCpuLimit`) at 5 concurrent jobs (5×16=80 cores) — the remaining 3 sat PENDING until cores freed up. This is a scheduler quota, not a bandwidth or correctness issue: queued jobs launch automatically as running ones finish, at no cost beyond wall-clock queue time. Practical planning implication: the cluster will only ever run ~5 Manta jobs simultaneously for this account regardless of how many are submitted at once, so batch size mainly affects how much is pre-queued rather than true parallelism — submitting the full remaining cohort at once would be reasonable (no wasted resources), but was done in smaller batches this session to keep the gate2/gate3/embed/score follow-through manageable.

**Dry-run result (complete):** HG00109 (job 1570485) and HG00110 (job 1570486) both completed successfully, MD5 verified OK, Manta exit 0. **Manta runWorkflow elapsed: HG00109 5,792s (1h36m32s), HG00110 6,378s (1h46m18s).** This lands between HG002's unusually fast 33-minute run and the two POC people's 6.2-7.4h runs — a genuine middle data point, suggesting ~1.5-2h/person is a reasonable planning figure for this specific 1000G 30x-coverage cohort (as opposed to the POC people's 60x CRAMs or HG002's 60x BAM). At 16 cores, that's ~24-28 CPU-hours/person (well below the earlier conservative ~109 CPU-hours/person estimate), meaning **≈720-960 CPU-hours for the full 30-person cohort's Manta stage** — a substantially lower and more favorable figure than the initial conservative estimate.

## 5. GPU embedding + scoring time

Measured directly from HG002 (Tesla T4, `gpu_T4` partition):

| Step | HG002 measured time | For 4,756 candidates |
|---|---|---|
| HyenaDNA ref/alt + read embeddings | 337s (5.6 min) | ~14.1 candidates/s combined |
| Ensemble scoring (M0/M2/M4 × 3 seeds) | 120s (2.0 min) | |

Per-person candidate counts for the 5 POC people ranged 3,283-3,640 (Phase F table) — smaller than HG002's 4,756-eligible set, so **per-person GPU time is expected to be ≤ HG002's ~7.5 min combined**, call it **~8 min/person total GPU wall-clock** (embedding + scoring) to be safe. **30 people ≈ 4 GPU-hours total** — trivial relative to the T4 partition's availability observed this session (jobs started within seconds of submission every time).

## 6. Extraction (CPU)

HG002: 4,761 eligible candidates extracted in 134s (35.5/s) + ~40s shard packing ≈ **175s/person**. **30 people ≈ 1.5 CPU-hours total** (single-threaded remote-CRAM-read bound, not parallelism-bound).

## 7. Total wall-clock estimate

| Stage | Per-person | 30 people, sequential | 30 people, batched (realistic) |
|---|---|---|---|
| Download | ~20-30 min | ~10-15h | parallelizable across many concurrent downloads — bandwidth-bound, not compute-bound |
| Manta | 33min-7.4h (avg ~4h planning estimate) | up to 222h | **parallelizable** — each Manta job is independent, cluster can run many concurrently (subject to fair-share; unconfirmed until dry run) |
| Extraction | ~3 min | 1.5h | same |
| Embedding+scoring (GPU) | ~8 min | 4h | GPU-partition concurrency unconfirmed — may need to queue if only 1-2 T4s available |

**Bottom line:** the dominant cost is Manta CPU-hours (~3,270 estimated) and the main unknowns are (a) whether HG002's unusually fast 33-minute run is representative or an outlier, and (b) how many Manta/GPU jobs the cluster will run concurrently for this account before queueing. Both are directly answered by the Part 4 item 2 two-person dry run before any commitment to launching all 30.

## 8. Recommendation

Storage headroom is enormous (>98% free either way) — not a limiting factor. The real open question is **queue concurrency and true per-person Manta wall-clock** on this shared cluster. Proceed to the 2-person infrastructure dry run next; use its actual observed timings to decide the batch size and whether extending from 30 to the full 45-person pre-vetted-adjacent pool (or beyond, per the deterministic-selection method already validated) is feasible without threatening the six-week deadline.
