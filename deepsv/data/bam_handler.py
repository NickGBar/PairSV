"""BAM file handling and read extraction"""
from typing import List, Tuple, Optional
import pysam
import numpy as np
import pandas as pd


class BAMHandler:
    """Handles BAM file operations and read extraction"""
    
    def __init__(self, bam_path: str):
        """
        Initialize BAM handler
        
        Args:
            bam_path: Path to BAM file
        """
        self.bam_path = bam_path
        self._bam_file: Optional[pysam.AlignmentFile] = None
    
    def __enter__(self):
        """Context manager entry"""
        self._bam_file = pysam.AlignmentFile(self.bam_path, "rb")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self._bam_file:
            self._bam_file.close()
    
    def get_coverage_depth(self, chrom: str, start: int, end: int) -> np.ndarray:
        """
        Calculate coverage depth for a region
        
        Args:
            chrom: Chromosome name
            start: Start position
            end: End position
            
        Returns:
            Array of depth values
        """
        if not self._bam_file:
            raise RuntimeError("BAM file not opened. Use context manager.")
        
        coverage = self._bam_file.count_coverage(chrom, start, end, quality_threshold=0)
        depth = np.array(list(coverage)).sum(axis=0)
        return depth
    
    def get_clipping_info(self, chrom: str, start: int, end: int) -> dict:
        """
        Extract per-base clipping/mapping-anomaly signal for a region.

        For every read overlapping [start, end), each genomic position is
        mapped back to that read's own query-sequence index, and the CIGAR
        operation actually covering that specific base is looked up via
        :meth:`_get_cigar_at_position` — the same helper
        :meth:`get_pileup_data` already uses, so there is one CIGAR-walk
        implementation instead of two.

        Bug fix (was: compare absolute genomic position against a
        cumulative CIGAR-length counter). Genomic coordinates are
        essentially always larger than that counter (which tops out around
        the read length), so the old comparison was true for every CIGAR
        op on every call — every position of a given read collapsed to
        that read's *last* CIGAR operation, regardless of which base
        ``pos`` actually referred to. Fixed by mapping ``pos`` to a
        query-relative index first, matching what :meth:`get_pileup_data`
        already did correctly.

        Args:
            chrom: Chromosome name
            start: Start position (inclusive)
            end: End position (exclusive)

        Returns:
            Dictionary mapping position → summed clipping signal across
            overlapping reads, integer-divided by 4 (same output scale as
            before, so downstream consumers are unaffected by the fix).
        """
        if not self._bam_file:
            raise RuntimeError("BAM file not opened. Use context manager.")

        clip_temp: List[Tuple[int, int]] = []

        for read in self._bam_file.fetch(chrom, start, end):
            if read.cigarstring is None:
                continue

            # Determine effective read span the same way legacy did:
            #   base_pos = read.get_reference_positions(full_length=True)
            #   count leading Nones → soft-clipped query bases at the start
            #   read_start = reference_start - leading_nones
            #   read_end   = read_start + read_len - 1
            base_pos = read.get_reference_positions(full_length=True)
            read_len = len(base_pos)

            leading_nones = 0
            for p in base_pos:
                if p is not None:
                    break
                leading_nones += 1

            read_start = read.reference_start - leading_nones
            read_end = read_start + read_len - 1

            # Map each reference position this read has an aligned base for
            # back to its query index, so we can look up the CIGAR
            # operation covering that specific base (not the read's last op).
            ref_to_query = {}
            for qi, rp in enumerate(base_pos):
                if rp is not None and rp not in ref_to_query:
                    ref_to_query[rp] = qi

            for i in range(end - start):
                pos = start + i
                if pos < read_start or pos > read_end:
                    continue

                query_idx = ref_to_query.get(pos)
                if query_idx is None:
                    # `pos` falls inside a deletion in this read relative to
                    # the reference — no aligned base to score here.
                    continue

                map_type = self._get_cigar_at_position(read, query_idx)
                clip_temp.append((pos, -map_type))

        if not clip_temp:
            return {}

        clip_record_np = np.array(clip_temp)
        df = pd.DataFrame(clip_record_np, columns=[0, 1])
        clip_record_df = df.groupby(0)[1].sum()
        clip_record_df = clip_record_df // 4
        temp = clip_record_df.reset_index()
        clip_record = np.array(temp).tolist()
        return {int(row[0]): int(row[1]) for row in clip_record}

    def _get_cigar_at_position(self, read: pysam.AlignedSegment, query_pos: int) -> int:
        """Get CIGAR operation type at a query position.

        Replicates the legacy ``pipeup_column`` CIGAR walk: advance a
        cumulative index by **every** CIGAR operation length (not only
        query-consuming ones) and compare against ``query_position``.

        Uses ``>=`` (not ``>``) so the first base of each operation —
        including ``query_pos == 0``, the very first base of the read —
        resolves to that operation instead of falling through to whatever
        the *previous* operation's default was. With ``>``, a read that is
        soft-clipped starting at its first base (a common case) would
        report ``query_pos == 0`` as unclipped, since the comparison never
        advanced past the initial ``index = 0``.
        """
        index = 0
        map_type = -1
        for op, length in read.cigartuples:
            if query_pos >= index:
                index = length + index
                map_type = op
        return map_type
    
    def get_pileup_data(self, chrom: str, start: int, end: int) -> List[Tuple]:
        """
        Extract pileup data for a region

        Args:
            chrom: Chromosome name
            start: Start position
            end: End position

        Returns:
            List of pileup records (pos, is_paired, is_proper_pair, mapq, cigar_type, base)
        """
        if not self._bam_file:
            raise RuntimeError("BAM file not opened. Use context manager.")

        pileup_records = []
        for pileup_column in self._bam_file.pileup(chrom, start, end):
            if start <= pileup_column.pos < end:
                for pileup_read in pileup_column.pileups:
                    alignment = pileup_read.alignment
                    if alignment.cigarstring is None or pileup_read.query_position is None:
                        continue

                    cigar_type = self._get_cigar_at_position(
                        alignment, pileup_read.query_position
                    )

                    base = alignment.query_sequence[pileup_read.query_position]
                    record = (
                        pileup_column.pos,
                        alignment.is_paired,
                        alignment.is_proper_pair,
                        alignment.mapping_quality,
                        cigar_type,
                        base,
                    )
                    pileup_records.append(record)

        return pileup_records
