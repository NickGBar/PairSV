# Design: CNN + Frozen Sequence-Backbone Comparison

Goal: compare four frozen sequence-embedding backbones fused with the CNN pileup
classifier —

1. HyenaDNA-small (already integrated)
2. Caduceus
3. Nucleotide Transformer v2-50M
4. DNABERT-2

on the deletion-calling task, and report which one improves over the CNN-only
(M0) baseline the most, and at what compute cost.

This machine has no GPU/torch/data, so this doc is the plan; execution happens
on your GPU cluster (the repo already has `scripts/slurm/`).

## 1. Base architecture: extend `main`, not the `claude/elastic-neumann-60eb31` branch

`main`'s `FusedDeepSV` ([deepsv/models/fused_cnn.py](../deepsv/models/fused_cnn.py)) is
already backbone-agnostic: it takes `embed_dim` as a constructor arg and fuses via
FiLM at two mid-level hooks + a zero-init late context-calibration delta on the
deletion logit. HyenaDNA-small (256-d) and NT-v2-100M (512-d) are already wired
through this exact path with no per-backbone code in the model itself — only the
precompute script differs. Adding 3 more backbones is "write a precompute script,
pass `--embed-dim`," not new model code.

The unmerged `claude/elastic-neumann-60eb31` branch ("DeepSV2") fuses DNABERT-2 by
PCA-reducing it to 8 channels and concatenating onto the RGB image (11-channel
input). That's a fundamentally different, less reusable design for a 4-way
comparison: every new backbone would need its own PCA-fit step and channel count,
and there's no equivalent of FiLM's clean identity-at-init property. Not using it.

## 2. The confound you need to decide on first: context-window parity

Each model has a different native/practical context length, and the repo's two
existing precompute scripts already made different choices:

| Backbone | embed_dim | Tokenization | Existing/native window | Params |
|---|---|---|---|---|
| HyenaDNA-small-32k | 256 | char-level (1bp/token) | 32,000 bp (30k core + 1k flank ×2), already implemented | ~6.6M |
| Caduceus | 256 | char-level, RC-aware | trained at 131k bp; usable at any shorter length | ~7.7M (16 layers) |
| NT-v2-50M | 512 | 6-mer BPE-free (fixed 6-mer), RoPE | repo's existing NT-v2-100M script already runs 12,240 bp (2040 tokens) via RoPE extrapolation — same architecture family, so 50M should handle the same geometry | 50M |
| DNABERT-2-117M | 768 | learned BPE (vocab 8000), ALiBi → no hard length cap | commonly run at ~1–5 kb in practice | 117M |

If each backbone gets its "natural" window, you can't tell whether a result
difference is from the backbone's representational quality or from how much
flanking sequence it saw. Recommendation:

- **Primary, controlled run:** give every backbone the same **12,240 bp window**
  (12,000 bp core + 120 bp flank ×2) — this matches the geometry already
  implemented for NT-v2 and is well within HyenaDNA-small's and Caduceus's
  range, and is a normal operating length for DNABERT-2. Same core/flank/window
  constants for all four → window size stops being a confound.
- **Optional secondary run:** each backbone at its own idiomatic window
  (HyenaDNA/Caduceus at their existing 32k, NT-v2 at 12kb, DNABERT-2 at ~4kb) to
  report a "best-effort" number alongside the controlled one. Treat this as a
  bonus table, not the headline comparison.

Also note the embed dims differ (256 / 256 / 512 / 768) — larger embeddings give
the FiLM/context heads strictly more capacity regardless of backbone quality.
Report parameter count of the fusion heads is constant (they scale with
`embed_dim` in `film.py`/`fused_cnn.py`), so this is a mild, known confound —
worth a footnote in the final report, not worth re-architecting over.

## 3. Per-backbone integration plan

### 3.1 HyenaDNA-small — already done
Nothing to build. `scripts/precompute_hyenadna_embeddings.py` +
`--embed-dim 256` is the reference arm all others are compared against.

