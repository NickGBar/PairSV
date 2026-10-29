# Cross-attention fusion: CNN + HyenaDNA-small

Chosen fusion strategy (see [`fusion_strategies_comparison.md`](fusion_strategies_comparison.md)): **cross-attention**, with **HyenaDNA-small** as the frozen sequence encoder. This doc is the concrete architecture, grounded in the actual shapes/conventions already in this repo, plus the reasoning for how it should improve on the existing FiLM / context-calibration results.

## What's implemented

| File | What it does |
|---|---|
| [`deepsv/data/fused_dataset.py`](../deepsv/data/fused_dataset.py) | `FusedDataset` now takes `context_radius`. `0` (default) = unchanged single-vector behavior. `>0` = returns a `(2*radius+1, embed_dim)` sequence of neighbouring 50bp-window embeddings, edge-padded by repeating the boundary row — the exact windowing convention already proven in `sequence_prior_dataset.py`'s `context_radius`. **No new precompute needed** — reuses the existing HyenaDNA-small HDF5 files as-is. |
| [`deepsv/models/cross_attn_cnn.py`](../deepsv/models/cross_attn_cnn.py) | `WindowCrossAttention` + `CrossAttnDeepSV`. |
| [`deepsv/models/__init__.py`](../deepsv/models/__init__.py) | Exports the new classes. |
| [`scripts/train_fused_model.py`](../scripts/train_fused_model.py) | `--model cross_attn` + `--context-radius` / `--attn-heads` / `--attn-d-model` / `--attn-dropout` / `--attn-hooks`. Reuses `FiLMTrainer` unchanged — `CrossAttnDeepSV` exposes the same `cnn_parameters()` / `fusion_parameters()` / `freeze_backbone()` / `unfreeze_backbone()` surface as `FusedDeepSV`, so the existing two-stage training loop, gradient clipping, LR scheduling, class-weighting and stratified validation all apply with zero trainer changes. |

**Not yet done** — `scripts/call_fused_deletions.py` / `FusedPredictor` still only do single-vector lookup. Inference with `cross_attn` needs the same `context_radius`-aware lookup added there before you can run it end-to-end. Flagging this now so it isn't a surprise later; it's the same edit pattern as the dataset change and should be small.

**Not yet tested** — there's no GPU/torch on this machine, so the code above is written and syntax-checked (`ast.parse`) but not shape-verified against a live forward pass. Before a full training run, do a 2-minute sanity check on your GPU box:

```python
import torch
from deepsv.models import CrossAttnDeepSV

model = CrossAttnDeepSV(embed_dim=256, context_radius=10, hooks=("hook3",))
image = torch.randn(4, 3, 256, 256)
embedding = torch.randn(4, 21, 256)  # T = 2*10+1
logits = model(image, embedding)
assert logits.shape == (4, 2)
print("OK", logits.shape)
```

## Architecture

### The core idea, and why it's different from what's already in the repo

FiLM and late context calibration (both live today) fuse **one pooled 256-d vector per target window** — the entire ~50bp of local sequence context gets averaged into a single point before the model ever sees it. A window that's a false-positive-prone deletion-like pileup signal, and the actual repeat element three windows upstream that explains *why* it's a false positive, look identical to those two fusion paths: neither can look elsewhere.

Cross-attention removes that pre-averaging. The CNN's own spatial columns (plural) each get to decide, per column, which of several neighbouring window embeddings is relevant — instead of one summary vector that's already had that decision baked in at precompute time.

### Where Q, K, V actually come from (grounded in this repo's shapes)

Reading `ModernDeletionCNN` directly (`deepsv/models/cnn.py`):

- Input images are 256×256. Four stride-2 max pools (one per block) mean the feature map at `hook3` (after block 3) is **96 channels × 32 × 32**, and at `hook4` (after block 4) is **96 × 16 × 16**.
- The classifier head already treats the two spatial axes asymmetrically: it keeps the **width axis (W)**, which is the genomic-position axis (README: "each pixel column = one genomic position"), and collapses the **height axis (H)**, the read/pileup-row axis, via `concat(avg_pool_H, max_pool_H)` before the final FC layers. Rows don't have a stable position meaning; columns do.

So the attention Q is built the same way the classifier already summarizes H — **one token per column**, `concat(avg_H, max_H)` — giving 32 query tokens at `hook3` (each spanning roughly 50bp / 32 ≈ 1.6bp of the rendered window) or 16 at `hook4` (~3.1bp/token). This isn't a new idea grafted onto the CNN; it's literally reusing the axis-preservation the architecture already commits to.

K/V come from `FusedDataset(context_radius=R)`: the target window's HyenaDNA-small embedding plus `R` neighbours on each side, `T = 2R+1` tokens of 256-d each. Default `R=10` → 21 tokens spanning ~1050bp around the target window — small enough (32×21 ≈ 670 Q·K pairs at `hook3`) that the "cross-attention is expensive" concern from the general comparison doesn't really apply to this specific design; the token counts are tiny because the tokens are pre-pooled per-window, not per-basepair.

