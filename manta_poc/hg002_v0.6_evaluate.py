#!/usr/bin/env python3
"""HG002 v0.6 (SECONDARY/sensitivity) final evaluation. Identical metric
suite to hg002_evaluate.py, applied to the v0.6/GRCh37 pipeline outputs.
Run exactly once, after every upstream step has completed and predictions
are hashed. Results here are NEVER pooled or averaged with the v5.0q
primary result (EXTERNAL_EVAL_PROTOCOL_FROZEN.md ADDENDUM section 10,
mission's explicit "never pool" rule) -- reported strictly as a separate
sensitivity analysis.

Usage: python3 hg002_v0.6_evaluate.py
"""
from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pysam
from sklearn.metrics import roc_auc_score, average_precision_score, matthews_corrcoef

WD = Path("/scratch/igorno-deepsv_poc/hg002_v0.6_external")
MODELS = ("M0", "M2", "M4")
LENGTH_BUCKETS = [("50-200bp_primary", 50, 200), ("200-1000bp_secondary", 200, 1000), ("1000-10000bp_exploratory", 1000, 10000)]
BREAKPOINT_BUCKETS = [("exact_0bp", 0, 0), ("1-10bp", 1, 10), ("11-50bp", 11, 50), ("51-100bp", 51, 100), (">100bp", 101, float("inf"))]


def confusion_at_threshold(labels: np.ndarray, preds: np.ndarray) -> dict:
    tp = int(((labels == 1) & (preds == 1)).sum())
    fn = int(((labels == 1) & (preds == 0)).sum())
    tn = int(((labels == 0) & (preds == 0)).sum())
    fp = int(((labels == 0) & (preds == 1)).sum())
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    specificity = tn / (tn + fp) if (tn + fp) else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) and not np.isnan(precision) and not np.isnan(recall) else float("nan")
    balanced_acc = (recall + specificity) / 2 if not (np.isnan(recall) or np.isnan(specificity)) else float("nan")
    mcc = matthews_corrcoef(labels, preds) if len(set(labels)) > 1 and len(set(preds)) > 1 else 0.0
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "recall": recall, "specificity": specificity,
            "precision": precision, "f1": f1, "balanced_accuracy": balanced_acc, "mcc": mcc,
            "n": tp + fn + tn + fp, "filtered_candidate_rate": (fn + tn) / (tp + fn + tn + fp) if (tp + fn + tn + fp) else float("nan")}


def accept_all_baseline(labels: np.ndarray) -> dict:
    n = len(labels)
    prevalence = float(labels.mean()) if n else float("nan")
    precision = prevalence
    recall = 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else float("nan")
    return {"n": n, "prevalence": prevalence, "recall": recall, "specificity": 0.0,
            "precision": precision, "f1": f1, "mcc": 0.0, "roc_auc": 0.5, "pr_auc": prevalence}


