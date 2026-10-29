#!/usr/bin/env python3
"""Collect every number shown in the progress-report deck from its source file.

No value on a slide is typed by hand. Each block below reads one frozen or
generated artifact; the 30-person cohort report is SHA-256-verified before it
is read, exactly as paper/extract_cohort_numbers.py does for the manuscript.
A handful of cross-checks assert that the extracted values agree with the
numbers already published in the manuscript, so a silently changed source
file stops the build instead of reaching a slide.

Output: presentation/deck_data.json
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "deck_data.json"

COHORT_REPORT = ROOT / "manta_poc/cohort_final_evaluation_report.json"
COHORT_SHA256 = "84f571b617025597b12d1caf55bb0ce3b18b0f021fbc58cf30e6798a0538b3d1"
HG002_REPORT = ROOT / "manta_poc/hg002_external/hg002_final_evaluation_report.json"
PHASE_F = ROOT / "manta_poc/truvari_gate2/phase_f"
TRAIN40 = ROOT / "reports/train40"
TEST_EVAL = ROOT / "reports/test_evaluation"
P2 = ROOT / "paper2_conformal/results"
MODELS = ("M0", "M2", "M4")


def rows(path: Path) -> list[dict]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def close(a: float, b: float, tol: float) -> None:
    if abs(a - b) > tol:
        raise SystemExit(f"cross-check failed: {a} vs published {b} (tol {tol})")


def article1() -> dict:
    raw = COHORT_REPORT.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != COHORT_SHA256:
        raise SystemExit(f"cohort report sha256 {got} != frozen {COHORT_SHA256}")
    rep = json.loads(raw)
    macro = rep["primary_macro_averaged_over_people"]

    cohort = {m: {
        "recall": macro["recall"][m]["macro_mean"],
        "recall_sd": macro["recall"][m]["macro_sd"],
        "recall_min": macro["recall"][m]["min"],
        "recall_max": macro["recall"][m]["max"],
        "specificity": macro["specificity"][m]["macro_mean"],
    } for m in MODELS}
    close(cohort["M0"]["recall"], 0.9453, 5e-5)
    close(cohort["M2"]["recall"], 0.9473, 5e-5)
    close(cohort["M4"]["recall"], 0.9471, 5e-5)

    diff = abs(cohort["M2"]["recall"] - cohort["M4"]["recall"])
    close(diff, 0.000176, 5e-7)
    sd = cohort["M4"]["recall_sd"]            # the 0.0062 quoted in the manuscript

    superpop = {}
    for pop, block in rep["by_superpopulation"].items():
        superpop[pop] = {m: {"recall": block["metrics"][m]["recall"]["macro_mean"],
                             "specificity": block["metrics"][m]["specificity"]["macro_mean"]}
                         for m in MODELS}

    pop_of = {p: pop for pop, b in rep["by_superpopulation"].items() for p in b["people"]}
    per_person = sorted(
        ({"person": p, "superpopulation": pop_of[p],
          "M2": rep["per_person"][p]["M2"]["primary"]["recall"],
          "M4": rep["per_person"][p]["M4"]["primary"]["recall"]}
         for p in rep["per_person"]),
        key=lambda r: r["M2"])

    cn = json.loads((ROOT / "paper/cohort_numbers_for_manuscript.json").read_text())
    prevalence = cn["accept_all_baseline_macro"]["prevalence"]

    hg = json.loads(HG002_REPORT.read_text())
    hg002 = {m: {k: hg["results_by_model"][m]["primary_at_frozen_threshold"][k]
                 for k in ("recall", "specificity")} for m in MODELS}
    close(hg002["M2"]["recall"], 0.9551, 5e-5)
    close(hg002["M4"]["recall"], 0.9327, 5e-5)

    # Manta's own end-to-end recall is not stored in the evaluation report (that
    # field is a text pointer); it lives in the Truvari summary it points to.
    tv = json.loads((HG002_REPORT.parent / "truvari_v5.0q_primary_summary.json").read_text())
    if (tv["TP-base"], tv["base cnt"]) != (4333, 10143):
        raise SystemExit(f"Truvari summary changed: {tv['TP-base']}/{tv['base cnt']} != 4333/10143")

    # controlled benchmark: internal-test bootstrap, zero-ablation, retrained removal
    boot = {r["comparison"]: r for r in rows(TEST_EVAL / "candidate_cluster_bootstrap.csv")}
    bootstrap = {k: {"delta_f1": float(boot[k]["f1_difference_mean"]),
                     "ci_low": float(boot[k]["f1_ci_low"]),
                     "ci_high": float(boot[k]["f1_ci_high"])}
                 for k in ("M4 - M0", "M2 - M0", "M4 - M2")}

    abl = {r["intervention"]: float(r["f1_change_mean"]) for r in rows(TRAIN40 / "ablations_aggregate.csv")}
    agg = {r["model"]: float(r["f1_mean"]) for r in rows(TRAIN40 / "three_seed_aggregate.csv")}
    branches = [("candidate", "Последовательность ДНК", "candidate_zero", "M4_NO_CANDIDATE"),
                ("read", "Прочтения человека", "read_zero", "M4_NO_READ"),
                ("scalar", "17 числовых признаков", "scalar_zero", "M4_NO_SCALAR")]
    # Cross-check the source values against the manuscript's §10.3 table, which
    # prints them to 5 decimals. The ratios are then computed from the unrounded
    # source values. Note: the manuscript's read-branch ratio "10.4x" was derived
    # from the rounded table (0.00751 / 0.00072 = 10.43); from source it is 10.498,
    # i.e. 10.5x. The deck shows the source-derived value.
    published = {"candidate": (0.00543, 0.00107), "read": (0.00751, 0.00072), "scalar": (0.01002, 0.00151)}
    ablation = []
    for key, label, zero_key, retrained_key in branches:
        zero = abl[zero_key]
        retrained = agg[retrained_key] - agg["M4"]
        close(-zero, published[key][0], 5e-6)
        close(-retrained, published[key][1], 5e-6)
        ablation.append({"branch": key, "label": label,
                         "zero_drop": -zero, "retrained_drop": -retrained,
                         "ratio": zero / retrained})

    # 5-person development study: frozen controlled-benchmark threshold vs LOPO recalibration
    frozen = rows(PHASE_F / "phaseF_1_macro_average_PRIMARY.csv")
    frozen_spec = [float(r["specificity_macro_mean"]) for r in frozen]
    frozen_auc = [float(r["roc_auc_macro_mean"]) for r in frozen]
    lopo = [r for r in rows(PHASE_F / "phaseF_5_lopo_aggregate.csv") if float(r["target_recall"]) == 0.95]
    lopo_spec = [float(r["specificity_macro_mean"]) for r in lopo]
    lopo_worst_recall = min(float(r["actual_recall_min"]) for r in lopo)

    return {
        "cohort": cohort,
        "cohort_m2_m4_recall_diff": diff,
        "cohort_between_person_sd": sd,
        "cohort_diff_vs_sd_ratio": sd / diff,
        "cohort_prevalence": prevalence,
        "cohort_superpopulation": superpop,
        "cohort_per_person_sorted_by_M2": per_person,
        "hg002_v5q": hg002,
        "hg002_manta_own_recall": tv["recall"],
        "internal_test_bootstrap": bootstrap,
        "ablation": ablation,
        "poc_frozen_threshold_specificity_range": [min(frozen_spec), max(frozen_spec)],
        "poc_frozen_threshold_roc_auc_range": [min(frozen_auc), max(frozen_auc)],
        "poc_lopo_specificity_range": [min(lopo_spec), max(lopo_spec)],
        "poc_lopo_worst_fold_recall": lopo_worst_recall,
    }


def article2() -> dict:
    cmp = json.loads((P2 / "compare_vs_heuristic_lopo_cohort.json").read_text())
    lopo30 = {}
    for m in MODELS:
        b = cmp["by_model"][m]
        lopo30[m] = {
            "heuristic_met": sum(f["old_heuristic"]["met_target"] for f in b["folds"]),
            "crc_met": sum(f["new_crc"]["met_target"] for f in b["folds"]),
            "heuristic_met_flags": [f["old_heuristic"]["met_target"] for f in b["folds"]],
            "heuristic_specificity": b["summary"]["old_heuristic_mean_specificity"],
            "crc_specificity": b["summary"]["new_crc_mean_specificity"],
            "crc_recall": b["summary"]["new_crc_mean_recall"],
        }

    grp = json.loads((P2 / "crc_group_conditional_target0.95.json").read_text())
    infeasible = sum(r["status"] == "INFEASIBLE"
                     for block in grp["by_superpopulation"].values()
                     for r in block["by_model"].values())
    total = sum(len(block["by_model"]) for block in grp["by_superpopulation"].values())

    gvp = json.loads((P2 / "group_vs_pooled_same_heldout.json").read_text())
    group_vs_pooled = {m: {
        "overall_delta": gvp["by_model"][m]["overall_mean_specificity_delta"],
        "by_superpopulation": {pop: {"group": r["group_mean_specificity"], "pooled": r["pooled_mean_specificity"]}
                               for pop, r in gvp["by_model"][m]["by_superpopulation"].items()},
    } for m in MODELS}

    mrc = json.loads((P2 / "matched_reliability_control.json").read_text())
    matched = {}
    for m in MODELS:
        b = mrc["by_model"][m]
        matched[m] = {
            "crc": {k: b["crc_at_0.95"][k] for k in ("mean_recall", "mean_specificity", "mean_loss",
                                                     "n_folds_at_or_above_eval_target")},
            "sweep": [{k: r[k] for k in ("nominal_target", "mean_recall", "mean_specificity",
                                         "n_folds_at_or_above_eval_target")} for r in b["heuristic_sweep"]],
            "matched": {k: b["heuristic_matched_reliability"][k]
                        for k in ("nominal_target", "mean_recall", "mean_specificity")},
        }

    alpha, n_calib, B = 0.05, 29, 1.0
    predicted_loss = (alpha * (n_calib + 1) - B) / n_calib
    for m in MODELS:
        close(matched[m]["crc"]["mean_loss"], predicted_loss, 1e-4)

    return {
        "lopo30": lopo30,
        "group_conditional_infeasible": infeasible,
        "group_conditional_total": total,
        "group_vs_pooled_target0.75": group_vs_pooled,
        "matched_reliability": matched,
        "effective_recall_predicted": 1 - predicted_loss,
        "dummy_share_of_budget": (B / (n_calib + 1)) / alpha,
        "max_guaranteed_recall_curve": [{"N": n, "value": n / (n + 1)} for n in range(1, 41)],
    }


if __name__ == "__main__":
    data = {"article1": article1(), "article2": article2(),
            "cohort_report_sha256": COHORT_SHA256}
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"wrote {OUT}")
    a1, a2 = data["article1"], data["article2"]
    print(f"  cohort recall M0/M2/M4: {[round(a1['cohort'][m]['recall'], 4) for m in MODELS]}")
    print(f"  M2-M4 diff {a1['cohort_m2_m4_recall_diff']:.6f}, sd {a1['cohort_between_person_sd']:.4f}, "
          f"ratio {a1['cohort_diff_vs_sd_ratio']:.1f}")
    print(f"  ablation ratios: {[round(r['ratio'], 1) for r in a1['ablation']]}")
    print(f"  POC frozen spec {a1['poc_frozen_threshold_specificity_range']}, "
          f"LOPO spec {a1['poc_lopo_specificity_range']}")
    print(f"  heuristic met: {[a2['lopo30'][m]['heuristic_met'] for m in MODELS]}, "
          f"CRC met: {[a2['lopo30'][m]['crc_met'] for m in MODELS]}")
    print(f"  group-conditional infeasible {a2['group_conditional_infeasible']}/{a2['group_conditional_total']}")
    print(f"  effective recall predicted {a2['effective_recall_predicted']:.5f}, "
          f"dummy share {a2['dummy_share_of_budget']:.0%}")
