#!/bin/bash
# Manual out-of-band retry for HG00436: its CRAM already downloaded and
# quickcheck-passed cleanly, but configManta failed because Docker Desktop
# was in the memory-starvation crash loop (decision 0030) at the time. No
# need to re-download -- just run configManta+runWorkflow directly.
set -u
BASE=/Users/nikolai/DNA/deletion_calling/manta_poc
DIGEST="sha256:48d0c2464fa0129935438c5cddec5f67c4b3d65e8f7a647f95164ee51662cc70"
SAMPLE=HG00436
SDIR="$BASE/local_slices/${SAMPLE}_full"
MASTER_LOG="$BASE/retry_four_wgs_master.log"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$MASTER_LOG"; }

log "=== MANUAL RETRY START $SAMPLE (CRAM reused, Docker-only retry) ==="

QC_STATUS="FAILED"
if samtools quickcheck -v "$SDIR/${SAMPLE}.final.cram" 2>>"$MASTER_LOG"; then
  QC_STATUS="PASSED"
fi
log "$SAMPLE: quickcheck (re-verified) $QC_STATUS"

RUNDIR="$BASE/results/${SAMPLE}_wgs"
rm -rf "$RUNDIR"
docker run --rm \
  -v "$BASE/reference:/ref" \
  -v "$SDIR:/bam" \
  -v "$BASE/results:/work" \
  "quay.io/biocontainers/manta@$DIGEST" \
  configManta.py --bam="/bam/${SAMPLE}.final.cram" --referenceFasta=/ref/GRCh38_full.fa --runDir="/work/${SAMPLE}_wgs" \
  >> "$MASTER_LOG" 2>&1
CONFIG_EXIT=$?
log "$SAMPLE: configManta exit=$CONFIG_EXIT"
if [ "$CONFIG_EXIT" -ne 0 ]; then
  log "$SAMPLE: CONFIG FAILED, aborting manual retry"
  exit 1
fi

STATS_LOG="$BASE/results/${SAMPLE}_wgs_docker_stats.log"
> "$STATS_LOG"
(
  while docker ps --filter "name=manta_wgs_${SAMPLE}" --format '{{.Names}}' 2>/dev/null | grep -q "manta_wgs_${SAMPLE}"; do
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    stats=$(docker stats "manta_wgs_${SAMPLE}" --no-stream --format '{{.MemUsage}}\t{{.CPUPerc}}' 2>/dev/null)
    echo -e "$ts\t$stats" >> "$STATS_LOG"
    sleep 30
  done
) &

START_EPOCH=$(date +%s)
docker run --rm \
  -v "$BASE/reference:/ref" \
  -v "$SDIR:/bam" \
  -v "$BASE/results:/work" \
  --name "manta_wgs_${SAMPLE}" \
  "quay.io/biocontainers/manta@$DIGEST" \
  "/work/${SAMPLE}_wgs/runWorkflow.py" -m local -j 4 -g 3 \
  > "$BASE/results/${SAMPLE}_wgs_run.log" 2>&1
REAL_EXIT=$?
END_EPOCH=$(date +%s)
ELAPSED=$((END_EPOCH - START_EPOCH))
PEAK_MEM=$(python3 -c "
import re
peak=0.0
try:
    for line in open('$STATS_LOG'):
        m = re.search(r'([0-9.]+)(GiB|MiB)', line)
        if not m: continue
        val = float(m.group(1)) * (1024 if m.group(2)=='GiB' else 1)
        peak = max(peak, val)
except FileNotFoundError:
    pass
print(round(peak,1))
" 2>/dev/null)
log "$SAMPLE: runWorkflow exit=$REAL_EXIT elapsed=${ELAPSED}s peak_mem_mib=$PEAK_MEM"
{
  echo "REAL_EXIT_CODE=$REAL_EXIT"
  echo "ELAPSED_SECONDS=$ELAPSED"
  echo "START_UTC=$(date -u -r "$START_EPOCH" +%Y-%m-%dT%H:%M:%SZ)"
  echo "END_UTC=$(date -u -r "$END_EPOCH" +%Y-%m-%dT%H:%M:%SZ)"
  echo "RETRY_ATTEMPT=3_manual_docker_only"
} > "$BASE/results/${SAMPLE}_wgs_exit_code.txt"

LOCAL_SHA=$(shasum -a 256 "$SDIR/${SAMPLE}.final.cram" | awk '{print $1}')
log "$SAMPLE: local CRAM sha256=$LOCAL_SHA"

python3 "$BASE/write_wgs_provenance.py" "$SAMPLE" "$LOCAL_SHA" "$REAL_EXIT" "$ELAPSED" \
  14273715124 "c77f2d76278c73b85e2f56528cf60cc6" \
  "https://ftp.sra.ebi.ac.uk/vol1/run/ERR324/ERR3241673/HG00436.final.cram" "CHS" "EAS" "$PEAK_MEM" "$QC_STATUS" \
  >> "$MASTER_LOG" 2>&1

if [ "$REAL_EXIT" -eq 0 ]; then
  rm -f "$SDIR/${SAMPLE}.final.cram"
  log "$SAMPLE: CRAM removed after successful run (documented sha256=$LOCAL_SHA)"
else
  log "$SAMPLE: WARNING runWorkflow did not exit 0 -- KEEPING CRAM for investigation"
fi
log "=== MANUAL RETRY END $SAMPLE ==="
