# 02. Technical Route Under H20 Constraints

## 1. 模型选择

### 推荐主线

| 阶段 | 推荐模型 | 用途 | 理由 |
| --- | --- | --- | --- |
| Pipeline debug | Qwen2.5-7B-Instruct 或 Qwen3-8B | 全流程打通 | 成本低，中文/技术问答较强 |
| Main experiments | Qwen2.5-14B-Instruct 或 Qwen3-14B | 主实验 | 质量和训练成本平衡 |
| Strong inference baseline | Qwen2.5-32B-Instruct 或 Qwen3-32B | 只推理或少量 LoRA | 可作为强模型对照，不建议主 GRPO |
| Cross-family sanity | Llama/Mistral 7B/8B instruct | 泛化补充 | 证明方法不是 Qwen-only |

说明：

- 7B/8B：适合先把 SFT/DPO/GRPO、reward 和评测全部跑通。
- 14B：建议作为 paper main model。H20 显存可承受 LoRA/QLoRA，rollout 成本仍可控。
- 32B：GRPO rollout 成本明显上升，适合做 inference baseline 或 appendix。

## 2. 训练路线

```text
Base instruct
  -> SFT on high-quality tool-use traces
  -> DPO on retrieval-aware preference pairs
  -> GRPO with verifier-based rewards
```

必须包含 GRPO，但 DPO 可以作为强 baseline 和可选 warm-up。

推荐实验主线：

1. SFT：让模型学会结构化工具调用、引用格式、拒答格式。
2. DPO：让模型偏好 supported answer、正确拒答、干净 citation。
3. GRPO：直接优化可验证 reward，改善 DPO 难以显式约束的行为。

## 3. LoRA/QLoRA 配置

### 7B/8B

- Quantization: 4-bit QLoRA or bf16 LoRA
- LoRA rank: 16 or 32
- LoRA alpha: 32 or 64
- Target modules: `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`
- Sequence length: 4096 first, then 8192 if needed
- Batch: micro batch 1-2, gradient accumulation 8-32

### 14B

- Quantization: 4-bit QLoRA preferred
- LoRA rank: 16 first; rank 32 for final run
- Sequence length: 4096/6144 practical default
- Gradient checkpointing: on
- Optimizer: paged AdamW 8-bit if using bitsandbytes
- GRPO group size: 4 first, 6-8 for main ablation

### 32B

- Use 4-bit QLoRA only if training is attempted.
- Prefer inference-only comparison with the same RAG harness.
- If running LoRA training, restrict to SFT or small GRPO pilot.

## 4. Frameworks

| Component | Recommended tool |
| --- | --- |
| SFT | TRL `SFTTrainer` or Axolotl if preferred |
| DPO | TRL `DPOTrainer` |
| GRPO | TRL `GRPOTrainer` |
| PEFT | Hugging Face PEFT |
| Distributed | Accelerate, DeepSpeed ZeRO-2/3 if multi-H20 |
| Fast rollout | vLLM for generation server where integration allows |
| Evaluation | Existing `graph2/ragas_eval.py` plus custom metrics |
| Retrieval env | Existing Milvus retriever and LangGraph tool path |

## 5. RAG Baseline 如何参与训练

现有 RAG 不作为待训练模块，而作为 fixed environment：

- 固定 chunking、embedding、Milvus collection、top-k、reranker。
- GRPO rollout 中，模型只能通过约定 JSON 调用 `rag_retriever`。
- 工具返回统一 schema，包括 chunk_id、title/source、content、score。
- reward 只基于 current tool output 判断 citation 和 support。

这样做的好处：

- 避免训练同时改变 retrieval 和 policy，导致实验不可解释。
- 保证 SFT/DPO/GRPO 对比公平。
- 可以把 retrieval noise 作为可控变量注入。

## 6. Reward Model 选择

优先不训练 reward model。

原因：

- H20 资源更应该给 policy training 和 rollouts。
- RAG/citation/refusal 中大量 reward 可以 verifier 化。
- 训练 reward model 会引入额外标注、校准和 overfitting 风险。

可选补充：

- 用小型 NLI/verifier 模型做 claim-evidence support。
- 用 LLM judge 只做离线评测和少量人工审计对齐。
- 如果 verifier 明显不稳，再考虑训练 lightweight citation support classifier。

## 7. 训练规模建议

首轮可执行规模：

| Data | Size |
| --- | ---: |
| SFT traces | 5k-15k |
| DPO pairs | 3k-10k |
| GRPO prompts | 2k-8k |
| Dev | 500-1k |
| Test in-domain | 1k |
| Test out-of-domain | 500 |
| Human audit subset | 100-200 |

GRPO 估算：

- group size 4，2k prompts 等于 8k rollouts。
- group size 8，2k prompts 等于 16k rollouts。
- 先做 500 prompt pilot，确认 reward 分布和 KL 稳定，再扩大。

## 8. 工程目录建议

后续可在 repo 中新增：

```text
post_training/
  data/
    build_sft_traces.py
    build_dpo_pairs.py
    build_grpo_prompts.py
  env/
    rag_tool_env.py
    schemas.py
  rewards/
    json_reward.py
    tool_reward.py
    citation_verifier.py
    refusal_reward.py
    composite_reward.py
  train/
    sft.py
    dpo.py
    grpo.py
  eval/
    run_eval.py
    metrics.py
    badcase_report.py
```

