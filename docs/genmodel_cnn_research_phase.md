# Research Phase — a genuinely candidate-aware Genomic-Model + CNN for deletion detection

**Status:** research report + implementation-ready recommendation. **No architecture code written.** Stop point for review before any coding (per request §12).

---

## 0. Framing (what the preliminary result does and does not show)

The measured single-seed result is:

> *Frozen reference-sequence HyenaDNA embeddings, fused into a pileup CNN through the tested FiLM and cross-attention implementations, did not produce a measurable improvement in the preliminary experiment.*

It is **not** evidence that "GenModel + CNN cannot work." The load-bearing weakness is **what the genomic branch is fed**, not that it is a genomic branch:

- The branch encodes the **reference** sequence in a fixed 50 bp grid window.
- The reference is **identical** whether or not the sample carries the deletion → the branch supplies a *locus prior* ("is this a fragile/repetitive place?"), never *evidence for this candidate*.
- Zero-ablation predictions (§A) are expected to confirm the trained fusion is ~ignoring the branch.

The whole research phase is therefore organised around one lever: **give the genomic branch information that is candidate-specific (depends on the hypothesised deletion) or sample-specific (depends on this sample's reads).** Everything below is scored against that lever.

The 3-seed confirmation + paired bootstrap of the preliminary result is running separately (`deepsv-confirm-3seed`); it adjudicates whether the 0.01 spread is noise but does not change this report's direction.

---

## Deliverable A — Diagnostic plan (Stage 0, cheap, run before any new architecture)

Purpose: separate **"the fusion machinery is broken"** from **"the reference embedding carries no usable signal."** All three run on the *existing* trained checkpoints and/or the existing dataset; no new architecture.

### A1. Oracle-signal test (positive control — can the machinery learn *anything*?)
- **Construction:** replace the genomic embedding fed to the fusion pathway with a **synthetic label-correlated vector**, at controlled signal-to-noise. Two variants:
  - *Scalar-expand:* `e = s·(2y−1)·u + ε`, where `u` is a fixed random unit vector (256-d), `y` the label, `ε ~ N(0, σ²)`, `s` sweeps SNR ∈ {high, medium, low}.
  - *Prototype:* `e = μ_pos` if `y=1` else `μ_neg`, plus per-sample noise; `‖μ_pos − μ_neg‖` sets separability.
- Train the **same** fusion pathway (frozen backbone, identity-init) on these synthetic embeddings, same split/optimizer/early-stopping.
- **Measure:** val/test F1 vs the image-only baseline.
- **Decision rule:**
  - Fusion F1 rises sharply toward the oracle ceiling ⇒ **machinery works**; the real HyenaDNA-ref representation simply lacks candidate signal ⇒ proceed to Families A/C (change the *input*).
  - Fusion F1 stays flat even with a strong oracle ⇒ **training/init/gradient/architecture bug** ⇒ fix that first (do **not** build a bigger model on broken plumbing).
- Cost: ~3 short fusion trainings (~20 min each on T4).
- ⚠️ The oracle deliberately leaks the label; it is a control, never reported as a real result.

### A2. Embedding-shuffle test (is the branch used at all?)
- **Construction:** permute the genomic embeddings across samples (break embedding↔(image,label) correspondence), keep images+labels intact. Two modes: (i) **train** a fresh fusion model on shuffled embeddings; (ii) **evaluate** an already-trained model with shuffled embeddings.
- **Measure:** ΔF1, ΔROC-AUC, and prediction agreement vs the unshuffled model.
- **Decision rule:** no meaningful change ⇒ the branch is inert (model relies on image only). A drop ⇒ the branch carries usable information.
- Cost: 1 training + eval passes (minutes).

### A3. Zero-ablation / representation-sensitivity test (how much does output move?)
For each existing trained fusion checkpoint (FiLM, film_context, cross_attn), evaluate the **same weights** under four genomic inputs: **original / zeros / per-batch-mean / shuffled**. Report:
- % of binary predictions that change;
- mean |Δlogit| (positive-class logit);
- ΔF1, ΔROC-AUC;
- **output norm of the fusion pathway** (the additive contribution to logits before/after the fusion head).

Also introspect the trained weights:
- gradient norms on fusion parameters (from a held-out batch);
- norm of the cross-attention output projection;
- learned **FiLM γ (scale) deviation from 1** and **β (bias) magnitude**;
- whether the **zero-initialised output projections stayed ≈ 0** (identity-at-init never escaped).

**Expected result given the preliminary run** (cross_attn ≡ FiLM byte-identical; film_context Δ = 5 negatives): near-zero %changed predictions, tiny |Δlogit|, FiLM γ≈1/β≈0, output projections ≈0 → the branch is being ignored **because the reference embedding has nothing to add**, not because of a bug. A2/A1 confirm which. This is the empirical justification for changing the *input representation* rather than the fusion plumbing.

**Stage-0 exit gate:** proceed to Family A only if A1 shows the machinery can exploit signal. If A1 fails, fix training first.

---

## Deliverable B — Literature table (primary sources)

Convention: "REF/ALT-aware" = does the genomic branch see the alternate/mutant allele (not just reference)? "Sample-specific" = does it see this sample's reads?

| # | Paper (year) | Task | Genomic input | Genomic model | 2nd modality | Fusion | REF/ALT-aware | Sample-specific | Main result | Relevance to us |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **DeepSV** (Cai et al., BMC Bioinf 2019) | deletion calling | — | CNN on pileup image | (single modality) | — | no | yes (reads→image) | CNN over pileup images calls deletions | Our M0 base; sequence not used at all |
| 2 | **DeepVariant** (Poplin et al., Nat Biotech 2018) + **Pangenome-aware** (2024) | small-variant calling | candidate genotype channels | CNN on pileup image | reference channel *as pixels* | channel concat | ref only, as image | yes | SOTA small-variant caller; pangenome ref improves recall | Sequence enters as an image channel, not an LM embedding — a fusion-by-channels precedent |
| 3 | **Cue** (Popic et al., bioRxiv 2022 / Nat Methods) | SV discovery+genotyping | read-signal image | CNN (image) | — | — | no | yes | Learns SV signals from images; notes images poorly capture large/complex SVs | Motivates adding sequence for what the image misses |
| 4 | **NPSV-deep** (Linderman et al., Bioinformatics 2024) | SV genotyping (ins/del) | in-silico vs real pileup | CNN, image-similarity | simulated ALT pileup | siamese/similarity | **yes (simulated ALT)** | yes | 25% fewer genotyping errors on GIAB HC SVs | **Directly relevant:** compares real reads to a *simulated ALT* — a sample×hypothesis contrast |
| 5 | **sv-channels** (Santuari et al., bioRxiv 2024) | deletion filtering | 1-D read-signal channels | 1-D CNN | — | — | no | yes | 1-D CNN filters deletion calls competitively | Alternative encoding of read evidence; no sequence branch |
| 6 | **HyenaDNA** (Nguyen et al., NeurIPS 2023) | genomic LM (pretrain) | reference DNA, ≤1M nt | implicit-conv LM | — | — | no | no | Single-nt, long-context genomic LM | Our current encoder; strong long-context but ref-only input here |
| 7 | **Caduceus** (Schiff et al., ICML 2024) | genomic LM / VEP | reference DNA | Mamba, RC-equivariant | — | — | no (ref LM) | no | RC-equivariance improves long-range VEP | Candidate encoder swap **only if** input becomes REF/ALT |
| 8 | **Nucleotide Transformer** (Dalla-Torre et al., Nat Methods 2024) | genomic LM / VEP | reference DNA (6-mer) | Transformer ≤2.5B | — | — | zero-shot via masking | no | Strong functional-variant prioritisation; LoRA-tunable | Encoder option; LoRA path for Family D |
| 9 | **DNABERT-2** (Zhou et al., 2023) | genomic LM | reference DNA (BPE) | Transformer | — | — | no | no | Efficient multi-species encoder | Encoder option; BPE tokenisation caveat for breakpoints |
| 10 | **GPN / GPN-MSA** (Benegas et al., PNAS 2023 / Nat Biotech 2024) | genome-wide VEP | REF vs ALT window (+MSA) | conv / MSA LM | — | — | **yes** | no | VEP = **log-likelihood ratio ALT/REF**; MSA adds conservation | Canonical REF-vs-ALT contrast; supports Family A delta |
| 11 | **Embedding-based VEP** (review: Tang & Koo, arXiv 2411.11158, 2024; benchmark: Nat Commun 2025) | non-coding VEP | REF vs ALT windows | multiple GFMs | — | — | **yes** | no | Compare REF/ALT **embeddings** (cosine/L2) as effect score; no single GFM dominates | **Core evidence** that E_alt−E_ref is a usable candidate representation |
| 12 | **Evo 2** (Brixi et al., Arc Institute 2025) + blind-spot critique (bioRxiv 2026) | multi-type VEP incl. **indels** | REF vs ALT (long ctx) | 7B genomic LM | — | — | **yes** | no | Embedding classifier 0.997 AUROC SNV, **zero-shot indels 0.991**; but short-range blind spots | Proof GFMs can score **indels/deletions** when given ALT; caution on short-range signal |
| 13 | **BMFM-DNA** (arXiv 2507.05265, 2025) | variant-effect FM | **variant-encoded** sequence | Transformer FM | — | — | **yes (allele-encoded)** | partial (population variants) | Variant-encoded model beats reference-only across tasks | Empirical: encoding the allele (not just ref) helps — validates candidate-aware input |
| 14 | **DeBreak** (Chen et al., Nat Commun 2023) | breakpoint precision | split-read subsequences | (alignment heuristics) | — | — | yes (junction) | yes | Precise breakpoints via split-read orientation/clipping | Blueprint for **Family C** sample-aware junction features |
| 15 | **Local-assembly junction** (SVMerge; Chen et al. cancer-genome assembly) | breakpoint validation | de-novo local consensus | assembly | reads | — | yes (ALT junction) | **yes** | Consensus junction sequence validates ~60% of deletions | The strongest sample-specific signal; motivates Family C |
| 16 | **RDBKE / deep segmentation refinement** (Zheng et al., PLOS Comp Biol 2021) | breakpoint refinement | read-depth + seq | seq-model refiner | read-depth | — | no | yes | Refines RD-based SV breakpoints to bp resolution | Our repo's BoundaryRefiner lineage; complementary |
| 17 | **PEFT for genome models** (Lan et al., arXiv 2402.08075, 2024) | GFM downstream | reference DNA | NT + LoRA | — | — | n/a | no | LoRA tunes GFMs with ~0.1% params, <15 min/GPU | Feasibility basis for **Family D** on our compute |
| 18 | **Gated / bilinear multimodal fusion** (survey Baltrušaitis et al.; GCA modules 2023–2025) | multimodal fusion | — | — | — | gated/bilinear/co-attn | n/a | n/a | Gated residual fusion preserves a strong unimodal path | **Family F**: keep image path dominant, let sequence modulate |

**Reading of the table (what information each branch actually gets):** rows 6–9 (ref-only LMs, our current setup) give a *locus prior*. Rows 10–13 (REF-vs-ALT) give a *candidate hypothesis* signal — the same sequence position scored under the alternate allele — which is exactly what distinguishes a true deletion junction from an intact locus, and generalises to indels (row 12). Rows 4, 14–15 give *sample evidence* — simulated-ALT pileups or real split-read/consensus junction sequence — the only branch that differs between a true deletion and a same-locus false candidate *in this sample*.

---

## Deliverable C — Architecture comparison matrix

**Scoring convention: 1–5, where 5 = most favorable** (so for cost/risk columns, 5 = cheap / low-risk). Candidates:

- **C1 — Delta-FiLM (Family A):** pooled `E_ref, E_alt, E_alt−E_ref` → FiLM/late-calibration into the CNN. *(default first experiment)*
- **C2 — Delta-cross-attention (Family A):** REF and ALT **token sequences** → cross-attention with CNN columns.
- **C3 — Dual-breakpoint / junction encoder (Family B):** left-context, right-context, ALT-junction encoders + length/repeat features → structured breakpoint-pair rep.
- **C4 — Sample-aware read/junction branch (Family C):** encode this sample's soft-clipped/split-read tails or local consensus junction with the GFM.
- **C5 — Partial LoRA fine-tune (Family D):** unfreeze last GFM block(s) / LoRA on the REF/ALT input (built on C1/C2).
- **C6 — Gated residual fusion (Family F):** fusion redesign that guarantees a dominant image-only path; applied to a delta input.

| Candidate | Mech. fit | Exp. gain | Novelty | Impl. cost | GPU cost | Data req. | Overfit risk | Debug risk | Pub. value | **Σ** |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **C1 Delta-FiLM** | 4 | 3 | 3 | 4 | 4 | 4 | 4 | 4 | 3 | **33** |
| **C2 Delta-cross-attn** | 4 | 3 | 4 | 3 | 3 | 4 | 3 | 3 | 4 | **31** |
| **C3 Dual-breakpoint** | 4 | 3 | 4 | 2 | 3 | 3 | 3 | 2 | 4 | **28** |
| **C4 Sample-aware reads** | 5 | 4 | 5 | 2 | 2 | 2 | 2 | 1 | 5 | **28** |
| **C5 LoRA + delta** | 4 | 3 | 2 | 3 | 2 | 4 | 2 | 2 | 3 | **25** |
| **C6 Gated fusion (alone)** | 2 | 2 | 2 | 4 | 4 | 5 | 4 | 3 | 2 | **28** |

(5 = favorable throughout; higher Σ = better first-screen candidate. C4 and C3 tie C6 on Σ but score far higher on mechanistic fit / pub value — Σ is a screen, not the ranking; see Deliverable D.)

### Required explicit answers, per candidate

**C1 Delta-FiLM** — *New info:* the alternate (post-deletion) junction sequence for this candidate, contrasted with the intact reference. *Absent from image because:* the image shows read geometry/coverage, not the reference nucleotide content at the hypothesised junction (microhomology, repeat, GC at the breakpoint). *Short deletions:* depth signal is weakest there, so an orthogonal sequence cue has the most headroom. *Anchor negatives:* their hypothesised junction sits at a shifted, non-breakpoint locus → different delta; repeat-driven anchors get a distinguishing sequence signature. *Current BAM/VCF:* yes. *Rebuild dataset:* no. *Re-run embeddings:* yes (add an ALT embedding per window). *Smallest falsifier:* Delta-FiLM ≤ film_context on val F1 with a non-zero learned FiLM γ deviation ⇒ delta carries no usable signal.

**C2 Delta-cross-attn** — *New info:* token-level REF↔ALT correspondence (where exactly the junction diverges), richer than a pooled delta. *Rest as C1*, but higher capacity ⇒ higher overfit/debug risk on 171-positive test. *Falsifier:* no gain over C1 despite more capacity ⇒ pooled delta already captures what's available.

**C3 Dual-breakpoint** — *New info:* explicit left/right breakpoint contexts + ALT junction + length/repeat/complexity scalars as a structured object. *Absent from image:* per-breakpoint sequence context and repeat annotation. *Short deletions / anchors:* directly models the two junctions that define a deletion. *Current data:* yes. *Rebuild:* no. *Re-run embeddings:* yes (3 encodings/candidate). *Falsifier:* structured encoder ≤ C1 ⇒ structure adds nothing over the pooled delta.

**C4 Sample-aware reads** — *New info:* the **sample's own** nucleotide evidence — soft-clipped tails, split-read junction subsequences, or a local consensus of the ALT junction. This is the *only* branch that differs between a true deletion and a same-locus false candidate in this sample. *Absent from image:* the pileup image discards base identity of clipped/split segments. *Short deletions:* small deletions still produce clipped/split reads whose junction sequence is decisive even when depth barely dips. *Anchor negatives:* a false candidate has no supporting ALT-junction reads → the branch sees noise, not a junction. *Current BAM:* yes (reads are available), but needs a per-candidate read-extraction + encoding pipeline. *Rebuild dataset:* partial (new per-candidate read features; images unchanged). *Re-run embeddings:* yes (sample-specific, cannot be precomputed genome-wide). *Falsifier:* shuffling read-derived features across candidates does not drop F1 ⇒ branch unused.

**C5 LoRA + delta** — *New info:* none beyond C1/C2's input; it *adapts the encoder* to the deletion-junction task. Only worth it once a frozen delta shows signal. *Overfit risk high* on one individual. *Falsifier:* LoRA over frozen-delta gives no val gain and worse test ⇒ overfitting, stop.

**C6 Gated fusion (alone)** — *New info:* **none** — it is plumbing. Included only as a *safety wrapper* to guarantee the sequence branch cannot degrade confident image predictions; must be paired with a better input (C1/C4). *Falsifier:* trivially, it cannot improve over image-only if the branch has no signal — that's the point of pairing it.

---

## Deliverable D — Top-three recommendation

Ranked by the request's priorities (mechanistic plausibility → true-vs-nearby discrimination → feasibility → novelty → P(measurable gain) → interpretable-if-null):

### #1 — Candidate-aware REF/ALT Delta Fusion (C1, with C6 gating as a wrapper)
- **Plain language:** for each candidate we build two sequences — the intact reference, and the sequence you'd get *if this exact deletion happened* (its breakpoint junction). We encode both with HyenaDNA and feed their **difference** to the CNN. Now the sequence branch depends on the specific candidate, and the image says whether the reads actually support that junction.
- **Inputs:** per window: `E_ref ∈ ℝ²⁵⁶`, `E_alt ∈ ℝ²⁵⁶` (mean-pooled over the junction window); candidate rep `[E_ref ‖ E_alt ‖ E_alt−E_ref] ∈ ℝ⁷⁶⁸`.
- **Fusion location:** FiLM at CNN `hook3`/`hook4` (reuse `film_context`), optionally wrapped in a **gated residual** (C6) so `logit = image_logit + g·Δ`, `g∈[0,1]` learned, `g`-init 0.
- **Trainable / frozen:** frozen HyenaDNA + frozen M0+SE backbone; train only the FiLM/gate head (~120–240 k params).
- **Loss:** weighted cross-entropy (as now). Optional auxiliary: contrastive REF/ALT compatibility (see E).
- **Schedule:** identity-init, Adam 1e-4, val-F1 checkpoint, patience 6 — identical to current runs.
- **Impl. time:** ~0.5–1 day (ALT-embedding precompute + head). **GPU:** ~1 embedding rebuild (~15 min) + 3 short trainings.
- **Failure modes:** (a) pseudo-candidate ambiguity for negatives (§E); (b) delta dominated by mean-pool coarseness (mitigate with C2); (c) 49 bp grid offset dilutes the junction (mitigate: center the ALT window on the breakpoint, not the 50 bp grid).
- **Success gate:** ≥ +0.01 F1 over film_context **and** improvement on 50–200 bp recall **or** anchor specificity, confirmed at 3 seeds + paired bootstrap.

### #2 — Sample-aware read/junction branch (C4)
- **Plain language:** instead of (or alongside) the reference, feed the GFM the *sample's own* reads at the candidate — the clipped/split-read tails and a local consensus of the junction. This is the only branch that actually differs between a real deletion and a false one in this sample.
- **Inputs:** per candidate, a set of read-derived subsequences (soft-clipped tails ≥ k bp, split-read segments) → GFM token embeddings → permutation-invariant pool (attention/DeepSets) → `ℝ²⁵⁶⁺`.
- **Fusion:** cross-attention or gated fusion with CNN features.
- **Trainable/frozen:** frozen GFM (Stage A), aggregation head trainable; LoRA later.
- **Loss:** weighted CE; optional REF/ALT read-support contrastive head.
- **Impl. time:** ~3–5 days (per-candidate read extraction from BAM, aggregation). **GPU:** higher (variable #reads/candidate, sample-specific, no precompute).
- **Failure modes:** read-extraction cost, error-prone clipped tails, variable read counts, leakage if features encode coverage the image already has.
- **Success gate:** same F1 + strata gate; must beat C1 to justify its cost.
- **Why #2 not #1:** highest ceiling and novelty, but highest implementation/debug/GPU cost and overfitting risk on one individual — sequence it *after* C1 proves the fusion can use candidate signal at all.

### #3 — Delta REF/ALT cross-attention (C2)
- **Plain language:** same REF/ALT idea as #1 but keep the *token sequences* and let the CNN columns attend over where REF and ALT diverge, instead of collapsing to a pooled difference.
- **Inputs:** `E_ref_tokens ∈ ℝ^{L×256}`, `E_alt_tokens ∈ ℝ^{L×256}` (L≈ junction window / pooling), cross-attention query from CNN columns.
- **Fusion:** cross-attention head (reuse `CrossAttnDeepSV`), zero-init output projection.
- **Trainable/frozen:** frozen encoders/backbone; attention head (~170 k) trainable.
- **Impl. time:** ~1 day on top of #1. **GPU:** modestly higher than #1.
- **Failure modes:** more capacity → more overfitting on small test; only worth it if #1 shows the pooled delta already helps.
- **Success gate:** must beat **#1** (not just film_context) to justify the extra capacity.

---

## Deliverable E — Implementation-ready spec: **Candidate-aware REF/ALT Delta Fusion** (C1)

> The default first architecture (request §8). Keeps the CNN and dataset unchanged; only the **sequence representation** and **fusion input** change.

### E1. Data-flow diagram
```
candidate (chrom, position p, hypothesised length L)
      │
      ├── REF window  = ref[p−F : p+F]                     (2F bp, intact locus)
      │        └─ HyenaDNA (frozen) ─ mean-pool ─► E_ref ∈ ℝ²⁵⁶
      │
      └── ALT window  = ref[p−F : p] ++ ref[p+L : p+L+F]   (2F bp, breakpoint junction)
               └─ HyenaDNA (frozen) ─ mean-pool ─► E_alt ∈ ℝ²⁵⁶

candidate rep  c = [E_ref ‖ E_alt ‖ (E_alt − E_ref)] ∈ ℝ⁷⁶⁸
      │
pileup image (256×256×3) ─► frozen M0+SE CNN ─ hook3,hook4 features
      │                                   │
      └────────── FiLM(c) → (γ,β) per channel ┘   (reuse film_context path)
      │
gated residual:  logit = image_logit + g · fused_Δlogit,   g = σ(w)·(init 0)
```

### E2. REF/ALT construction algorithm
For every window row (manifest has `position p`, `del_length L`, `label`, `neg_type`):
1. **Positives:** `(p, L)` = the true breakpoint window and its deletion length → ALT reconstructs the *real* junction.
2. **Negatives:** no true interval; assign a **hypothesised** length `L = del_length` (inherited from the source deletion the negative was drawn from) and treat `p` as a hypothesised left breakpoint. ALT is then a *counterfactual* junction the reads will not support. **This pseudo-candidate choice is the central design decision and the first ablation (E10).**
3. Build REF/ALT windows with flank `F` (below). Clamp at contig ends by N-padding (reuse the existing padding convention). For `L` beyond encoder context, only the **junction neighbourhood** is encoded (we never encode the full deleted segment), so context is never exceeded.
4. **Center the ALT window on the breakpoint**, not on the 50 bp embedding grid — removes the ≤49 bp grid offset that dilutes the junction in the current pipeline.

### E3. Exact sequence lengths
- Flank `F = 512 bp` (sweep {256, 512, 1024}); windows = `2F = 1024 bp`.
- HyenaDNA-small-32k handles ≤32 k → comfortable; junction at token `F`.
- Pooling: mean over the 1024 tokens (matches current), **plus** a variant pooling only the central ±128 bp around the junction (ablation).

### E4. Tensor shapes
- `E_ref, E_alt : (B, 256)`; `c : (B, 768)`.
- FiLM generator: `768 → 128 → (2·C_hook)` producing `γ,β : (B, C_hook)` at hook3 and hook4 (`C_hook = 96`).
- Gate: scalar `g : (B, 1)` from `c` (or global), init 0.
- Logits: `(B, 2)`.

### E5. Model modules
- `RefAltDeltaFiLM`: wraps frozen `ModernDeletionCNN(use_se=True)`; FiLM generators (reuse `FiLMGenerator`); zero-init output; gated residual add.
- Precompute module: `precompute_refalt_embeddings.py` — for each distinct `(chrom, p, L)` compute `E_ref` and `E_alt`; store two HDF5s (or one with `/ref`, `/alt` groups) keyed by candidate id. Reuse the *unchanged* HyenaDNA pooling from the current producer.

### E6. Fusion equations
```
γ_h, β_h = FiLMGen_h(c)                         h ∈ {hook3, hook4}
F'_h     = (1 + γ_h) ⊙ F_h + β_h                 (FiLM, γ,β zero-init ⇒ identity)
Δlogit   = ClassifierHead(F'_hook4) − image_logit
logit    = image_logit + g · Δlogit,   g = σ(w), w init −∞→ g≈0  (identity-at-init)
```

### E7. Initialization
- All FiLM output layers zero-init (γ,β = 0 ⇒ `F'_h = F_h`), gate `g≈0` ⇒ model ≡ M0+SE at step 0 (identity-at-init discipline preserved).

### E8. Trainable parameter groups, LRs, losses, checkpoint
- **Frozen:** HyenaDNA, M0+SE backbone (BN/dropout in `eval()` during training).
- **Trainable:** FiLM generators + gate (~120–240 k). Adam, **lr 1e-4**, weight decay 1e-6, grad-clip 1.0, ReduceLROnPlateau on val F1.
- **Loss:** class-weighted CE (current weights). *Optional aux:* contrastive term pulling image-features toward `E_alt` for true junctions and toward `E_ref` for negatives (weight 0.1; ablation).
- **Checkpoint:** best **val F1**; patience 6; seed first, then 3 seeds for anything promising.

### E9. Expected memory / runtime
- Precompute: ~2× current targeted embeddings (REF+ALT) → ~30 min on T4, dense-indexed sparse HDF5 (reuse `_SparseWindowArray`).
- Training: same envelope as `film_context` (~20 min/model, batch 32, ~7 GB T4).

### E10. Ablations
1. Pseudo-candidate length for negatives: `del_length` vs fixed median vs sampled — check it isn't a length-leak shortcut.
2. Delta form: `E_alt−E_ref` vs `|E_alt−E_ref|` vs full `[ref‖alt‖Δ]` vs cosine score.
3. Pooling: full-window vs central-junction.
4. Flank F ∈ {256, 512, 1024}.
5. Gate on/off (does the safety wrapper matter?).
6. Grid-centered vs grid-aligned ALT window (quantify the offset effect).

### E11. Success gate
- **Primary:** ≥ **+0.01** test F1 over `film_context`, **and** improvement on **50–200 bp recall** *or* **anchor-{up,down} specificity**, **confirmed at 3 seeds with paired-bootstrap 95% CI excluding 0**. A single-seed sub-0.01 bump does not count.

### E12. Rollback plan
- If Stage-0 (A1) fails → do **not** run C1; fix the fusion machinery first.
- If C1's ALT embeddings are byte-identical to REF for most windows (delta ≈ 0) → the junction window/flank is wrong (grid offset or F too large) → fix E4/E2 before concluding null.
- If C1 is null but zero-ablation now shows the branch *is* being read (γ≠1, output≠0) with no F1 gain → the reference-derived delta genuinely lacks sample evidence → escalate to **C4** (sample-aware reads), not to a bigger frozen-reference model.

---

## Deliverable F — Minimal experiment roadmap (each stage can stop the project)

| Stage | Experiment | Stop-if | Go-if |
|---|---|---|---|
| **0** | Oracle / shuffle / zero-ablation (A1–A3) | oracle can't be learned ⇒ fix machinery, halt new arch | machinery works ⇒ Stage 1 |
| **1** | Delta-FiLM / Delta-late-fusion (C1) | no signal *and* delta verified non-degenerate ⇒ escalate to C4 | ≥+0.01 F1 + strata gate ⇒ Stage 2 |
| **2** | Delta-cross-attention (C2) | ≤ C1 ⇒ pooled delta suffices, stop adding capacity | beats C1 ⇒ Stage 3 |
| **3** | Partial CNN unfreeze + GFM LoRA (C5/Family D), two-stage (freeze→low-lr unfreeze) | overfits (val↑ test↓) ⇒ revert to best frozen | robust gain ⇒ consider Stage 4 |
| **4** | Sample-aware read/junction branch (C4) | read features shuffle-invariant ⇒ unused, stop | gain over C1–C3 ⇒ strongest result, write up |

**Do not implement all stages at once.** Each stage is gated by 3-seed + paired-bootstrap confirmation, held-out F1, and at least one of {short-deletion recall, anchor specificity}.

---

## Data-quality note (do not mix with the first architecture experiment)
Keep the current dataset fixed for Stage 0–1 comparability. Before any **publication** claim, separately: rebuild random negatives within-split, store true chrom/pos explicitly, evaluate on additional GIAB individuals (HG002…), and report all-truth vs refinement-confirmable subsets. Mixing dataset correction into the first architecture run would confound the source of any gain.

## Research discipline (self-check against §12)
- The preliminary result is framed as a null of *one input representation + two fusion impls*, **not** of GenModel+CNN.
- Every candidate is justified by the **specific new information** it adds (candidate-aware ALT, or sample-aware reads), not by size.
- The smallest, most defensible modification (C1: REF/ALT delta on the unchanged CNN/dataset) is the recommended first step.
- Encoder swaps with unchanged ref-only input are explicitly deprioritised (C-matrix, Family E).

---
*Primary sources:* DeepSV (BMC Bioinf 2019); DeepVariant (Nat Biotech 2018) / Pangenome-aware DeepVariant (2024); Cue (Nat Methods); NPSV-deep (Bioinformatics 2024); sv-channels (bioRxiv 2024); HyenaDNA (NeurIPS 2023); Caduceus (ICML 2024); Nucleotide Transformer (Nat Methods 2024); DNABERT-2 (2023); GPN / GPN-MSA (PNAS 2023 / Nat Biotech 2024); embedding-VEP review (arXiv 2411.11158) + benchmark (Nat Commun 2025); Evo 2 (Arc 2025) + blind-spot critique (bioRxiv 2026); BMFM-DNA (arXiv 2507.05265); DeBreak (Nat Commun 2023); local-assembly junction (SVMerge); RDBKE (PLOS Comp Biol 2021); PEFT/LoRA for GFMs (arXiv 2402.08075); multimodal gated/bilinear fusion (survey + GCA).
