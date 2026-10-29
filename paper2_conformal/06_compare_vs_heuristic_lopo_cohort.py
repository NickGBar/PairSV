#!/usr/bin/env python3
"""Same comparison as 04_compare_vs_heuristic_lopo.py (old floor-heuristic,
imported unmodified from phase_f_analysis.py, vs new single-split CRC), but
run as full leave-one-out over the 30-person cohort instead of the 5 POC
people. N=29 calibration people per fold -> max_guaranteed_recall =
29/30 ~= 0.967, so target_recall=0.95 (the project's actual deployment
target) is genuinely feasible here -- this is the first real head-to-head
at 0.95 with realistic held-out validation, not the infeasible-at-N=4 case
in 04.

This is a heavier use of the cohort than the single deterministic passes in
02/03/05 (30 distinct calibration+held-out cycles). Proceeding was an
explicit user decision on 2026-08-15, made before formal §7 resolution with
a future advisor -- recorded here and in PAPER2_RESEARCH_PLAN.md, not done
silently.
"""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
ROOT = HERE.parent
MODELS = ("M0", "M2", "M4")
TARGET_RECALL = 0.95


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
    data = json.loads((RESULTS / "person_level_scores__cohort.json").read_text())
    people = data["people"]
    superpop_of = data["superpopulation_of_person"]
    out = {"target_recall": target_recall, "n_people": len(people), "by_model": {}}

    for model in MODELS:
        pos_by_person = {p: np.array(data["models"][model][p]["pos_probs_sorted"]) for p in people}
        neg_by_person = {p: np.array(data["models"][model][p]["neg_probs_sorted"]) for p in people}

        folds = []
        for held_out in people:
            calib_people = [p for p in people if p != held_out]
            n_calib = len(calib_people)

            pooled_calib_pos = np.concatenate([pos_by_person[p] for p in calib_people])
            old_threshold = phase_f.select_threshold_for_recall(pooled_calib_pos, target_recall)
            old_recall, old_spec = recall_and_specificity(
                pos_by_person[held_out], neg_by_person[held_out], old_threshold
            )

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
                new_recall, new_spec = 1.0, 0.0
                crc_feasible = False

            folds.append({
                "held_out_person": held_out,
                "superpopulation": superpop_of.get(held_out, "UNKNOWN"),
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

        by_pop = {}
        for pop in sorted({f["superpopulation"] for f in folds}):
            pop_folds = [f for f in folds if f["superpopulation"] == pop]
            by_pop[pop] = {
                "n_folds": len(pop_folds),
                "old_heuristic_met_target": sum(f["old_heuristic"]["met_target"] for f in pop_folds),
                "new_crc_met_target": sum(f["new_crc"]["met_target"] for f in pop_folds),
                "old_heuristic_mean_recall": float(np.mean([f["old_heuristic"]["held_out_recall"] for f in pop_folds])),
                "new_crc_mean_recall": float(np.mean([f["new_crc"]["held_out_recall"] for f in pop_folds])),
                "old_heuristic_mean_specificity": float(np.mean([f["old_heuristic"]["held_out_specificity"] for f in pop_folds])),
                "new_crc_mean_specificity": float(np.mean([f["new_crc"]["held_out_specificity"] for f in pop_folds])),
            }

        out["by_model"][model] = {
            "folds": folds,
            "summary": {
                "old_heuristic_folds_meeting_target": f"{n_old_met}/{len(people)}",
                "new_crc_folds_meeting_target": f"{n_new_met}/{len(people)}",
                "new_crc_folds_feasible": f"{n_new_feasible}/{len(people)}",
                "old_heuristic_mean_specificity": float(np.mean([f["old_heuristic"]["held_out_specificity"] for f in folds])),
                "new_crc_mean_specificity": float(np.mean([f["new_crc"]["held_out_specificity"] for f in folds])),
                "old_heuristic_mean_recall": float(np.mean([f["old_heuristic"]["held_out_recall"] for f in folds])),
                "new_crc_mean_recall": float(np.mean([f["new_crc"]["held_out_recall"] for f in folds])),
            },
            "by_superpopulation": by_pop,
        }
    return out


if __name__ == "__main__":
    t0 = time.time()
    res = run(TARGET_RECALL)
    print(f"target_recall = {TARGET_RECALL}, N_people = {res['n_people']} (full LOPO, N_calib=29 per fold)\n")
    for model, block in res["by_model"].items():
        s = block["summary"]
        print(f"[{model}]")
        print(f"  old heuristic: {s['old_heuristic_folds_meeting_target']} folds met target, "
              f"mean recall={s['old_heuristic_mean_recall']:.4f}, mean specificity={s['old_heuristic_mean_specificity']:.4f}")
        print(f"  new CRC:       {s['new_crc_folds_feasible']} folds feasible, "
              f"{s['new_crc_folds_meeting_target']} folds met target, "
              f"mean recall={s['new_crc_mean_recall']:.4f}, mean specificity={s['new_crc_mean_specificity']:.4f}")
        print("  by superpopulation:")
        for pop, row in block["by_superpopulation"].items():
            print(f"    {pop}: old {row['old_heuristic_met_target']}/{row['n_folds']} met "
                  f"(recall={row['old_heuristic_mean_recall']:.4f}, spec={row['old_heuristic_mean_specificity']:.4f})  "
                  f"| new {row['new_crc_met_target']}/{row['n_folds']} met "
                  f"(recall={row['new_crc_mean_recall']:.4f}, spec={row['new_crc_mean_specificity']:.4f})")
        print()

    out_path = RESULTS / "compare_vs_heuristic_lopo_cohort.json"
    out_path.write_text(json.dumps(res, indent=2))
    print(f"wrote {out_path} ({time.time()-t0:.1f}s)")
