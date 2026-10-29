"""Production feature extraction for PAIR-SV sample-candidate examples."""
from __future__ import annotations

import hashlib
import math
import os
import time
import warnings
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import numpy as np


BREAKPOINT_WINDOW = 128
MAX_IMAGE_READS = 64
MAX_SEQUENCE_READS = 48
READ_SEQUENCE_LENGTH = 128
IMAGE_SHAPE = (2, 6, MAX_IMAGE_READS, BREAKPOINT_WINDOW)
READ_TOKEN_SHAPE = (2, MAX_SEQUENCE_READS, READ_SEQUENCE_LENGTH)
READ_MASK_SHAPE = (2, MAX_SEQUENCE_READS)
SCALAR_FEATURE_NAMES = (
    "left_soft_clip_count",
    "right_soft_clip_count",
    "split_read_count",
    "supplementary_alignment_count",
    "discordant_pair_count",
    "reference_spanning_read_count",
    "candidate_alt_support_count",
    "inside_depth",
    "left_flank_depth",
    "right_flank_depth",
    "inside_flank_depth_ratio",
    "mean_mapq",
    "mean_base_quality",
    "mean_abs_insert_size",
    "insert_size_anomaly_fraction",
    "left_right_evidence_balance",
    "log1p_deletion_length",
)
SELECTION_REASON_CODES = {
    "ordinary": 0,
    "discordant": 1,
    "deletion_cigar": 2,
    "soft_clipped": 3,
    "split_sa": 4,
    "supplementary": 5,
}
BASE_TOKEN = {"A": 1, "C": 2, "G": 3, "T": 4, "N": 5}
BASE_IMAGE = {"A": 48, "C": 96, "G": 144, "T": 192, "N": 24}


class CandidateExtractionError(RuntimeError):
    """A single candidate failed and must be explicitly flagged, not zero-filled."""


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    chrom: str
    del_start0: int
    del_end0: int
    length: int

    def __post_init__(self) -> None:
        if self.del_end0 - self.del_start0 != self.length:
            raise ValueError("candidate length does not match its half-open interval")
        if not 50 <= self.length <= 10_000:
            raise ValueError("candidate length is outside 50-10,000 bp")


@dataclass
class ExampleTensors:
    images: np.ndarray
    read_tokens: np.ndarray
    read_mask: np.ndarray
    scalars: np.ndarray
    read_cigar: np.ndarray
    read_strand: np.ndarray
    read_mapq: np.ndarray
    read_mean_bq: np.ndarray
    read_supplementary: np.ndarray
    read_name_hash: np.ndarray
    read_selection_reason: np.ndarray


def tokenize_dna(sequence: str, width: int | None = None) -> np.ndarray:
    sequence = sequence.upper()
    width = len(sequence) if width is None else int(width)
    out = np.zeros(width, dtype=np.uint8)
    for index, base in enumerate(sequence[:width]):
        out[index] = BASE_TOKEN.get(base, BASE_TOKEN["N"])
    return out


def build_candidate_refalt_tokens(
    candidate: Candidate,
    fetch_reference: Callable[[str, int, int], str],
    *,
    flank: int = 512,
) -> np.ndarray:
    """Build deduplicated junction-centred REF/ALT candidate tokens.

    REF is the intact sequence around the left breakpoint; ALT joins the left
    flank to the sequence immediately after the deletion.  Both are 2F long.
    """
    left_start = candidate.del_start0 - flank
    pad_left = max(0, -left_start)
    left = ("N" * pad_left) + fetch_reference(
        candidate.chrom, max(0, left_start), candidate.del_start0
    ).upper()
    left = left[-flank:].rjust(flank, "N")
    ref_right = fetch_reference(
        candidate.chrom, candidate.del_start0, candidate.del_start0 + flank
    ).upper().ljust(flank, "N")[:flank]
    alt_right = fetch_reference(
        candidate.chrom, candidate.del_end0, candidate.del_end0 + flank
    ).upper().ljust(flank, "N")[:flank]
    ref = left + ref_right
    alt = left + alt_right
    if len(ref) != 2 * flank or len(alt) != 2 * flank:
        raise CandidateExtractionError("candidate REF/ALT construction length mismatch")
    return np.stack((tokenize_dna(ref), tokenize_dna(alt)))


