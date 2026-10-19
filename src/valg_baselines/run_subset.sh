#!/usr/bin/env bash

# Run a small, fixed Valg reproduction subset inside the already prepared
# `valg-repro` Docker container. This script uses only official Valg agents and
# official artifact scripts; it does not modify the Valg algorithm.

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONTAINER="${VALG_CONTAINER:-valg-repro}"
CONTAINER_SCRIPTS="/home/Valg/Valg/scripts"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
HOST_RUN_DIR="${PROJECT_ROOT}/results/valg_baselines/runs/${RUN_ID}"

usage() {
  echo "Usage:"
  echo "  bash src/valg_baselines/run_subset.sh check"
  echo "  bash src/valg_baselines/run_subset.sh xeger"
  echo "  bash src/valg_baselines/run_subset.sh javadbf"
  echo "  bash src/valg_baselines/run_subset.sh route53-infima"
  echo "  bash src/valg_baselines/run_subset.sh core3"
  echo "  bash src/valg_baselines/run_subset.sh all5"
  echo
  echo "Optional projects: jlemmagen, jackson-antpathfilter"
}

project_record() {
  case "$1" in
    xeger)
      echo "agarciadom/xeger|f3b8a33b0f4438d639150b57b9a0257d50c71bc2"
      ;;
    javadbf)
      echo "albfernandez/javadbf|395265f33bcf9080b02f2102c4b6284921cefae2"
      ;;
    route53-infima)
      echo "awslabs/route53-infima|cabce497698e41d610a949e8a5e4a0528170382b"
      ;;
    jlemmagen)
      echo "hlavki/jlemmagen|43f7c636811a1f7fea7ae7db403ec6f3ec60e9b7"
      ;;
    jackson-antpathfilter)
      echo "Antibrumm/jackson-antpathfilter|40f3af16e9a32fec910fadfde144c4b58217d5e7"
      ;;
    *)
      return 1
      ;;
  esac
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

CHECK_ONLY=false
case "$1" in
  check)
    CHECK_ONLY=true
    PROJECTS=()
    ;;
  core3)
    PROJECTS=(xeger javadbf route53-infima)
    ;;
  all5)
    PROJECTS=(xeger javadbf route53-infima jlemmagen jackson-antpathfilter)
    ;;
  *)
    if ! project_record "$1" >/dev/null; then
      echo "[ERROR] Unknown project: $1"
      usage
      exit 2
    fi
    PROJECTS=("$1")
    ;;
esac

mkdir -p "${HOST_RUN_DIR}"

if ! docker info >/dev/null 2>&1; then
  echo "[ERROR] Docker is not available. Start Docker Desktop, then rerun this command."
  exit 1
fi

if ! docker inspect "${CONTAINER}" >/dev/null 2>&1; then
  echo "[ERROR] Container '${CONTAINER}' does not exist."
  echo "Use the already prepared Valg container, or set VALG_CONTAINER to its name."
  exit 1
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}")" != "true" ]]; then
  echo "[INFO] Starting container ${CONTAINER}"
  docker start "${CONTAINER}" >/dev/null
fi

echo "[INFO] Validating the prepared agents"
if ! docker exec "${CONTAINER}" bash -lc "
  set -e
  cd '${CONTAINER_SCRIPTS}'
  test -s valgj-agent.jar
  test -s valgt-agent.jar
  test -s ../experiments/javamop.jar
  test -s ../experiments/tracemop.jar
"; then
  echo "[ERROR] Required agent JARs are missing. Recheck the official Valg artifact setup."
  exit 1
fi

if [[ "${CHECK_ONLY}" == "true" ]]; then
  echo "[READY] Docker, container, and all four required agents are available."
  echo "Next command: bash src/valg_baselines/run_subset.sh xeger"
  exit 0
fi

run_mode() {
  local project_slug="$1"
  local mode="$2"
  local command="$3"
  local log_file="${HOST_RUN_DIR}/${project_slug}/${mode}.console.log"
  local status_file="${HOST_RUN_DIR}/${project_slug}/status.tsv"
  local rc

  echo
  echo "============================================================"
  echo "[RUN] ${project_slug} / ${mode}"
  echo "============================================================"

  set +e
  docker exec "${CONTAINER}" bash -lc "${command}" 2>&1 | tee "${log_file}"
  rc=${PIPESTATUS[0]}
  set -e

  printf '%s\t%s\t%s\n' "${project_slug}" "${mode}" "${rc}" >> "${status_file}"
  if [[ ${rc} -eq 0 ]]; then
    echo "[OK] ${project_slug} / ${mode}"
  else
    echo "[FAILED] ${project_slug} / ${mode}; continuing to the next mode."
  fi
  return 0
}

copy_if_exists() {
  local container_path="$1"
  local host_path="$2"
  if docker exec "${CONTAINER}" bash -lc "test -e '${container_path}'"; then
    docker cp "${CONTAINER}:${container_path}" "${host_path}" >/dev/null
  fi
}

set -e

