#!/usr/bin/env python3
"""Targeted HyenaDNA-small embeddings for the DeepSV fusion experiment.

Genome-wide precompute (``precompute_hyenadna_embeddings.py``) is intractable
for this experiment (~150 GB for chr1-22) and unnecessary: the fusion models
only ever look up the fixed 50 bp grid bins that appear in the manifest, plus
a small context radius. This script computes embeddings ONLY for those bins,
reusing the genome-wide chunking + mean-pooling **unchanged** (imported, not
reimplemented), so every stored value is byte-identical to a full run.

Coordinate contract (identical in producer and both consumers):
    manifest ``position`` = 0-based START of the image's 50 bp window
    window_idx = position // window_size        # floor
    stored row window_idx = pooled hidden states over bin [50*wi, 50*wi+50)

The output HDF5 is dense-indexed (row i == global window i), so
``FusedDataset`` / ``FusedPredictor`` index it by ``position // 50`` with no
changes. Un-needed rows are the HDF5 fill value (0) and compress to nothing;
``FusedDataset`` pulls only the needed rows into RAM.

The Kaggle GPU run of this logic lives in the ``deepsv-hyenadna-targeted-emb``
kernel (self-contained, downloads the b37 FASTA in-kernel); this module is the
importable repo equivalent for local/reproducible runs.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import logging
import math
from collections import defaultdict
from pathlib import Path

import h5py
import numpy as np
import pyfaidx

from precompute_hyenadna_embeddings import (  # shared, UNCHANGED algorithm
    CORE_BP,
    EMBED_DIM,
    FLANK_BP,
    HYENADNA_MODEL_ID,
    SEQ_BP,
    WINDOW_BP,
    WINDOWS_PER_CHUNK,
    embed_chunk,
    fasta_md5,
    fetch_chunk_sequence,
    load_model,
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)


def _resolve_contig(keys: set[str], chrom: str) -> str | None:
    if chrom in keys:
        return chrom
    if chrom.startswith("chr") and chrom[3:] in keys:
        return chrom[3:]
    if f"chr{chrom}" in keys:
        return f"chr{chrom}"
    return None


def precompute_targeted(
    manifest: str,
    fasta_path: str,
    output_path: str,
    context_radius: int = 10,
    model_id: str = HYENADNA_MODEL_ID,
    model_revision: str = "main",
    device: str = "cuda",
    genome_build: str = "",
) -> None:
    # 1. manifest -> positions per chromosome
    positions_by_chrom: dict[str, set[int]] = defaultdict(set)
    with open(manifest) as fh:
        for row in csv.DictReader(fh):
            positions_by_chrom[str(row["chrom"])].add(int(row["position"]))
    logger.info("manifest chroms: %s", sorted(positions_by_chrom))

    fasta = pyfaidx.Fasta(fasta_path, sequence_always_upper=False, as_raw=True)
    keys = set(fasta.keys())

    # 2. plan: needed windows -> owning 32 kb chunks
    plan = {}
    for chrom, pos_set in positions_by_chrom.items():
        contig = _resolve_contig(keys, chrom)
        if contig is None:
            logger.warning("chrom %s not in FASTA — skipping", chrom)
            continue
        clen = len(fasta[contig])
        n_windows = math.ceil(clen / WINDOW_BP)
        needed_wi = set()
        for p in pos_set:
            c = p // WINDOW_BP
            for wi in range(c - context_radius, c + context_radius + 1):
                if 0 <= wi < n_windows:
                    needed_wi.add(wi)
        chunks = sorted({wi // WINDOWS_PER_CHUNK for wi in needed_wi})
        plan[chrom] = (contig, clen, n_windows, chunks, len(needed_wi))
        logger.info("chr%s: windows=%d needed=%d chunks=%d",
                    chrom, n_windows, len(needed_wi), len(chunks))

    ref_md5 = fasta_md5(fasta_path)
    model, tokenizer = load_model(model_id, model_revision, device)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    hdf = h5py.File(str(out), "a")
    hdf.attrs.update(dict(
        model_id=model_id, model_revision=model_revision, window_bp=WINDOW_BP,
        flank_bp=FLANK_BP, core_bp=CORE_BP, seq_bp=SEQ_BP, embed_dim=EMBED_DIM,
        context_radius=context_radius, coverage="targeted",
        reference_md5=ref_md5, genome_build=genome_build,
        date_utc=_dt.datetime.utcnow().isoformat(timespec="seconds"),
    ))

    # 3. embed needed chunks, write dense-indexed rows (resume per-chrom)
    for chrom, (contig, clen, n_windows, chunks, n_needed) in plan.items():
        if chrom in hdf and hdf[chrom].attrs.get("complete", 0) == 1:
            logger.info("chr%s already complete — skip", chrom)
            continue
        if chrom in hdf:
            del hdf[chrom]
        dset = hdf.create_dataset(
            chrom, shape=(n_windows, EMBED_DIM), dtype=np.float16,
            chunks=(min(1024, n_windows), EMBED_DIM),
            compression="gzip", compression_opts=4, fillvalue=0.0)
        rec = fasta[contig]
        for i, ck in enumerate(chunks):
            pooled = embed_chunk(
                fetch_chunk_sequence(rec, ck, clen),
                model, tokenizer, device)
            r0 = ck * WINDOWS_PER_CHUNK
            r1 = min(r0 + WINDOWS_PER_CHUNK, n_windows)
            dset[r0:r1] = pooled[:r1 - r0]
            if (i + 1) % 200 == 0 or i == len(chunks) - 1:
                logger.info("  chr%s %d/%d chunks", chrom, i + 1, len(chunks))
        dset.attrs["complete"] = 1
        dset.attrs["n_needed_windows"] = n_needed
        hdf.flush()
        logger.info("  ✓ chr%s done", chrom)

    hdf.close()
    fasta.close()
    logger.info("done: %s", output_path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True, help="manifest_all.csv (needs chrom,position)")
    ap.add_argument("--fasta", required=True, help="reference FASTA (b37)")
    ap.add_argument("--output", required=True, help="output HDF5 path")
    ap.add_argument("--context-radius", type=int, default=10)
    ap.add_argument("--model-id", default=HYENADNA_MODEL_ID)
    ap.add_argument("--model-revision", default="main")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--genome-build", default="")
    a = ap.parse_args()
    precompute_targeted(
        manifest=a.manifest, fasta_path=a.fasta, output_path=a.output,
        context_radius=a.context_radius, model_id=a.model_id,
        model_revision=a.model_revision, device=a.device,
        genome_build=a.genome_build)


if __name__ == "__main__":
    main()