### 3.2 Caduceus
- Model: `kuleshov-group/caduceus-ph_seqlen-131k_d_model-256_n_layer-16`
  (primary — this is the variant reported in most of the paper's main
  benchmark tables). Also stage
  `kuleshov-group/caduceus-ps_seqlen-131k_d_model-256_n_layer-16` (RC-equivariant
  parameter-sharing variant) as an optional robustness arm — cheap to add since
  it's the same embed_dim/tokenizer, just a different `--model-id`.
- Load via `AutoModel.from_pretrained(model_id, trust_remote_code=True)`.
- Tokenization: character-level (1 bp/token), same shape as HyenaDNA — the new
  script can be a near-copy of `precompute_hyenadna_embeddings.py` with
  `CORE_BP=12_000, FLANK_BP=120` (see §2) and `EMBED_DIM=256`, swapping the
  model id/loader.
- **Biggest infra risk of the four**: Caduceus depends on `mamba-ssm` +
  `causal-conv1d`, CUDA-extension packages whose prebuilt wheels are pinned to
  specific torch/CUDA ABI combinations. Pin exact `torch`/`cuda`/`mamba-ssm`
  versions in the cluster env *before* writing the script, and test
  `AutoModel.from_pretrained(...)` loads in isolation first. If `mamba-ssm`
  cannot be installed on the target cluster, there's no pure-PyTorch fallback
  worth trusting for a fair comparison — flag this back to whoever owns the
  cluster env early, not after the other 3 arms are done.
- New file: `scripts/precompute_caduceus_embeddings.py`.

