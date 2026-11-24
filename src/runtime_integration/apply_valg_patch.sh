#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALG_ROOT="${1:-}"

if [[ -z "${VALG_ROOT}" || ! -d "${VALG_ROOT}/.git" ]]; then
  echo "Usage: bash apply_valg_patch.sh /absolute/path/to/Valg"
  exit 2
fi

PATCH="${SCRIPT_DIR}/valg_patch/selective-location-policy.patch"
if git -C "${VALG_ROOT}" apply --check "${PATCH}"; then
  git -C "${VALG_ROOT}" apply "${PATCH}"
  echo "[OK] Selective-location runtime patch applied."
elif git -C "${VALG_ROOT}" apply --reverse --check "${PATCH}"; then
  echo "[OK] Patch was already applied; no files changed."
else
  echo "[ERROR] Patch does not apply cleanly. Use the official Valg revision recorded below."
  exit 1
fi

echo "Valg revision used during development: $(git -C "${VALG_ROOT}" rev-parse HEAD)"
