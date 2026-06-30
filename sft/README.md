# Query Planner SFT Data Generation

This folder contains scripts for generating high-quality SFT samples for the RAG query planner.

The intended training target is **not** question answering. It is:

```text
raw semiconductor user question -> structured retrieval query_plan JSON
```

The generated data can be used by LLaMA-Factory with LoRA, for example on Qwen2.5-0.5B-Instruct.

## Files

- `generate_seed_query_plan_data.py`: reads `datas/md/*.md`, chunks documents, calls Seed2.0, validates/deduplicates samples, and writes raw + Alpaca-format data.
- `results/`: default output directory.

## Environment

Do not write API keys into code. Export them before running:

```bash
export ARK_API_KEY='your-key'
export SEED_MODEL='doubao-seed-2-0-pro-260215'
export SEED_BASE_URL='https://ark.cn-beijing.volces.com/api/v3'
```

If the internal Merlin environment uses a different Seed model name or compatible endpoint, override `SEED_MODEL` and `SEED_BASE_URL`.

## Dry Run

Preview document discovery and chunking without calling Seed:

```bash
python sft/generate_seed_query_plan_data.py --dry-run --max-chunks 5
```

## Generate Candidates

Generate and filter toward 1000 SFT samples:

```bash
python sft/generate_seed_query_plan_data.py \
  --target-samples 1000 \
  --samples-per-chunk 3 \
  --chunk-size 1200 \
  --chunk-overlap 150 \
  --sleep-seconds 0.2 \
  --workers 4
```

Outputs are written under `sft/results/` by default:

- `raw_seed_candidates.jsonl`: validated raw samples with source chunk metadata.
- `llamafactory_alpaca.json`: LLaMA-Factory Alpaca-format SFT dataset.
- `run_summary.json`: run metadata and counters.
- `failed_chunks.jsonl`: chunks where Seed returned invalid JSON or an API error occurred.

## LLaMA-Factory Dataset Mapping

Example `dataset_info.json` entry:

```json
{
  "rag_query_planner_seed": {
    "file_name": "llamafactory_alpaca.json",
    "columns": {
      "prompt": "instruction",
      "query": "input",
      "response": "output"
    }
  }
}
```


## Pipeline Layers

### 1. Data Generation

Generate teacher samples from markdown chunks:

```bash
python RAG_PROJECT/sft/generate_seed_query_plan_data.py \
  --target-samples 1000 \
  --samples-per-chunk 3 \
  --chunk-size 1200 \
  --chunk-overlap 150 \
  --workers 4 \
  --model doubao-seed-2-0-pro-260215 \
  --output-dir RAG_PROJECT/sft/results_lite
```

### 2. Data QA And Split

Validate raw candidates, deduplicate, and split train/validation:

```bash
python RAG_PROJECT/sft/prepare_dataset.py \
  --raw RAG_PROJECT/sft/results_lite/raw_seed_candidates.jsonl \
  --output-dir RAG_PROJECT/sft/dataset \
  --valid-ratio 0.1
```

Current split from the first 1000 samples:

- train: 900
- validation: 100
- rejected: 0

### 3. Baseline Evaluation

Raw query baseline:

```bash
python RAG_PROJECT/sft/eval_query_planner.py \
  --mode raw_query \
  --input RAG_PROJECT/sft/dataset/valid_alpaca.json \
  --output RAG_PROJECT/sft/eval_results/raw_query_baseline.json
```

Base model baseline after starting an OpenAI-compatible Qwen server:

```bash
export EVAL_BASE_URL=http://127.0.0.1:8000/v1
export EVAL_MODEL=Qwen/Qwen2.5-0.5B-Instruct
bash RAG_PROJECT/sft/llamafactory/run_base_eval.sh
```

### 4. LoRA Training

On the Merlin GPU machine, install LLaMA-Factory, copy this project folder, then run:

```bash
bash RAG_PROJECT/sft/llamafactory/train.sh
```

Merge/export the trained model:

```bash
bash RAG_PROJECT/sft/llamafactory/export.sh
```

Main configs:

- `sft/llamafactory/qwen2_5_0_5b_query_planner_lora.yaml`
- `sft/llamafactory/qwen2_5_0_5b_query_planner_export.yaml`
- `sft/llamafactory/dataset_info.json`
