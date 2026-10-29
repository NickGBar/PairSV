#!/usr/bin/env python3
"""Step 4 (inference): run a trained model over a manifest and write predictions.

Reads:
  * Manifest CSV from ``generate_fused_dataset.py``
  * Trained checkpoint from ``train_fused_model.py``
  * HyenaDNA embeddings HDF5 (only needed for ``--model fused``)

Writes a predictions CSV with one row per input window:

    image_path, chrom, position, label, length,
    prob_deletion, predicted_class

Optionally, neighbouring positive windows are merged into deletion calls
written to a minimal VCF (``--vcf-out``).

Examples
--------
    # Inference with the fused (M1) model
    python3 scripts/call_fused_deletions.py \\
        --manifest data/fused/NA12878/manifest.csv \\
        --model fused \\
        --checkpoint models/fused_best.pth \\
        --embeddings data/hyenadna_embeddings.h5 \\
        --predictions-out runs/NA12878_predictions.csv \\
        --vcf-out runs/NA12878.vcf

    # Inference with the CNN-only (M0) model — no embeddings needed
    python3 scripts/call_fused_deletions.py \\
        --manifest data/fused/NA12878/manifest.csv \\
        --model cnn \\
        --checkpoint models/image_only_model.pth \\
        --predictions-out runs/NA12878_cnn_predictions.csv

    # Inference with the cross-attention fusion model — --context-radius
    # must match training (default 10)
    python3 scripts/call_fused_deletions.py \\
        --manifest data/fused/NA12878/manifest.csv \\
        --model cross_attn \\
        --checkpoint models/cross_attn_r10_hook3.pth \\
        --embeddings data/hyenadna_embeddings.h5 \\
        --context-radius 10 \\
        --attn-hooks hook3 \\
        --predictions-out runs/NA12878_cross_attn_predictions.csv
"""
from __future__ import annotations

import argparse
import csv
import logging
import math
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deepsv.inference import FusedPredictor, SequencePriorPredictor
from deepsv.inference.predictor import DeletionPredictor
from deepsv.models import ModernDeletionCNN, FusedDeepSV, CrossAttnDeepSV

# Reuse manifest/checkpoint helpers from the training script.
try:
    from train_fused_model import load_manifest, load_torch_state_dict  # type: ignore  # noqa: E402
except ModuleNotFoundError:
    from scripts.train_fused_model import load_manifest, load_torch_state_dict  # type: ignore  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


WINDOW_BP = 50  # must match generation


# ─────────────────────────────────────────────────────────────────────────────
# Inference paths per model
# ─────────────────────────────────────────────────────────────────────────────


def predict_m0(
    rows: List[dict],
    checkpoint: str,
    threshold: float,
    batch_size: int,
    use_se: bool = True,
    se_reduction: int = 8,
) -> List[Tuple[float, int]]:
    """Image-only inference.

    ``use_se``/``se_reduction`` must match how ``checkpoint`` was trained —
    see ``deepsv/models/cnn.py:SEBlock``. A mismatch surfaces as a strict
    ``load_state_dict`` failure below rather than silently loading a
    partially-initialized model.
    """
    model = ModernDeletionCNN(num_classes=2, use_se=use_se, se_reduction=se_reduction)
    state = load_torch_state_dict(checkpoint)
    model.load_state_dict(state)
    predictor = DeletionPredictor(model=model, threshold=threshold)
    image_paths = [Path(r["image_path"]) for r in rows]
    return predictor.predict_batch(image_paths)


