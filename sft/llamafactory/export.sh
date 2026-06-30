#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work"

cp "${SCRIPT_DIR}/qwen2_5_0_5b_query_planner_export.yaml" "${WORK_DIR}/export.yaml"
cd "${WORK_DIR}"
llamafactory-cli export export.yaml
