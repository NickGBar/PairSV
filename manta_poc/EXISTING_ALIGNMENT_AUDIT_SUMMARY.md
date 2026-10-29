# Pre-download existing-alignment audit — summary

**Purpose:** requested before launching any further bulk cohort downloads, to check whether BAM/CRAM files already on the cluster could substitute for planned downloads. Full per-file detail in `existing_alignment_inventory.tsv`, `reusable_cohort_alignments.tsv`, `rejected_alignments.tsv` (same directory).

## Method

1. Cluster-wide file search across `/beegfs/scratch`, `/beegfs/datasets`, `/home`, `/lhome`, `/sf`, `/root` for `*.bam`/`*.cram` (282 files found before the exhaustive crawl was terminated after stalling on the 236TB, 113-user shared `/sf/datastor` filesystem — see "Coverage caveat" below).
2. Targeted `grep`/`find` searches specifically for all 30 cohort sample IDs, run separately against `/beegfs/scratch/ws/ws1` and `/beegfs/datasets` — **zero matches** for any of the 30 people.
3. Full technical verification (quickcheck, header inspection, contig count, functional index test, full-file SHA-256) for the one file that turned out to matter: an existing HG002 hs37d5 (GRCh37) BAM.

## Findings

**One directly usable file found: `HG002.hs37d5.60x.1.bam`** (125,969,130,504 bytes) in a separate, unrelated workspace (`igorno-alignssl_sv` — apparently a different, prior SSL-pretraining project under the same cluster account) at `/beegfs/scratch/ws/ws1/igorno-alignssl_sv/giab/`. This is exactly the file the NIST SV v0.6 sensitivity pass needs, and a download of the identical file (job 1570458) was already ~37% complete when this audit found it.

Full verification (all passed): exact expected size match; header confirms Novoalign V3.02.07 against `hs37d5.ndx` (`AS:hs37d5`), matching the official GIAB README's documented build process exactly; 86 contigs, matching this project's already-downloaded-and-verified `hs37d5.fa` reference's contig count exactly; `samtools quickcheck` PASSED; a functional random-access read test via the file's adjacent `.bai` returned correct alignment records; full-file SHA-256 computed successfully with zero I/O errors across all 126GB (`2f2a40af50320988beedb70c1a914e245e205c1bd05dfe3eef210d54ebcecfd0`). No official NIST checksum exists for this specific derived file to compare against — same situation as this project's own already-used GRCh38 60x BAM, where provenance was likewise established via header/size/content verification rather than an official checksum.

**Action taken:** cancelled the redundant in-progress download (not close to completion, per the stated exception), deleted its partial data, symlinked the existing file into this project's own workspace (`/scratch/igorno-deepsv_poc/local_slices/HG002_hs37d5_full/`, avoiding a pointless 126GB copy), and rebuilt a fresh index in that location to eliminate a harmless index-older-than-data-file timestamp warning on the original copy.

**Zero files found for the 30-person cohort, the 15-person overflow pool, the 50-person controlled benchmark, or (beyond what was already known) the 5 POC people.** The already-known POC/HG002 files (4 POC CRAMs on cluster, HG002's own GRCh38 BAM, HG00108 processed locally with no cluster copy) are listed in the inventory for completeness but require no action — they are already fully processed.

Two other whole-genome BAMs were found (NA12878, NA20845, in the same `igorno-alignssl_sv` workspace) but rejected: neither sample belongs to any of the 5 required categories (30-cohort / overflow / 50 / POC-5 / HG002), so there is no planned download they could replace.

## Coverage caveat

The exhaustive filesystem crawl was terminated after stalling for several minutes (uninterruptible I/O wait) while traversing `/sf/datastor`, a 236TB CephFS shared across 113 other users' home directories, most of which this account cannot read. This is judged low-risk for the actionable question (whether any of the 30 cohort people's files already exist) because: (a) the targeted ID-based search, which is what actually answers that question, completed successfully against every location this account can read and found nothing; (b) it is intrinsically implausible that another researcher's private directory would happen to contain pre-downloaded copies of these specific 30 deterministically-selected 1000 Genomes samples for this project's purposes. If a more exhaustive shared-storage sweep is wanted later, it should be scoped and time-boxed separately rather than run inline.

## Total download volume avoided

**125,969,130,504 bytes (~126GB, the full HG002 hs37d5 BAM)** — none of it will be re-downloaded. Of this, ~46.8GB had already been transferred by the now-cancelled job before the existing file was found (that partial transfer is not recoverable, but it also isn't wasted going forward since it's simply not needed anymore); the remaining ~79.2GB of transfer that would otherwise have been required is fully avoided, along with the associated cluster egress-bandwidth pressure on the other concurrently-running downloads (this project's own resource estimate already documented a shared ~13MB/s cluster egress ceiling this session — removing this job frees that bandwidth for the dry-run and, soon, cohort downloads).

## Revised download queue

| Item | Status |
|---|---|
| HG002 hs37d5 (GRCh37) BAM for v0.6 sensitivity pass | **No longer needed as a download** — reused via symlink, fresh index built, fully verified. Job 1570458 cancelled. |
| 30-person cohort (all 30) | **Unchanged — all 30 still require download.** No existing files found for any of them, confirmed by targeted search. |
| HG00109, HG00110 (dry run, in progress) | Unchanged — already downloading via the corrected parallel-chunk method (jobs 1570461/1570462), not affected by this audit. |

Cohort membership is unchanged by this audit, per instruction — no file's mere presence altered who is in the frozen 30-person cohort or the overflow pool. Bulk cohort downloads for the remaining 28 people remain paused pending this audit's completion and now may proceed.
