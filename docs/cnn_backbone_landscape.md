# Is there a newer DeepSV? What the literature actually shows

Short answer: **no official DeepSV v2 exists.** The original authors (Cai, Wu, Gao — BMC Bioinformatics, Dec 2019) never published a follow-up, and their GitHub (`CSuperlei/DeepSV`) has no newer release. But the field moved on without them, and there are two genuinely separate upgrade paths worth distinguishing before picking one.

## The two things "DeepSV is dumb" could mean

1. **The CNN backbone is dated** — `ModernDeletionCNN` is explicitly "matching legacy Keras model" (its own docstring), a VGG-style stack of plain 3×3 conv + BatchNorm + max-pool blocks. That's a 2015-era design choice, contemporaries of Inception V3.
2. **The whole framing is dated** — DeepSV treats deletion calling as *classify one 50bp sliding-window pileup image as deletion/non-deletion*. That framing itself, independent of backbone quality, has a structural weakness: a fixed small window can't see a breakpoint pair that's far apart, and cross-breakpoint context gets lost.

These have different fixes, different costs, and — importantly — the second one has already been solved by someone else.

## Path A: swap the backbone, keep the framing (low risk)

A 2025/2026 paper on modernizing DeepVariant-style pileup classifiers found that swapping **Inception V3 → EfficientNet-B3** gave a real, unambiguous win: F1 +0.51pp (94.80% → 95.31%), **half the parameters** (23.9M → 12.3M), and ~35 min/epoch faster training. The gain came specifically from **MBConv blocks with squeeze-and-excitation (SE)** — a cheap per-channel attention mechanism that reweights feature-map channels by how informative they are — which the authors credit with better sensitivity to "fine-grained cues," i.e. exactly the subtle pileup signals (soft-clipping, mapping-quality dips) this repo's CNN is trying to pick up on.

This is directly, cheaply applicable to `ModernDeletionCNN`: it's the same *kind* of legacy plain-conv design as Inception V3, at a much smaller scale. Adding SE blocks to the existing 5-block structure (a ~10-line addition per block: global-avg-pool → 2-layer MLP → sigmoid gate → channel-wise multiply) is a small, backward-compatible change that wouldn't disturb any of the FiLM/cross-attention hook points, since SE just reweights channels in-place before the hooks fire.

**Verdict: worth doing, and cheap.** This is the "improve the CNN without touching the framing" lever.

## Path B: change the framing itself (what Cue actually did)

**Cue** (Nature Methods, 2023) is the closest thing to a real successor in spirit, and it's a bigger rethink than a backbone swap:

- Instead of classifying one window as deletion/non-deletion, Cue frames SV discovery as **multi-class keypoint localization** — a stacked-hourglass CNN (borrowed from human pose estimation) predicts *breakpoint heatmaps* over a 256×256 image that juxtaposes two genome intervals on the x and y axes, with five signal channels (depth, split-reads, read-pair orientation signals, etc.) instead of RGB.
- Cue's own stated motivation is almost verbatim the Path-A-doesn't-fix-this critique: "read pileup images are not well suited for detecting complex types and larger sizes of SVs due to the loss of relevant cross-breakpoint information." Treating detection as image classification (what this repo does) inherently can't see two breakpoints that are far apart in the same decision; keypoint regression over a wide juxtaposed interval can.
- Results: 1–15% F1 improvement over prior state of the art for deletions on synthetic data, 3–22% F1 improvement on HG002 real data, plus the ability to call inversions, duplications, and complex compound SVs (INVDUP, INVDEL) the sliding-window approach can't represent at all.
- Trained entirely on synthetic SVs (SURVIVOR-simulated), Adam @ 1e-4, focal-L2 loss to handle the extreme foreground/background pixel imbalance in a keypoint heatmap.

**Verdict: the real "is there something better" answer — but it's a different system, not a drop-in upgrade.** Adopting Cue's framing would mean replacing the 50bp-window/manifest/classification pipeline this whole repo (and the FiLM/cross-attention fusion work already built) is organized around, with a breakpoint-heatmap pipeline. That's a rewrite, not a refactor.

## Other things that came up, briefly

- **NPSV-deep** (Bioinformatics, 2024) — Siamese/contrastive network that compares real reads against *simulated* reads of known genotype in a shared embedding space. Solves a different stage of the problem (genotyping a *known* candidate SV, not discovering one) — not directly relevant to what this repo does, but the "compare against simulated reads" trick is a reasonable idea if genotyping is ever added downstream.
- **DeepSVFilter** (2021) — a post-hoc filter for existing SV callers' output, not a caller itself.
- **BreakNet**, **SVcnn**, **Cnngeno** — CNN-based SV/genotyping tools, but built for **long-read** data (PacBio/ONT); this repo's BAM handling and image generation are short-read-pileup specific, so these aren't directly portable.
- **VariantTransformer** — a transformer that re-classifies already-called variants from tabular VCF-derived features (89% accuracy, ROC-AUC 0.88), i.e. a filtering/refinement layer on top of a caller's output, not a raw-pileup model.

## What this means for this repo's roadmap

Given the fusion work already in progress (HyenaDNA + cross-attention, see [`cross_attention_design.md`](cross_attention_design.md)), the CNN backbone question is orthogonal but not independent — it's worth sequencing deliberately:

1. **Do Path A first, and soon.** Adding SE blocks to `ModernDeletionCNN` is small, cheap, backward-compatible with every fusion hook already built, and has direct published evidence of a free win on the same *kind* of architecture. It should probably happen *before* the cross-attention ablations in the improvement roadmap, since a stronger backbone changes what "beating the baseline" means for every fusion experiment downstream — do it too late and you'd have to re-run comparisons.
2. **Treat Path B (Cue-style reframing) as a separate, much bigger decision — not part of the current roadmap.** It's the honest answer to "is there something fundamentally better," but committing to it means deciding whether this project's goal is "best deletion caller possible" (in which case, seriously consider it) or "demonstrate that fusing a frozen genomic LM improves a pileup-CNN caller" (in which case Cue's framing is a different research question, and swapping to it now would strand the fusion work already built). Worth a deliberate go/no-go conversation on its own, not folded into the next sprint.
3. Not pursuing NPSV-deep/BreakNet/SVcnn/DeepSVFilter/VariantTransformer right now — each solves an adjacent stage (genotyping, long-read input, post-hoc filtering) that this repo doesn't currently do, rather than the discovery task the fusion work targets.

---

Sources:
- [DeepSV — BMC Bioinformatics (2019)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6909530/)
- [Cue: a deep learning framework for structural variant discovery and genotyping — PMC (Nature Methods, 2023)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10152467/)
- [NPSV-deep — Bioinformatics (2024)](https://academic.oup.com/bioinformatics/article/40/3/btae129/7623007)
- [Rethinking DeepVariant: Efficient Neural Architectures for Intelligent Variant Calling — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12786509/)
- [A deep learning approach for filtering structural variants (DeepSVFilter) — PubMed](https://pubmed.ncbi.nlm.nih.gov/33378767/)
- [BreakNet: detecting deletions using long reads — BMC Bioinformatics](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-021-04499-5)
- [SVcnn: detecting structural variation from long-read data — BMC Bioinformatics](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-023-05324-x)
- [Cnngeno: CNN-based SV genotype calling — PubMed](https://pubmed.ncbi.nlm.nih.gov/33810991/)
- [A Hitchhiker Guide to Structural Variant Calling: benchmark across sequencing technologies](https://www.mdpi.com/2227-9059/13/8/1949)