def predict_m1(
    rows: List[dict],
    checkpoint: str,
    embeddings_h5: str,
    threshold: float,
    batch_size: int,
    embed_dim: int,
    fusion_mode: str,
    context_hidden_dim: int,
    context_dropout: float,
    use_se: bool = True,
    se_reduction: int = 8,
) -> List[Tuple[float, int]]:
    """Fused (image + embedding) inference.

    ``use_se``/``se_reduction`` must match how ``checkpoint`` was trained —
    see ``deepsv/models/cnn.py:SEBlock``.
    """
    model = FusedDeepSV(
        embed_dim=embed_dim,
        num_classes=2,
        fusion_mode=fusion_mode,
        context_hidden_dim=context_hidden_dim,
        context_dropout_rate=context_dropout,
        use_se=use_se,
        se_reduction=se_reduction,
    )
    state = load_torch_state_dict(checkpoint)
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing:
        logger.warning(
            "Checkpoint is missing %d model keys; newly initialized keys stay at "
            "their default values. First few missing keys: %s",
            len(missing),
            missing[:8],
        )
    if unexpected:
        logger.warning(
            "Checkpoint has %d unexpected keys ignored by this model. First few: %s",
            len(unexpected),
            unexpected[:8],
        )

    chroms_in_manifest = sorted({r["chrom"] for r in rows})
    with FusedPredictor(
        model=model,
        embeddings_h5=embeddings_h5,
        threshold=threshold,
        preload_chroms=chroms_in_manifest,
    ) as predictor:
        return predictor.predict_batch(
            image_paths=[Path(r["image_path"]) for r in rows],
            chroms=[r["chrom"] for r in rows],
            positions=[r["position"] for r in rows],
            batch_size=batch_size,
        )


def predict_cross_attn(
    rows: List[dict],
    checkpoint: str,
    embeddings_h5: str,
    threshold: float,
    batch_size: int,
    embed_dim: int,
    context_radius: int,
    attn_d_model: int,
    attn_heads: int,
    attn_dropout: float,
    attn_hooks: str,
    use_se: bool = True,
    se_reduction: int = 8,
) -> List[Tuple[float, int]]:
    """Cross-attention fusion inference.

    ``context_radius`` (and ``use_se``/``se_reduction``) must match how
    ``checkpoint`` was trained — a mismatch changes the expected embedding
    token count or the backbone's parameter shapes, and surfaces as a
    missing/unexpected state_dict key warning below rather than silently
    running with the wrong architecture.
    """
    model = CrossAttnDeepSV(
        embed_dim=embed_dim,
        num_classes=2,
        context_radius=context_radius,
        d_model=attn_d_model,
        n_heads=attn_heads,
        attn_dropout_rate=attn_dropout,
        hooks=tuple(h.strip() for h in attn_hooks.split(",") if h.strip()),
        use_se=use_se,
        se_reduction=se_reduction,
    )
    state = load_torch_state_dict(checkpoint)
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing:
        logger.warning(
            "Checkpoint is missing %d model keys; newly initialized keys stay at "
            "their default values. First few missing keys: %s",
            len(missing),
            missing[:8],
        )
    if unexpected:
        logger.warning(
            "Checkpoint has %d unexpected keys ignored by this model. First few: %s",
            len(unexpected),
            unexpected[:8],
        )

    chroms_in_manifest = sorted({r["chrom"] for r in rows})
    with FusedPredictor(
        model=model,
        embeddings_h5=embeddings_h5,
        threshold=threshold,
        preload_chroms=chroms_in_manifest,
        context_radius=context_radius,
    ) as predictor:
        return predictor.predict_batch(
            image_paths=[Path(r["image_path"]) for r in rows],
            chroms=[r["chrom"] for r in rows],
            positions=[r["position"] for r in rows],
            batch_size=batch_size,
        )


