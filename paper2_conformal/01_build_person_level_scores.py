#!/usr/bin/env python3
"""Build per-person, per-model sorted probability arrays for conformal risk
control. Person is the exchangeable unit (PAPER2_RESEARCH_PLAN.md §4) --
candidates within one person are not independent, so nonconformity/loss is
computed per person, not per candidate.

Two sources, kept separate (different SHA256-verified provenance, never
merged silently):
  - POC / LOPO: manta_poc/truvari_gate2/phase_f/phaseF_merged_all.pkl (5 people)
  - Cohort: paper2_conformal/raw_cohort_predictions/<PERSON>/*_ensembled_LABEL_BLIND.csv (30 people)

Output per source: JSON with, for each model (M0/M2/M4) and person, the
sorted array of ensembled probabilities for known positives and known
negatives. This is sufficient to compute recall(person, lambda) or
specificity(person, lambda) at any threshold via searchsorted -- no need to
recompute per-candidate predictions downstream.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "results"

POC_PKL = ROOT / "manta_poc/truvari_gate2/phase_f/phaseF_merged_all.pkl"
POC_PKL_SHA256 = "844d8f8cd2e35c681e52434a12d2c758e02a791561e63183d32e3d518215c2da"

COHORT_DIR = Path(__file__).resolve().parent / "raw_cohort_predictions"
COHORT_REPORT = ROOT / "manta_poc/cohort_final_evaluation_report.json"

MODELS = ("M0", "M2", "M4")


def verify_sha256(path: Path, expected: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(
            f"FATAL: {path} sha256 mismatch\n  expected {expected}\n  actual   {actual}\n"
            "Refusing to read unverified source data."
        )


def person_scores_from_labeled(labeled: pd.DataFrame) -> dict:
    """labeled: columns person, model, candidate_id, label, probability
    (already ensembled across seeds -- one row per candidate per model)."""
    out = {m: {} for m in MODELS}
    for model in MODELS:
        sub = labeled[labeled.model == model]
        for person, g in sub.groupby("person"):
            pos = np.sort(g.loc[g.label == 1, "probability"].to_numpy())
            neg = np.sort(g.loc[g.label == 0, "probability"].to_numpy())
            out[model][person] = {
                "n_pos": int(len(pos)),
                "n_neg": int(len(neg)),
                "pos_probs_sorted": pos.round(8).tolist(),
                "neg_probs_sorted": neg.round(8).tolist(),
            }
    return out


def build_poc() -> None:
    verify_sha256(POC_PKL, POC_PKL_SHA256)
    df = pd.read_pickle(POC_PKL)
    df = df[df["class"].isin(["positive", "known_negative"])].copy()
    ens = (
        df.groupby(["person", "model", "candidate_id", "label"], as_index=False)
        .agg(probability=("probability", "mean"))
    )
    scores = person_scores_from_labeled(ens)
    payload = {
        "source": "5 POC / LOPO",
        "source_file": str(POC_PKL.relative_to(ROOT)),
        "source_sha256": POC_PKL_SHA256,
        "ensembling": "mean probability across 3 frozen seeds (20260720/21/22), per (person, model, candidate_id)",
        "n_people": len(next(iter(scores.values()))),
        "people": sorted({p for m in scores.values() for p in m}),
        "models": scores,
    }
    out_path = OUT / "person_level_scores__poc.json"
    out_path.write_text(json.dumps(payload, indent=2))
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"wrote {out_path} ({len(payload['people'])} people), sha256 {digest}")


def build_cohort() -> None:
    if not COHORT_REPORT.exists():
        print(f"SKIP cohort: {COHORT_REPORT} not found")
        return
    report = json.loads(COHORT_REPORT.read_text())
    recorded_hashes = report["prediction_file_sha256"]
    superpop_of = {}
    for pop, block in report["by_superpopulation"].items():
        for person in block["people"]:
            superpop_of[person] = pop

    # Predictions are LABEL_BLIND by design (matches the frozen one-shot
    # evaluation protocol) -- ground truth lives in a separate per-person
    # gate3_candidate_manifest.json, joined on candidate_id. That manifest
    # has no recorded SHA256 anywhere in the frozen artifacts (unlike the
    # predictions CSVs), so its integrity is NOT cryptographically verified
    # here -- only its co-location with the verified prediction files. This
    # is disclosed, not hidden.
    rows = []
    for person, hashes in recorded_hashes.items():
        pred_path = COHORT_DIR / person / f"{person}_gate3_predictions_ensembled_LABEL_BLIND.csv"
        manifest_path = COHORT_DIR / person / "gate3_candidate_manifest.json"
        if not pred_path.exists():
            raise SystemExit(f"FATAL: missing cohort prediction file for {person}: {pred_path}")
        if not manifest_path.exists():
            raise SystemExit(f"FATAL: missing candidate manifest (ground truth) for {person}: {manifest_path}")
        verify_sha256(pred_path, hashes["ensembled"])

        preds = pd.read_csv(pred_path)
        manifest = pd.DataFrame(json.loads(manifest_path.read_text()))
        expected_cols = {"candidate_id", "label", "class"}
        missing = expected_cols - set(manifest.columns)
        if missing:
            raise SystemExit(
                f"FATAL: {manifest_path} missing expected columns {missing}; "
                f"got {sorted(manifest.columns)}. Not guessing a schema."
            )
        merged = preds.merge(
            manifest[["candidate_id", "label", "class"]], on="candidate_id", how="left", validate="many_to_one"
        )
        if merged["class"].isna().any():
            n_missing = int(merged["class"].isna().sum())
            raise SystemExit(
                f"FATAL: {n_missing} candidates for {person} had no matching manifest entry -- "
                "prediction/manifest candidate_id sets disagree, refusing to silently drop rows."
            )
        merged["person"] = person
        rows.append(merged)
    all_df = pd.concat(rows, ignore_index=True)

    labeled = all_df[all_df["class"].isin(["positive", "known_negative"])].copy()
    scores = person_scores_from_labeled(labeled)
    for model in MODELS:
        for person in scores[model]:
            scores[model][person]["superpopulation"] = superpop_of.get(person, "UNKNOWN")

    payload = {
        "source": "30-person cohort",
        "source_files": f"{len(recorded_hashes)} per-person ensembled prediction CSVs, SHA256-verified against {COHORT_REPORT.relative_to(ROOT)}",
        "n_people": len(recorded_hashes),
        "people": sorted(recorded_hashes),
        "superpopulation_of_person": superpop_of,
        "models": scores,
    }
    out_path = OUT / "person_level_scores__cohort.json"
    out_path.write_text(json.dumps(payload, indent=2))
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"wrote {out_path} ({len(payload['people'])} people), sha256 {digest}")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    build_poc()
    build_cohort()
