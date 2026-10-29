"""PAIR-SV multisample data preparation and extraction utilities."""

from .manifest import (
    MANIFEST_SCHEMA_VERSION,
    assign_person_shards,
    normalize_pure_deletion,
    validate_pair_manifest,
)
from .extraction import (
    IMAGE_SHAPE,
    READ_MASK_SHAPE,
    READ_TOKEN_SHAPE,
    SCALAR_FEATURE_NAMES,
    Candidate,
    CandidateExtractionError,
    extract_example_from_reads,
    select_reads,
)

__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "IMAGE_SHAPE",
    "READ_MASK_SHAPE",
    "READ_TOKEN_SHAPE",
    "SCALAR_FEATURE_NAMES",
    "Candidate",
    "CandidateExtractionError",
    "assign_person_shards",
    "extract_example_from_reads",
    "normalize_pure_deletion",
    "select_reads",
    "validate_pair_manifest",
]
