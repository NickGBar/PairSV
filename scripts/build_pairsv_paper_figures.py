#!/usr/bin/env python3
"""Create artifact-derived figures for the controlled PAIR-SV Train15 paper.

The script deliberately reads only the frozen validation extraction snapshot and
controlled Train15 result CSVs.  It never opens the internal-test cohort.
"""

from __future__ import annotations

from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures" / "legacy"   # Train15-era figures; current figures are built by paper/build_figures.py
H5 = ROOT / "kaggle/deepsv-ms-extract-shard0/output-v1/pairsv_shard_00.h5"
MANIFEST = ROOT / "kaggle/deepsv-ms-manifest50-hq/output-v4/sample_candidate_manifest.tsv"
METRICS = ROOT / "reports/pairsv_train15_main_metrics.csv"
BOOTSTRAP = ROOT / "reports/pairsv_train15_bootstrap.csv"
ABLATIONS = ROOT / "reports/pairsv_train15_ablations.csv"


PALETTE = {"M0": "#3b6ea5", "M2": "#e08a32", "M4": "#1c9b78"}


def save(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(OUT / f"{stem}.{suffix}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def box(ax, x, y, w, h, text, color, *, frozen=False, fontsize=8.5):
    style = "round,pad=0.02,rounding_size=0.025"
    patch = FancyBboxPatch((x, y), w, h, boxstyle=style, linewidth=1.25,
                           edgecolor="#25455c", facecolor=color)
    ax.add_patch(patch)
    # Color and the explicit ``frozen`` / ``trainable`` label carry state;
    # regular weight keeps compact scientific labels inside their boxes.
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            fontweight="normal", wrap=True)
    return patch


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=12, lw=1.1, color="#405260"))


def figure1_same_site() -> None:
    fig, ax = plt.subplots(figsize=(9.0, 3.7))
    ax.set_axis_off(); ax.set_xlim(0, 10); ax.set_ylim(0, 4)
    ax.text(0.25, 3.72, "One candidate locus, two independently sampled individuals", fontsize=13, weight="bold")
    ax.plot([0.55, 4.25], [3.20, 3.20], color="#405260", lw=5, solid_capstyle="round")
    ax.plot([4.85, 9.45], [3.20, 3.20], color="#405260", lw=5, solid_capstyle="round")
    ax.plot([4.25, 4.85], [3.20, 3.20], color="#cf4040", lw=3, linestyle="--")
    ax.text(0.65, 3.41, "REF flank", fontsize=10); ax.text(4.17, 3.41, "deletion D", fontsize=10, color="#a22828")
    ax.text(7.9, 3.41, "REF flank", fontsize=10)
    ax.text(4.52, 2.82, "ALT junction", fontsize=10, ha="center", color="#197c62")
    arrow(ax, 4.25, 2.98, 4.85, 2.98)
    box(ax, .45, 1.25, 3.65, 1.05, "Individual A\nGT 0/1 or 1/1\nclip/split/discordant evidence", "#dff3e9", fontsize=10)
    box(ax, 5.85, 1.25, 3.65, 1.05, "Individual B\nGT 0/0\nreference-spanning evidence", "#fae1df", fontsize=10)
    ax.text(4.98, 1.78, "same candidate ID\nand coordinates", fontsize=9.5, ha="center", va="center")
    arrow(ax, 4.1, 1.78, 5.8, 1.78)
    box(ax, 2.45, .18, 5.1, .58, "PAIR-SV predicts deletion carriage from sample-specific evidence", "#dde9f4", fontsize=9.5)
    save(fig, "figure1_same_site_design")