def _prob_to_logit(prob: float, eps: float = 1e-6) -> float:
    p = min(max(float(prob), eps), 1.0 - eps)
    return math.log(p / (1.0 - p))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def apply_sequence_prior(
    rows: List[dict],
    base_preds: List[Tuple[float, int]],
    embeddings_h5: str,
    prior_checkpoint: str,
    prior_weight: float,
    prior_bias: float,
    threshold: float,
    batch_size: int,
    context_radius: Optional[int],
    preload: bool,
) -> Tuple[List[Tuple[float, int]], List[Tuple[float, float]]]:
    """Mix base model probabilities with a sequence-prior checkpoint."""
    chroms = [r["chrom"] for r in rows]
    positions = [int(r["position"]) for r in rows]
    preload_chroms = sorted({r["chrom"] for r in rows}) if preload else None

    with SequencePriorPredictor.from_checkpoint(
        checkpoint=prior_checkpoint,
        embeddings_h5=embeddings_h5,
        context_radius=context_radius,
        preload_chroms=preload_chroms,
    ) as predictor:
        prior_scores = predictor.predict_batch(
            chroms=chroms,
            positions=positions,
            batch_size=batch_size,
        )

    final_preds: List[Tuple[float, int]] = []
    for (base_prob, _), (_, prior_logit) in zip(base_preds, prior_scores):
        final_logit = _prob_to_logit(base_prob) + prior_weight * prior_logit + prior_bias
        final_prob = _sigmoid(final_logit)
        final_preds.append((final_prob, 1 if final_prob > threshold else 0))
    return final_preds, prior_scores


# ─────────────────────────────────────────────────────────────────────────────
# Merge adjacent positive windows into VCF calls
# ─────────────────────────────────────────────────────────────────────────────


def merge_to_calls(rows: List[dict], preds: List[Tuple[float, int]]) -> List[dict]:
    """Merge adjacent positive windows on the same chromosome into calls.

    Windows are considered adjacent if they share a chromosome and start
    positions differ by exactly ``WINDOW_BP``. A call is emitted with the
    span from the first window's start to the last window's end + WINDOW_BP.
    """
    paired = [{**r, "prob": p, "pred": c} for r, (p, c) in zip(rows, preds)]
    paired.sort(key=lambda r: (r["chrom"], r["position"]))

    calls: List[dict] = []
    cur: Optional[dict] = None
    for r in paired:
        if r["pred"] != 1:
            if cur is not None:
                calls.append(cur)
                cur = None
            continue
        if cur is None:
            cur = {
                "chrom": r["chrom"],
                "start": r["position"],
                "end": r["position"] + WINDOW_BP,
                "max_prob": r["prob"],
                "n_windows": 1,
            }
        elif r["chrom"] == cur["chrom"] and r["position"] == cur["end"]:
            cur["end"] = r["position"] + WINDOW_BP
            cur["max_prob"] = max(cur["max_prob"], r["prob"])
            cur["n_windows"] += 1
        else:
            calls.append(cur)
            cur = {
                "chrom": r["chrom"],
                "start": r["position"],
                "end": r["position"] + WINDOW_BP,
                "max_prob": r["prob"],
                "n_windows": 1,
            }
    if cur is not None:
        calls.append(cur)
    return calls