### 3.3 Nucleotide Transformer v2-50M
- Model: `InstaDeepAI/nucleotide-transformer-v2-50m-multi-species`. Same
  architecture family (ESM-style with GLU FFN) and same 6-mer tokenizer as the
  already-integrated v2-100M — `scripts/precompute_ntv2_embeddings.py`'s
  `load_model()` custom-loading logic (to force the GLU FFN variant instead of
  transformers' built-in non-GLU ESM) should work unchanged. `EMBED_DIM=512` is
  identical between 50M and 100M (they differ in `num_hidden_layers`, not
  hidden size), so **no new script is strictly needed** — the existing script
  already parameterizes `--model-id`/`--model-path`. Lowest-risk backbone to add.
- Action: download `InstaDeepAI/nucleotide-transformer-v2-50m-multi-species` to
  `models/nucleotide-transformer-v2-50m-multi-species` (same layout convention
  as the existing 100M snapshot) and run
  `precompute_ntv2_embeddings.py --model-id models/nucleotide-transformer-v2-50m-multi-species`.
  Verify `config.json`'s `num_hidden_layers`/`hidden_size` match expectations
  before a full-genome run (cheap sanity check, one chunk).

### 3.4 DNABERT-2
- Model: `zhihan1996/DNABERT-2-117M`, `EMBED_DIM=768`, load with
  `trust_remote_code=True` for both tokenizer and model.
- Tokenization is the hard part: DNABERT-2 uses a **learned BPE tokenizer**
  (vocab 8000), so tokens don't align to fixed-width k-mers the way
  HyenaDNA/Caduceus (1bp) or NT-v2 (6bp) do — token spans in bp vary. To pool
  into the same 50bp-window grid as the other three:
  1. Tokenize with `return_offsets_mapping=True` (needs the fast tokenizer;
     confirm `DNABERT-2-117M`'s shipped tokenizer supports this — if it's a
     pure sentencepiece/BPE-fast tokenizer it should).
  2. For each 50bp output window, find all tokens whose character span
     overlaps it, and mean-pool their hidden states weighted by
     overlap-fraction (a token straddling a window boundary contributes to
     both).
  3. This is different code from the other three scripts (they just
     `reshape().mean(dim=...)` because token span is constant) — write it as
     its own pooling function, don't try to force it into the existing
     reshape-based helper.
- No hard context-length cap (ALiBi), so the same 12,240 bp window as the
  controlled comparison is fine; just expect more tokens per chunk than the
  6-mer/char-level models since BPE tokens average >1bp but aren't fixed.
- Known integration risk: DNABERT-2's `trust_remote_code` model file has
  historically broken against newer `transformers` releases (import errors
  around `triton`/`flash_attn` paths and an `einops` version pin) — pin
  `transformers`, `triton`, `einops` versions in a venv and confirm a single
  forward pass works before writing the full precompute loop.
- New file: `scripts/precompute_dnabert2_embeddings.py`.

## 4. Training protocol (identical across all 4 arms)

Reuse `FiLMTrainer` exactly as-is (`deepsv/training/film_trainer.py`) so the only
thing that changes between runs is the embeddings file and `--embed-dim`:

- Same M0 checkpoint as `--init-cnn-checkpoint` warm-start for all 4 (train M0
  once, reuse it as backbone for every fused run — a difference in CNN backbone
  is not something we want to compare).
- Same `--fusion-mode film_context`, `--stage-a-epochs 2`, `--lr-cnn 1e-4`,
  `--lr-film 1e-3`, `--epochs`, same train/val chromosome split, same manifest.
- Best checkpoint selected by validation F1 (already the trainer's default).

This isolates the comparison to "does this frozen embedding, fused the same way,
with the same training budget, improve F1 over M0" — not "did we tune backbone
X harder than backbone Y."

## 5. Evaluation / comparison report

`FiLMTrainer.validate()` already reports stratified precision/recall/F1 by
deletion-length bucket and by negative-source (`anchor`/`regional`/`random`).
Run inference (`scripts/call_fused_deletions.py`) for M0 + all 4 fused arms on
the same held-out chromosome and build one comparison table with:

- Overall precision / recall / F1 / AUC vs. M0 baseline.
- Per-length-bucket F1 (50–200, 200–500, 500–1k, 1k–5k, 5k–10k bp) — this is
  where sequence context is expected to matter most (repeat-rich regions,
  breakpoint motifs).
- Per-negative-type false-positive rate (are context-aware models better at
  suppressing false positives in `regional`/`random` negatives specifically?).
- Cost column per backbone: param count, embedding precompute wall-clock/VRAM,
  fused-model train wall-clock. A backbone that wins by 1 F1 point at 10x the
  precompute cost is a different recommendation than one that wins for free.

New file: `scripts/compare_backbones.py` — takes N prediction CSVs + labels,
emits the table above (reuse the stratification logic already in
`film_trainer.py` rather than reimplementing it).

## 6. Execution order

1. Pin versions / confirm each model loads in isolation (single forward pass,
   no genome) — cheapest way to surface the Caduceus/DNABERT-2 dependency risks
   before committing to full precompute runs.
2. Implement `precompute_caduceus_embeddings.py` and
   `precompute_dnabert2_embeddings.py`; confirm NT-v2-50M works via the
   existing script with a new `--model-id`.
3. Precompute embeddings for the same chromosome set already used for
   HyenaDNA/NT-v2-100M (so all 5 embedding files cover identical genomic
   coordinates).
4. Train M0 once. Train 4 fused arms (HyenaDNA-small, Caduceus, NT-v2-50M,
   DNABERT-2) from that same M0 checkpoint, identical hyperparameters.
5. Run inference for all 5 models (M0 + 4 fused) on the held-out validation
   chromosome(s).
6. Run `compare_backbones.py`, produce the report table in §5.

## 7. Open decisions for you to confirm before implementation starts

- Caduceus-Ph vs -Ps as the primary arm (recommend Ph; add Ps only if time
  allows — see §3.2).
- Controlled-window-only (§2 option, recommended) vs. also running the
  secondary "native window" table.
- Which chromosomes/train-val split to standardize on for the 4-way run (reuse
  whatever `NA12878`/chrom 20,21,22 split is already used for HyenaDNA/NT-v2 in
  your existing runs, if any exist).