def figure2_architecture() -> None:
    # Four spacious lanes route to separate fusion ports; labels deliberately
    # stay inside their boxes at the final two-column PDF scale.
    fig, ax = plt.subplots(figsize=(7.25, 5.25))
    ax.set_axis_off(); ax.set_xlim(0, 13.05); ax.set_ylim(0, 10.35)
    ax.text(.30, 9.82, "PAIR-SV multimodal architecture", fontsize=12.7, weight="bold")
    train = "#dbe9f5"; frozen = "#dff3e9"; scalar = "#fce9ca"; fusion = "#eadcf5"
    ys = {"image": 7.34, "candidate": 5.19, "reads": 3.04, "scalar": .89}
    lane_labels = {"image": "Image lane", "candidate": "Candidate REF/ALT lane", "reads": "Sample-read lane", "scalar": "Scalar lane"}
    for name, y in ys.items():
        ax.text(.45, y + 1.16, lane_labels[name], fontsize=8.45, weight="bold", color="#405260")

    def lane(y, first, middle, last, color, *, is_frozen=False, mid_font=8.35, last_font=8.35):
        box(ax, .45, y, 2.25, .98, first, color, frozen=is_frozen, fontsize=8.35)
        box(ax, 3.22, y, 1.82, .98, middle, color, frozen=is_frozen, fontsize=mid_font)
        box(ax, 5.56, y, 1.78, .98, last, color, frozen=is_frozen, fontsize=last_font)
        arrow(ax, 2.70, y + .49, 3.22, y + .49)
        arrow(ax, 5.04, y + .49, 5.56, y + .49)

    lane(ys["image"], "Left + right\npileups\n2 × (6, 64, 128)", "Tied CNN\ntrainable", "Paired image\nfeature", train)
    lane(ys["candidate"], "REF / ALT\ncontext\n2 × 1,024 bp", "HyenaDNA\nfrozen", "REF, ALT, Δ,\n|Δ|, J\n5 × 256", frozen, is_frozen=True, last_font=8.15)
    lane(ys["reads"], "Selected\nreads\n2 × 48 × 128", "Read encoder\nmask pooling\nfrozen", "Pooled read\nvector: 768", frozen, is_frozen=True, mid_font=8.05)
    lane(ys["scalar"], "17 scalar\nread-support\nfeatures", "Train-only\nnormalization", "Scalar\nvector", scalar)

    # One aligned fusion column has four dedicated, non-crossing input ports.
    box(ax, 8.12, 2.26, 2.63, 4.92,
        "Residual late fusion\n\ntrainable\n\nImage path preserved\nat initialization", fusion, fontsize=8.55)
    for y in ys.values():
        arrow(ax, 7.34, y + .49, 8.12, y + .49)
    box(ax, 11.42, 4.13, 1.22, 1.16, "Deletion\nprobability", "#d8edf2", fontsize=8.15)
    arrow(ax, 10.75, 4.71, 11.42, 4.71)
    ax.text(.45, .43, "Blue: trainable. Green: frozen encoders. Orange: scalar support. Identity and label-provenance metadata are excluded.", fontsize=8.1)
    save(fig, "figure2_pairsv_architecture")


