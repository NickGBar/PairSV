"""Hash the label-blind test predictions BEFORE any label is ever joined to them.

This is a hard procedural gate, not just a convention: evaluate_test_predictions.py
refuses to run until reports/test_evaluation/frozen_prediction_hashes.json exists.
Run this immediately after retrieving pairsv_test_predictions_LABEL_BLIND.csv from
the inference kernel, and before opening or reading the manifest's label column
for test rows.
"""
import hashlib, json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "kaggle/deepsv-ms-test-inference/output-v1/pairsv_test_predictions_LABEL_BLIND.csv"
OUT = ROOT / "reports" / "test_evaluation"
OUT.mkdir(parents=True, exist_ok=True)


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


if __name__ == "__main__":
    if not PRED.exists():
        raise SystemExit(f"{PRED} not found -- retrieve the inference kernel output first")

    df = pd.read_csv(PRED)
    forbidden = {"label", "genotype", "negative_type"} & set(df.columns)
    if forbidden:
        raise SystemExit(f"REFUSING TO FREEZE: predictions file contains label-conditioned column(s) {forbidden}")

    record = {
        "file": str(PRED.relative_to(ROOT)),
        "sha256": sha256_file(PRED),
        "n_rows": len(df),
        "n_models": int(df.model.nunique()),
        "n_seeds": int(df.seed.nunique()),
        "models": sorted(df.model.unique().tolist()),
        "seeds": sorted(df.seed.unique().tolist()),
        "columns": list(df.columns),
        "label_blind_verified": True,
    }
    json.dump(record, open(OUT / "frozen_prediction_hashes.json", "w"), indent=1)
    print(json.dumps(record, indent=1))
    print(f"\nFROZEN. SHA-256: {record['sha256']}")
    print("Only now is it safe to run evaluate_test_predictions.py.")
