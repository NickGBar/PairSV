"""Full controlled M0-M4 analysis on the frozen Train40 validation predictions.

Loads every (model, seed) prediction file produced by the train40 primary/
secondary kernels, recomputes every metric independently from the raw
per-row predictions (never trusts the kernel's own "selected" metrics
blindly), and produces:
  1. per-seed + 3-seed mean/std metrics for M0-M4
  2. precision/recall/F1/ROC-AUC/PR-AUC/MCC
  3. candidate-cluster paired bootstrap (resamples CANDIDATES, not rows --
     a locus recurring across people is not an independent observation)
  4. per-person metrics
  5. deletion-length subgroups (50-200bp called out explicitly)
  6. genotype subgroups
  7. same-site-negative specificity
  8. repeat/mappability subgroup -- reported as UNAVAILABLE (manifest's
     repeat_bucket is 100% "annotation_unavailable"; not fabricated)
  10. prediction-disagreement / error-overlap between M0 and M4, broken
      out by length, to test whether fusion helps specifically on hard
      short deletions even if the aggregate F1 gap is small.

Ablations (item 9's zero/shuffle half) are aggregated from the per-seed
ablations.json already produced by the primary kernels; the "retrained
branch-removal" half is a separate, additional training task (not yet run).

Run again once all 3 M1/M3 secondary seeds are available; auto-detects
which files exist and reports what is/isn't complete rather than failing.
"""
import glob, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score, matthews_corrcoef, precision_recall_fscore_support,
    roc_auc_score, confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "train40"
OUT.mkdir(parents=True, exist_ok=True)

PRIMARY = {
    1: ROOT / "kaggle/deepsv-ms-train40-primary-seed1/output-v1/pairsv_train40_seed20260720_primary_predictions.csv",
    2: ROOT / "kaggle/deepsv-ms-train40-primary-seed2/output-v1/pairsv_train40_seed20260721_primary_predictions.csv",
    3: ROOT / "kaggle/deepsv-ms-train40-primary-seed3/output-v1/pairsv_train40_seed20260722_primary_predictions.csv",
}
SECONDARY = {
    1: ROOT / "kaggle/deepsv-ms-train40-secondary-seed1/output-v1/pairsv_train40_seed20260720_secondary_predictions.csv",
    2: ROOT / "kaggle/deepsv-ms-train40-secondary-seed2/output-v1/pairsv_train40_seed20260721_secondary_predictions.csv",
    3: ROOT / "kaggle/deepsv-ms-train40-secondary-seed3/output-v1/pairsv_train40_seed20260722_secondary_predictions.csv",
}
RETRAINED_ABLATIONS = {
    1: ROOT / "kaggle/deepsv-ms-train40-ablation-seed1/output-v1/pairsv_train40_seed20260720_ablation_predictions.csv",
    2: ROOT / "kaggle/deepsv-ms-train40-ablation-seed2/output-v1/pairsv_train40_seed20260721_ablation_predictions.csv",
    3: ROOT / "kaggle/deepsv-ms-train40-ablation-seed3/output-v1/pairsv_train40_seed20260722_ablation_predictions.csv",
}
PRIMARY_ABLATIONS = {
    1: ROOT / "kaggle/deepsv-ms-train40-primary-seed1/output-v1/pairsv_train40_seed20260720_primary_ablations.json",
    2: ROOT / "kaggle/deepsv-ms-train40-primary-seed2/output-v1/pairsv_train40_seed20260721_primary_ablations.json",
    3: ROOT / "kaggle/deepsv-ms-train40-primary-seed3/output-v1/pairsv_train40_seed20260722_primary_ablations.json",
}
MODELS = ("M0", "M1", "M2", "M3", "M4")


def load_all():
    frames = []
    missing = []
    for seed, path in PRIMARY.items():
        if path.exists():
            frames.append(pd.read_csv(path))
        else:
            missing.append(str(path))
    for seed, path in SECONDARY.items():
        if path.exists():
            frames.append(pd.read_csv(path))
        else:
            missing.append(str(path))
    for seed, path in RETRAINED_ABLATIONS.items():
        if path.exists():
            frames.append(pd.read_csv(path))
        else:
            missing.append(str(path))
    if not frames:
        raise SystemExit("no prediction files found")
    df = pd.concat(frames, ignore_index=True)
    have = df.groupby(["seed", "model"]).size().unstack(fill_value=0)
    print("available (seed x model) row counts:\n", have, "\n")
    if missing:
        print("NOT YET AVAILABLE (will be excluded from this run):")
        for m in missing:
            print(" ", m)
        print()
    return df


