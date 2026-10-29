"""Candidate-aware REF/ALT construction for the second research phase.

The genomic branch must see the *specific candidate deletion*, not a static
reference locus. For a candidate deletion on ``chrom`` spanning the 0-based
half-open interval ``[cstart, cend)`` we build two fixed-length sequences with
flank ``F``:

    REF = ref[cstart-F : cstart]  +  ref[cstart : cstart+F]      # = ref[cstart-F : cstart+F]
    ALT = ref[cstart-F : cstart]  +  ref[cend   : cend+F]        # breakpoint junction

Both are ``2F`` bp; the junction sits at index ``F`` (REF: the base at
``cstart``; ALT: between the last left-flank base ``cstart-1`` and the first
right-flank base ``cend``). Out-of-contig positions are N-padded so the length
is always ``2F``.

CRITICAL coordinate rule (see the Stage-1 spec):
  * POSITIVE rows: the true interval comes from ``source_del`` (the original
    truth-VCF interval ``chrom:start-end``), NOT from ``position + del_length``
    — ``position`` may be a left/right/centre/jittered *image* window, which
    would place the junction wrong. Every augmented row of one deletion maps to
    the SAME candidate.
  * NEGATIVE rows: no real interval. Use a pseudo-interval
    ``[pseudo_start, pseudo_start + del_length)`` where ``pseudo_start`` is the
    negative's TRUE genomic position (from the image filename, because the
    random-negative manifest ``chrom`` is known-wrong), and ``del_length`` is
    the matched source-deletion length → a counterfactual junction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple


def parse_source_del(source_del: str) -> Tuple[str, int, int]:
    """``"16:1000-2000"`` -> ``("16", 1000, 2000)`` (0-based half-open)."""
    chrom, span = source_del.rsplit(":", 1)
    a, b = span.split("-")
    return chrom, int(a), int(b)


def true_coord_from_image(image_path: str) -> Tuple[str, int]:
    """Image basename ``{true_chrom}_{start}_{end}_{label}_{tag}.png`` ->
    ``(true_chrom, start)``. This is the authoritative (chrom, position) — the
    manifest chrom is wrong for random negatives."""
    import os
    parts = os.path.basename(image_path).split("_")
    return parts[0], int(parts[1])


@dataclass(frozen=True)
class Candidate:
    chrom: str
    cstart: int          # 0-based, inclusive
    cend: int            # 0-based, exclusive
    ctype: str           # "positive" | "anchor_up" | "anchor_down" | "regional" | "random"

    @property
    def cid(self) -> str:
        return f"{self.chrom}:{self.cstart}-{self.cend}:{self.ctype}"

    @property
    def length(self) -> int:
        return self.cend - self.cstart


def candidate_for_row(row: dict) -> Candidate:
    """Map a manifest row to its candidate. ``row`` needs keys: ``label``,
    ``source_del``, ``del_length``, ``neg_type``, ``image_path``."""
    label = int(row["label"])
    if label == 1:
        chrom, dstart, dend = parse_source_del(row["source_del"])
        return Candidate(chrom, dstart, dend, "positive")
    # negative: pseudo interval at the negative's TRUE position, matched length
    tchrom, tpos = true_coord_from_image(row["image_path"])
    L = int(row["del_length"])
    ctype = row.get("neg_type") or "negative"
    return Candidate(tchrom, tpos, tpos + L, ctype)


def slice_ref(get_len: int, get: Callable[[int, int], str], a: int, b: int) -> str:
    """Return ``ref[a:b]`` uppercased, N-padded to exactly ``b-a`` bp for
    out-of-contig positions. ``get(s, e)`` returns the raw contig slice for
    ``0 <= s <= e <= get_len``."""
    s = max(0, a)
    e = min(get_len, b)
    core = get(s, e).upper() if e > s else ""
    return ("N" * (s - a)) + core + ("N" * (b - e))


def build_ref_alt(chrom_len: int, get: Callable[[int, int], str],
                  cstart: int, cend: int, flank: int) -> Tuple[str, str]:
    """Build the ``2*flank`` bp REF and ALT sequences. ``get(s, e)`` returns the
    contig slice ``ref[s:e]`` (0-based half-open, already within bounds)."""
    left = slice_ref(chrom_len, get, cstart - flank, cstart)   # F bp
    body = slice_ref(chrom_len, get, cstart, cstart + flank)   # F bp (REF right half)
    right = slice_ref(chrom_len, get, cend, cend + flank)      # F bp (ALT right half)
    ref_seq = left + body
    alt_seq = left + right
    assert len(ref_seq) == len(alt_seq) == 2 * flank, (len(ref_seq), len(alt_seq))
    return ref_seq, alt_seq