def _soft_clip_bases(read) -> int:
    return sum(length for op, length in (read.cigartuples or ()) if op == 4)


def _has_large_deletion(read, minimum: int = 20) -> bool:
    return any(op == 2 and length >= minimum for op, length in (read.cigartuples or ()))


def is_discordant(read) -> bool:
    if not getattr(read, "is_paired", False):
        return False
    return bool(
        getattr(read, "mate_is_unmapped", False)
        or getattr(read, "reference_id", -1) != getattr(read, "next_reference_id", -1)
        or not getattr(read, "is_proper_pair", False)
        or abs(int(getattr(read, "template_length", 0) or 0)) > 1_000
    )


def selection_reason(read) -> str:
    if getattr(read, "is_supplementary", False):
        return "supplementary"
    if read.has_tag("SA"):
        return "split_sa"
    if _soft_clip_bases(read) >= 10:
        return "soft_clipped"
    if _has_large_deletion(read):
        return "deletion_cigar"
    if is_discordant(read):
        return "discordant"
    return "ordinary"


def _distance_to_breakpoint(read, breakpoint: int) -> int:
    start = int(getattr(read, "reference_start", breakpoint) or breakpoint)
    end = int(getattr(read, "reference_end", start) or start)
    if start <= breakpoint <= end:
        return 0
    return min(abs(start - breakpoint), abs(end - breakpoint))