for slug in "${PROJECTS[@]}"; do
  record="$(project_record "${slug}")"
  repo="${record%%|*}"
  sha="${record#*|}"
  container_output="${CONTAINER_SCRIPTS}/output-subset-${slug}-${RUN_ID}"
  host_project_dir="${HOST_RUN_DIR}/${slug}"
  mkdir -p "${host_project_dir}/artifact-output"
  printf 'project\tmode\texit_code\n' > "${host_project_dir}/status.tsv"
  printf 'slug=%s\nrepo=%s\nsha=%s\ncontainer=%s\ncontainer_output=%s\n' \
    "${slug}" "${repo}" "${sha}" "${CONTAINER}" "${container_output}" \
    > "${host_project_dir}/metadata.txt"

  # 1. ValgJ. The official script also runs the uninstrumented no-RV baseline
  # once because the fourth argument is true.
  run_mode "${slug}" "01-valgj" "
    set -e
    cd '${CONTAINER_SCRIPTS}'
    cp valgj-agent.jar no-track-no-stats-agent.jar
    rm -f '${container_output}/project/violation-counts'
    bash not_collect_traces.sh '${repo}' '${sha}' '${container_output}' true
    mkdir -p '${container_output}/saved-logs'
    cp '${container_output}/logs/initial-test.log' '${container_output}/saved-logs/no-rv-baseline.log'
    cp '${container_output}/logs/mop.log' '${container_output}/saved-logs/valgj-mop.log'
    if [[ -f '${container_output}/project/violation-counts' ]]; then
      cp '${container_output}/project/violation-counts' '${container_output}/saved-logs/valgj-violation-counts.txt'
    fi
  "

  # 2. Full JavaMOP on the same checkout and Maven dependency cache.
  run_mode "${slug}" "02-javamop" "
    set -e
    cd '${CONTAINER_SCRIPTS}'
    cp ../experiments/javamop.jar no-track-no-stats-agent.jar
    rm -f '${container_output}/project/violation-counts'
    bash not_collect_traces.sh '${repo}' '${sha}' '${container_output}' false
    mkdir -p '${container_output}/saved-logs'
    cp '${container_output}/logs/mop.log' '${container_output}/saved-logs/javamop-mop.log'
    if [[ -f '${container_output}/project/violation-counts' ]]; then
      cp '${container_output}/project/violation-counts' '${container_output}/saved-logs/javamop-violation-counts.txt'
    fi
  "

  # 3. ValgT selective trace collection.
  run_mode "${slug}" "03-valgt" "
    set -e
    cd '${CONTAINER_SCRIPTS}'
    cp valgt-agent.jar track-no-stats-agent.jar
    rm -f '${container_output}/project/violation-counts'
    bash collect_traces.sh '${repo}' '${sha}' '${container_output}' false
    mkdir -p '${container_output}/saved-logs'
    cp '${container_output}/logs/traces.log' '${container_output}/saved-logs/valgt-traces.log'
    if [[ -d '${container_output}/all-traces' ]]; then
      mv '${container_output}/all-traces' '${container_output}/valgt-all-traces'
    fi
    if [[ -f '${container_output}/project/violation-counts' ]]; then
      cp '${container_output}/project/violation-counts' '${container_output}/saved-logs/valgt-violation-counts.txt'
    fi
  "

  # 4. Full TraceMOP. A timeout here is recorded but does not erase the other
  # successful modes or stop the remaining projects.
  run_mode "${slug}" "04-tracemop" "
    set -e
    cd '${CONTAINER_SCRIPTS}'
    cp ../experiments/tracemop.jar track-no-stats-agent.jar
    rm -f '${container_output}/project/violation-counts'
    bash collect_traces.sh '${repo}' '${sha}' '${container_output}' false
    mkdir -p '${container_output}/saved-logs'
    cp '${container_output}/logs/traces.log' '${container_output}/saved-logs/tracemop-traces.log'
    if [[ -d '${container_output}/all-traces' ]]; then
      mv '${container_output}/all-traces' '${container_output}/tracemop-all-traces'
    fi
    if [[ -f '${container_output}/project/violation-counts' ]]; then
      cp '${container_output}/project/violation-counts' '${container_output}/saved-logs/tracemop-violation-counts.txt'
    fi
  "

  echo "[INFO] Copying compact results from Docker to ${host_project_dir}/artifact-output"
  copy_if_exists "${container_output}/saved-logs" "${host_project_dir}/artifact-output/"
  copy_if_exists "${container_output}/logs" "${host_project_dir}/artifact-output/official-logs"
  copy_if_exists "${container_output}/valgt-all-traces" "${host_project_dir}/artifact-output/"
  copy_if_exists "${container_output}/tracemop-all-traces" "${host_project_dir}/artifact-output/"

  # Preserve failed/partial trace directories for diagnosis without treating
  # them as successful data.
  while IFS= read -r partial_dir; do
    [[ -n "${partial_dir}" ]] || continue
    partial_name="$(basename "${partial_dir}")"
    copy_if_exists "${partial_dir}" "${host_project_dir}/artifact-output/partial-${partial_name}"
  done < <(docker exec "${CONTAINER}" bash -lc "find '${container_output}' -maxdepth 1 -type d -name 'all-traces*' -print" 2>/dev/null)
done

echo
echo "[INFO] Building summary CSV"
python3 "${SCRIPT_DIR}/summarize_subset.py" "${HOST_RUN_DIR}"

echo
echo "[DONE] Results are in:"
echo "  ${HOST_RUN_DIR}"
echo "Open summary.csv first. Failed modes remain visible in each status.tsv."
