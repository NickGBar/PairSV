#!/usr/bin/env python3
"""HG002 v0.6 (SECONDARY/sensitivity) gate-3 scoring. Identical logic to
hg002_score_ensemble.py -- same frozen checkpoints, same normalization, same
frozen deployment thresholds -- only the input shard/embedding paths differ
(v0.6/hs37d5 instead of v5.0q/GRCh38). Label-blind; predictions SHA-256
hashed before any label is loaded.

Usage: python3 hg002_v0.6_score_ensemble.py
"""
from __future__ import annotations

import hashlib
import json

import h5py
import numpy as np
import pandas as pd
import torch

import sys
sys.path.insert(0, "/scratch/igorno-deepsv_poc/pairsv_parity")
from deepsv.models.pairsv import PairSV
from deepsv.multisample.dataset import ScalarNormalizer

from pathlib import Path

WD = Path("/scratch/igorno-deepsv_poc/hg002_v0.6_external")
PAIRSV_ROOT = Path("/scratch/igorno-deepsv_poc/pairsv_parity")
CKPT_ROOT = PAIRSV_ROOT / "kaggle"
SEEDS = (20260720, 20260721, 20260722)
SEED_DIR = {20260720: "deepsv-ms-train40-ckpt-seed1", 20260721: "deepsv-ms-train40-ckpt-seed2", 20260722: "deepsv-ms-train40-ckpt-seed3"}
VARIANTS = ("M0", "M2", "M4")

DEPLOYMENT_THRESHOLDS_PATH = PAIRSV_ROOT / "manta_poc/truvari_gate2/phase_f/phaseF_deployment_thresholds_FROZEN.json"


