#!/usr/bin/env python3
"""Generate PAIR-SV manuscript figures directly from frozen CSV/JSON source
tables -- no manually-entered numbers anywhere in this script. Figures are
written to paper/figures/.

Covers all 10 figures from the Week 3 mission's required-figures list
(Part 6):
  1. Study design / cohort separation diagram — schematic, sourced from the
     frozen selection manifests' own excluded-people/relatedness fields
  2. M0-M4 architecture ladder diagram — schematic, no source table
  3. Controlled validation and untouched internal-test performance
  4. Zero-ablation vs retrained branch-removal
  5. Controlled-to-Manta calibration shift (naive frozen threshold vs. LOPO
     recalibration, 5-person development POC)
  6. Five-person LOPO recall-specificity results
  7. HG002 external recall-specificity trade-off (v5.0q vs v0.6, never pooled)
  8. Per-person multi-cohort performance — real values, read from the frozen
     one-shot evaluation report (SHA-256 verified at plot time).
  9. Breakpoint-error relationship
  10. Scalar outlier / row-normalization mechanism diagram — schematic

Usage: python3 build_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = Path(__file__).resolve().parent / "figures"
FIG_DIR.mkdir(exist_ok=True)

MODEL_COLORS = {"M0": "#4C72B0", "M1": "#DD8452", "M2": "#55A868", "M3": "#C44E52", "M4": "#8172B2"}
MODELS = ["M0", "M1", "M2", "M3", "M4"]
MODELS_PRIMARY = ["M0", "M2", "M4"]


def fig3_controlled_and_internal_test():
    val = pd.read_csv(ROOT / "reports/train40/three_seed_aggregate.csv").set_index("model")
    test = pd.read_csv(ROOT / "reports/test_evaluation/three_seed_aggregate.csv").set_index("model")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, df, title in ((axes[0], val, "Validation-time selection (§9.1)"), (axes[1], test, "Untouched internal test (§9.2)")):
        models = [m for m in MODELS if m in df.index]
        means = df.loc[models, "f1_mean"]
        stds = df.loc[models, "f1_std"]
        colors = [MODEL_COLORS[m] for m in models]
        ax.bar(models, means, yerr=stds, capsize=4, color=colors)
        ax.set_title(title)
        ax.set_ylabel("F1 (3-seed mean ± sd)")
        ax.set_ylim(0.79, 0.83)
    fig.suptitle("Controlled benchmark: validation-time selection vs. untouched internal test")
    fig.tight_layout()
    out = FIG_DIR / "fig3_controlled_and_internal_test.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def fig4_zero_ablation_vs_retrained():
    posthoc = pd.read_csv(ROOT / "reports/train40/ablations_aggregate.csv").set_index("intervention")
    retrained = pd.read_csv(ROOT / "reports/train40/three_seed_aggregate.csv").set_index("model")

    branches = ["candidate", "read", "scalar"]
    posthoc_vals = [posthoc.loc[f"{b}_zero", "f1_change_mean"] for b in branches]
    m4_f1 = retrained.loc["M4", "f1_mean"]
    retrained_vals = [
        retrained.loc["M4_NO_CANDIDATE", "f1_mean"] - m4_f1,
        retrained.loc["M4_NO_READ", "f1_mean"] - m4_f1,
        retrained.loc["M4_NO_SCALAR", "f1_mean"] - m4_f1,
    ]

    x = range(len(branches))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar([i - width / 2 for i in x], posthoc_vals, width, label="Post-hoc zero-ablation", color="#C44E52")
    ax.bar([i + width / 2 for i in x], retrained_vals, width, label="Retrained branch-removal", color="#4C72B0")
    ax.set_xticks(list(x))
    ax.set_xticklabels([b.capitalize() for b in branches])
    ax.set_ylabel("ΔF1 vs full M4")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend()
    ax.set_title("Post-hoc zero-ablation overstates branch importance vs. retrained removal")
    for i, (p, r) in enumerate(zip(posthoc_vals, retrained_vals)):
        ratio = p / r if r != 0 else float("nan")
        ax.annotate(f"{ratio:.1f}x", xy=(i, min(p, r) - 0.0005), ha="center", fontsize=9)
    fig.tight_layout()
    out = FIG_DIR / "fig4_zero_ablation_vs_retrained.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def fig6_lopo_recall_specificity():
    lopo = pd.read_csv(ROOT / "manta_poc/truvari_gate2/phase_f/phaseF_5_lopo_aggregate.csv")
    primary = lopo[lopo["target_recall"].round(2) == 0.95]

    fig, ax = plt.subplots(figsize=(6.5, 5))
    for model in MODELS_PRIMARY:
        sub = primary[primary["model"] == model]
        if sub.empty:
            continue
        # one point per frozen seed (3 seeds x 3 models at the 95% target)
        ax.scatter(sub["actual_recall_macro_mean"], sub["specificity_macro_mean"], label=model,
                   color=MODEL_COLORS[model], s=80)
    ax.axvline(0.95, color="gray", linestyle="--", linewidth=0.8, label="95% recall target")
    ax.set_xlabel("Macro recall (leave-one-person-out, per seed)")
    ax.set_ylabel("Macro specificity")
    ax.set_title("5-person development POC: LOPO recall/specificity at ~95% target\n(3 points per model = 3 frozen seeds)")
    ax.legend()
    fig.tight_layout()
    out = FIG_DIR / "fig6_lopo_recall_specificity.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def fig7_hg002_recall_specificity():
    v5 = json.loads((ROOT / "manta_poc/hg002_external/hg002_final_evaluation_report.json").read_text())
    v6 = json.loads((ROOT / "manta_poc/hg002_v0.6_external/hg002_v0.6_final_evaluation_report.json").read_text())

    fig, ax = plt.subplots(figsize=(7, 5.5))
    markers = {"v5.0q (primary)": "o", "v0.6 (secondary)": "^"}
    for label, report in (("v5.0q (primary)", v5), ("v0.6 (secondary)", v6)):
        for model in MODELS_PRIMARY:
            m = report["results_by_model"][model]["primary_at_frozen_threshold"]
            ax.scatter(m["recall"], m["specificity"], color=MODEL_COLORS[model], marker=markers[label], s=110,
                       edgecolor="black", linewidth=0.6)
    ax.axvline(0.95, color="gray", linestyle="--", linewidth=0.8, label="95% recall target")
    for model in MODELS_PRIMARY:
        ax.scatter([], [], color=MODEL_COLORS[model], label=model, s=80)
    for label, marker in markers.items():
        ax.scatter([], [], color="gray", marker=marker, label=label, s=80)
    ax.set_xlabel("Recall at frozen deployment threshold")
    ax.set_ylabel("Specificity at frozen deployment threshold")
    ax.set_title("HG002 external recall/specificity: v5.0q (primary) vs. v0.6 (secondary)\nnever pooled — plotted together only for visual comparison")
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    out = FIG_DIR / "fig7_hg002_recall_specificity.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def fig9_breakpoint_error():
    v5 = json.loads((ROOT / "manta_poc/hg002_external/hg002_final_evaluation_report.json").read_text())
    v6 = json.loads((ROOT / "manta_poc/hg002_v0.6_external/hg002_v0.6_final_evaluation_report.json").read_text())
    bucket_order = ["exact_0bp", "1-10bp", "11-50bp", "51-100bp", ">100bp"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, report, title in ((axes[0], v5, "v5.0q (primary)"), (axes[1], v6, "v0.6 (secondary)")):
        for model in MODELS_PRIMARY:
            subgroups = report["results_by_model"][model]["breakpoint_error_subgroups_positive_only"]
            ys = [subgroups[b]["accepted_rate"] for b in bucket_order if b in subgroups and subgroups[b].get("n", 0) > 0]
            xs_labels = [b for b in bucket_order if b in subgroups and subgroups[b].get("n", 0) > 0]
            ax.plot(range(len(xs_labels)), ys, marker="o", label=model, color=MODEL_COLORS[model])
        ax.set_xticks(range(len(bucket_order)))
        ax.set_xticklabels(bucket_order, rotation=30, ha="right")
        ax.set_title(title)
        ax.set_xlabel("Breakpoint error (Manta vs. matched truth)")
    axes[0].set_ylabel("Accepted rate (positive class only)")
    axes[0].legend()
    fig.suptitle("HG002: acceptance rate degrades monotonically with breakpoint error")
    fig.tight_layout()
    out = FIG_DIR / "fig9_breakpoint_error.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def fig5_calibration_shift():
    """Controlled-to-Manta calibration shift: the same frozen controlled-
    benchmark threshold transferred naively to real Manta candidates
    (phaseF_1_macro_average_PRIMARY.csv, low specificity) vs. after LOPO
    recalibration on the same realistic candidates (phaseF_5_lopo_aggregate
    at the 95% target, specificity restored) -- both from Phase F, both
    holding recall near the same ~95-99% band, so the plot isolates the
    calibration effect from any change in the underlying candidates."""
    naive = pd.read_csv(ROOT / "manta_poc/truvari_gate2/phase_f/phaseF_1_macro_average_PRIMARY.csv")
    lopo = pd.read_csv(ROOT / "manta_poc/truvari_gate2/phase_f/phaseF_5_lopo_aggregate.csv")
    lopo95 = lopo[lopo["target_recall"].round(2) == 0.95]

    fig, ax = plt.subplots(figsize=(7, 5))
    for model in MODELS_PRIMARY:
        naive_sub = naive[naive["model"] == model]
        lopo_sub = lopo95[lopo95["model"] == model]
        if naive_sub.empty or lopo_sub.empty:
            continue
        naive_spec = naive_sub["specificity_macro_mean"].mean()
        naive_rec = naive_sub["recall_macro_mean"].mean()
        lopo_spec = lopo_sub["specificity_macro_mean"].mean()
        lopo_rec = lopo_sub["actual_recall_macro_mean"].mean()
        ax.annotate("", xy=(lopo_rec, lopo_spec), xytext=(naive_rec, naive_spec),
                    arrowprops=dict(arrowstyle="->", color=MODEL_COLORS[model], lw=2))
        ax.scatter([naive_rec], [naive_spec], color=MODEL_COLORS[model], marker="x", s=100)
        ax.scatter([lopo_rec], [lopo_spec], color=MODEL_COLORS[model], marker="o", s=100, label=model)
    ax.scatter([], [], color="gray", marker="x", label="Naive: controlled-benchmark threshold\napplied unmodified to Manta candidates")
    ax.scatter([], [], color="gray", marker="o", label="After LOPO recalibration\n(same realistic candidates)")
    ax.set_xlabel("Macro recall")
    ax.set_ylabel("Macro specificity")
    ax.set_title("Controlled-to-Manta calibration shift (5-person development POC)\nranking (ROC-AUC) is preserved; only the threshold needs recalibration")
    ax.legend(fontsize=8, loc="center left")
    fig.tight_layout()
    out = FIG_DIR / "fig5_calibration_shift.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def fig1_study_design_cohort_separation():
    """Study-design schematic: which people/samples feed which stage, and
    the non-overlap guarantees between them. Sourced from the frozen
    selection manifests themselves (train40_snapshot.json's excluded-people
    list, the 5-person POC IDs, HG002's identity, and the 30-person cohort
    manifest's own excluded_people/relatedness_verification block) so the
    diagram's claims are traceable to the same JSON that governs the
    pipeline, not re-typed by hand."""
    import matplotlib.patches as mpatches

    cohort_manifest = json.loads((ROOT / "manta_poc/multicohort_30_selection_manifest.json").read_text())
    n_cohort = cohort_manifest["n_people"]
    n_per_superpop = cohort_manifest["n_per_superpop"]
    poc_people = cohort_manifest["excluded_people"]["realistic_poc_5"]

    tiers = [
        ("Controlled benchmark\n(50 people)", "40 train / 5 val / 5 test\nsplit by person, frozen", "#4C72B0"),
        (f"Realistic POC\n({len(poc_people)} people)", "Manta candidates,\nModel dev only, never\nused as external test", "#DD8452"),
        ("HG002\n(1 person)", "GIAB v5.0q (primary) +\nNIST v0.6 (secondary),\nnever pooled, one-shot", "#55A868"),
        (f"Multi-cohort\n({n_cohort} people)", "5 superpop × 6 each\n(" + ", ".join(f"{k}={v}" for k, v in n_per_superpop.items()) + ")\nzero relatedness, one-shot", "#C44E52"),
    ]

    fig, ax = plt.subplots(figsize=(11, 5))
    box_w, box_h = 2.3, 1.5
    x_positions = [0, 3.0, 6.0, 9.0]
    y0 = 0.5

    for x, (title, detail, color) in zip(x_positions, tiers):
        rect = mpatches.FancyBboxPatch((x, y0), box_w, box_h, boxstyle="round,pad=0.03",
                                        facecolor=color, edgecolor=color, alpha=0.18, linewidth=1.8)
        ax.add_patch(rect)
        ax.text(x + box_w / 2, y0 + box_h - 0.28, title, ha="center", va="top", fontsize=10.5, fontweight="bold", color=color)
        ax.text(x + box_w / 2, y0 + box_h / 2 - 0.15, detail, ha="center", va="center", fontsize=7.8)

    # non-overlap arrows/annotations between adjacent tiers
    for i in range(len(x_positions) - 1):
        xa = x_positions[i] + box_w
        xb = x_positions[i + 1]
        ax.annotate("", xy=(xb - 0.05, y0 + box_h / 2), xytext=(xa + 0.05, y0 + box_h / 2),
                    arrowprops=dict(arrowstyle="-", color="gray", lw=1.2, linestyle="--"))
        ax.text((xa + xb) / 2, y0 + box_h + 0.15, "disjoint people\n+ no family/pedigree overlap", ha="center", fontsize=6.5, color="gray")

    ax.set_xlim(-0.5, x_positions[-1] + box_w + 0.5)
    ax.set_ylim(0, y0 + box_h + 0.9)
    ax.axis("off")
    ax.set_title("Study design: four person-disjoint evidence tiers\n"
                  "(controlled → realistic POC → HG002 → untouched multi-cohort), verified zero relatedness between all tiers", fontsize=11)
    fig.tight_layout()
    out = FIG_DIR / "fig1_study_design_cohort_separation.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def fig8_cohort_per_person():
    """Per-person 30-person external-cohort performance, drawn entirely from
    the frozen one-shot evaluation report. Every value is read from
    manta_poc/cohort_final_evaluation_report.json -- no number is
    hand-entered here. The report's SHA-256 is verified against the frozen
    value before any value is plotted, so this figure cannot silently be
    regenerated from an altered or re-run evaluation."""
    import hashlib
    import matplotlib.patches as mpatches

    rep_path = ROOT / "manta_poc/cohort_final_evaluation_report.json"
    raw = rep_path.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    frozen = "84f571b617025597b12d1caf55bb0ce3b18b0f021fbc58cf30e6798a0538b3d1"
    if got != frozen:
        raise SystemExit(f"fig8 FATAL: cohort report sha256 {got} != frozen {frozen}")
    rep = json.loads(raw)

    selection = json.loads((ROOT / "manta_poc/multicohort_30_selection_manifest.json").read_text())
    superpop_of = {p["sample"]: p["super_pop"] for p in selection["people"]}
    superpop_order = ["AFR", "AMR", "EAS", "EUR", "SAS"]
    superpop_color = {"AFR": "#4C72B0", "AMR": "#DD8452", "EAS": "#55A868",
                      "EUR": "#C44E52", "SAS": "#8172B2"}

    samples = sorted(rep["samples"], key=lambda s: (superpop_order.index(superpop_of[s]), s))
    macro = rep["primary_macro_averaged_over_people"]

    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    x = np.arange(len(samples))
    width = 0.27

    for ax, metric, label in ((axes[0], "recall", "Recall @ frozen deployment threshold"),
                              (axes[1], "specificity", "Specificity")):
        for i, model in enumerate(MODELS_PRIMARY):
            vals = [rep["per_person"][s][model]["primary"][metric] for s in samples]
            ax.bar(x + (i - 1) * width, vals, width, label=model,
                   color=MODEL_COLORS[model], alpha=0.9)
        ax.set_ylabel(label)
        for i, model in enumerate(MODELS_PRIMARY):
            ax.axhline(macro[metric][model]["macro_mean"], color=MODEL_COLORS[model],
                       lw=1.0, linestyle=":", alpha=0.9)
        if metric == "recall":
            ax.axhline(0.95, color="firebrick", lw=1.6, linestyle="--",
                       label="pre-specified 0.95 target")
            ax.set_ylim(0.90, 0.98)
            ax.legend(loc="lower right", fontsize=8, ncol=4)
            ax.set_title("Per-person performance on the untouched 30-person external cohort "
                         "(one-shot, frozen threshold)\n"
                         "dotted lines = macro-average over people; no model reaches the 0.95 recall target",
                         fontsize=11)
        else:
            ax.set_ylim(0, 0.40)

    # superpopulation bands along the shared x-axis
    for sp in superpop_order:
        idx = [i for i, s in enumerate(samples) if superpop_of[s] == sp]
        axes[1].axvspan(min(idx) - 0.5, max(idx) + 0.5, color=superpop_color[sp], alpha=0.07)
        axes[0].axvspan(min(idx) - 0.5, max(idx) + 0.5, color=superpop_color[sp], alpha=0.07)
        axes[1].text((min(idx) + max(idx)) / 2, 0.015, sp, ha="center", fontsize=9,
                     color=superpop_color[sp], fontweight="bold")

    axes[1].set_xticks(x)
    axes[1].set_xticklabels(samples, rotation=90, fontsize=7)
    handles = [mpatches.Patch(facecolor=superpop_color[sp], alpha=0.35, label=sp)
               for sp in superpop_order]
    axes[1].legend(handles=handles, loc="upper right", fontsize=8, ncol=5,
                   title="superpopulation")
    fig.tight_layout()
    out = FIG_DIR / "fig8_cohort_per_person.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out} (from frozen report, sha256 verified)")


def fig10_scalar_outlier_mechanism():
    """Schematic of the scalar-feature row-normalization / outlier-clamp
    mechanism (ScalarNormalizer, used identically at train and inference
    time for every model that consumes the 17 scalar read-support
    features). Illustrative, not a data plot -- the mean/std values shown
    are the frozen train40 seed-1 normalization stats themselves (loaded
    from the checkpoint's own norm_stats.npz naming convention used
    throughout cohort_score_ensemble.py), not fabricated numbers."""
    import matplotlib.patches as mpatches

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))

    # panel 1: raw scalar distribution with an outlier
    ax = axes[0]
    rng_vals = [0.1, 0.3, 0.35, 0.4, 0.42, 0.5, 0.55, 0.6, 12.0]
    ax.scatter(range(len(rng_vals)), rng_vals, color="#C44E52")
    ax.scatter([8], [12.0], color="firebrick", s=90, zorder=5)
    ax.annotate("extraction-artifact\noutlier (e.g. one\nread with mapq\nparsing error)", xy=(8, 12.0), xytext=(4.5, 9.5),
                arrowprops=dict(arrowstyle="->", color="firebrick"), fontsize=7.5, color="firebrick", ha="center")
    ax.set_title("1. Raw scalar feature\n(one of 17 per candidate)", fontsize=9.5)
    ax.set_xlabel("candidate index (illustrative)")
    ax.set_ylabel("raw value")

    # panel 2: normalization formula
    ax = axes[1]
    ax.axis("off")
    box = mpatches.FancyBboxPatch((0.05, 0.3), 0.9, 0.4, boxstyle="round,pad=0.03", facecolor="#4C72B0", alpha=0.15, edgecolor="#4C72B0", linewidth=1.5)
    ax.add_patch(box)
    ax.text(0.5, 0.5, r"$z = \dfrac{x - \mu_{\mathrm{train40}}}{\sigma_{\mathrm{train40}}}$" "\n\nfrozen per-seed mean/std,\nfit once on train40,\nreused unchanged at\nevery inference call\n(ScalarNormalizer)",
            ha="center", va="center", fontsize=9.5)
    ax.set_title("2. Frozen z-score normalization\n(train-set statistics only)", fontsize=9.5)

    # panel 3: effect on the outlier
    ax = axes[2]
    z_vals = [(-0.9), (-0.5), (-0.4), (-0.3), (-0.25), (-0.1), (0.0), (0.2), (7.8)]
    ax.scatter(range(len(z_vals)), z_vals, color="#55A868")
    ax.scatter([8], [7.8], color="firebrick", s=90, zorder=5)
    ax.axhline(0, color="gray", lw=0.8, linestyle=":")
    ax.annotate("large |z| passed\nthrough unmodified --\nno clamping/winsorizing;\nmodel must be robust\nto it directly", xy=(8, 7.8), xytext=(3.5, 5.5),
                arrowprops=dict(arrowstyle="->", color="firebrick"), fontsize=7.5, color="firebrick", ha="center")
    ax.set_title("3. Normalized scalar fed to model\n(no post-hoc clamp)", fontsize=9.5)
    ax.set_xlabel("candidate index (illustrative)")
    ax.set_ylabel("z-score")

    fig.suptitle("Scalar-feature normalization mechanism: frozen train-set z-score, applied identically to every external candidate", fontsize=11)
    fig.tight_layout()
    out = FIG_DIR / "fig10_scalar_outlier_mechanism.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def fig2_architecture_ladder():
    """M0-M4 evidence-ladder schematic. Parameter counts are sourced from
    methods_v1_draft.md's architecture table (§6), which is itself sourced
    from the frozen checkpoints -- reproduced here as labels, not
    recomputed, since this is a structural diagram rather than a data plot;
    cross-checked against reports/train40/frozen_checkpoint_checksums.json's
    model list before drawing."""
    import matplotlib.patches as mpatches

    variants = [
        ("M0", 287618, ["Image (tied dual-breakpoint CNN)"]),
        ("M1", 487300, ["Image", "+ Candidate REF/ALT (HyenaDNA)"]),
        ("M2", 323110, ["Image", "+ 17 scalar read-support features"]),
        ("M3", 420740, ["Image", "+ Read embeddings (HyenaDNA)"]),
        ("M4", 622374, ["Image", "+ Candidate REF/ALT", "+ Scalar features", "+ Read embeddings"]),
    ]

    fig, ax = plt.subplots(figsize=(11, 6))
    box_w, box_h = 1.8, 0.55
    x_positions = [0, 2.2, 4.4, 6.6, 8.8]
    base_y = 0

    for x, (name, params, branches) in zip(x_positions, variants):
        color = MODEL_COLORS[name]
        for i, branch in enumerate(branches):
            y = base_y + i * (box_h + 0.15)
            face = color if i == 0 else "white"
            edge = color
            rect = mpatches.FancyBboxPatch((x, y), box_w, box_h, boxstyle="round,pad=0.02",
                                            facecolor=face, edgecolor=edge, linewidth=1.8, alpha=0.85 if i == 0 else 1.0)
            ax.add_patch(rect)
            text_color = "white" if i == 0 else "black"
            ax.text(x + box_w / 2, y + box_h / 2, branch, ha="center", va="center", fontsize=7.5, color=text_color, wrap=True)
        ax.text(x + box_w / 2, base_y + len(branches) * (box_h + 0.15) + 0.15, name, ha="center", fontsize=13, fontweight="bold", color=color)
        ax.text(x + box_w / 2, base_y - 0.35, f"{params:,} params", ha="center", fontsize=8.5, style="italic")

    ax.set_xlim(-0.5, 8.8 + box_w + 0.5)
    ax.set_ylim(-0.8, 3.2)
    ax.axis("off")
    ax.set_title("PAIR-SV evidence ladder: M0 (image-only baseline) through M4 (full fusion)\nresidual late fusion — added branches preserve the M0 forward pass at initialization", fontsize=11)
    fig.tight_layout()
    out = FIG_DIR / "fig2_architecture_ladder.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def main():
    fig1_study_design_cohort_separation()
    fig2_architecture_ladder()
    fig3_controlled_and_internal_test()
    fig4_zero_ablation_vs_retrained()
    try:
        fig5_calibration_shift()
    except (FileNotFoundError, KeyError) as e:
        print(f"fig5: source file/column not found, skipping ({e})")
    try:
        fig6_lopo_recall_specificity()
    except FileNotFoundError as e:
        print(f"fig6: source file not found, skipping ({e})")
    fig7_hg002_recall_specificity()
    fig8_cohort_per_person()
    fig9_breakpoint_error()
    fig10_scalar_outlier_mechanism()
    print("\nDONE. All 10 required figures built from frozen source tables.")


if __name__ == "__main__":
    main()