def figure3_pileups() -> None:
    manifest = pd.read_csv(MANIFEST, sep="\t")
    manifest = manifest[manifest["split"].eq("val")].copy()
    with h5py.File(H5, "r") as h5:
        ex = h5["examples"]
        row_ids = [x.decode() if isinstance(x, bytes) else str(x) for x in ex["row_id"][:]]
        index = {row_id: i for i, row_id in enumerate(row_ids)}
        manifest = manifest[manifest.row_id.isin(index)].copy()
        categories = [
            ("Short positive\n50-200 bp", (manifest.label.eq(1) & manifest.length.between(50, 200))),
            ("Long positive\n1,000-10,000 bp", (manifest.label.eq(1) & manifest.length.between(1000, 10000))),
            ("Heterozygous positive\nGT 0/1 or 1/0", (manifest.label.eq(1) & manifest.genotype.isin(["0/1", "1/0"]))),
            ("Homozygous-alt positive\nGT 1/1", (manifest.label.eq(1) & manifest.genotype.eq("1/1"))),
            ("Same-site negative\nGT 0/0", (manifest.label.eq(0) & manifest.negative_type.eq("same_site_negative"))),
        ]
        chosen = []
        used = set()
        for name, mask in categories:
            choices = manifest.loc[mask & ~manifest.row_id.isin(used)].sort_values("row_id")
            if choices.empty:
                raise RuntimeError(f"No successful validation row for {name}")
            row = choices.iloc[len(choices) // 2]
            chosen.append((name, row))
            used.add(row.row_id)
        fig, axes = plt.subplots(5, 2, figsize=(7.0, 8.5), constrained_layout=True)
        for r, (name, row) in enumerate(chosen):
            ii = index[row.row_id]
            images = ex["images"][ii]
            for bp in range(2):
                # Alignment-state plus alternate-evidence is a readable real QC composite.
                arr = images[bp, 4].astype(float) + .55 * images[bp, 5].astype(float)
                axes[r, bp].imshow(arr, aspect="auto", interpolation="nearest", cmap="magma", vmin=0, vmax=340)
                axes[r, bp].axvline(64, color="#6ce6ff", linewidth=.7)
                axes[r, bp].set_xticks([0, 64, 127]); axes[r, bp].set_xticklabels(["-64", "breakpoint", "+63"], fontsize=8.5)
                axes[r, bp].set_yticks([0, 32, 63]); axes[r, bp].set_yticklabels(["1", "32", "64"], fontsize=8.5)
                if r == 0: axes[r, bp].set_title("left breakpoint" if bp == 0 else "right breakpoint", fontsize=10.5, weight="bold")
                if bp == 0: axes[r, bp].set_ylabel(name, fontsize=10)
        fig.suptitle("Representative validation pileups (real successful extraction rows; identifiers suppressed)", fontsize=12, weight="bold")
        save(fig, "figure3_representative_pileups")


def figure4_metrics_bootstrap() -> None:
    m = pd.read_csv(METRICS).set_index("model").loc[["M0", "M2", "M4"]]
    b = pd.read_csv(BOOTSTRAP)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 3.8), gridspec_kw={"width_ratios": [1.15, 1]})
    names = ["F1", "ROC-AUC", "PR-AUC", "MCC"]
    cols = ["f1", "roc_auc", "pr_auc", "mcc"]
    x = np.arange(len(names)); width = .23
    for j, model in enumerate(m.index):
        ax1.bar(x + (j - 1) * width, m.loc[model, cols].to_numpy(float), width, label=model, color=PALETTE[model])
    ax1.set_ylim(.5, .95); ax1.set_xticks(x, names); ax1.set_ylabel("Validation metric", fontsize=9)
    ax1.legend(frameon=False, ncols=3, loc="upper left", fontsize=8); ax1.grid(axis="y", alpha=.25)
    ax1.set_title("A  Controlled validation metrics", loc="left", weight="bold", fontsize=10)
    labels = [str(x).replace(" − ", " - ") for x in b.comparison]
    ypos = np.arange(len(b))[::-1]
    for y, (_, row) in zip(ypos, b.iterrows()):
        low = row.f1_difference - row.f1_ci_low; high = row.f1_ci_high - row.f1_difference
        ax2.errorbar(row.f1_difference, y, xerr=np.array([[low], [high]]), fmt="o", color="#314b5f", capsize=3)
    ax2.axvline(0, color="#a33", lw=1, linestyle="--"); ax2.set_yticks(ypos, labels); ax2.set_xlabel("Observed F1 difference (95% paired row-bootstrap CI)", fontsize=8)
    ax2.set_title("B  1,000 paired bootstrap resamples", loc="left", weight="bold", fontsize=10); ax2.grid(axis="x", alpha=.25)
    for axis in (ax1, ax2): axis.tick_params(labelsize=8.5)
    fig.tight_layout(); save(fig, "figure4_metrics_bootstrap")


def figure5_ablations() -> None:
    a = pd.read_csv(ABLATIONS).set_index("intervention").loc[["candidate_zero", "read_zero", "scalar_zero"]]
    labels = ["Candidate\nzeroed", "Read\nzeroed", "Scalar\nzeroed"]
    fig, ax = plt.subplots(figsize=(7.0, 4.25))
    bars = ax.bar(np.arange(3), a.f1_change.to_numpy(float), color=["#8075b5", "#4f9f9f", "#d17b42"], width=.63)
    ax.axhline(0, color="#444", lw=.9); ax.set_ylim(-.019, .0018); ax.set_xticks(range(3), labels); ax.set_ylabel("Change in validation F1 versus full M4")
    ax.set_title("M4 zero-branch ablations", loc="left", weight="bold"); ax.grid(axis="y", alpha=.25)
    for bar, val in zip(bars, a.f1_change): ax.text(bar.get_x() + bar.get_width()/2, val - .00065, f"{val:+.4f}", ha="center", va="top", fontsize=9)
    fig.tight_layout(); save(fig, "figure5_zero_ablations")


def main() -> None:
    figure1_same_site(); figure2_architecture(); figure3_pileups(); figure4_metrics_bootstrap(); figure5_ablations()
    print("Wrote figures to", OUT)


if __name__ == "__main__":
    main()
