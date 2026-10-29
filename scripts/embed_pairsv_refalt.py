#!/usr/bin/env python3
"""Deduplicated frozen HyenaDNA REF/ALT embeddings for PAIR-SV shards."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


MODEL_ID = "LongSafari/hyenadna-small-32k-seqlen-hf"
MODEL_REVISION = "8fe770c78eb13fe33bf81501612faeddf4d6f331"
TOKEN_TO_BASE = np.asarray(["N", "A", "C", "G", "T", "N"], dtype="U1")


def tokens_to_sequence(tokens: np.ndarray) -> str:
    """Decode the PAIR-SV A/C/G/T/N uint8 convention without metadata."""
    values = np.asarray(tokens, dtype=np.uint8)
    if values.ndim != 1 or values.shape[0] != 1024:
        raise ValueError(f"REF/ALT token sequence must be (1024,), got {values.shape}")
    return "".join(TOKEN_TO_BASE[np.minimum(values, 5)])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def read_candidates(shards: list[Path]) -> tuple[list[str], np.ndarray, dict[str, str]]:
    by_id: dict[str, np.ndarray] = {}
    checksums = {}
    for path in shards:
        checksums[path.name] = sha256_file(path)
        with h5py.File(path, "r") as h5:
            ids = [value.decode() if isinstance(value, bytes) else str(value) for value in h5["candidates/candidate_id"][:]]
            tokens = h5["candidates/refalt_tokens"][:]
            for candidate_id, value in zip(ids, tokens):
                previous = by_id.get(candidate_id)
                if previous is not None and not np.array_equal(previous, value):
                    raise ValueError(f"candidate {candidate_id} has inconsistent REF/ALT tokens across shards")
                by_id[candidate_id] = value
    candidate_ids = sorted(by_id)
    return candidate_ids, np.stack([by_id[candidate_id] for candidate_id in candidate_ids]), checksums


def encode(
    candidate_ids: list[str],
    refalt_tokens: np.ndarray,
    output: Path,
    *,
    model_id: str,
    revision: str,
    batch_size: int,
    device: str,
) -> None:
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_id, revision=revision, trust_remote_code=True, torch_dtype=torch.bfloat16)
    model.to(device).eval()
    all_sequences = [tokens_to_sequence(tokens) for tokens in refalt_tokens.reshape(-1, 1024)]
    e_ref, e_alt, e_junction = [], [], []
    with torch.inference_mode():
        for start in range(0, len(all_sequences), batch_size):
            sequences = all_sequences[start:start + batch_size]
            encoded = tokenizer(sequences, return_tensors="pt", padding=True, add_special_tokens=False)
            input_ids = encoded["input_ids"].to(device)
            if input_ids.shape[1] != 1024:
                raise RuntimeError(f"HyenaDNA tokenizer returned {input_ids.shape[1]} tokens, expected 1024")
            with torch.autocast(device_type="cuda" if device.startswith("cuda") else "cpu", dtype=torch.bfloat16):
                hidden = model(input_ids).last_hidden_state
            pooled = hidden.mean(dim=1).to(torch.float16).cpu().numpy().reshape(-1, 2, hidden.shape[-1])
            junction = hidden[:, 448:576].mean(dim=1).to(torch.float16).cpu().numpy().reshape(-1, 2, hidden.shape[-1])
            e_ref.append(pooled[:, 0])
            e_alt.append(pooled[:, 1])
            e_junction.append(junction[:, 1])
    ref = np.concatenate(e_ref)
    alt = np.concatenate(e_alt)
    junction = np.concatenate(e_junction)
    output.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(output, "w") as h5:
        h5.attrs.update({
            "schema_version": "pairsv-refalt-embeddings-v1",
            "model_id": model_id,
            "model_revision": revision,
            "sequence_length": 1024,
            "junction_center": 512,
            "junction_pool_start": 448,
            "junction_pool_end": 576,
            "frozen": True,
        })
        string = h5py.string_dtype("utf-8")
        h5.create_dataset("candidate_id", data=np.asarray(candidate_ids, dtype=object), dtype=string)
        compression = {"compression": "gzip", "compression_opts": 1, "shuffle": True}
        for name, values in {
            "e_ref": ref,
            "e_alt": alt,
            "e_alt_minus_ref": alt - ref,
            "abs_e_alt_minus_ref": np.abs(alt - ref),
            "junction_embedding": junction,
        }.items():
            h5.create_dataset(name, data=values.astype(np.float16), chunks=(min(256, len(values)), values.shape[1]), **compression)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", action="append", required=True, help="PAIR-SV extraction HDF5; repeatable")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    paths = [Path(value) for value in args.shard]
    candidate_ids, tokens, checksums = read_candidates(paths)
    encode(candidate_ids, tokens, Path(args.output), model_id=args.model_id, revision=args.model_revision, batch_size=args.batch_size, device=args.device)
    Path(str(args.output) + ".inputs.json").write_text(json.dumps({"shards": [str(path) for path in paths], "sha256": checksums, "candidates": len(candidate_ids)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
