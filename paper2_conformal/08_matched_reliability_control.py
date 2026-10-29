#!/usr/bin/env python3
"""The control that decides whether §10.6's headline survives review.

§10.6 compared both procedures at the same NOMINAL target (0.95) and found
CRC reliable (30/30 folds at or above target) where the heuristic is not
(15-18/30), at roughly a third of the specificity. But CRC also overshoots:
its mean held-out recall is 0.983, not 0.950. So the comparison confounds
two things -- "CRC is better calibrated" and "CRC is simply more
conservative, and conservatism costs specificity for anyone".

The obvious objection: give the old heuristic a higher nominal target until
it too reaches 30/30, then compare specificity at MATCHED RELIABILITY. If
the heuristic then matches or beats CRC, the contribution is not efficiency
-- it is that CRC reaches that operating point by construction, with a
stated guarantee, instead of by trial and error against the held-out data
(which is itself a form of tuning on the test set, and not available to
someone deploying on a new population).

This script sweeps the heuristic's nominal target over a grid, runs the same
full 30-person leave-one-person-out protocol at each, and reports the
specificity each procedure achieves at matched reliability and at matched
mean recall.
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
EVAL_TARGET = 0.95            # the recall level a fold is judged against
HEURISTIC_GRID = [0.95, 0.96, 0.97, 0.975, 0.98, 0.985, 0.99, 0.995]


def _import(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


phase_f = _import(ROOT / "manta_poc/truvari_gate2/phase_f_analysis.py", "phase_f_analysis")
crc_pooled = _import(HERE / "02_crc_pooled.py", "crc_pooled")


def recall_and_specificity(pos, neg, threshold):
    recall = float((pos >= threshold).sum() / len(pos)) if len(pos) else float("nan")
    specificity = float((neg < threshold).sum() / len(neg)) if len(neg) else float("nan")
    return recall, specificity


def lopo(pos_by_person, neg_by_person, people, select_threshold):
    """Run full leave-one-person-out with a supplied threshold-selection rule."""
    recalls, specs = [], []
    for held_out in people:
        calib = [p for p in people if p != held_out]
        tau = select_threshold(calib, pos_by_person)
        r, s = recall_and_specificity(pos_by_person[held_out], neg_by_person[held_out], tau)
        recalls.append(r); specs.append(s)
    recalls, specs = np.array(recalls), np.array(specs)
    return {
        "mean_recall": float(recalls.mean()),
        "mean_specificity": float(specs.mean()),
        "n_folds_at_or_above_eval_target": int((recalls >= EVAL_TARGET - 1e-9).sum()),
        "n_folds": len(people),
        "mean_loss": float((1.0 - recalls).mean()),   # the quantity CRC claims to bound
    }


def run() -> dict:
    data = json.loads((RESULTS / "person_level_scores__cohort.json").read_text())
    people = data["people"]
    out = {"eval_target": EVAL_TARGET, "by_model": {}}

    for model in MODELS:
        pos_by_person = {p: np.array(data["models"][model][p]["pos_probs_sorted"]) for p in people}
        neg_by_person = {p: np.array(data["models"][model][p]["neg_probs_sorted"]) for p in people}

        # CRC at the honest nominal target of 0.95
        def crc_rule(calib, pos, _t=EVAL_TARGET):
            res = crc_pooled.solve_threshold({p: pos[p] for p in calib}, _t)
            return res["threshold"] if res["status"] == "OK" else -np.inf

        crc = lopo(pos_by_person, neg_by_person, people, crc_rule)

        sweep = []
        for nominal in HEURISTIC_GRID:
            def heur_rule(calib, pos, _t=nominal):
                pooled = np.concatenate([pos[p] for p in calib])
                return phase_f.select_threshold_for_recall(pooled, _t)
            row = lopo(pos_by_person, neg_by_person, people, heur_rule)
            row["nominal_target"] = nominal
            sweep.append(row)

        # cheapest heuristic setting that matches CRC's reliability
        matched = next((r for r in sweep
                        if r["n_folds_at_or_above_eval_target"] >= crc["n_folds_at_or_above_eval_target"]),
                       None)
        # heuristic setting whose mean recall is closest to CRC's
        closest = min(sweep, key=lambda r: abs(r["mean_recall"] - crc["mean_recall"]))

        out["by_model"][model] = {
            "crc_at_0.95": crc,
            "heuristic_sweep": sweep,
            "heuristic_matched_reliability": matched,
            "heuristic_closest_mean_recall": closest,
        }
    return out


if __name__ == "__main__":
    res = run()
    for model, b in res["by_model"].items():
        c = b["crc_at_0.95"]
        print(f"\n===== {model} =====")
        print(f"CRC (nominal 0.95): reliability {c['n_folds_at_or_above_eval_target']}/30, "
              f"mean recall {c['mean_recall']:.4f}, mean specificity {c['mean_specificity']:.4f}, "
              f"mean loss {c['mean_loss']:.4f}")
        print(" heuristic sweep:")
        for r in b["heuristic_sweep"]:
            print(f"   nominal {r['nominal_target']:.3f}: reliability {r['n_folds_at_or_above_eval_target']:>2}/30, "
                  f"mean recall {r['mean_recall']:.4f}, mean specificity {r['mean_specificity']:.4f}")
        m = b["heuristic_matched_reliability"]
        if m:
            d = m["mean_specificity"] - c["mean_specificity"]
            print(f" -> matched reliability at nominal {m['nominal_target']:.3f}: "
                  f"specificity {m['mean_specificity']:.4f} vs CRC {c['mean_specificity']:.4f} "
                  f"({d:+.4f} for the heuristic)")
        else:
            print(" -> no heuristic setting on the grid reaches CRC's reliability")

    out_path = RESULTS / "matched_reliability_control.json"
    out_path.write_text(json.dumps(res, indent=2))
    print(f"\nwrote {out_path}")
