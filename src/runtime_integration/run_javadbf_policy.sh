#!/usr/bin/env bash
# Run one real javadbf configuration with a policy already exported by export_policy.py.
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "Usage: bash run_javadbf_policy.sh CONTAINER POLICY_FILE OUTPUT_NAME [REPETITIONS]"
  exit 2
fi

CONTAINER="$1"
POLICY_FILE="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
OUTPUT_NAME="$3"
REPETITIONS="${4:-5}"
CONTAINER_SCRIPTS="/home/Valg/Valg/scripts"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="albfernandez/javadbf"
SHA="395265f33bcf9080b02f2102c4b6284921cefae2"

if [[ ! -f "${POLICY_FILE}" ]]; then
  echo "[ERROR] Policy file not found: ${POLICY_FILE}"
  exit 1
fi

docker exec "${CONTAINER}" mkdir -p "${CONTAINER_SCRIPTS}/policies"
docker cp "${POLICY_FILE}" "${CONTAINER}:${CONTAINER_SCRIPTS}/policies/${OUTPUT_NAME}.tsv" >/dev/null

for repetition in $(seq 1 "${REPETITIONS}"); do
  output="${CONTAINER_SCRIPTS}/output-${OUTPUT_NAME}-r${repetition}"
  console_log="${OUTPUT_NAME}-r${repetition}.console.log"
  stats_log="${OUTPUT_NAME}-r${repetition}.docker-memory.log"
  echo "[RUN] ${OUTPUT_NAME}, repetition ${repetition}/${REPETITIONS}"
  set +e
  docker exec \
    -e VALG_SELECTION_FILE="${CONTAINER_SCRIPTS}/policies/${OUTPUT_NAME}.tsv" \
    -e VALG_SELECTION_LOG="${output}/selection-decisions.tsv" \
    "${CONTAINER}" bash -lc "
      set -e
      cd '${CONTAINER_SCRIPTS}'
      cp valgj-policy-agent.jar no-track-no-stats-agent.jar
      bash not_collect_traces.sh '${REPO}' '${SHA}' '${output}' true
    " 2>&1 | tee "${console_log}" &
  run_pid=$!
  : > "${stats_log}"
  while kill -0 "${run_pid}" 2>/dev/null; do
    docker stats --no-stream --format '{{.MemUsage}}' "${CONTAINER}" >> "${stats_log}" 2>/dev/null || true
    sleep 0.25
  done
  wait "${run_pid}"
  run_status=$?
  set -e
  if [[ ${run_status} -ne 0 ]]; then
    echo "[ERROR] Runtime execution failed; see ${console_log}"
    exit "${run_status}"
  fi
  docker cp "${CONTAINER}:${output}/selection-decisions.tsv" "${OUTPUT_NAME}-r${repetition}.selection-decisions.tsv"
  docker cp "${CONTAINER}:${output}/logs/mop.log" "${OUTPUT_NAME}-r${repetition}.mop.log"
  duration_ms="$(awk '/\[OK\] Duration:/ {print $(NF-1)}' "${console_log}" | tail -n 1)"
  peak_kb="$(python3 "${SCRIPT_DIR}/parse_peak_memory.py" "${stats_log}")"
  metrics="${OUTPUT_NAME}-metrics.csv"
  if [[ ! -f "${metrics}" ]]; then
    echo "project,configuration,repetition,elapsed_seconds,peak_container_memory_kb" > "${metrics}"
  fi
  awk -v name="${OUTPUT_NAME}" -v rep="${repetition}" -v ms="${duration_ms}" -v kb="${peak_kb}" \
    'BEGIN {printf "javadbf,%s,%d,%.3f,%d\n", name, rep, ms/1000, kb}' >> "${metrics}"
done

echo "[DONE] Logs and monitor create/skip counts are in the current directory."
