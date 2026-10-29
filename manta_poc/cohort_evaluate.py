#!/usr/bin/env python3
"""One-shot evaluation of the untouched 30-person multi-cohort.

FROZEN BEFORE FIRST RUN. This script is checksummed into
`manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json` before it is ever executed,
so that the metric and subgroup definitions cannot be adjusted after seeing
any result. It is run exactly once.

Metric definitions are deliberately IDENTICAL to the frozen HG002 external
evaluation (`manta_poc/hg002_evaluate.py`) -- same confusion-matrix
construction, same recall/specificity/precision/F1/balanced-accuracy/MCC
formulas, same ROC-AUC/PR-AUC, same filtered-candidate-rate, same
accept-all-Manta baseline, same length buckets. Reusing them unchanged is
what makes the cohort result comparable to the single-person result rather
than a differently-defined number that happens to share a name.

PRIMARY AGGREGATION: per-person metrics, macro-averaged over the 30
independent people. Candidate rows are NOT pooled across people for the
headline number -- people are the independent unit, candidates are not
(the same reasoning as the candidate-cluster bootstrap in section 9.2).
Pooled-over-all-candidates figures are additionally reported as a clearly
labelled secondary view, never as the headline.

M0, M2 and M4 are all reported. No model is selected, preferred, or
promoted on the basis of anything computed here -- M4 remains the
predefined primary model and M0/M2 the mandatory baselines, per the
standing constraint, regardless of which performs best.

Usage: python3 cohort_evaluate.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, matthews_corrcoef

PAIRSV_ROOT = Path("/scratch/igorno-deepsv_poc/pairsv_parity")
GATE2 = PAIRSV_ROOT / "manta_poc/truvari_gate2"
SELECTION_MANIFEST = PAIRSV_ROOT / "manta_poc/multicohort_30_selection_manifest.json"
OUT_PATH = PAIRSV_ROOT / "manta_poc/cohort_final_evaluation_report.json"

MODELS = ("M0", "M2", "M4")
LENGTH_BUCKETS = [("50-200bp_primary", 50, 200),
                  ("200-1000bp_secondary", 200, 1000),
                  ("1000-10000bp_exploratory", 1000, 10000)]
BREAKPOINT_BUCKETS = [("exact_0bp", 0, 0), ("1-10bp", 1, 10), ("11-50bp", 11, 50),
                      ("51-100bp", 51, 100), (">100bp", 101, float("inf"))]
SUPERPOPS = ("AFR", "AMR", "EAS", "EUR", "SAS")


def confusion_at_threshold(labels: np.ndarray, preds: np.ndarray) -> dict:
    """Identical to hg002_evaluate.confusion_at_threshold -- do not alter."""
    tp = int(((labels == 1) & (preds == 1)).sum())
    fn = int(((labels == 1) & (preds == 0)).sum())
    tn = int(((labels == 0) & (preds == 0)).sum())
    fp = int(((labels == 0) & (preds == 1)).sum())
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    specificity = tn / (tn + fp) if (tn + fp) else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) and not np.isnan(precision) and not np.isnan(recall)
          else float("nan"))
    balanced_acc = ((recall + specificity) / 2
                    if not (np.isnan(recall) or np.isnan(specificity)) else float("nan"))
    mcc = (matthews_corrcoef(labels, preds)
           if len(set(labels)) > 1 and len(set(preds)) > 1 else 0.0)
    n = tp + fn + tn + fp
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "recall": recall,
            "specificity": specificity, "precision": precision, "f1": f1,
            "balanced_accuracy": balanced_acc, "mcc": mcc, "n": n,
            "filtered_candidate_rate": (fn + tn) / n if n else float("nan")}


def accept_all_baseline(labels: np.ndarray) -> dict:
    """Identical to hg002_evaluate.accept_all_baseline -- do not alter."""
    n = len(labels)
    prevalence = float(labels.mean()) if n else float("nan")
    precision = prevalence
    recall = 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else float("nan")
    return {"n": n, "prevalence": prevalence, "recall": recall, "specificity": 0.0,
            "precision": precision, "f1": f1, "mcc": 0.0, "roc_auc": 0.5,
            "pr_auc": prevalence}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_person(sample: str) -> tuple[pd.DataFrame, dict, dict]:
    """Return (merged predictions+labels, gate2 report, extraction accounting)."""
    wd = GATE2 / sample
    manifest = pd.DataFrame(json.loads((wd / "gate3_candidate_manifest.json").read_text()))
    gate2_report = json.loads((wd / "gate2_classification_report.json").read_text())
    ensembled = pd.read_csv(wd / f"{sample}_gate3_predictions_ensembled_LABEL_BLIND.csv")

    # Supervised metrics use ONLY confidently-labelled candidates. Unknown
    # candidates (PanGenie did not confidently genotype the site either way)
    # are never converted into negatives -- they are counted and reported
    # separately, exactly as in the 5-person POC and the HG002 pass.
    labelled = manifest[manifest["class"].isin(["positive", "known_negative"])].copy()
    eligible = manifest[manifest["extraction_precheck_status"] == "ok"]

    merged = ensembled.merge(
        labelled[["candidate_id", "label", "length", "class",
                  "truth_StartDistance", "truth_EndDistance", "manta_genotype"]],
        on="candidate_id", how="inner")

    merged["breakpoint_error_bp"] = np.maximum(
        merged["truth_StartDistance"].abs().fillna(0),
        merged["truth_EndDistance"].abs().fillna(0))

    counts = gate2_report["class_counts"]
    n_unknown = counts.get("unknown", 0)
    total = gate2_report["total_manta_pass_del"]
    n_scored_per_model = len(merged) // len(MODELS) if len(merged) else 0
    accounting = {
        "total_manta_pass_del": total,
        "class_counts": counts,
        "unknown_fraction_of_total": n_unknown / total if total else float("nan"),
        "n_eligible_for_extraction": int(len(eligible)),
        "n_extraction_failures": int(len(eligible) - n_scored_per_model
                                     - (len(eligible) - len(labelled[labelled["extraction_precheck_status"] == "ok"]))),
        "n_labelled_candidates_scored": n_scored_per_model,
    }
    return merged, gate2_report, accounting


def evaluate_person(sample: str, merged: pd.DataFrame) -> dict:
    per_model = {}
    for model in MODELS:
        sub = merged[merged.model == model]
        labels = sub["label"].to_numpy()
        preds = sub["prediction"].to_numpy()
        probs = sub["probability"].to_numpy()

        res = confusion_at_threshold(labels, preds)
        res["threshold"] = float(sub["threshold"].iloc[0]) if len(sub) else float("nan")
        if len(set(labels)) > 1:
            res["roc_auc"] = float(roc_auc_score(labels, probs))
            res["pr_auc"] = float(average_precision_score(labels, probs))
        else:
            res["roc_auc"] = float("nan")
            res["pr_auc"] = float("nan")

        length_subgroups = {}
        for name, lo, hi in LENGTH_BUCKETS:
            b = sub[(sub.length >= lo) & (sub.length < hi)]
            if len(b) == 0 or b["label"].nunique() < 2:
                length_subgroups[name] = {"n": int(len(b)),
                                          "note": "insufficient class diversity for full metrics"}
                continue
            m = confusion_at_threshold(b["label"].to_numpy(), b["prediction"].to_numpy())
            m["roc_auc"] = float(roc_auc_score(b["label"], b["probability"]))
            m["pr_auc"] = float(average_precision_score(b["label"], b["probability"]))
            length_subgroups[name] = m

        pos = sub[sub.label == 1]
        breakpoint_subgroups = {}
        for name, lo, hi in BREAKPOINT_BUCKETS:
            b = pos[(pos.breakpoint_error_bp >= lo) & (pos.breakpoint_error_bp <= hi)]
            if len(b) == 0:
                breakpoint_subgroups[name] = {"n": 0}
                continue
            breakpoint_subgroups[name] = {
                "n": int(len(b)),
                "accepted_rate": float(b["prediction"].mean()),
                "median_score": float(b["probability"].median()),
            }

        per_model[model] = {"primary": res, "length_subgroups": length_subgroups,
                            "breakpoint_error_subgroups": breakpoint_subgroups}

    any_model = merged[merged.model == MODELS[0]]
    per_model["accept_all_manta_baseline"] = accept_all_baseline(any_model["label"].to_numpy())
    return per_model


def macro_average(per_person: dict, field: str) -> dict:
    """Primary aggregation: mean over PEOPLE (not over pooled candidates)."""
    out = {}
    for model in MODELS:
        vals = [p[model]["primary"][field] for p in per_person.values()
                if not np.isnan(p[model]["primary"][field])]
        out[model] = {
            "macro_mean": float(np.mean(vals)) if vals else float("nan"),
            "macro_sd": float(np.std(vals, ddof=1)) if len(vals) > 1 else float("nan"),
            "min": float(np.min(vals)) if vals else float("nan"),
            "max": float(np.max(vals)) if vals else float("nan"),
            "n_people": len(vals),
        }
    return out


def main() -> None:
    selection = json.loads(SELECTION_MANIFEST.read_text())
    people = selection["people"]
    superpop_of = {p["sample"]: p["super_pop"] for p in people}
    samples = [p["sample"] for p in people]

    per_person, accounting_all, prediction_hashes = {}, {}, {}
    for sample in samples:
        merged, _gate2, accounting = load_person(sample)
        per_person[sample] = evaluate_person(sample, merged)
        accounting_all[sample] = accounting
        wd = GATE2 / sample
        prediction_hashes[sample] = {
            "ensembled": sha256(wd / f"{sample}_gate3_predictions_ensembled_LABEL_BLIND.csv"),
            "per_seed": sha256(wd / f"{sample}_gate3_predictions_per_seed_LABEL_BLIND.csv"),
        }
        print(f"{sample}: evaluated", flush=True)

    primary_fields = ["recall", "specificity", "precision", "f1",
                      "balanced_accuracy", "mcc", "roc_auc", "pr_auc",
                      "filtered_candidate_rate"]
    macro = {f: macro_average(per_person, f) for f in primary_fields}

    by_superpop = {}
    for sp in SUPERPOPS:
        members = [s for s in samples if superpop_of[s] == sp]
        by_superpop[sp] = {"people": members, "n_people": len(members), "metrics": {}}
        for model in MODELS:
            entry = {}
            for f in ("recall", "specificity"):
                vals = [per_person[s][model]["primary"][f] for s in members
                        if not np.isnan(per_person[s][model]["primary"][f])]
                entry[f] = {"macro_mean": float(np.mean(vals)) if vals else float("nan"),
                            "macro_sd": float(np.std(vals, ddof=1)) if len(vals) > 1 else float("nan")}
            by_superpop[sp]["metrics"][model] = entry

    report = {
        "report_version": "COHORT_30_ONE_SHOT_EVALUATION_v1",
        "aggregation_note": ("PRIMARY = per-person metrics macro-averaged over 30 independent "
                             "people. Candidate rows are not independent samples and are never "
                             "reported as such."),
        "model_selection_note": ("M0/M2/M4 all reported. No model is selected or preferred on the "
                                 "basis of these results; M4 remains the predefined primary model "
                                 "and M0/M2 the mandatory baselines."),
        "n_people": len(samples),
        "samples": samples,
        "frozen_deployment_thresholds_source":
            "manta_poc/truvari_gate2/phase_f/phaseF_deployment_thresholds_FROZEN.json",
        "primary_macro_averaged_over_people": macro,
        "by_superpopulation": by_superpop,
        "per_person": per_person,
        "candidate_accounting": accounting_all,
        "prediction_file_sha256": prediction_hashes,
    }
    OUT_PATH.write_text(json.dumps(report, indent=2))
    print(f"wrote {OUT_PATH}")
    print(f"sha256 {sha256(OUT_PATH)}")


if __name__ == "__main__":
    main()
