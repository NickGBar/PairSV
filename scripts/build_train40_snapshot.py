"""Construct and checksum the immutable Train40 snapshot.

Merges the 8 audited train shards (already individually schema/checksum
verified by audit_pairsv_shard.py) into one frozen, content-addressed
definition: which shards, which people, which rows, and a fingerprint that
changes if a single row's identity or label changes -- independent of HDF5
file bytes/compression, so it survives any future re-save of the same
content. Does not touch validation or the internal test set.
"""
import hashlib, json, sys
import h5py

TRAIN_SHARD_PATHS = {
    s: f"kaggle/deepsv-ms-extract-train-shard{s}/output-v1/pairsv_shard_0{s}.h5"
    for s in range(1, 9)
}
TRAIN_SHARD_SHA256 = {
    1: "23f178baaedaa24a16bd74ed94bf7641780cd8c741187d34e92dace7c0972efd",
    2: "b62fa72761ef2cc37e51a28e3ecc6d2706a103f2262d97c719e57fd18bb8eb89",
    3: "a670ecef8684927dfe8aca7d2d102e67d1af9749e1fbc7ac376b0aae7ca6000b",
    4: "be1e5fadff75aeea217f2ba560f5c4dfdb8c9745c80255521714ac69dbb7e0c7",
    5: "28e892e64c70cb803ebe081c37fb6bb83b6a62ff49a9441ffbc21a90747e1b26",
    6: "e7a1178b271241b228869223ff1e12dd5f1de4bb11ccd8893bf9821da45971b8",
    7: "0b1a26ca772caa7ee6d45371c2ef910ae918bf4bd17c03acbafa18fbb526eb3b",
    8: "253ecaad513f2cfa54298dec1aa994b4ae7780a7158adff9d8d388d3f48d88e0",
}
VAL_SAMPLES = {"HG01894", "HG00732", "HG00422", "HG00106", "HG02597"}
TEST_SAMPLES = {"HG01896", "HG00734", "HG00428", "HG00107", "HG02600"}


def sha256_file(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def build():
    per_shard = {}
    all_rows = []  # (shard, row_id, sample_id, candidate_id, label, success)
    all_samples = set()

    for shard_id, path in TRAIN_SHARD_PATHS.items():
        actual_sha = sha256_file(path)
        expected_sha = TRAIN_SHARD_SHA256[shard_id]
        if actual_sha != expected_sha:
            print(f"FATAL: shard {shard_id} sha256 {actual_sha} != recorded {expected_sha}", file=sys.stderr)
            sys.exit(1)

        f = h5py.File(path, "r")
        row_id = f["examples/row_id"][:]
        sample_id = f["examples/sample_id"][:]
        candidate_id = f["examples/candidate_id"][:]
        label = f["examples/label"][:]
        success = f["examples/success"][:]

        def dec(x):
            return x.decode() if isinstance(x, bytes) else x

        samples_here = {dec(s) for s in sample_id}
        if not samples_here.issubset(set()) and (samples_here & VAL_SAMPLES or samples_here & TEST_SAMPLES):
            print(f"FATAL: shard {shard_id} contains a val/test sample: "
                  f"{(samples_here & VAL_SAMPLES) | (samples_here & TEST_SAMPLES)}", file=sys.stderr)
            sys.exit(1)
        all_samples |= samples_here

        for rid, sid, cid, lab, suc in zip(row_id, sample_id, candidate_id, label, success):
            all_rows.append((shard_id, dec(rid), dec(sid), dec(cid), int(lab), int(suc)))

        per_shard[shard_id] = {
            "path": path,
            "sha256": actual_sha,
            "n_rows": len(row_id),
            "n_success": int(success.sum()),
            "n_failed": int(len(success) - success.sum()),
            "samples": sorted(samples_here),
        }
        f.close()
        print(f"shard {shard_id}: {per_shard[shard_id]['n_rows']} rows, "
              f"{per_shard[shard_id]['n_success']} successful, samples={per_shard[shard_id]['samples']}",
              flush=True)

    row_ids_flat = [f"{s}:{r}" for s, r, *_ in all_rows]
    if len(set(row_ids_flat)) != len(row_ids_flat):
        print("FATAL: duplicate row_id across train shards", file=sys.stderr)
        sys.exit(1)

    if len(all_samples) != 40:
        print(f"FATAL: expected exactly 40 train samples, got {len(all_samples)}: {sorted(all_samples)}", file=sys.stderr)
        sys.exit(1)

    # content-addressed fingerprint: independent of file bytes/compression,
    # changes if any row's shard/row_id/sample/candidate/label/success changes.
    all_rows.sort()
    h = hashlib.sha256()
    for row in all_rows:
        h.update("|".join(str(x) for x in row).encode() + b"\n")
    fingerprint = h.hexdigest()

    successful = [r for r in all_rows if r[5] == 1]
    n_pos = sum(1 for r in successful if r[4] == 1)
    n_neg = sum(1 for r in successful if r[4] == 0)

    snapshot = {
        "schema_version": "pairsv-train40-snapshot-v1",
        "n_train_people": len(all_samples),
        "train_samples_sorted": sorted(all_samples),
        "n_shards": len(TRAIN_SHARD_PATHS),
        "per_shard": per_shard,
        "total_rows": len(all_rows),
        "total_successful": len(successful),
        "total_failed": len(all_rows) - len(successful),
        "label_balance_successful": {"pos": n_pos, "neg": n_neg},
        "val_samples_excluded": sorted(VAL_SAMPLES),
        "test_samples_excluded_untouched": sorted(TEST_SAMPLES),
        "content_fingerprint_sha256": fingerprint,
    }
    return snapshot


if __name__ == "__main__":
    snapshot = build()
    out_path = "train40_snapshot.json"
    json.dump(snapshot, open(out_path, "w"), indent=1)
    print()
    print(json.dumps({k: v for k, v in snapshot.items() if k != "per_shard"}, indent=1))
    print(f"\nwritten to {out_path}")
