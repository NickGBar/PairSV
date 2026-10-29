#!/bin/bash
# Retry pass for the 4 POC samples after their first attempt all failed on
# Docker Desktop instability (decision 0025). Same frozen Manta config
# (decisions 0016-0018), no caller/Truvari parameter changes. HG02601's CRAM
# survived its config-only failure and is reused as-is; the other three need
# a fresh download since their CRAMs were deleted (already checksummed) to
# relieve disk pressure during the first pass.
set -u

BASE=/Users/nikolai/DNA/deletion_calling/manta_poc
DIGEST="sha256:48d0c2464fa0129935438c5cddec5f67c4b3d65e8f7a647f95164ee51662cc70"
MASTER_LOG="$BASE/retry_four_wgs_master.log"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$MASTER_LOG"; }

get_url() {
  case "$1" in
    HG01912) echo "https://ftp.sra.ebi.ac.uk/vol1/run/ERR324/ERR3242234/HG01912.final.cram" ;;
    HG00736) echo "https://ftp.sra.ebi.ac.uk/vol1/run/ERR324/ERR3241756/HG00736.final.cram" ;;
    HG00436) echo "https://ftp.sra.ebi.ac.uk/vol1/run/ERR324/ERR3241673/HG00436.final.cram" ;;
    HG02601) echo "https://ftp.sra.ebi.ac.uk/vol1/run/ERR324/ERR3242400/HG02601.final.cram" ;;
  esac
}
get_size() {
  case "$1" in
    HG01912) echo 14133539017 ;;
    HG00736) echo 17648023901 ;;
    HG00436) echo 14273715124 ;;
    HG02601) echo 15275521140 ;;
  esac
}
get_md5() {
  case "$1" in
    HG01912) echo "00b340835cdddf5c65bf15062f009c89" ;;
    HG00736) echo "a3102972323f61b147ebafeb717c4c0a" ;;
    HG00436) echo "c77f2d76278c73b85e2f56528cf60cc6" ;;
    HG02601) echo "a21fa3c889efbc00bd752961ea17858b" ;;
  esac
}
get_pop() {
  case "$1" in
    HG01912) echo "ACB" ;; HG00736) echo "PUR" ;; HG00436) echo "CHS" ;; HG02601) echo "PJL" ;;
  esac
}
get_superpop() {
  case "$1" in
    HG01912) echo "AFR" ;; HG00736) echo "AMR" ;; HG00436) echo "EAS" ;; HG02601) echo "SAS" ;;
  esac
}

# HG02601 first (CRAM already present from the first pass), then the 3 that
# need a fresh download.
SAMPLES="HG02601 HG01912 HG00736 HG00436"

for SAMPLE in $SAMPLES; do
  log "=== RETRY START $SAMPLE ==="
  SDIR="$BASE/local_slices/${SAMPLE}_full"
  mkdir -p "$SDIR"
  CRAM="$SDIR/${SAMPLE}.final.cram"
  CRAI="$CRAM.crai"
  URL="$(get_url "$SAMPLE")"
  EXPECTED="$(get_size "$SAMPLE")"

  have=$(stat -f%z "$CRAM" 2>/dev/null || echo 0)
  if [ "$have" -ge "$EXPECTED" ]; then
    log "$SAMPLE: CRAM already present and complete ($have bytes), skipping download"
  else
    if [ ! -s "$CRAI" ]; then
      curl -s -o "$CRAI" "${URL}.crai"
      log "$SAMPLE: crai downloaded ($(stat -f%z "$CRAI" 2>/dev/null) bytes)"
    fi
    ATTEMPT=0
    while true; do
      ATTEMPT=$((ATTEMPT+1))
      have=$(stat -f%z "$CRAM" 2>/dev/null || echo 0)
      if [ "$have" -ge "$EXPECTED" ]; then log "$SAMPLE: download complete ($have bytes)"; break; fi
      log "$SAMPLE: download attempt $ATTEMPT, resuming from $have/$EXPECTED"
      curl -s -C - --speed-time 30 --speed-limit 2000 -o "$CRAM" "$URL"
      rc=$?
      have=$(stat -f%z "$CRAM" 2>/dev/null || echo 0)
      log "$SAMPLE: attempt $ATTEMPT curl exit=$rc have=$have"
      if [ "$have" -ge "$EXPECTED" ]; then log "$SAMPLE: download complete ($have bytes)"; break; fi
      sleep 3
    done
  fi

  QC_STATUS="FAILED"
  if samtools quickcheck -v "$CRAM" 2>>"$MASTER_LOG"; then
    QC_STATUS="PASSED"
  fi
  log "$SAMPLE: quickcheck $QC_STATUS"

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
    log "$SAMPLE: CONFIG FAILED, skipping to next sample without deleting CRAM"
    continue
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
    "/work/${SAMPLE}_wgs/runWorkflow.py" -m local -j 4 -g 5 \
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
    echo "RETRY_ATTEMPT=2"
  } > "$BASE/results/${SAMPLE}_wgs_exit_code.txt"

  LOCAL_SHA=$(shasum -a 256 "$CRAM" | awk '{print $1}')
  log "$SAMPLE: local CRAM sha256=$LOCAL_SHA"

  python3 "$BASE/write_wgs_provenance.py" "$SAMPLE" "$LOCAL_SHA" "$REAL_EXIT" "$ELAPSED" \
    "$EXPECTED" "$(get_md5 "$SAMPLE")" "$URL" "$(get_pop "$SAMPLE")" "$(get_superpop "$SAMPLE")" "$PEAK_MEM" "$QC_STATUS" \
    >> "$MASTER_LOG" 2>&1

  if [ "$REAL_EXIT" -eq 0 ]; then
    rm -f "$CRAM"
    log "$SAMPLE: CRAM removed after successful run (documented sha256=$LOCAL_SHA, re-downloadable from $URL)"
  else
    log "$SAMPLE: WARNING runWorkflow did not exit 0 -- KEEPING CRAM for investigation"
  fi
  log "=== RETRY END $SAMPLE ==="
done

log "RETRY PASS COMPLETE FOR ALL 4 SAMPLES"