def full_metrics(y, pred, prob):
    pr, re, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    out = {"n": len(y), "precision": pr, "recall": re, "f1": f1, "mcc": matthews_corrcoef(y, pred),
           "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
    if len(np.unique(y)) == 2:
        out["roc_auc"] = roc_auc_score(y, prob)
        out["pr_auc"] = average_precision_score(y, prob)
    else:
        out["roc_auc"] = np.nan
        out["pr_auc"] = np.nan
        if (y == 0).any():
            out["specificity"] = tn / (tn + fp) if (tn + fp) else np.nan
    return out


def per_seed_metrics(df):
    rows = []
    for (seed, model), g in df.groupby(["seed", "model"]):
        rows.append({"seed": seed, "model": model, **full_metrics(g.label.values, g.prediction.values, g.probability.values)})
    return pd.DataFrame(rows)


def three_seed_aggregate(per_seed):
    agg = []
    for model, g in per_seed.groupby("model"):
        n_seeds = len(g)
        row = {"model": model, "n_seeds": n_seeds}
        for col in ("precision", "recall", "f1", "roc_auc", "pr_auc", "mcc"):
            row[f"{col}_mean"] = g[col].mean()
            row[f"{col}_std"] = g[col].std(ddof=0) if n_seeds > 1 else 0.0
            row[f"{col}_min"] = g[col].min()
            row[f"{col}_max"] = g[col].max()
        agg.append(row)
    return pd.DataFrame(agg)


def subgroup_metrics(df):
    rows = []
    for (seed, model), g in df.groupby(["seed", "model"]):
        specs = [
            ("50-200bp", (g.length >= 50) & (g.length <= 200)),
            ("200-1000bp", (g.length > 200) & (g.length <= 1000)),
            ("1000-10000bp", g.length > 1000),
            ("GT_0/1", (g.label == 1) & (g.genotype == "0/1")),
            ("GT_1/1", (g.label == 1) & (g.genotype == "1/1")),
            ("same_site_negative", (g.label == 0) & (g.negative_type == "same_site_negative")),
        ]
        for name, mask in specs:
            sub = g[mask]
            if len(sub) == 0:
                rows.append({"seed": seed, "model": model, "subgroup": name, "n": 0})
                continue
            m = full_metrics(sub.label.values, sub.prediction.values, sub.probability.values)
            rows.append({"seed": seed, "model": model, "subgroup": name, **m})
        for person, sub in g.groupby("sample"):
            m = full_metrics(sub.label.values, sub.prediction.values, sub.probability.values)
            rows.append({"seed": seed, "model": model, "subgroup": f"person:{person}", **m})
    return pd.DataFrame(rows)


def candidate_cluster_bootstrap(df, comparisons, n_boot=2000, seed0=20260725, length_range=None):
    """Resample CANDIDATES with replacement (not rows) -- accounts for the
    same locus recurring across multiple people, unlike R47's naive row
    bootstrap. Pooled across all 3 seeds' predictions for each model (each
    seed's run is an independent training instance on the same candidates)."""
    rng = np.random.default_rng(seed0)
    results = []
    for a, b in comparisons:
        # index rows by (seed, candidate_id) so a resampled candidate pulls in
        # that candidate's rows from every seed where it appears, per model
        sel = df
        if length_range is not None:
            lo, hi = length_range
            sel = df[(df.length >= lo) & (df.length <= hi)]
        da = sel[sel.model == a].copy()
        db = sel[sel.model == b].copy()
        merge_keys = ["seed", "row_id"]
        merged = da[merge_keys + ["label", "prediction", "probability", "candidate_id", "length"]].merge(
            db[merge_keys + ["prediction", "probability"]], on=merge_keys, suffixes=("_a", "_b"))
        candidates = merged["candidate_id"].unique()
        by_cand = merged.groupby("candidate_id").groups
        diffs = []
        pr_diffs = []
        for _ in range(n_boot):
            picked = rng.choice(candidates, size=len(candidates), replace=True)
            idx = np.concatenate([by_cand[c].to_numpy() for c in picked])
            sub = merged.loc[idx]
            y = sub.label.values
            if len(np.unique(y)) < 2:
                continue
            f_a = precision_recall_fscore_support(y, sub.prediction_a.values, average="binary", zero_division=0)[2]
            f_b = precision_recall_fscore_support(y, sub.prediction_b.values, average="binary", zero_division=0)[2]
            diffs.append(f_b - f_a)
            pr_diffs.append(average_precision_score(y, sub.probability_b.values) - average_precision_score(y, sub.probability_a.values))
        diffs = np.array(diffs)
        results.append({
            "comparison": f"{b} - {a}", "n_bootstrap": len(diffs), "n_candidates": len(candidates),
            "f1_difference_mean": float(diffs.mean()), "f1_ci_low": float(np.quantile(diffs, .025)),
            "f1_ci_high": float(np.quantile(diffs, .975)), "f1_win_proportion": float((diffs > 0).mean()),
            "pr_auc_difference_mean": float(np.mean(pr_diffs)),
        })
    return pd.DataFrame(results)


def disagreement_analysis(df):
    wide_pred = df.pivot_table(index=["seed", "row_id"], columns="model", values="prediction")
    meta = df.drop_duplicates(["seed", "row_id"]).set_index(["seed", "row_id"])[["label", "length", "sample", "genotype", "negative_type"]]
    joined = wide_pred.join(meta)
    rows = []
    for length_name, mask in [
        ("50-200bp", (joined.length >= 50) & (joined.length <= 200)),
        ("200-1000bp", (joined.length > 200) & (joined.length <= 1000)),
        ("1000-10000bp", joined.length > 1000),
        ("all", pd.Series(True, index=joined.index)),
    ]:
        sub = joined[mask]
        if "M0" not in sub or "M4" not in sub:
            continue
        m0_wrong = sub["M0"] != sub["label"]
        m4_wrong = sub["M4"] != sub["label"]
        rows.append({
            "length_bucket": length_name, "n": len(sub),
            "m0_correct_m4_correct": int((~m0_wrong & ~m4_wrong).sum()),
            "m0_wrong_m4_correct": int((m0_wrong & ~m4_wrong).sum()),
            "m0_correct_m4_wrong": int((~m0_wrong & m4_wrong).sum()),
            "m0_wrong_m4_wrong": int((m0_wrong & m4_wrong).sum()),
            "m4_fixes_rate_among_m0_errors": float((m0_wrong & ~m4_wrong).sum() / max(1, m0_wrong.sum())),
            "m4_breaks_rate_among_m0_correct": float((~m0_wrong & m4_wrong).sum() / max(1, (~m0_wrong).sum())),
        })
    return pd.DataFrame(rows)


def aggregate_ablations():
    rows = []
    for seed, path in PRIMARY_ABLATIONS.items():
        if not path.exists():
            continue
        d = json.loads(path.read_text())
        for intervention, m in d.items():
            rows.append({"seed": seed, "intervention": intervention, **m})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    agg = df.groupby("intervention").agg(
        f1_change_mean=("f1_change", "mean"), f1_change_std=("f1_change", "std"),
        roc_auc_change_mean=("roc_auc_change", "mean"), pr_auc_change_mean=("pr_auc_change", "mean"),
        n_seeds=("seed", "nunique"),
    ).reset_index()
    return df, agg


if __name__ == "__main__":
    df = load_all()
    per_seed = per_seed_metrics(df)
    per_seed.to_csv(OUT / "per_seed_metrics.csv", index=False)
    print("=== per-seed metrics ===")
    print(per_seed.round(5).to_string(index=False))

    agg = three_seed_aggregate(per_seed)
    agg.to_csv(OUT / "three_seed_aggregate.csv", index=False)
    print("\n=== 3-seed aggregate (mean/std/min/max) ===")
    print(agg[["model", "n_seeds", "f1_mean", "f1_std", "f1_min", "f1_max",
               "precision_mean", "recall_mean", "roc_auc_mean", "pr_auc_mean", "mcc_mean"]].round(5).to_string(index=False))

    sub = subgroup_metrics(df)
    sub.to_csv(OUT / "subgroup_metrics.csv", index=False)
    print(f"\nwrote subgroup_metrics.csv ({len(sub)} rows)")
    print("NOTE: repeat/low-mappability subgroup NOT computed -- manifest's repeat_bucket "
          "is 100% 'annotation_unavailable' (never populated), not silently skipped.")

    have_models = set(df.model.unique())
    comparisons = [("M0", "M4")]
    if "M2" in have_models: comparisons += [("M0", "M2"), ("M2", "M4")]
    if "M1" in have_models: comparisons += [("M0", "M1")]
    if "M3" in have_models: comparisons += [("M0", "M3")]
    # item 9, retrained half: full M4 vs each genuinely-retrained 2-branch model.
    # Direction is (ablated -> M4), so a positive difference means the removed
    # branch contributed.
    for abl in ("M4_NO_CANDIDATE", "M4_NO_READ", "M4_NO_SCALAR"):
        if abl in have_models:
            comparisons.append((abl, "M4"))
            comparisons.append(("M0", abl))
    boot = candidate_cluster_bootstrap(df, comparisons)
    boot.to_csv(OUT / "candidate_cluster_bootstrap.csv", index=False)
    print("\n=== candidate-cluster paired bootstrap (all lengths) ===")
    print(boot.round(5).to_string(index=False))

    # the specific question: does fusion help on DIFFICULT SHORT deletions,
    # even when the aggregate difference is small? Same bootstrap, restricted
    # to 50-200bp candidates.
    boot_short = candidate_cluster_bootstrap(df, comparisons, length_range=(50, 200))
    boot_short.to_csv(OUT / "candidate_cluster_bootstrap_50_200bp.csv", index=False)
    print("\n=== candidate-cluster paired bootstrap, 50-200bp ONLY ===")
    print(boot_short.round(5).to_string(index=False))

    dis = disagreement_analysis(df)
    dis.to_csv(OUT / "disagreement_m0_vs_m4.csv", index=False)
    print("\n=== M0 vs M4 disagreement, by length ===")
    print(dis.round(4).to_string(index=False))

    abl = aggregate_ablations()
    if isinstance(abl, tuple):
        abl_raw, abl_agg = abl
        abl_raw.to_csv(OUT / "ablations_per_seed.csv", index=False)
        abl_agg.to_csv(OUT / "ablations_aggregate.csv", index=False)
        print("\n=== zero/shuffle ablations, aggregated across seeds ===")
        print(abl_agg.round(5).to_string(index=False))

    print(f"\nall outputs written to {OUT}")