def select_reads(reads: Iterable, breakpoint: int, limit: int = MAX_IMAGE_READS) -> list:
    """Select evidence reads first while retaining ordinary spanning controls."""
    unique = {}
    for read in reads:
        if (
            getattr(read, "is_unmapped", False)
            or getattr(read, "is_secondary", False)
            or getattr(read, "is_duplicate", False)
            or getattr(read, "is_qcfail", False)
            or not getattr(read, "query_sequence", None)
        ):
            continue
        key = (
            getattr(read, "query_name", ""),
            int(getattr(read, "reference_start", -1)),
            bool(getattr(read, "is_read1", False)),
            bool(getattr(read, "is_supplementary", False)),
        )
        unique[key] = read
    reason_rank = SELECTION_REASON_CODES
    ranked = sorted(
        unique.values(),
        key=lambda read: (
            -reason_rank[selection_reason(read)],
            _distance_to_breakpoint(read, breakpoint),
            -int(getattr(read, "mapping_quality", 0)),
            str(getattr(read, "query_name", "")),
        ),
    )
    if len(ranked) <= limit:
        return ranked
    evidence = [read for read in ranked if selection_reason(read) != "ordinary"]
    controls = [read for read in ranked if selection_reason(read) == "ordinary"]
    # Reserve at least one eighth of the rows for ordinary spanning controls.
    reserve = min(len(controls), max(4, limit // 8))
    return evidence[: limit - reserve] + controls[:reserve]


def _query_center_for_breakpoint(read, breakpoint: int) -> int:
    best_query = None
    best_distance = math.inf
    try:
        for query_pos, ref_pos in read.get_aligned_pairs(matches_only=False):
            if query_pos is None or ref_pos is None:
                continue
            distance = abs(int(ref_pos) - breakpoint)
            if distance < best_distance:
                best_query, best_distance = int(query_pos), distance
    except Exception:
        best_query = None
    if best_query is not None:
        return best_query
    return max(0, len(read.query_sequence or "") // 2)


def tokenize_read(read, breakpoint: int, width: int = READ_SEQUENCE_LENGTH) -> np.ndarray:
    sequence = (read.query_sequence or "").upper()
    center = _query_center_for_breakpoint(read, breakpoint)
    start = center - width // 2
    out = np.zeros(width, dtype=np.uint8)
    source_start = max(0, start)
    source_end = min(len(sequence), start + width)
    target_start = source_start - start
    for index, base in enumerate(sequence[source_start:source_end], start=target_start):
        out[index] = BASE_TOKEN.get(base, BASE_TOKEN["N"])
    return out


def _read_name_hash(read) -> bytes:
    return hashlib.sha256(str(getattr(read, "query_name", "")).encode()).hexdigest()[:16].encode()


def _mean_base_quality(read) -> float:
    qualities = getattr(read, "query_qualities", None)
    return float(np.mean(qualities)) if qualities is not None and len(qualities) else 0.0


def _read_metadata_arrays(selected_by_side: Sequence[Sequence]) -> tuple[np.ndarray, ...]:
    shape = READ_MASK_SHAPE
    cigar = np.full(shape, b"", dtype="S64")
    strand = np.zeros(shape, dtype=np.int8)
    mapq = np.zeros(shape, dtype=np.uint8)
    mean_bq = np.zeros(shape, dtype=np.float32)
    supplementary = np.zeros(shape, dtype=np.uint8)
    name_hash = np.full(shape, b"", dtype="S16")
    reason = np.zeros(shape, dtype=np.uint8)
    for side, reads in enumerate(selected_by_side):
        for slot, read in enumerate(reads[:MAX_SEQUENCE_READS]):
            cigar[side, slot] = str(getattr(read, "cigarstring", "") or "").encode()[:64]
            strand[side, slot] = -1 if getattr(read, "is_reverse", False) else 1
            mapq[side, slot] = np.uint8(min(255, max(0, int(getattr(read, "mapping_quality", 0)))))
            mean_bq[side, slot] = _mean_base_quality(read)
            supplementary[side, slot] = int(getattr(read, "is_supplementary", False))
            name_hash[side, slot] = _read_name_hash(read)
            reason[side, slot] = SELECTION_REASON_CODES[selection_reason(read)]
    return cigar, strand, mapq, mean_bq, supplementary, name_hash, reason


def build_read_tensors(selected_by_side: Sequence[Sequence], breakpoints: Sequence[int]) -> tuple[np.ndarray, np.ndarray]:
    tokens = np.zeros(READ_TOKEN_SHAPE, dtype=np.uint8)
    mask = np.zeros(READ_MASK_SHAPE, dtype=np.uint8)
    for side, (reads, breakpoint) in enumerate(zip(selected_by_side, breakpoints)):
        for slot, read in enumerate(reads[:MAX_SEQUENCE_READS]):
            tokens[side, slot] = tokenize_read(read, breakpoint)
            mask[side, slot] = 1
    return tokens, mask


def _aligned_pairs(read):
    try:
        return read.get_aligned_pairs(matches_only=False)
    except Exception:
        return ()


def build_pileup_tensor(
    reads: Sequence,
    chrom: str,
    breakpoint: int,
    fetch_reference: Callable[[str, int, int], str],
) -> np.ndarray:
    """Build one ``(6,64,128) uint8`` evidence image."""
    start = max(0, breakpoint - BREAKPOINT_WINDOW // 2)
    end = start + BREAKPOINT_WINDOW
    reference = fetch_reference(chrom, start, end).upper()
    if len(reference) < BREAKPOINT_WINDOW:
        reference += "N" * (BREAKPOINT_WINDOW - len(reference))
    tensor = np.zeros((6, MAX_IMAGE_READS, BREAKPOINT_WINDOW), dtype=np.uint8)
    for row, read in enumerate(reads[:MAX_IMAGE_READS]):
        mapq = np.uint8(round(min(60, int(getattr(read, "mapping_quality", 0))) * 255 / 60))
        strand = np.uint8(255 if getattr(read, "is_reverse", False) else 64)
        evidence = np.uint8(64 + 32 * SELECTION_REASON_CODES[selection_reason(read)])
        sequence = (read.query_sequence or "").upper()
        qualities = getattr(read, "query_qualities", None)
        for query_pos, ref_pos in _aligned_pairs(read):
            if ref_pos is None:
                continue
            col = int(ref_pos) - start
            if not 0 <= col < BREAKPOINT_WINDOW:
                continue
            tensor[2, row, col] = mapq
            tensor[3, row, col] = strand
            tensor[5, row, col] = evidence
            if query_pos is None:
                tensor[0, row, col] = 255
                tensor[4, row, col] = 255
                continue
            base = sequence[int(query_pos)] if int(query_pos) < len(sequence) else "N"
            tensor[0, row, col] = BASE_IMAGE.get(base, BASE_IMAGE["N"])
            quality = int(qualities[int(query_pos)]) if qualities is not None and int(query_pos) < len(qualities) else 0
            tensor[1, row, col] = np.uint8(round(min(60, quality) * 255 / 60))
            tensor[4, row, col] = 64 if base == reference[col] else 160
    return tensor


def _coverage(reads: Iterable, start: int, end: int) -> float:
    if end <= start:
        return 0.0
    depth = np.zeros(end - start, dtype=np.int32)
    seen = set()
    for read in reads:
        key = (getattr(read, "query_name", ""), int(getattr(read, "reference_start", -1)), bool(getattr(read, "is_read1", False)))
        if key in seen:
            continue
        seen.add(key)
        for query_pos, ref_pos in _aligned_pairs(read):
            if query_pos is not None and ref_pos is not None and start <= int(ref_pos) < end:
                depth[int(ref_pos) - start] += 1
    return float(depth.mean()) if len(depth) else 0.0


def _spans(read, breakpoint: int, margin: int = 10) -> bool:
    return bool(
        int(getattr(read, "reference_start", breakpoint) or breakpoint) <= breakpoint - margin
        and int(getattr(read, "reference_end", breakpoint) or breakpoint) >= breakpoint + margin
        and selection_reason(read) == "ordinary"
    )


def scalar_features(candidate: Candidate, selected_by_side: Sequence[Sequence]) -> np.ndarray:
    left_reads, right_reads = selected_by_side
    all_reads = list(left_reads) + list(right_reads)
    unique = {}
    for read in all_reads:
        unique[(getattr(read, "query_name", ""), int(getattr(read, "reference_start", -1)), bool(getattr(read, "is_read1", False)), bool(getattr(read, "is_supplementary", False)))] = read
    reads = list(unique.values())
    left_soft = sum(_soft_clip_bases(read) >= 10 for read in left_reads)
    right_soft = sum(_soft_clip_bases(read) >= 10 for read in right_reads)
    split = sum(read.has_tag("SA") for read in reads)
    supplementary = sum(getattr(read, "is_supplementary", False) for read in reads)
    discordant = sum(is_discordant(read) for read in reads)
    spanning = sum(_spans(read, candidate.del_start0) or _spans(read, candidate.del_end0) for read in reads)
    left_alt = sum(selection_reason(read) != "ordinary" for read in left_reads)
    right_alt = sum(selection_reason(read) != "ordinary" for read in right_reads)
    alt_support = sum(selection_reason(read) != "ordinary" for read in reads)

    flank_width = 64
    left_flank = _coverage(left_reads, max(0, candidate.del_start0 - flank_width), candidate.del_start0)
    right_flank = _coverage(right_reads, candidate.del_end0, candidate.del_end0 + flank_width)
    inside_parts = [
        _coverage(left_reads, candidate.del_start0, min(candidate.del_end0, candidate.del_start0 + flank_width)),
        _coverage(right_reads, max(candidate.del_start0, candidate.del_end0 - flank_width), candidate.del_end0),
    ]
    inside = float(np.mean(inside_parts))
    flank = (left_flank + right_flank) / 2.0
    ratio = inside / max(flank, 1e-6)
    mapqs = [float(getattr(read, "mapping_quality", 0)) for read in reads]
    baseqs = [_mean_base_quality(read) for read in reads]
    inserts = [abs(float(getattr(read, "template_length", 0) or 0)) for read in reads if getattr(read, "is_paired", False)]
    anomaly_fraction = float(np.mean([value > 1_000 for value in inserts])) if inserts else 0.0
    evidence_balance = min(left_alt, right_alt) / max(1, max(left_alt, right_alt))
    values = np.asarray(
        [
            left_soft,
            right_soft,
            split,
            supplementary,
            discordant,
            spanning,
            alt_support,
            inside,
            left_flank,
            right_flank,
            ratio,
            np.mean(mapqs) if mapqs else 0.0,
            np.mean(baseqs) if baseqs else 0.0,
            np.mean(inserts) if inserts else 0.0,
            anomaly_fraction,
            evidence_balance,
            math.log1p(candidate.length),
        ],
        dtype=np.float32,
    )
    if not np.isfinite(values).all():
        raise CandidateExtractionError("non-finite scalar feature")
    return values


def extract_example_from_reads(
    candidate: Candidate,
    left_reads: Sequence,
    right_reads: Sequence,
    fetch_reference: Callable[[str, int, int], str],
) -> ExampleTensors:
    selected = [
        select_reads(left_reads, candidate.del_start0, MAX_IMAGE_READS),
        select_reads(right_reads, candidate.del_end0, MAX_IMAGE_READS),
    ]
    if not selected[0] or not selected[1]:
        raise CandidateExtractionError("empty reads at one or both breakpoints")
    images = np.stack(
        [
            build_pileup_tensor(selected[0], candidate.chrom, candidate.del_start0, fetch_reference),
            build_pileup_tensor(selected[1], candidate.chrom, candidate.del_end0, fetch_reference),
        ]
    )
    read_tokens, read_mask = build_read_tensors(selected, (candidate.del_start0, candidate.del_end0))
    metadata = _read_metadata_arrays(selected)
    return ExampleTensors(
        images=images,
        read_tokens=read_tokens,
        read_mask=read_mask,
        scalars=scalar_features(candidate, selected),
        read_cigar=metadata[0],
        read_strand=metadata[1],
        read_mapq=metadata[2],
        read_mean_bq=metadata[3],
        read_supplementary=metadata[4],
        read_name_hash=metadata[5],
        read_selection_reason=metadata[6],
    )


class RemoteCramSession:
    """One reusable remote CRAM handle with bounded retries and reopening."""

    def __init__(
        self,
        cram_url: str,
        crai_path: str,
        reference_path: str,
        *,
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
        timeout_seconds: int = 120,
    ) -> None:
        self.cram_url = cram_url
        self.crai_path = crai_path
        self.reference_path = reference_path
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.timeout_seconds = timeout_seconds
        self._alignment = None
        os.environ.setdefault("HTS_HTTP_TIMEOUT", str(timeout_seconds))
        os.environ.setdefault("HTS_RETRY", str(max_attempts))

    def open(self) -> None:
        import pysam

        self.close()
        self._alignment = pysam.AlignmentFile(
            self.cram_url,
            "rc",
            reference_filename=self.reference_path,
            index_filename=self.crai_path,
        )

    def close(self) -> None:
        # htslib's cleanup path for a remote HTTP-streamed CRAM can raise
        # OSError("Illegal seek") purely while releasing the network handle,
        # after every read for this session has already completed
        # successfully -- this is a resource-teardown failure, not a data
        # extraction failure. Swallow it here (and always clear the handle,
        # even on failure) rather than let it crash the whole shard and
        # abandon every sample still to be processed. All per-candidate
        # extraction logic, windows, filters, and failure categorization are
        # unchanged; this touches only the cleanup of an already-finished
        # session.
        if self._alignment is not None:
            try:
                self._alignment.close()
            except OSError as exc:
                warnings.warn(f"ignoring CRAM handle close-time error (data already read): {exc!r}", RuntimeWarning)
            finally:
                self._alignment = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def _fetch_once(self, chrom: str, start: int, end: int) -> list:
        if self._alignment is None:
            self.open()
        return list(self._alignment.fetch(chrom, max(0, start), end))

    def fetch_breakpoints(self, candidate: Candidate) -> tuple[list, list, int, float]:
        half = BREAKPOINT_WINDOW // 2
        left_interval = (max(0, candidate.del_start0 - half), candidate.del_start0 + half)
        right_interval = (max(0, candidate.del_end0 - half), candidate.del_end0 + half)
        last_error = None
        started = time.monotonic()
        for attempt in range(1, self.max_attempts + 1):
            fetches = 0
            try:
                if left_interval[1] >= right_interval[0]:
                    reads = self._fetch_once(candidate.chrom, left_interval[0], right_interval[1])
                    fetches = 1
                    left = [read for read in reads if (read.reference_end or 0) > left_interval[0] and read.reference_start < left_interval[1]]
                    right = [read for read in reads if (read.reference_end or 0) > right_interval[0] and read.reference_start < right_interval[1]]
                else:
                    left = self._fetch_once(candidate.chrom, *left_interval)
                    right = self._fetch_once(candidate.chrom, *right_interval)
                    fetches = 2
                return left, right, fetches, time.monotonic() - started
            except Exception as exc:  # htslib raises several transport-specific types
                last_error = exc
                self.close()
                if attempt < self.max_attempts:
                    time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
        raise CandidateExtractionError(
            f"remote_fetch_exhausted:{type(last_error).__name__}:{last_error}"
        )