def main() -> None:
    manifest = pd.DataFrame(json.load(open(WD / "hg002_v0.6_gate3_candidate_manifest.json")))
    class_counts = manifest["class"].value_counts().to_dict() if "class" in manifest.columns else {}
    gate2_report = json.loads((WD / "hg002_v0.6_gate2_classification_report.json").read_text())

    breakpoint_dist = {}
    vf = pysam.VariantFile(str(WD / "truvari_v0.6_secondary" / "tp-comp.vcf.gz"))
    for rec in vf:
        sd = rec.info.get("StartDistance")
        ed = rec.info.get("EndDistance")
        breakpoint_dist[rec.id] = max(abs(sd) if sd is not None else 0, abs(ed) if ed is not None else 0)

    ensembled = pd.read_csv(WD / "hg002_v0.6_gate3_predictions_ensembled_LABEL_BLIND.csv")
    labeled_manifest = manifest[manifest["extraction_precheck_status"] == "ok"].copy()

    with h5py.File(WD / "hg002_v0.6_gate3_extracted.h5", "r") as h5:
        cids = [c.decode() if isinstance(c, bytes) else c for c in h5["candidate_id"][:]]
        success = h5["success"][:]
        failure_reason = [r.decode() if isinstance(r, bytes) else r for r in h5["failure_reason"][:]]
    extraction_status = pd.DataFrame({"candidate_id": cids, "success": success, "failure_reason": failure_reason})
    n_extraction_failures = int((~extraction_status["success"]).sum())
    failure_reasons_breakdown = (extraction_status.loc[~extraction_status["success"], "failure_reason"]
                                  .apply(lambda s: s.split(":")[0]).value_counts().to_dict())

    merged = ensembled.merge(labeled_manifest[["candidate_id", "label", "length", "manta_id", "manta_genotype"]], on="candidate_id", how="left")
    merged["breakpoint_error_bp"] = merged["manta_id"].map(breakpoint_dist)

    results = {}
    for model in MODELS:
        sub = merged[merged.model == model].copy()
        labels = sub["label"].to_numpy()
        preds = sub["prediction"].to_numpy()
        probs = sub["probability"].to_numpy()

        primary = confusion_at_threshold(labels, preds)
        primary["roc_auc"] = float(roc_auc_score(labels, probs))
        primary["pr_auc"] = float(average_precision_score(labels, probs))
        primary["threshold"] = float(sub["threshold"].iloc[0])

        length_subgroups = {}
        for name, lo, hi in LENGTH_BUCKETS:
            bsub = sub[(sub.length >= lo) & (sub.length < hi)]
            if len(bsub) == 0 or bsub["label"].nunique() < 2:
                length_subgroups[name] = {"n": int(len(bsub)), "note": "insufficient class diversity for full metrics"}
                continue
            b = confusion_at_threshold(bsub["label"].to_numpy(), bsub["prediction"].to_numpy())
            b["roc_auc"] = float(roc_auc_score(bsub["label"], bsub["probability"]))
            b["pr_auc"] = float(average_precision_score(bsub["label"], bsub["probability"]))
            length_subgroups[name] = b

        pos_sub = sub[(sub.label == 1) & sub["breakpoint_error_bp"].notna()]
        breakpoint_subgroups = {}
        for name, lo, hi in BREAKPOINT_BUCKETS:
            bsub = pos_sub[(pos_sub.breakpoint_error_bp >= lo) & (pos_sub.breakpoint_error_bp <= hi)]
            if len(bsub) == 0:
                breakpoint_subgroups[name] = {"n": 0}
                continue
            breakpoint_subgroups[name] = {
                "n": int(len(bsub)),
                "accepted_rate": float((bsub.prediction == 1).mean()),
                "median_score": float(bsub.probability.median()),
            }

        results[model] = {
            "primary_at_frozen_threshold": primary,
            "length_subgroups": length_subgroups,
            "breakpoint_error_subgroups_positive_only": breakpoint_subgroups,
        }

    accept_all = accept_all_baseline(merged[merged.model == "M0"]["label"].to_numpy())

    report = {
        "sample": "HG002", "truth_source": "NIST SV v0.6 GRCh37 Tier1 (SECONDARY/sensitivity, mature but self-reported <=50% genome-wide SV coverage, biased toward easier SVs)",
        "reference_build": "GRCh37/hs37d5",
        "pooled_with_v5.0q_primary": False,
        "note": "This result is a separate sensitivity analysis. It must never be pooled, averaged, or presented as replacing the v5.0q primary result, regardless of which shows better or worse numbers.",
        "manta_pass_del_total": gate2_report["total_manta_pass_del"],
        "class_counts": {"positive": class_counts.get("positive", 0), "known_negative": class_counts.get("known_negative", 0)},
        "unknown_excluded_by_benchmark_region_rule": gate2_report["class_counts"].get("excluded_outside_or_crossing_benchmark_bed", 0),
        "extraction_failures": {"n": n_extraction_failures, "reasons": failure_reasons_breakdown, "n_eligible": len(labeled_manifest), "n_success": len(labeled_manifest) - n_extraction_failures},
        "accept_all_manta_baseline": accept_all,
        "manta_own_recall_against_v0.6_truth_in_benchmark_regions": "see hg002_v0.6_gate2_classification_report.json / truvari_v0.6_secondary/summary.json for Manta's own end-to-end recall against v0.6 (SEPARATE from PAIR-SV-as-filter metrics below)",
        "results_by_model": results,
    }

    out_path = WD / "hg002_v0.6_final_evaluation_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\nWROTE: {out_path}")


if __name__ == "__main__":
    main()
