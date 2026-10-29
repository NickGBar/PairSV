#!/usr/bin/env python3
"""H2: the same VB-CRC formula as 02_crc_pooled.py (same theorem, same
proof -- within-group exchangeability is enough), applied separately within
each real superpopulation group in the cohort (n=6 each). Not a different
algorithm -- see PAPER2_RESEARCH_PLAN.md §9.0b. Reports
max_guaranteed_recall = N_group/(N_group+1) explicitly for every group and
does not hide the degenerate/infeasible case.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import importlib.util

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
MODELS = ("M0", "M2", "M4")

spec = importlib.util.spec_from_file_location("crc_pooled", HERE / "02_crc_pooled.py")
crc_pooled = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crc_pooled)
solve_threshold = crc_pooled.solve_threshold


def run(target_recall: float) -> dict:
    fpath = RESULTS / "person_level_scores__cohort.json"
    data = json.loads(fpath.read_text())
    superpop_of = data["superpopulation_of_person"]

    groups = defaultdict(list)
    for person in data["people"]:
        groups[superpop_of[person]].append(person)

    out = {"target_recall": target_recall, "by_superpopulation": {}}
    for pop, people in sorted(groups.items()):
        out["by_superpopulation"][pop] = {"n_people": len(people), "people": sorted(people), "by_model": {}}
        for model in MODELS:
            pos_by_person = {
                p: np.array(data["models"][model][p]["pos_probs_sorted"]) for p in people
            }
            res = solve_threshold(pos_by_person, target_recall)
            out["by_superpopulation"][pop]["by_model"][model] = res
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-recall", type=float, default=0.95)
    args = ap.parse_args()

    result = run(args.target_recall)
    print(f"target_recall = {args.target_recall}\n")
    for pop, block in result["by_superpopulation"].items():
        n = block["n_people"]
        max_g = n / (n + 1)
        print(f"=== {pop} (n={n}, max_guaranteed_recall={max_g:.4f}) ===")
        for model, res in block["by_model"].items():
            if res["status"] == "OK":
                print(f"  {model}: threshold={res['threshold']:.6f}")
            else:
                print(f"  {model}: INFEASIBLE -- {res['reason']}")
        print()

    out_path = RESULTS / f"crc_group_conditional_target{args.target_recall}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"wrote {out_path}")
