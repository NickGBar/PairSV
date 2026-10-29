#!/usr/bin/env python3
"""Small-n stress test -- the headline H2 finding (PAPER2_RESEARCH_PLAN.md
§3a, §9.0b, §10.2), characterized as a curve rather than a single point.

Two genuinely different things are computed here, kept separate on purpose:

  (A) Analytical feasibility curve: max_guaranteed_recall(N) = N/(N+1).
      Pure arithmetic -- does not touch any data at all, cannot "leak"
      anything about the cohort, safe to compute for any N.

  (B) Empirical efficiency curve: how tight (specificity) is the resulting
      threshold as N shrinks, at a FIXED feasible target_recall. This uses
      ONLY the 5 POC people (already "spent" as Article-1 development data,
      per PAPER2_RESEARCH_PLAN.md §7's discipline -- LOPO/POC data is free
      to explore repeatedly; the cohort's real superpopulation groups are
      not, beyond the one pass each already run in
      02_crc_pooled.py/03_crc_group_conditional.py). Every subset of size k
      from the 5 POC people is enumerated exhaustively (C(5,k) is small --
      no bootstrap sampling noise to worry about).

  Cohort reference points: the ALREADY-COMPUTED max_guaranteed_recall for
  N=6 (per superpopulation) and N=30 (pooled) -- from results already
  written by 02/03 -- are overlaid on curve (A) only, since that number is
  data-independent (depends only on N). No NEW empirical (data-dependent)
  specificity number is computed for the cohort here. Extending curve (B)
  to the cohort is deliberately deferred to Phase 4 / §7, not silently done.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
MODELS = ("M0", "M2", "M4")
EMPIRICAL_TARGET_RECALL = 0.65  # feasible for every k >= 2 (2/3 = 0.667 > 0.65)


def _import(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


crc_pooled = _import(HERE / "02_crc_pooled.py", "crc_pooled")
solve_threshold = crc_pooled.solve_threshold


def analytical_curve(n_max: int = 40) -> list[dict]:
    return [{"N": n, "max_guaranteed_recall": n / (n + 1)} for n in range(1, n_max + 1)]


def in_sample_specificity(pos_by_person, neg_by_person, people_subset, threshold) -> float:
    all_neg = np.concatenate([neg_by_person[p] for p in people_subset])
    if len(all_neg) == 0:
        return float("nan")
    return float((all_neg < threshold).sum() / len(all_neg))


def empirical_poc_curve(target_recall: float) -> dict:
    data = json.loads((RESULTS / "person_level_scores__poc.json").read_text())
    people = data["people"]
    out = {"target_recall": target_recall, "by_model": {}}

    for model in MODELS:
        pos_by_person = {p: np.array(data["models"][model][p]["pos_probs_sorted"]) for p in people}
        neg_by_person = {p: np.array(data["models"][model][p]["neg_probs_sorted"]) for p in people}

        by_k = {}
        for k in range(2, len(people) + 1):
            subset_results = []
            for subset in itertools.combinations(people, k):
                sub_pos = {p: pos_by_person[p] for p in subset}
                res = solve_threshold(sub_pos, target_recall)
                if res["status"] != "OK":
                    subset_results.append({"subset": subset, "feasible": False})
                    continue
                spec = in_sample_specificity(pos_by_person, neg_by_person, subset, res["threshold"])
                subset_results.append({
                    "subset": subset,
                    "feasible": True,
                    "threshold": res["threshold"],
                    "in_sample_specificity": spec,
                })
            feasible_specs = [r["in_sample_specificity"] for r in subset_results if r["feasible"]]
            by_k[k] = {
                "n_subsets": len(subset_results),
                "n_feasible": len(feasible_specs),
                "max_guaranteed_recall": k / (k + 1),
                "mean_in_sample_specificity": float(np.mean(feasible_specs)) if feasible_specs else None,
                "min_in_sample_specificity": float(np.min(feasible_specs)) if feasible_specs else None,
                "max_in_sample_specificity": float(np.max(feasible_specs)) if feasible_specs else None,
            }
        out["by_model"][model] = by_k
    return out


def cohort_reference_points() -> dict:
    """Reuse ALREADY-COMPUTED max_guaranteed_recall values from 02/03's
    outputs (data-independent, depends only on N) -- no new cohort access."""
    ref = {}
    pooled_path = RESULTS / "crc_pooled_target0.95.json"
    group_path = RESULTS / "crc_group_conditional_target0.95.json"
    if pooled_path.exists():
        pooled = json.loads(pooled_path.read_text())
        if "cohort" in pooled:
            n = pooled["cohort"]["n_people"]
            ref["cohort_pooled"] = {"N": n, "max_guaranteed_recall": n / (n + 1),
                                     "source": "already computed by 02_crc_pooled.py, reused not recomputed"}
    if group_path.exists():
        group = json.loads(group_path.read_text())
        ref["cohort_by_superpopulation"] = {
            pop: {"N": block["n_people"], "max_guaranteed_recall": block["n_people"] / (block["n_people"] + 1)}
            for pop, block in group["by_superpopulation"].items()
        }
        ref["_note"] = "reused from 03_crc_group_conditional.py output, no new cohort computation performed here"
    return ref


if __name__ == "__main__":
    curve = analytical_curve()
    print("Analytical: max_guaranteed_recall = N/(N+1)")
    for row in curve:
        if row["N"] in (2, 4, 5, 6, 10, 18, 19, 20, 30, 35, 40):
            print(f"  N={row['N']:>3d}  max_guaranteed_recall={row['max_guaranteed_recall']:.4f}")

    print(f"\nEmpirical POC curve (target_recall={EMPIRICAL_TARGET_RECALL}, exhaustive subsets, in-sample specificity):")
    emp = empirical_poc_curve(EMPIRICAL_TARGET_RECALL)
    for model, by_k in emp["by_model"].items():
        print(f"\n[{model}]")
        for k, row in sorted(by_k.items()):
            print(f"  k={k}  n_subsets={row['n_subsets']}  n_feasible={row['n_feasible']}  "
                  f"mean_spec={row['mean_in_sample_specificity']}  "
                  f"range=[{row['min_in_sample_specificity']}, {row['max_in_sample_specificity']}]")

    ref = cohort_reference_points()
    print("\nCohort reference points (reused, not recomputed):")
    print(json.dumps(ref, indent=2))

    out = {"analytical_curve": curve, "empirical_poc_curve": emp, "cohort_reference_points": ref}
    out_path = RESULTS / "small_n_stress_test.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")
