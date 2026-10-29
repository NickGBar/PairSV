"""ONE-SHOT internal-test evaluation. Run ONLY after pairsv_test_predictions_LABEL_BLIND.csv
has been retrieved and SHA-256-hashed (see freeze_and_hash_test_predictions.py).
This script is the first point at which test labels are read at all.

Reproduces every metric already used for the validation-phase analysis
(scripts/analyze_train40_controlled.py) so the reported numbers are directly
comparable: per-seed + 3-seed mean/std, full metric suite, per-person,
length subgroups (50-200bp called out), genotype subgroups, same-site-negative
specificity, confusion matrices, candidate-cluster paired bootstrap. Adds two
test-specific analyses: leave-one-person-out sensitivity (does the headline
number depend on any single test person) and the explicit pass/fail check
against the pre-registered mean F1 >= 0.72 criterion.

This script does not select, retrain, or change any threshold. It only
reads already-frozen predictions and already-frozen labels.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score, matthews_corrcoef, precision_recall_fscore_support,
    roc_auc_score, confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "test_evaluation"
OUT.mkdir(parents=True, exist_ok=True)

PREDICTIONS = ROOT / "kaggle/deepsv-ms-test-inference/output-v1/pairsv_test_predictions_LABEL_BLIND.csv"
MANIFEST = ROOT / "kaggle/deepsv-ms-manifest50-hq/output-v4/sample_candidate_manifest.tsv"
SUCCESS_ROOT = ROOT / "kaggle/deepsv-ms-extract-test-shard9/output-v1"
FREEZE_HASHES = ROOT / "reports" / "test_evaluation" / "frozen_prediction_hashes.json"

F1_CRITERION = 0.72
MODELS = ("M0", "M1", "M2", "M3", "M4")
SEEDS = (20260720, 20260721, 20260722)


def load_predictions_and_labels():
    if not FREEZE_HASHES.exists():
        raise SystemExit(
            "frozen_prediction_hashes.json not found -- predictions must be hashed "
            "BEFORE this script runs. Run freeze_and_hash_test_predictions.py first."
        )
    pred = pd.read_csv(PREDICTIONS)
    assert not ({"label", "genotype", "negative_type"} & set(pred.columns)), \
        "predictions file contains label-conditioned columns -- label-blindness violated"
    manifest = pd.read_csv(MANIFEST, sep="\t", usecols=["row_id", "label", "genotype", "negative_type", "sample", "split"])
    test_manifest = manifest[manifest.split == "test"]
    assert set(test_manifest["row_id"]) >= set(pred["row_id"]), "predictions reference row_ids absent from the test manifest"
    df = pred.merge(test_manifest[["row_id", "label", "genotype", "negative_type"]], on="row_id", how="left")
    if df["label"].isna().any():
        raise SystemExit(f"{df['label'].isna().sum()} predicted rows have no matching test-manifest label")
    df["label"] = df["label"].astype(int)
    return df


def full_metrics(y, pred, prob):
    pr, re, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    out = {"n": len(y), "precision": pr, "recall": re, "f1": f1, "mcc": matthews_corrcoef(y, pred),
           "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
    has_pos, has_neg = (y == 1).any(), (y == 0).any()
    out["roc_auc"] = roc_auc_score(y, prob) if has_neg else np.nan
    out["pr_auc"] = average_precision_score(y, prob) if has_neg else np.nan
    out["specificity"] = tn / (tn + fp) if has_neg and (tn + fp) else np.nan
    return out


def per_seed_metrics(df):
    rows = []
    for (seed, model), g in df.groupby(["seed", "model"]):
        rows.append({"seed": seed, "model": model, **full_metrics(g.label.values, g.prediction.values, g.probability.values)})
    return pd.DataFrame(rows)


def three_seed_aggregate(per_seed):
    agg = []
    for model, g in per_seed.groupby("model"):
        row = {"model": model, "n_seeds": len(g)}
        for col in ("precision", "recall", "f1", "roc_auc", "pr_auc", "mcc"):
            row[f"{col}_mean"] = g[col].mean()
            row[f"{col}_std"] = g[col].std(ddof=0)
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
            m = full_metrics(sub.label.values, sub.prediction.values, sub.probability.values) if len(sub) else {"n": 0}
            rows.append({"seed": seed, "model": model, "subgroup": name, **m})
        for person, sub in g.groupby("sample"):
            m = full_metrics(sub.label.values, sub.prediction.values, sub.probability.values)
            rows.append({"seed": seed, "model": model, "subgroup": f"person:{person}", **m})
    return pd.DataFrame(rows)


def leave_one_person_out(df):
    """Does the headline mean-F1 depend on any single test person?"""
    people = sorted(df["sample"].unique())
    rows = []
    for model in MODELS:
        gm = df[df.model == model]
        for held_out in people:
            sub = gm[gm["sample"] != held_out]
            f1s = []
            for seed, gs in sub.groupby("seed"):
                m = full_metrics(gs.label.values, gs.prediction.values, gs.probability.values)
                f1s.append(m["f1"])
            rows.append({"model": model, "held_out_person": held_out, "f1_mean_without_person": float(np.mean(f1s)), "n_seeds": len(f1s)})
    return pd.DataFrame(rows)


def candidate_cluster_bootstrap(df, comparisons, n_boot=2000, seed0=20260726):
    rng = np.random.default_rng(seed0)
    results = []
    for a, b in comparisons:
        da = df[df.model == a].copy()
        db = df[df.model == b].copy()
        merged = da[["seed", "row_id", "label", "prediction", "probability", "candidate_id", "length"]].merge(
            db[["seed", "row_id", "prediction", "probability"]], on=["seed", "row_id"], suffixes=("_a", "_b"))
        candidates = merged["candidate_id"].unique()
        by_cand = merged.groupby("candidate_id").groups
        diffs, pr_diffs = [], []
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


def extraction_qc_summary():
    runtime_path = SUCCESS_ROOT / "pairsv_shard_09_runtime.json"
    if not runtime_path.exists():
        return None
    return json.loads(runtime_path.read_text())


if __name__ == "__main__":
    df = load_predictions_and_labels()
    print(f"loaded {len(df)} predictions ({df.model.nunique()} models x {df.seed.nunique()} seeds x {len(df)//15} rows)")

    rt = extraction_qc_summary()
    if rt:
        print("\n=== extraction success/failure (from frozen runtime.json) ===")
        print(json.dumps({k: rt[k] for k in ("candidates_attempted", "candidates_completed", "candidates_failed", "failure_rate", "failure_categories")}, indent=1))

    per_seed = per_seed_metrics(df)
    per_seed.to_csv(OUT / "per_seed_metrics.csv", index=False)
    print("\n=== per-seed metrics ===")
    print(per_seed.round(5).to_string(index=False))

    agg = three_seed_aggregate(per_seed)
    agg.to_csv(OUT / "three_seed_aggregate.csv", index=False)
    print("\n=== 3-seed aggregate (mean/std/min/max) ===")
    print(agg[["model", "n_seeds", "f1_mean", "f1_std", "f1_min", "f1_max",
               "precision_mean", "recall_mean", "roc_auc_mean", "pr_auc_mean", "mcc_mean"]].round(5).to_string(index=False))

    print("\n=== PRIMARY CRITERION CHECK: mean test F1 >= 0.72 ===")
    for model in MODELS:
        row = agg[agg.model == model].iloc[0]
        verdict = "PASS" if row["f1_mean"] >= F1_CRITERION else "FAIL"
        print(f"  {model}: mean F1 = {row['f1_mean']:.5f}  ->  {verdict} (criterion {F1_CRITERION})")

    sub = subgroup_metrics(df)
    sub.to_csv(OUT / "subgroup_metrics.csv", index=False)
    print(f"\nwrote subgroup_metrics.csv ({len(sub)} rows) -- includes per-person, 50-200bp, genotype, same-site-negative")

    loo = leave_one_person_out(df)
    loo.to_csv(OUT / "leave_one_person_out.csv", index=False)
    print("\n=== leave-one-person-out sensitivity (3-seed mean F1 excluding each person) ===")
    print(loo.groupby("model")["f1_mean_without_person"].agg(["mean", "std", "min", "max"]).round(5).to_string())

    comparisons = [("M0", "M4"), ("M0", "M1"), ("M0", "M2"), ("M0", "M3"), ("M2", "M4")]
    boot = candidate_cluster_bootstrap(df, comparisons)
    boot.to_csv(OUT / "candidate_cluster_bootstrap.csv", index=False)
    print("\n=== candidate-cluster paired bootstrap ===")
    print(boot.round(5).to_string(index=False))

    boot_short = candidate_cluster_bootstrap(df[(df.length >= 50) & (df.length <= 200)], comparisons)
    boot_short.to_csv(OUT / "candidate_cluster_bootstrap_50_200bp.csv", index=False)
    print("\n=== candidate-cluster paired bootstrap, 50-200bp only ===")
    print(boot_short.round(5).to_string(index=False))

    cms = []
    for (seed, model), g in df.groupby(["seed", "model"]):
        tn, fp, fn, tp = confusion_matrix(g.label.values, g.prediction.values, labels=[0, 1]).ravel()
        cms.append({"seed": seed, "model": model, "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)})
    pd.DataFrame(cms).to_csv(OUT / "confusion_matrices.csv", index=False)
    print(f"\nwrote confusion_matrices.csv ({len(cms)} rows)")

    print(f"\nall outputs written to {OUT}")
