"""Full structural + content audit for a recovered PAIR-SV train shard HDF5.

Checks (per project QC policy, no check skipped/assumed):
  - file opens as valid HDF5
  - exact key set + shapes + dtypes match the reference schema (shard5, itself
    byte-verified against a previously recorded publisher checksum)
  - attrs.schema_version / shard_id match expectation
  - exactly 10,000 rows on every row-aligned dataset
  - success/failed counts match the kernel's own runtime.json ground truth
  - unique row_id count == total rows (no duplicated rows)
  - sample_id set == expected five samples from runtime.json, exactly
  - label balance among successful rows
  - scalars finite (no NaN/Inf) on successful rows
  - images/read_tokens non-all-zero on a sample of successful rows
  - candidate_id referential integrity: every example candidate_id exists in
    candidates/candidate_id
  - SHA-256 of the file (recorded as canonical; compared against a prior
    value only if one is passed in, since shards 7/8 have no earlier
    successful download to compare against)
"""
import argparse, hashlib, json, sys
import h5py
import numpy as np

REFERENCE_SCHEMA = {
    "candidates/candidate_id": ("object", None),
    "candidates/coordinates": ("int64", (None, 2)),
    "candidates/refalt_tokens": ("uint8", (None, 2, 1024)),
    "examples/breakpoints": ("int64", (10000, 2)),
    "examples/candidate_id": ("object", (10000,)),
    "examples/candidate_index": ("int32", (10000,)),
    "examples/chrom": ("object", (10000,)),
    "examples/failure_reason": ("object", (10000,)),
    "examples/images": ("uint8", (10000, 2, 6, 64, 128)),
    "examples/label": ("uint8", (10000,)),
    "examples/read_mask": ("uint8", (10000, 2, 48)),
    "examples/read_tokens": ("uint8", (10000, 2, 48, 128)),
    "examples/row_id": ("object", (10000,)),
    "examples/sample_id": ("object", (10000,)),
    "examples/scalars": ("float32", (10000, 17)),
    "examples/success": ("uint8", (10000,)),
    "read_metadata/cigar": ("|S64", (10000, 2, 48)),
    "read_metadata/mapq": ("uint8", (10000, 2, 48)),
    "read_metadata/mean_base_quality": ("float32", (10000, 2, 48)),
    "read_metadata/read_name_hash": ("|S16", (10000, 2, 48)),
    "read_metadata/selection_reason": ("uint8", (10000, 2, 48)),
    "read_metadata/strand": ("int8", (10000, 2, 48)),
    "read_metadata/supplementary": ("uint8", (10000, 2, 48)),
}


def flatten(f):
    out = {}
    def walk(g, prefix=""):
        for k in g.keys():
            item = g[k]
            if isinstance(item, h5py.Group):
                walk(item, prefix + k + "/")
            else:
                out[prefix + k] = item
    walk(f)
    return out


