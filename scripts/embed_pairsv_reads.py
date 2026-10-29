#!/usr/bin/env python3
"""Frozen, mask-aware sample-specific read embeddings for PAIR-SV shards.

The output is keyed by shard filename plus stable row ID and deliberately
contains no label, sample ID, genotype quality, negative type, or read count
model feature.  Read counts are retained only as an embedding QC field.
"""
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def decode_read(tokens: np.ndarray) -> str:
    values = np.asarray(tokens, dtype=np.uint8)
    if values.shape != (128,):
        raise ValueError(f"read tokens must be (128,), got {values.shape}")
    return "".join(TOKEN_TO_BASE[np.minimum(values, 5)])


def _encode_sequences(model, tokenizer, sequences: list[str], *, device: str, batch_size: int) -> np.ndarray:
    import torch

    parts = []
    with torch.inference_mode():
        for start in range(0, len(sequences), batch_size):
            encoded = tokenizer(sequences[start:start + batch_size], return_tensors="pt", padding=True, add_special_tokens=False)
            input_ids = encoded["input_ids"].to(device)
            if input_ids.shape[1] != 128:
                raise RuntimeError(f"HyenaDNA tokenizer returned {input_ids.shape[1]} tokens, expected 128")
            with torch.autocast(device_type="cuda" if device.startswith("cuda") else "cpu", dtype=torch.bfloat16):
                hidden = model(input_ids).last_hidden_state
            parts.append(hidden.mean(dim=1).float().cpu().numpy())
    return np.concatenate(parts, axis=0)


def embed_shard(path: Path, output: h5py.File, model, tokenizer, *, device: str, batch_size: int, row_chunk: int) -> int:
    """Append one success-only shard using a left/right mask-aware mean pool."""
    with h5py.File(path, "r") as source:
        examples = source["examples"]
        success_rows = np.flatnonzero(examples["success"][:].astype(bool))
        row_ids = examples["row_id"][success_rows]
        for start in range(0, len(success_rows), row_chunk):
            rows = success_rows[start:start + row_chunk]
            tokens = examples["read_tokens"][rows]
            mask = examples["read_mask"][rows].astype(bool)
            offsets = np.argwhere(mask)
            if not len(offsets):
                raise RuntimeError(f"{path.name}: successful rows have no selected reads")
            sequences = [decode_read(tokens[row, side, read]) for row, side, read in offsets]
            encoded = _encode_sequences(model, tokenizer, sequences, device=device, batch_size=batch_size)
            hidden_dim = encoded.shape[1]
            pooled = np.zeros((len(rows), 2, hidden_dim), dtype=np.float32)
            counts = np.zeros((len(rows), 2), dtype=np.int16)
            for vector, (row, side, _read) in zip(encoded, offsets):
                pooled[row, side] += vector
                counts[row, side] += 1
            if np.any(counts == 0):
                raise RuntimeError(f"{path.name}: successful row lacks selected reads at one breakpoint")
            pooled /= counts[..., None]
            features = np.concatenate((pooled[:, 0], pooled[:, 1], np.abs(pooled[:, 0] - pooled[:, 1])), axis=1).astype(np.float16)
            n = len(rows)
            output["source_shard"].resize((output["source_shard"].shape[0] + n,))
            output["row_id"].resize((output["row_id"].shape[0] + n,))
            if output["read_embedding"].shape[1] != features.shape[1]:
                raise RuntimeError("frozen read-encoder hidden size disagrees with output schema")
            output["read_embedding"].resize((output["read_embedding"].shape[0] + n, features.shape[1]))
            output["valid_read_count_qc"].resize((output["valid_read_count_qc"].shape[0] + n, 2))
            output["source_shard"][-n:] = [path.name] * n
            output["row_id"][-n:] = row_ids[start:start + n]
            output["read_embedding"][-n:] = features
            output["valid_read_count_qc"][-n:] = counts
            output.flush()
            print(f"[read-embed] {path.name}: {start + n}/{len(success_rows)} rows", flush=True)
    return len(success_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", action="append", required=True, help="PAIR-SV extraction HDF5; repeatable")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--row-chunk", type=int, default=64)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    import torch
    from transformers import AutoModel, AutoTokenizer

    paths = [Path(value) for value in args.shard]
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, revision=args.model_revision, trust_remote_code=True)
    model = AutoModel.from_pretrained(args.model_id, revision=args.model_revision, trust_remote_code=True, torch_dtype=torch.bfloat16)
    model.to(args.device).eval()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    string = h5py.string_dtype("utf-8")
    with h5py.File(output_path, "w") as output:
        output.attrs.update({"schema_version": "pairsv-read-embeddings-v1", "model_id": args.model_id, "model_revision": args.model_revision, "frozen": True, "pooling": "mean_per_breakpoint_then_left_right_absdiff"})
        hidden_dim = int(getattr(model.config, "d_model", getattr(model.config, "hidden_size", 0)))
        if hidden_dim <= 0:
            raise RuntimeError("cannot determine frozen read-encoder hidden size")
        output.create_dataset("source_shard", shape=(0,), maxshape=(None,), dtype=string)
        output.create_dataset("row_id", shape=(0,), maxshape=(None,), dtype=string)
        output.create_dataset("read_embedding", shape=(0, hidden_dim * 3), maxshape=(None, hidden_dim * 3), dtype="f2", chunks=(min(256, max(1, args.row_chunk)), hidden_dim * 3), compression="gzip", compression_opts=1, shuffle=True)
        output.create_dataset("valid_read_count_qc", shape=(0, 2), maxshape=(None, 2), dtype="i2")
        completed = sum(embed_shard(path, output, model, tokenizer, device=args.device, batch_size=args.batch_size, row_chunk=args.row_chunk) for path in paths)
        output.attrs["successful_examples"] = completed
    Path(str(output_path) + ".inputs.json").write_text(json.dumps({"shards": [str(path) for path in paths], "sha256": {path.name: sha256_file(path) for path in paths}}, indent=2) + "\n")


if __name__ == "__main__":
    main()
