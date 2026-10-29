#!/usr/bin/env python3
"""Refined H2 question (PAPER2_RESEARCH_PLAN.md §10.6): pooled CRC already
delivers uniform per-superpopulation reliability at target=0.95 (§10.6,
30/30 folds). So the open question is no longer "does group-conditional
fix reliability" -- it's "does restricting calibration to a person's own
ancestry group buy anything (recovered specificity) relative to pooling
everyone, for the SAME held-out person, at a target both can reach."

For every one of the 30 cohort people, two thresholds are computed and
both evaluated on that SAME held-out person:
  (a) group-conditional: calibrated on the other 5 members of their own
      superpopulation (N=5, max_guaranteed_recall=5/6~0.833)
  (b) pooled: calibrated on all other 29 people (N=29, max=29/30~0.967)
at target_recall=0.75, safely inside both feasibility bounds -- a genuine
apples-to-apples comparison, not one method degenerate and the other not.
"""
from __future__ import annotations

import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
MODELS = ("M0", "M2", "M4")
TARGET_RECALL = 0.75


def _import(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


crc_pooled = _import(HERE / "02_crc_pooled.py", "crc_pooled")
solve_threshold = crc_pooled.solve_threshold


def recall_and_specificity(pos: np.ndarray, neg: np.ndarray, threshold: float) -> tuple[float, float]:
    n_pos, n_neg = len(pos), len(neg)
    recall = float((pos >= threshold).sum() / n_pos) if n_pos else float("nan")
    specificity = float((neg < threshold).sum() / n_neg) if n_neg else float("nan")
    return recall, specificity


def run(target_recall: float) -> dict:
    data = json.loads((RESULTS / "person_level_scores__cohort.json").read_text())
    people = data["people"]
    superpop_of = data["superpopulation_of_person"]
    groups = defaultdict(list)
    for p in people:
        groups[superpop_of[p]].append(p)

    out = {"target_recall": target_recall, "by_model": {}}
    for model in MODELS:
        pos_by_person = {p: np.array(data["models"][model][p]["pos_probs_sorted"]) for p in people}
        neg_by_person = {p: np.array(data["models"][model][p]["neg_probs_sorted"]) for p in people}

        rows = []
        for held_out in people:
            pop = superpop_of[held_out]
            group_calib = [p for p in groups[pop] if p != held_out]  # N=5
            pooled_calib = [p for p in people if p != held_out]      # N=29

            group_res = solve_threshold({p: pos_by_person[p] for p in group_calib}, target_recall)
            pooled_res = solve_threshold({p: pos_by_person[p] for p in pooled_calib}, target_recall)

            g_recall, g_spec = recall_and_specificity(
                pos_by_person[held_out], neg_by_person[held_out], group_res["threshold"]
            )
            p_recall, p_spec = recall_and_specificity(
                pos_by_person[held_out], neg_by_person[held_out], pooled_res["threshold"]
            )
            rows.append({
                "held_out_person": held_out,
                "superpopulation": pop,
                "group_conditional": {"threshold": group_res["threshold"], "recall": g_recall, "specificity": g_spec,
                                       "met_target": bool(g_recall >= target_recall - 1e-9)},
                "pooled": {"threshold": pooled_res["threshold"], "recall": p_recall, "specificity": p_spec,
                           "met_target": bool(p_recall >= target_recall - 1e-9)},
                "specificity_delta_group_minus_pooled": g_spec - p_spec,
            })

        by_pop = {}
        for pop in sorted(groups):
            pop_rows = [r for r in rows if r["superpopulation"] == pop]
            by_pop[pop] = {
                "n": len(pop_rows),
                "group_mean_specificity": float(np.mean([r["group_conditional"]["specificity"] for r in pop_rows])),
                "pooled_mean_specificity": float(np.mean([r["pooled"]["specificity"] for r in pop_rows])),
                "mean_specificity_delta": float(np.mean([r["specificity_delta_group_minus_pooled"] for r in pop_rows])),
                "group_met_target": sum(r["group_conditional"]["met_target"] for r in pop_rows),
                "pooled_met_target": sum(r["pooled"]["met_target"] for r in pop_rows),
            }

        out["by_model"][model] = {
            "rows": rows,
            "by_superpopulation": by_pop,
            "overall_mean_specificity_delta": float(np.mean([r["specificity_delta_group_minus_pooled"] for r in rows])),
            "overall_group_met_target": sum(r["group_conditional"]["met_target"] for r in rows),
            "overall_pooled_met_target": sum(r["pooled"]["met_target"] for r in rows),
        }
    return out


if __name__ == "__main__":
    res = run(TARGET_RECALL)
    print(f"target_recall = {TARGET_RECALL} (feasible for both: group N=5 max=0.833, pooled N=29 max=0.967)\n")
    for model, block in res["by_model"].items():
        print(f"[{model}] overall: group met {block['overall_group_met_target']}/30, "
              f"pooled met {block['overall_pooled_met_target']}/30, "
              f"mean specificity delta (group-pooled) = {block['overall_mean_specificity_delta']:+.4f}")
        for pop, row in block["by_superpopulation"].items():
            print(f"    {pop}: group_spec={row['group_mean_specificity']:.4f} "
                  f"pooled_spec={row['pooled_mean_specificity']:.4f} "
                  f"delta={row['mean_specificity_delta']:+.4f}  "
                  f"(group met {row['group_met_target']}/{row['n']}, pooled met {row['pooled_met_target']}/{row['n']})")
        print()

    out_path = RESULTS / "group_vs_pooled_same_heldout.json"
    out_path.write_text(json.dumps(res, indent=2))
    print(f"wrote {out_path}")