def sha256_file(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def audit(h5_path, runtime_json_path, expected_shard_id, prior_sha256=None):
    problems = []
    info = {}

    runtime = json.loads(open(runtime_json_path).read())
    if runtime["shard"] != expected_shard_id:
        problems.append(f"runtime.json shard={runtime['shard']} != expected {expected_shard_id}")

    try:
        f = h5py.File(h5_path, "r")
    except Exception as e:
        return {"ok": False, "problems": [f"HDF5 failed to open: {e!r}"], "info": {}}

    datasets = flatten(f)
    missing = sorted(set(REFERENCE_SCHEMA) - set(datasets))
    extra = sorted(set(datasets) - set(REFERENCE_SCHEMA))
    if missing:
        problems.append(f"missing datasets: {missing}")
    if extra:
        problems.append(f"unexpected extra datasets: {extra}")

    for name, (exp_dtype, exp_shape) in REFERENCE_SCHEMA.items():
        if name not in datasets:
            continue
        ds = datasets[name]
        if str(ds.dtype) != exp_dtype:
            problems.append(f"{name}: dtype {ds.dtype} != expected {exp_dtype}")
        if exp_shape is not None:
            for axis, (got, exp) in enumerate(zip(ds.shape, exp_shape)):
                if exp is not None and got != exp:
                    problems.append(f"{name}: shape axis {axis} = {got} != expected {exp}")
            if len(ds.shape) != len(exp_shape):
                problems.append(f"{name}: shape rank {ds.shape} != expected rank {exp_shape}")

    schema_version = f.attrs.get("schema_version")
    if schema_version != "pairsv-shard-v1":
        problems.append(f"schema_version={schema_version!r} != 'pairsv-shard-v1'")
    shard_attr = int(f.attrs.get("shard_id", -1))
    if shard_attr != expected_shard_id:
        problems.append(f"attrs.shard_id={shard_attr} != expected {expected_shard_id}")

    n = datasets["examples/label"].shape[0]
    if n != 10000:
        problems.append(f"examples row count = {n} != 10000")

    success = datasets["examples/success"][:]
    n_success = int(success.sum())
    n_failed = n - n_success
    if n_success != runtime["candidates_completed"]:
        problems.append(f"success.sum()={n_success} != runtime candidates_completed={runtime['candidates_completed']}")
    if n_failed != runtime["candidates_failed"]:
        problems.append(f"n_failed={n_failed} != runtime candidates_failed={runtime['candidates_failed']}")

    row_id = datasets["examples/row_id"][:]
    if len(set(row_id)) != len(row_id):
        problems.append(f"row_id not unique: {len(row_id)} rows, {len(set(row_id))} unique")

    sample_id = datasets["examples/sample_id"][:]
    got_samples = {s.decode() if isinstance(s, bytes) else s for s in np.unique(sample_id)}
    expected_samples = set(runtime["samples"])
    if got_samples != expected_samples:
        problems.append(f"sample_id set {got_samples} != runtime samples {expected_samples}")

    label = datasets["examples/label"][:]
    succ_mask = success.astype(bool)
    lab_succ = label[succ_mask]
    n_pos = int((lab_succ == 1).sum())
    n_neg = int((lab_succ == 0).sum())
    info["label_balance_successful_rows"] = {"pos": n_pos, "neg": n_neg}
    if n_pos == 0 or n_neg == 0:
        problems.append(f"label balance degenerate among successful rows: pos={n_pos} neg={n_neg}")
    imbalance = abs(n_pos - n_neg) / max(1, n_pos + n_neg)
    if imbalance > 0.15:
        problems.append(f"label imbalance among successful rows {imbalance:.3f} exceeds 0.15 tolerance (pos={n_pos}, neg={n_neg})")

    scalars = datasets["examples/scalars"][:][succ_mask]
    if not np.isfinite(scalars).all():
        n_bad = int((~np.isfinite(scalars)).sum())
        problems.append(f"{n_bad} non-finite scalar values among successful rows")

    succ_idx = np.flatnonzero(succ_mask)
    sample_idx = succ_idx[:: max(1, len(succ_idx) // 200)][:200]
    images = datasets["examples/images"]
    read_tokens = datasets["examples/read_tokens"]
    n_allzero_img = sum(1 for i in sample_idx if not images[i].any())
    n_allzero_rt = sum(1 for i in sample_idx if not read_tokens[i].any())
    if n_allzero_img:
        problems.append(f"{n_allzero_img}/{len(sample_idx)} sampled successful rows have all-zero images")
    if n_allzero_rt:
        problems.append(f"{n_allzero_rt}/{len(sample_idx)} sampled successful rows have all-zero read_tokens")

    cand_ids = set(datasets["candidates/candidate_id"][:])
    ex_cand_ids = set(datasets["examples/candidate_id"][:][succ_mask])
    orphans = ex_cand_ids - cand_ids
    if orphans:
        problems.append(f"{len(orphans)} example candidate_id(s) missing from candidates/candidate_id, e.g. {list(orphans)[:3]}")

    f.close()

    sha = sha256_file(h5_path)
    info["sha256"] = sha
    if prior_sha256 is not None and prior_sha256 != sha:
        problems.append(f"SHA-256 mismatch: got {sha}, expected {prior_sha256}")

    info["n_rows"] = n
    info["n_success"] = n_success
    info["n_failed"] = n_failed
    info["expected_samples"] = sorted(expected_samples)
    info["runtime_json"] = runtime

    return {"ok": len(problems) == 0, "problems": problems, "info": info}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("h5_path")
    ap.add_argument("runtime_json_path")
    ap.add_argument("expected_shard_id", type=int)
    ap.add_argument("--prior-sha256", default=None)
    args = ap.parse_args()
    result = audit(args.h5_path, args.runtime_json_path, args.expected_shard_id, args.prior_sha256)
    print(json.dumps(result, indent=1, default=str))
    sys.exit(0 if result["ok"] else 1)
