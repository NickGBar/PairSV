#!/usr/bin/env python3
"""H1: single-split Conformal Risk Control (VB-CRC formula, Angelopoulos et
al. 2022/2024; verified against Cohen et al. 2024 eq. 10-11, see
PAPER2_RESEARCH_PLAN.md §9.0b) applied directly to all people in one data
source -- no K-fold retraining, because the underlying classifier is frozen
and does not need training data.

Loss per person at probability threshold tau:
    ell(person, tau) = 1 - recall(person, tau)
      = 1 - (fraction of that person's true positives with probability >= tau)
bounded in [0, 1] (b=0, B=1), non-decreasing in tau -- exactly the
false-negative-rate worked example in Angelopoulos et al., with "person"
playing the role of "example x" and that person's true-positive candidates
playing the role of the true label set.

Risk estimate (Cohen et al. eq. 10, VB-CRC, our Dtr is vacuous so the whole
data source plays the role of Dval):
    Rhat(tau) = 1/(N+1) * ( sum_person ell(person, tau) + B )

Threshold (eq. 11, translated from NC-score space to probability-threshold
space -- see PAPER2_RESEARCH_PLAN.md working notes: bigger tau means fewer
candidates kept, so we want the SUP feasible tau, not inf):
    tau* = sup{ tau : Rhat(tau) <= alpha }

Theorem 1 (Cohen et al.) requires N >= B/(alpha-b) - 1, i.e. here N >= 1/alpha
- 1, for the guarantee to be invokable at all. Equivalently:
    max_guaranteed_recall(N) = N / (N + 1)
This is checked and reported explicitly -- if target_recall exceeds
N/(N+1), the procedure is infeasible for every threshold and this script
says so rather than returning a number that looks like it means something.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

RESULTS = Path(__file__).resolve().parent / "results"
MODELS = ("M0", "M2", "M4")
B = 1.0  # max loss (FNR is in [0, 1])


def solve_threshold(pos_probs_by_person: dict[str, np.ndarray], target_recall: float) -> dict:
    N = len(pos_probs_by_person)
    alpha = 1.0 - target_recall
    max_guaranteed_recall = N / (N + 1)

    # candidate thresholds: every distinct probability value across all
    # people's positives (ascending) -- recall(tau) only changes at these points
    all_probs = np.sort(np.unique(np.concatenate(list(pos_probs_by_person.values()))))
    sorted_pos = {p: np.sort(v) for p, v in pos_probs_by_person.items()}

    def risk_at(tau: float) -> float:
        total_loss = 0.0
        for p, pos in sorted_pos.items():
            n = len(pos)
            if n == 0:
                continue
            idx = np.searchsorted(pos, tau, side="left")
            recall = (n - idx) / n
            total_loss += 1.0 - recall
        return (total_loss + B) / (N + 1)

    # Rhat is non-decreasing in tau. Feasible set is (-inf, tau_crit] in
    # NC-score space == [tau_crit, +inf) is INfeasible in probability space
    # ... concretely: find the largest probability threshold tau such that
    # risk_at(tau) <= alpha. Check the most permissive point first.
    risk_at_permissive = risk_at(-np.inf)  # tau = -inf: keep everyone, all recalls = 1
    if risk_at_permissive > alpha:
        return {
            "status": "INFEASIBLE",
            "reason": (
                f"target_recall={target_recall} requires alpha={alpha:.6f} < "
                f"minimum achievable risk {risk_at_permissive:.6f} = B/(N+1) at N={N}. "
                f"max_guaranteed_recall at this N is {max_guaranteed_recall:.6f}. "
                "No threshold satisfies the constraint -- the theorem's own "
                "precondition (N >= B/(alpha-b) - 1) is violated."
            ),
            "N": N,
            "target_recall": target_recall,
            "alpha": alpha,
            "max_guaranteed_recall": max_guaranteed_recall,
            "degenerate_threshold": -np.inf,
            "degenerate_meaning": "accept every candidate (recall=1, specificity=0)",
        }

    # feasible: find sup{tau : risk_at(tau) <= alpha} via linear scan over
    # candidate thresholds (N here is small -- tens, not needing binary search)
    best_tau = -np.inf
    for tau in all_probs:
        if risk_at(tau) <= alpha:
            best_tau = tau
        else:
            break  # risk_at is non-decreasing in tau; once infeasible, stays infeasible
    achieved_risk = risk_at(best_tau)

    return {
        "status": "OK",
        "N": N,
        "target_recall": target_recall,
        "alpha": alpha,
        "max_guaranteed_recall": max_guaranteed_recall,
        "threshold": float(best_tau),
        "achieved_risk_estimate": float(achieved_risk),
        "guarantee_statement": (
            f"E[1 - recall] <= {alpha} in expectation over the randomness of the "
            f"calibration set (N={N} people) and a fresh exchangeable person. "
            "This is an average-case guarantee over hypothetical new people, "
            "NOT a high-probability/PAC statement about recall on one specific "
            "new person (Angelopoulos et al. 2022/2024; Cohen et al. 2024 Theorem 1)."
        ),
        "guarantee_type": "average risk, in expectation",
    }


def run(source_file: Path, source_label: str, target_recall: float) -> dict:
    data = json.loads(source_file.read_text())
    results = {}
    for model in MODELS:
        pos_by_person = {
            person: np.array(rec["pos_probs_sorted"])
            for person, rec in data["models"][model].items()
        }
        results[model] = solve_threshold(pos_by_person, target_recall)
    return {
        "source": source_label,
        "source_file": str(source_file.name),
        "n_people": data["n_people"],
        "target_recall": target_recall,
        "by_model": results,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-recall", type=float, default=0.95)
    args = ap.parse_args()

    out = {}
    for label, fname in [("poc", "person_level_scores__poc.json"), ("cohort", "person_level_scores__cohort.json")]:
        fpath = RESULTS / fname
        if not fpath.exists():
            print(f"SKIP {label}: {fpath} not found (run 01_build_person_level_scores.py first)")
            continue
        out[label] = run(fpath, label, args.target_recall)
        for model, res in out[label]["by_model"].items():
            if res["status"] == "OK":
                print(f"[{label}/{model}] N={res['N']} target={args.target_recall} "
                      f"-> threshold={res['threshold']:.6f} "
                      f"max_guaranteed_recall={res['max_guaranteed_recall']:.4f}")
            else:
                print(f"[{label}/{model}] N={res['N']} target={args.target_recall} "
                      f"-> INFEASIBLE (max_guaranteed_recall={res['max_guaranteed_recall']:.4f})")

    out_path = RESULTS / f"crc_pooled_target{args.target_recall}.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")
