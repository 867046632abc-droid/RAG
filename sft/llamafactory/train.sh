#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SFT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORK_DIR="${SCRIPT_DIR}/work"
DATA_DIR="${WORK_DIR}/data"

mkdir -p "${DATA_DIR}"
cp "${SFT_DIR}/dataset/train_alpaca.json" "${DATA_DIR}/train_alpaca.json"
cp "${SFT_DIR}/dataset/valid_alpaca.json" "${DATA_DIR}/valid_alpaca.json"
cp "${SCRIPT_DIR}/dataset_info.json" "${DATA_DIR}/dataset_info.json"
cp "${SCRIPT_DIR}/qwen2_5_0_5b_query_planner_lora.yaml" "${WORK_DIR}/train.yaml"

cd "${WORK_DIR}"
llamafactory-cli train train.yaml