def write_vcf(calls: List[dict], path: str, sample: str = "SAMPLE") -> None:
    """Write a minimal VCF with one DEL line per merged call."""
    with open(path, "w") as f:
        f.write("##fileformat=VCFv4.2\n")
        f.write('##INFO=<ID=SVTYPE,Number=1,Type=String,Description="SV type">\n')
        f.write('##INFO=<ID=END,Number=1,Type=Integer,Description="End position">\n')
        f.write('##INFO=<ID=SVLEN,Number=1,Type=Integer,Description="SV length">\n')
        f.write(
            '##INFO=<ID=NWIN,Number=1,Type=Integer,Description="Number of merged windows">\n'
        )
        f.write(
            '##INFO=<ID=MAXPROB,Number=1,Type=Float,Description="Max P(DEL) among merged windows">\n'
        )
        f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
        for i, c in enumerate(calls, 1):
            length = c["end"] - c["start"]
            info = (
                f"SVTYPE=DEL;END={c['end']};SVLEN=-{length};"
                f"NWIN={c['n_windows']};MAXPROB={c['max_prob']:.4f}"
            )
            qual = f"{c['max_prob'] * 100:.1f}"
            f.write(
                f"{c['chrom']}\t{c['start']}\tDEL_{i}\tN\t<DEL>\t{qual}\tPASS\t{info}\n"
            )


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--manifest", required=True)
    p.add_argument("--checkpoint", required=True, help="Trained model state_dict")
    p.add_argument(
        "--model",
        choices=["cnn", "fused", "cross_attn"],
        default="fused",
        help=(
            "cnn=M0 (image only); fused=M1 (FiLM/context-calibration); "
            "cross_attn=M1 variant, CNN spatial columns attend over a "
            "context-window embedding sequence (requires --context-radius > 0, "
            "matching how the checkpoint was trained)."
        ),
    )
    p.add_argument(
        "--embeddings",
        default=None,
        help="HDF5 file (required for --model fused / cross_attn)",
    )
    p.add_argument(
        "--predictions-out",
        required=True,
        help="Output CSV with per-window predictions",
    )
    p.add_argument("--vcf-out", default=None, help="Optional VCF with merged DEL calls")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--embed-dim", type=int, default=256)
    p.add_argument(
        "--fusion-mode",
        choices=["film", "context", "film_context"],
        default="film_context",
        help=(
            "Embedding fusion used by the fused checkpoint. Match the training "
            "setting when using non-default modes."
        ),
    )
    p.add_argument(
        "--context-hidden-dim",
        type=int,
        default=128,
        help="Hidden width for context calibration heads (default: 128)",
    )
    p.add_argument(
        "--context-dropout",
        type=float,
        default=0.1,
        help="Dropout probability for context heads; inactive during eval.",
    )
    p.add_argument(
        "--context-radius",
        type=int,
        default=10,
        help=(
            "--model cross_attn only: number of neighbouring 50bp windows "
            "attended to on each side of the target window. Must match how "
            "--checkpoint was trained (default: 10, i.e. a 21-token sequence)."
        ),
    )
    p.add_argument(
        "--attn-heads",
        type=int,
        default=4,
        help="--model cross_attn only: number of attention heads (default: 4)",
    )
    p.add_argument(
        "--attn-d-model",
        type=int,
        default=128,
        help="--model cross_attn only: attention hidden width (default: 128)",
    )
    p.add_argument(
        "--attn-dropout",
        type=float,
        default=0.1,
        help="--model cross_attn only: dropout inside the attention block; inactive during eval.",
    )
    p.add_argument(
        "--attn-hooks",
        default="hook3",
        help=(
            "--model cross_attn only: comma-separated hook points, e.g. 'hook3' "
            "(default) or 'hook3,hook4'. Must match how --checkpoint was trained."
        ),
    )
    p.add_argument(
        "--sequence-prior-checkpoint",
        default=None,
        help="Optional SequenceDeletionPrior checkpoint to mix into final scores.",
    )
    p.add_argument(
        "--sequence-prior-weight",
        type=float,
        default=1.0,
        help="Weight for prior logit in final_logit = base_logit + w * prior_logit + b.",
    )
    p.add_argument(
        "--sequence-prior-bias",
        type=float,
        default=0.0,
        help="Bias term added after sequence-prior logit mixing.",
    )
    p.add_argument(
        "--sequence-prior-context-radius",
        type=int,
        default=None,
        help="Override context radius stored in the prior checkpoint.",
    )
    p.add_argument(
        "--sequence-prior-preload",
        action="store_true",
        help="Preload manifest chromosomes from the embedding H5 for prior scoring.",
    )
    p.add_argument("--sample-id", default="SAMPLE")
    p.add_argument(
        "--use-se",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Must match how --checkpoint was trained (see train_fused_model.py "
            "--use-se). Default: on."
        ),
    )
    p.add_argument(
        "--se-reduction",
        type=int,
        default=8,
        help="Must match how --checkpoint was trained (default: 8).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_manifest(args.manifest)
    logger.info("Loaded %d rows from %s", len(rows), args.manifest)

    if args.model in ("fused", "cross_attn") and not args.embeddings:
        raise SystemExit(f"--embeddings is required for --model {args.model}")
    if args.model == "cross_attn" and args.context_radius <= 0:
        raise SystemExit(
            "--model cross_attn requires --context-radius > 0 (there is "
            "nothing to attend over with a single window)."
        )
    if args.sequence_prior_checkpoint and not args.embeddings:
        raise SystemExit("--embeddings is required for --sequence-prior-checkpoint")

    if args.model == "cnn":
        base_preds = predict_m0(
            rows,
            args.checkpoint,
            args.threshold,
            args.batch_size,
            use_se=args.use_se,
            se_reduction=args.se_reduction,
        )
    elif args.model == "fused":
        base_preds = predict_m1(
            rows,
            args.checkpoint,
            args.embeddings,
            args.threshold,
            args.batch_size,
            args.embed_dim,
            args.fusion_mode,
            args.context_hidden_dim,
            args.context_dropout,
            use_se=args.use_se,
            se_reduction=args.se_reduction,
        )
    else:  # cross_attn
        base_preds = predict_cross_attn(
            rows,
            args.checkpoint,
            args.embeddings,
            args.threshold,
            args.batch_size,
            args.embed_dim,
            args.context_radius,
            args.attn_d_model,
            args.attn_heads,
            args.attn_dropout,
            args.attn_hooks,
            use_se=args.use_se,
            se_reduction=args.se_reduction,
        )

    preds = base_preds
    prior_scores: Optional[List[Tuple[float, float]]] = None
    if args.sequence_prior_checkpoint:
        preds, prior_scores = apply_sequence_prior(
            rows=rows,
            base_preds=base_preds,
            embeddings_h5=args.embeddings,
            prior_checkpoint=args.sequence_prior_checkpoint,
            prior_weight=args.sequence_prior_weight,
            prior_bias=args.sequence_prior_bias,
            threshold=args.threshold,
            batch_size=args.batch_size,
            context_radius=args.sequence_prior_context_radius,
            preload=args.sequence_prior_preload,
        )

    # Per-window predictions CSV.
    Path(args.predictions_out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.predictions_out, "w", newline="") as f:
        w = csv.writer(f)
        if prior_scores is None:
            w.writerow(
                [
                    "image_path",
                    "chrom",
                    "position",
                    "label",
                    "length",
                    "prob_deletion",
                    "predicted_class",
                ]
            )
            for r, (prob, cls) in zip(rows, preds):
                w.writerow(
                    [
                        r["image_path"],
                        r["chrom"],
                        r["position"],
                        r["label"],
                        r["length"],
                        f"{prob:.6f}",
                        cls,
                    ]
                )
        else:
            w.writerow(
                [
                    "image_path",
                    "chrom",
                    "position",
                    "label",
                    "length",
                    "base_prob_deletion",
                    "sequence_prior_prob",
                    "sequence_prior_logit",
                    "prob_deletion",
                    "predicted_class",
                ]
            )
            for r, (base_prob, _), (prior_prob, prior_logit), (prob, cls) in zip(
                rows,
                base_preds,
                prior_scores,
                preds,
            ):
                w.writerow(
                    [
                        r["image_path"],
                        r["chrom"],
                        r["position"],
                        r["label"],
                        r["length"],
                        f"{base_prob:.6f}",
                        f"{prior_prob:.6f}",
                        f"{prior_logit:.6f}",
                        f"{prob:.6f}",
                        cls,
                    ]
                )
    logger.info("Wrote per-window predictions to %s", args.predictions_out)

    # Optional VCF output.
    if args.vcf_out:
        calls = merge_to_calls(rows, preds)
        Path(args.vcf_out).parent.mkdir(parents=True, exist_ok=True)
        write_vcf(calls, args.vcf_out, sample=args.sample_id)
        logger.info("Wrote %d merged DEL calls to %s", len(calls), args.vcf_out)


if __name__ == "__main__":
    main()