def load_deployment_thresholds() -> dict:
    manifest = json.loads(DEPLOYMENT_THRESHOLDS_PATH.read_text())
    out = {}
    for model in VARIANTS:
        result = manifest["results_by_model"][model]
        assert result["status"] == "OK", f"{model}: deployment threshold not OK: {result}"
        out[model] = result["threshold"]
    return out


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", device, flush=True)
    if device == "cuda":
        print("gpu:", torch.cuda.get_device_name(0), flush=True)

    deployment_thresholds = load_deployment_thresholds()
    print("frozen deployment thresholds:", deployment_thresholds, flush=True)

    with h5py.File(WD / "hg002_v0.6_gate3_extracted.h5", "r") as h5:
        success = h5["success"][:]
        idx = success.nonzero()[0]
        candidate_id = h5["candidate_id"][idx]
        images = h5["images"][idx].astype(np.float32) / 255.0
        scalars_raw = h5["scalars"][idx].astype(np.float32)

    with h5py.File(WD / "pairsv_refalt_embeddings_HG002v06_gate3_cluster.h5", "r") as h5:
        refalt_ids = h5["candidate_id"][:]
        e_ref = h5["e_ref"][:].astype(np.float32)
        e_alt = h5["e_alt"][:].astype(np.float32)
        e_alt_minus_ref = h5["e_alt_minus_ref"][:].astype(np.float32)
        abs_e_alt_minus_ref = h5["abs_e_alt_minus_ref"][:].astype(np.float32)
        junction = h5["junction_embedding"][:].astype(np.float32)
    candidate_features_by_id = {
        (cid.decode() if isinstance(cid, bytes) else cid): np.concatenate([e_ref[i], e_alt[i], e_alt_minus_ref[i], abs_e_alt_minus_ref[i], junction[i]])
        for i, cid in enumerate(refalt_ids)
    }

    with h5py.File(WD / "pairsv_read_embeddings_HG002v06_gate3_cluster.h5", "r") as h5:
        read_row_ids = h5["row_id"][:]
        read_embedding = h5["read_embedding"][:].astype(np.float32)
    read_features_by_id = {
        (rid.decode() if isinstance(rid, bytes) else rid): read_embedding[i]
        for i, rid in enumerate(read_row_ids)
    }

    ids_str = [cid.decode() if isinstance(cid, bytes) else cid for cid in candidate_id]
    missing_cand = [cid for cid in ids_str if cid not in candidate_features_by_id]
    missing_read = [cid for cid in ids_str if cid not in read_features_by_id]
    assert not missing_cand, f"{len(missing_cand)} candidates missing refalt embeddings, e.g. {missing_cand[:5]}"
    assert not missing_read, f"{len(missing_read)} candidates missing read embeddings, e.g. {missing_read[:5]}"

    candidate_features_raw = np.stack([candidate_features_by_id[cid] for cid in ids_str])
    read_features_raw = np.stack([read_features_by_id[cid] for cid in ids_str])

    n = len(candidate_id)
    print(f"HG002 v0.6: scoring {n} candidates", flush=True)

    images_t = torch.from_numpy(images).to(device)

    per_seed_rows = []
    for seed in SEEDS:
        outdir = f"{CKPT_ROOT}/{SEED_DIR[seed]}/output-v1"
        norm = np.load(f"{outdir}/pairsv_train40_seed{seed}_norm_stats.npz")
        scalar_mean, scalar_std = norm["scalar_mean"], norm["scalar_std"]
        cand_mean, cand_std = norm["cand_mean"], norm["cand_std"]
        read_mean, read_std = norm["read_mean"], norm["read_std"]

        sn = ScalarNormalizer(mean=scalar_mean, std=scalar_std)
        scalars_norm = torch.from_numpy(sn.transform(scalars_raw)).to(device)
        cand_norm = torch.from_numpy(((candidate_features_raw - cand_mean) / cand_std).astype(np.float32)).to(device)
        read_norm = torch.from_numpy(((read_features_raw - read_mean) / read_std).astype(np.float32)).to(device)

        for variant in VARIANTS:
            ckpt_path = f"{outdir}/pairsv_train40_seed{seed}_{variant}.pt"
            ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
            assert ckpt["variant"] == variant and ckpt["seed"] == seed
            model = PairSV(variant, **ckpt["model_kwargs"]).to(device)
            model.load_state_dict(ckpt["model_state_dict"], strict=True)
            model.eval()

            kwargs = {}
            if variant in ("M1", "M4"):
                kwargs["candidate_features"] = cand_norm
            if variant in ("M2", "M4"):
                kwargs["scalar_features"] = scalars_norm
            if variant in ("M3", "M4"):
                kwargs["read_features"] = read_norm

            probs = np.zeros(n, dtype=np.float32)
            batch_size = 64
            with torch.no_grad():
                for start in range(0, n, batch_size):
                    end = min(start + batch_size, n)
                    batch_kwargs = {k: v[start:end] for k, v in kwargs.items()}
                    z = model(images_t[start:end], **batch_kwargs)
                    p = torch.softmax(z, 1)[:, 1].cpu().numpy()
                    probs[start:end] = p
            for cid, p in zip(candidate_id, probs.tolist()):
                per_seed_rows.append({
                    "seed": seed, "model": variant,
                    "candidate_id": cid.decode() if isinstance(cid, bytes) else cid,
                    "probability": p,
                })
            print(f"HG002 v0.6: seed={seed} model={variant}: {n} raw probabilities computed", flush=True)

    per_seed_df = pd.DataFrame(per_seed_rows)
    assert len(per_seed_df) == len(SEEDS) * len(VARIANTS) * n

    ensembled = (per_seed_df.groupby(["model", "candidate_id"], as_index=False)
                              .agg(probability=("probability", "mean")))
    assert len(ensembled) == len(VARIANTS) * n

    ensembled["threshold"] = ensembled["model"].map(deployment_thresholds)
    ensembled["prediction"] = (ensembled["probability"] >= ensembled["threshold"]).astype(int)

    assert not ({"label", "genotype", "negative_type", "class"} & set(per_seed_df.columns))
    assert not ({"label", "genotype", "negative_type", "class"} & set(ensembled.columns))

    per_seed_path = WD / "hg002_v0.6_gate3_predictions_per_seed_LABEL_BLIND.csv"
    ensembled_path = WD / "hg002_v0.6_gate3_predictions_ensembled_LABEL_BLIND.csv"
    per_seed_df.to_csv(per_seed_path, index=False)
    ensembled.to_csv(ensembled_path, index=False)

    for path in (per_seed_path, ensembled_path):
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        (Path(str(path) + ".sha256")).write_text(f"{sha}  {path.name}\n")
        print(f"HG002 v0.6: {path.name} sha256={sha}", flush=True)

    print("DONE: HG002 v0.6 ensemble scoring, predictions hashed, no label accessed", flush=True)


if __name__ == "__main__":
    main()
