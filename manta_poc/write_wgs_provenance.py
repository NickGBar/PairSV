#!/usr/bin/env python3
"""Write a whole-genome Manta provenance JSON for one POC sample, matching
the exact structure used for HG00108 (manta_poc/results/HG00108_wgs_provenance.json)."""
import json
import sys

sample = sys.argv[1]
local_sha256 = sys.argv[2]
exit_code = int(sys.argv[3])
elapsed_seconds = int(sys.argv[4])
cram_size = int(sys.argv[5])
cram_md5 = sys.argv[6]
cram_url = sys.argv[7]
population = sys.argv[8]
super_pop = sys.argv[9]
peak_mem_mib = float(sys.argv[10]) if len(sys.argv) > 10 and sys.argv[10] else None
quickcheck_status = sys.argv[11] if len(sys.argv) > 11 else "unknown"

out = {
    "run": f"{sample} whole-genome ({super_pop}/{population})",
    "manta": {
        "version": "1.6.0",
        "container_image": "quay.io/biocontainers/manta",
        "container_tag": "1.6.0--py27h9948957_6",
        "container_digest": "sha256:48d0c2464fa0129935438c5cddec5f67c4b3d65e8f7a647f95164ee51662cc70",
        "container_digest_source": "same pinned digest used for HG00108 chr21 smoke test and whole-genome run, reused unchanged",
    },
    "platform_note": "amd64 image run under emulation on an arm64 (Apple Silicon) host via Docker Desktop; runtime/CPU figures reflect this, not native execution",
    "reference": {
        "url": "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/GRCh38_reference_genome/GRCh38_full_analysis_set_plus_decoy_hla.fa",
        "sha256_locally_computed": "3b103f4742abfd54938fb0333e19ad067635c8eb86f1dbf0ce44b165c4292b50",
        "note_no_official_checksum": "No official MD5/SHA published for this file; identical local copy reused unchanged from HG00108's run (same physical file, unmodified)",
        "contig_count": 3366,
    },
    "sample": {
        "id": sample,
        "population": population,
        "super_pop": super_pop,
        "cram_url": cram_url,
        "cram_md5_from_official_sequence_index": cram_md5,
        "local_full_cram": f"manta_poc/local_slices/{sample}_full/{sample}.final.cram",
        "local_full_cram_size_bytes": cram_size,
        "local_full_cram_sha256": local_sha256,
        "acquisition_method": "direct byte-for-byte resumable curl download (no samtools re-encode) -- original CRAM confirmed v3.0 via magic-byte check before download, same as HG00108 (decision 0017)",
        "cram_format_version": "3.0",
        "cram_quickcheck": quickcheck_status,
        "cram_header_contig_count": 3366,
    },
    "command_lines": {
        "configManta": f"configManta.py --bam=/bam/{sample}.final.cram --referenceFasta=/ref/GRCh38_full.fa --runDir=/work/{sample}_wgs",
        "configManta_note": "no --callRegions -- whole genome, unchanged frozen configuration from HG00108",
        "runWorkflow": f"/work/{sample}_wgs/runWorkflow.py -m local -j 4 -g 5",
    },
    "resources": {
        "docker_cpus": 8,
        "docker_memory_limit_gib": 5.785,
        "runWorkflow_job_limit": 4,
        "runWorkflow_mem_limit_gb": 5,
        "observed_peak_memory_mib": peak_mem_mib,
    },
    "runtime": {
        "elapsed_seconds": elapsed_seconds,
        "elapsed_human": f"{elapsed_seconds // 3600}h{(elapsed_seconds % 3600) // 60}m{elapsed_seconds % 60}s",
        "workflow_version": "1.6.0",
    },
    "result": {
        "exit_code_verified_no_pipe_masking": exit_code,
        "status": "PASS" if exit_code == 0 else "FAIL",
    },
    "frozen_config_note": "Identical Manta version, container digest, reference, and command-line flags as HG00108 (decisions 0016-0018). No caller or Truvari parameter changes.",
}

path = f"/Users/nikolai/DNA/deletion_calling/manta_poc/results/{sample}_wgs_provenance.json"
with open(path, "w") as f:
    json.dump(out, f, indent=2)
print(f"wrote {path}")
