#!/usr/bin/env python3
"""Extract every number destined for manuscript section 15.12 directly from
the frozen cohort artifacts. No value is transcribed by hand anywhere in the
manuscript-integration path: this script reads the authoritative JSONs,
verifies their SHA-256 against the frozen values, and emits the prose-ready
markdown fragment plus a machine-readable sidecar.

Sources (all checksum-verified before use):
  manta_poc/cohort_final_evaluation_report.json   (the one-shot result)
  manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json   (frozen pre-eval state)
  manta_poc/hg002_external/hg002_final_evaluation_report.json      (v5.0q)
  manta_poc/hg002_v0.6_external/hg002_v0.6_final_evaluation_report.json (v0.6)

Usage: python3 extract_cohort_numbers.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ("M0", "M2", "M4")
SUPERPOPS = ("AFR", "AMR", "EAS", "EUR", "SAS")

EXPECTED_SHA = {
    "manta_poc/cohort_final_evaluation_report.json":
        "84f571b617025597b12d1caf55bb0ce3b18b0f021fbc58cf30e6798a0538b3d1",
    "manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json":
        "3a670e207d8f3bb99a695e05c3755349fd934685b0c1ff402cfbf5d771403942",
}


def load_verified(rel: str) -> dict:
    p = ROOT / rel
    raw = p.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if rel in EXPECTED_SHA and got != EXPECTED_SHA[rel]:
        raise SystemExit(f"FATAL: {rel} sha256 {got} != frozen {EXPECTED_SHA[rel]}")
    return json.loads(raw)


def f4(x) -> str:
    return "n/a" if x is None else f"{x:.4f}"


def main() -> None:
    rep = load_verified("manta_poc/cohort_final_evaluation_report.json")
    manifest = load_verified("manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json")

    macro = rep["primary_macro_averaged_over_people"]
    acct = rep["candidate_accounting"]

    # cohort-scale candidate accounting, summed from per-person source records
    total_pass_del = sum(a["total_manta_pass_del"] for a in acct.values())
    total_unknown = sum(a["class_counts"].get("unknown", 0) for a in acct.values())
    total_scored = sum(a["n_labelled_candidates_scored"] for a in acct.values())
    unknown_frac = total_unknown / total_pass_del

    # Extraction failures: taken from the PRE-EVALUATION MANIFEST, which is the
    # authoritative source. The evaluation report's own n_extraction_failures
    # field is known-incorrect (see COHORT_EVALUATION_ERRATUM.md) and is
    # deliberately NOT used here.
    total_extraction_failures = manifest["cohort_totals"]["total_extraction_failures"]
    total_eligible = sum(a["n_eligible_for_extraction"] for a in acct.values())
    extraction_failure_rate = total_extraction_failures / total_eligible

    # accept-all-Manta baseline, macro-averaged over people
    per_person = rep["per_person"]
    samples = rep["samples"]
    base_prev = sum(per_person[s]["accept_all_manta_baseline"]["prevalence"]
                    for s in samples) / len(samples)
    base_f1 = sum(per_person[s]["accept_all_manta_baseline"]["f1"]
                  for s in samples) / len(samples)

    out = {
        "n_people": rep["n_people"],
        "macro": {f: {m: macro[f][m] for m in MODELS} for f in macro},
        "by_superpopulation": rep["by_superpopulation"],
        "totals": {
            "total_manta_pass_del": total_pass_del,
            "total_labelled_scored": total_scored,
            "total_unknown": total_unknown,
            "unknown_fraction": unknown_frac,
            "total_extraction_failures": total_extraction_failures,
            "total_eligible_for_extraction": total_eligible,
            "extraction_failure_rate": extraction_failure_rate,
        },
        "accept_all_baseline_macro": {"prevalence": base_prev, "f1": base_f1},
        "source_sha256": EXPECTED_SHA,
    }
    sidecar = ROOT / "paper" / "cohort_numbers_for_manuscript.json"
    sidecar.write_text(json.dumps(out, indent=2))

    # ---- prose-ready markdown fragment ----
    L = []
    A = L.append
    A("| metric | M0 | M2 | M4 |")
    A("|---|---|---|---|")
    for field, label in [("recall", "Recall @ frozen threshold"),
                         ("specificity", "Specificity"),
                         ("precision", "Precision"),
                         ("f1", "F1"),
                         ("balanced_accuracy", "Balanced accuracy"),
                         ("mcc", "MCC"),
                         ("roc_auc", "ROC-AUC"),
                         ("pr_auc", "PR-AUC"),
                         ("filtered_candidate_rate", "Filtered-candidate rate")]:
        cells = []
        for m in MODELS:
            e = macro[field][m]
            cells.append(f"{f4(e['macro_mean'])} ± {f4(e['macro_sd'])}")
        A(f"| {label} | " + " | ".join(cells) + " |")
    table_main = "\n".join(L)

    L = []
    A = L.append
    A("| superpopulation | metric | M0 | M2 | M4 |")
    A("|---|---|---|---|---|")
    for sp in SUPERPOPS:
        v = rep["by_superpopulation"][sp]["metrics"]
        for metric in ("recall", "specificity"):
            cells = [f"{f4(v[m][metric]['macro_mean'])} ± {f4(v[m][metric]['macro_sd'])}"
                     for m in MODELS]
            A(f"| {sp} (n={rep['by_superpopulation'][sp]['n_people']}) | {metric} | "
              + " | ".join(cells) + " |")
    table_sp = "\n".join(L)

    rng = {m: macro["recall"][m] for m in MODELS}
    range_line = "; ".join(
        f"{m} {f4(rng[m]['min'])}-{f4(rng[m]['max'])}" for m in MODELS)

    frag = ROOT / "paper" / "cohort_15_12_fragment.md"
    frag.write_text(
        f"### Primary (macro-averaged over {rep['n_people']} people)\n\n{table_main}\n\n"
        f"Recall range across people: {range_line}\n\n"
        f"### By superpopulation\n\n{table_sp}\n\n"
        f"### Candidate accounting\n\n"
        f"- Manta PASS DEL: {total_pass_del:,}\n"
        f"- Labelled candidates scored: {total_scored:,}\n"
        f"- Unknown: {total_unknown:,} ({unknown_frac:.1%})\n"
        f"- Extraction failures: {total_extraction_failures} "
        f"({extraction_failure_rate:.4%} of {total_eligible:,} eligible)\n"
        f"- Accept-all-Manta baseline: prevalence {f4(base_prev)}, F1 {f4(base_f1)}\n")

    print(f"verified sources, wrote:\n  {sidecar}\n  {frag}")
    print(f"\nrecall  : " + "  ".join(
        f"{m}={f4(macro['recall'][m]['macro_mean'])}±{f4(macro['recall'][m]['macro_sd'])}"
        for m in MODELS))
    print(f"spec    : " + "  ".join(
        f"{m}={f4(macro['specificity'][m]['macro_mean'])}" for m in MODELS))
    print(f"none reach 0.95 recall: "
          f"{all(macro['recall'][m]['macro_mean'] < 0.95 for m in MODELS)}")
    print(f"M2-M4 recall gap: "
          f"{abs(macro['recall']['M2']['macro_mean'] - macro['recall']['M4']['macro_mean']):.6f}"
          f"  (between-person SD M4 = {f4(macro['recall']['M4']['macro_sd'])})")


if __name__ == "__main__":
    main()
