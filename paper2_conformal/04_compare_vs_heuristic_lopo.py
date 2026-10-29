#!/usr/bin/env python3
"""Head-to-head: old floor-heuristic (imported unmodified from
manta_poc/truvari_gate2/phase_f_analysis.py) vs new single-split CRC
(02_crc_pooled.py's solve_threshold), both run on the same 5 LOPO folds
(5 POC people, calibrate on 4, test held-out 1). Neither the heuristic
script nor any statья-1 artifact is modified.

Two target_recall values are used, deliberately:
  - 0.95 (the project's headline target): at N=4 calibration people,
    max_guaranteed_recall = 4/5 = 0.80, so CRC is INFEASIBLE here in every
    fold. The old heuristic does not check feasibility -- it runs anyway
    and returns a definite number regardless. That contrast (old method
    silently promises something it cannot structurally deliver at this N;
    new method says so) is itself part of the result, not a bug in the
    comparison.
  - 0.75 (safely inside 4/5): a genuine apples-to-apples efficiency
    comparison where both methods produce a real threshold.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
ROOT = HERE.parent
MODELS = ("M0", "M2", "M4")


def _import(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


phase_f = _import(ROOT / "manta_poc/truvari_gate2/phase_f_analysis.py", "phase_f_analysis")
crc_pooled = _import(HERE / "02_crc_pooled.py", "crc_pooled")


def recall_and_specificity(pos: np.ndarray, neg: np.ndarray, threshold: float) -> tuple[float, float]:
    n_pos, n_neg = len(pos), len(neg)
    recall = float((pos >= threshold).sum() / n_pos) if n_pos else float("nan")
    specificity = float((neg < threshold).sum() / n_neg) if n_neg else float("nan")
    return recall, specificity


def run(target_recall: float) -> dict:
    data = json.loads((RESULTS / "person_level_scores__poc.json").read_text())
    people = data["people"]
    out = {"target_recall": target_recall, "by_model": {}}

    for model in MODELS:
        pos_by_person = {p: np.array(data["models"][model][p]["pos_probs_sorted"]) for p in people}
        neg_by_person = {p: np.array(data["models"][model][p]["neg_probs_sorted"]) for p in people}

        folds = []
        for held_out in people:
            calib_people = [p for p in people if p != held_out]
            n_calib = len(calib_people)

            # --- old heuristic: pool all calibration positives, floor-quantile ---
            pooled_calib_pos = np.concatenate([pos_by_person[p] for p in calib_people])
            old_threshold = phase_f.select_threshold_for_recall(pooled_calib_pos, target_recall)
            old_recall, old_spec = recall_and_specificity(
                pos_by_person[held_out], neg_by_person[held_out], old_threshold
            )

            # --- new CRC: person-level risk control over the 4 calibration people ---
            calib_pos_by_person = {p: pos_by_person[p] for p in calib_people}
            crc_res = crc_pooled.solve_threshold(calib_pos_by_person, target_recall)
            if crc_res["status"] == "OK":
                new_threshold = crc_res["threshold"]
                new_recall, new_spec = recall_and_specificity(
                    pos_by_person[held_out], neg_by_person[held_out], new_threshold
                )
                crc_feasible = True
            else:
                new_threshold = -np.inf
                new_recall, new_spec = 1.0, 0.0  # accept-everything degenerate rule
                crc_feasible = False

            folds.append({
                "held_out_person": held_out,
                "n_calibration_people": n_calib,
                "max_guaranteed_recall_at_this_N": n_calib / (n_calib + 1),
                "old_heuristic": {
                    "threshold": float(old_threshold),
                    "held_out_recall": old_recall,
                    "held_out_specificity": old_spec,
                    "met_target": bool(old_recall >= target_recall - 1e-9),
                },
                "new_crc": {
                    "feasible": crc_feasible,
                    "threshold": float(new_threshold) if crc_feasible else None,
                    "held_out_recall": new_recall,
                    "held_out_specificity": new_spec,
                    "met_target": bool(new_recall >= target_recall - 1e-9),
                },
            })

        n_old_met = sum(f["old_heuristic"]["met_target"] for f in folds)
        n_new_met = sum(f["new_crc"]["met_target"] for f in folds)
        n_new_feasible = sum(f["new_crc"]["feasible"] for f in folds)
        out["by_model"][model] = {
            "folds": folds,
            "summary": {
                "old_heuristic_folds_meeting_target": f"{n_old_met}/5",
                "new_crc_folds_meeting_target": f"{n_new_met}/5",
                "new_crc_folds_feasible": f"{n_new_feasible}/5",
                "old_heuristic_mean_specificity": float(np.mean([f["old_heuristic"]["held_out_specificity"] for f in folds])),
                "new_crc_mean_specificity": float(np.mean([f["new_crc"]["held_out_specificity"] for f in folds])),
            },
        }
    return out


if __name__ == "__main__":
    all_out = {}
    for target in (0.95, 0.75):
        res = run(target)
        all_out[str(target)] = res
        print(f"\n{'='*70}\ntarget_recall = {target}\n{'='*70}")
        for model, block in res["by_model"].items():
            s = block["summary"]
            print(f"\n[{model}]")
            print(f"  old heuristic: {s['old_heuristic_folds_meeting_target']} folds met target, "
                  f"mean held-out specificity = {s['old_heuristic_mean_specificity']:.4f}")
            print(f"  new CRC:       {s['new_crc_folds_feasible']} folds feasible, "
                  f"{s['new_crc_folds_meeting_target']} folds met target, "
                  f"mean held-out specificity = {s['new_crc_mean_specificity']:.4f}")

    out_path = RESULTS / "compare_vs_heuristic_lopo.json"
    out_path.write_text(json.dumps(all_out, indent=2))
    print(f"\nwrote {out_path}")
