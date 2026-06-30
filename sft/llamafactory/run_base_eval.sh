#!/usr/bin/env bash
set -euo pipefail

# Start your base Qwen2.5-0.5B-Instruct OpenAI-compatible server first, then run this.
# Example server options: vLLM, SGLang, llama.cpp, or LLaMA-Factory API.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SFT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

python "${SFT_DIR}/eval_query_planner.py" \
  --mode endpoint \
  --input "${SFT_DIR}/dataset/valid_alpaca.json" \
  --output "${SFT_DIR}/eval_results/base_qwen2_5_0_5b.json" \
  --model "${EVAL_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}" \
  --base-url "${EVAL_BASE_URL:-http://127.0.0.1:8000/v1}"
