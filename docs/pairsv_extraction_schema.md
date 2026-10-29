# PAIR-SV extraction schema v1

The production container is HDF5 with schema attribute `pairsv-shard-v1`.
Every failed candidate remains present with `examples/success=0` and a nonempty
`examples/failure_reason`; failed tensors are never accepted by a loader as
successful zero evidence.

## Model tensors

Only these paths are model inputs (also stored in the root
`model_tensor_datasets` attribute):

| Path | Shape | Type | Meaning |
|---|---:|---|---|
| `examples/images` | `(N,2,6,64,128)` | uint8 | tied left/right breakpoint pileups |
| `examples/read_tokens` | `(N,2,48,128)` | uint8 | sample read sequences; 0=padding |
| `examples/read_mask` | `(N,2,48)` | uint8 | valid-read mask |
| `examples/scalars` | `(N,17)` | float32 | documented read-support features |
| `candidates/refalt_tokens` | `(C,2,1024)` | uint8 | deduplicated candidate REF/ALT sequences |

`examples/candidate_index` maps an example to the candidate tensor. Label is a
training target, not an input tensor.

## Pileup channels

1. base identity;
2. base quality;
3. mapping quality;
4. strand;
5. reference match/mismatch/deletion state;
6. evidence reason (ordinary, discordant, deletion CIGAR, clipped, SA split,
   supplementary).

Reads are ranked by supplementary, SA split, soft clip, deletion CIGAR,
discordance, distance to the breakpoint, and MAPQ. Ordinary spanning reads are
reserved as controls.

## Scalar order

1. left soft-clip read count;
2. right soft-clip read count;
3. SA split-read count;
4. supplementary-alignment count;
5. discordant-pair count;
6. reference-spanning-read count;
7. candidate ALT-support count;
8. inside depth near the two deletion edges;
9. left-flank depth;
10. right-flank depth;
11. inside/flank depth ratio;
12. mean MAPQ;
13. mean base quality;
14. mean absolute insert size;
15. insert-size anomaly fraction;
16. left/right ALT-evidence balance;
17. `log1p(deletion length)`.

Repeat and mappability are not silently fabricated. The manifest records
`repeat_bucket=annotation_unavailable`; these features can be added only after
a versioned GRCh38 annotation source is attached.

## QC-only metadata

Stable row ID, sample ID, population, split, GT, GQ, candidate ID, coordinates,
negative type, source filename, CIGAR, strand, per-read MAPQ/base-quality
summary, supplementary flag, read-name hash, selection reason, extraction
status, and failure reason remain available for QC. Sample ID, population,
split, GT/GQ, negative type, source filename, and read-name hash are excluded
from the model-tensor whitelist.