### Preserving the repo's identity-at-init discipline

FiLM's `(1+γ)` zero-init and the context-calibration `_ZeroInitMLP` both guarantee the model is an exact identity wrapper around the image-only CNN at step 0 — training only deviates once the fusion heads learn something useful. Cross-attention doesn't get this for free (a generic attention block computes something non-trivial from step 0), so `WindowCrossAttention` engineers it in explicitly: **only the output projection is zero-initialised**. The attention itself (Q/K/V projections, softmax, relative-position embedding) computes real, non-degenerate weights from the start — so gradients flowing back through attention aren't dead — but the *delta added back into the CNN feature map* is `out_proj(attn_out) = 0` exactly at step 0, because `out_proj`'s weight and bias are zero. Net effect: same training-stability guarantee as the other two live fusion paths, without neutering attention's internals the way a fully zero-initialised block would.

### Relative position embedding

Context tokens are ordered upstream → target → downstream. Without a position signal, attention can't tell "two windows upstream" from "two windows downstream," which matters for asymmetric signals like a breakpoint motif that only appears on one side. `_RelativePositionEmbedding` is a small zero-initialised lookup table added to K, so — consistent with the same discipline — position carries no bias at step 0 and is learned in gradually.

## How to improve results from here

Roughly in the order I'd actually try them:

1. **Warm-start from the M0 checkpoint, same as FiLM.** `--init-cnn-checkpoint` + Stage A (backbone frozen, attention-only) is already wired through `FiLMTrainer` unchanged. Skipping this and training cross-attention on a random backbone is testing a different, harder problem — don't do that first.
2. **Ablate `context_radius` before anything else.** 10 (≈1050bp) is a reasonable default given HyenaDNA-small's own causal receptive field extends much further (32kb), but the *window-granularity* context that's actually useful for calling a 50–10,000bp deletion is an empirical question. Try 5, 10, 20 and check the stratified F1 by deletion-length bucket (already implemented in `FiLMTrainer.validate`) — I'd expect larger radius to help disproportionately on the 1k–10k bp bucket and matter less for 50–200bp.
3. **Combine with the existing context-calibration path.** Nothing stops you from also adding a late zero-init logit delta on top of cross-attention's mid-level fusion — the two are not mutually exclusive, and `film_context`'s success (mid-level + late-logit) is direct evidence this combination is worth the small extra parameter cost. Would need a small model change (a `context` flag alongside `hooks` on `CrossAttnDeepSV`) — not yet built, but cheap to add if cross-attention alone helps.
4. **Try `hooks=("hook3", "hook4")` once single-hook works.** Multi-scale attention (fine 32-wide + coarse 16-wide) roughly doubles attention compute but is still small in absolute terms given the token counts above — worth an ablation once the simpler single-hook version is validated, not before.
5. **Use attention weights for QA, not just prediction.** `nn.MultiheadAttention(..., need_weights=True)` at eval time gives you, per false positive/negative, exactly which context windows the model attended to. This is the one diagnostic capability none of the single-vector fusion methods can offer: if the model is consistently attending to windows that don't overlap known repeat/segdup tracks for its false positives, that's a data or label problem, not a modeling one — and you'd only find that out by looking at the weights.
6. **Once this works, the K/V source doesn't have to be HyenaDNA alone.** The repo already has NT-v2-100M embeddings precomputed. A straightforward extension is concatenating both backbones' context windows into one longer K/V sequence (with a small learned "which encoder" embedding added, same trick as the position embedding) — lets attention pick whichever encoder is more informative per column instead of committing to one upfront. Worth doing only after the single-backbone version is validated; don't multiply unknowns.
7. **Watch Stability at init in practice, not just in theory.** The zero-init output projection guarantees identity *at step 0* but cross-attention's qualitative stability score was still the lowest of the two live methods (see the scorecard in `fusion_strategies_comparison.md`) — meaning it's more prone to drifting once training starts, not at init. Keep `lr_film` (the attention param group's LR) conservative initially and lean on the already-implemented `ReduceLROnPlateau` + gradient clipping; if validation F1 is noisier than FiLM's was, that's the expected failure mode, not a bug.

## Suggested first experiment

```bash
python scripts/train_fused_model.py \
    --manifest data/fused/NA12878/manifest.csv \
    --model cross_attn \
    --embeddings data/hyenadna_embeddings.h5 \
    --train-chroms 20,21 --val-chroms 22 \
    --output models/cross_attn_r10_hook3.pth \
    --init-cnn-checkpoint models/m0_best.pth \
    --context-radius 10 \
    --attn-hooks hook3 \
    --attn-heads 4 \
    --stage-a-epochs 2 \
    --epochs 10
```

Compare its stratified F1 directly against the existing `film_context` M1 run on the same split — same manifest, same chroms, same M0 warm-start, only the fusion mechanism differs. That isolates the comparison to what this doc is actually claiming: does letting spatial columns attend over a context window beat pre-pooling that context into one vector.
