# 07. Roadmap and Deliverables

## 1. 10 周计划

### Week 1: Problem Lock and Baseline Freeze

输入：

- 当前 RAG_PROJECT。
- 已有 RAGAS eval。

输出：

- 固定 baseline config。
- 研究问题和实验矩阵冻结。
- evidence schema 和 JSON output schema。

验收：

- 同一测试集可复现实验结果。
- baseline config 写入 repo。

风险：

- 当前评测集太小。

Pivot：

- 先构建 synthetic policy dataset 作为主评测。

### Week 2: Dataset Builder

输入：

- policy docs 或半导体 docs。

输出：

- answerable/unanswerable/multi-hop/adversarial 数据生成脚本。
- document-level split。
- 初版 dataset card。

验收：

- 至少 2k QA。
- 100 条人工审计通过率大于 85%。

风险：

- synthetic 问题风格单一。

Pivot：

- 加模板扰动、LLM paraphrase、真实 badcase 改写。

### Week 3: Tool-Use Traces and SFT

输出：

- 5k-10k SFT traces。
- SFT training script。
- 7B model SFT checkpoint。

验收：

- JSON validity 明显高于 base instruct。
- tool-call accuracy 达到 90%+。

风险：

- 模型学格式但答案不提升。

Pivot：

- 加入更高质量 multi-hop traces 和 refusal traces。

### Week 4: Verifier and Metrics Harness

输出：

- citation verifier。
- refusal evaluator。
- hallucination checker。
- eval harness 与 `graph2/ragas_eval.py` 对接。

验收：

- metrics 可跑完整 dev set。
- human audit subset 与 verifier agreement 可接受。

风险：

- verifier 噪声大。

Pivot：

- 训练 reward 用保守 rule/gold evidence，论文评测用 LLM judge + human audit。

### Week 5: DPO Baseline

输出：

- 3k-10k retrieval-aware preference pairs。
- DPO checkpoint。

验收：

- citation precision 或 refusal accuracy 至少一项优于 SFT。

风险：

- DPO 提升有限。

Pivot：

- 把 DPO 定位为 strong warm-up，而非主贡献。

### Week 6: GRPO Pilot

输出：

- GRPO reward function。
- 500 prompt pilot run。
- reward distribution report。

验收：

- group 内 reward 有方差。
- KL 稳定。
- dev hallucination 或 citation support 有初步提升。

风险：

- reward 被 hack 或模型全部拒答。

Pivot：

- 调低 hallucination penalty，加入 over-refusal penalty 和 answerability-balanced sampling。

### Week 7: Main GRPO Runs

输出：

- SFT+GRPO。
- SFT+DPO+GRPO。
- 7B main result。

验收：

- 至少一个 GRPO 变体在 end-to-end success、hallucination、citation support 上超过 SFT/DPO。

风险：

- 训练成本高。

Pivot：

- 减少 prompts，优先完成 ablation 证据；14B 只跑最优设置。

### Week 8: Ablations

输出：

- reward ablation。
- group size ablation。
- process vs outcome。

验收：

- 能解释主结果来自哪些 reward。
- 能观察 citation-refusal trade-off。

风险：

- ablation 差异小。

Pivot：

- 转向 badcase taxonomy 和 robustness 分析，强调 reward trade-off。

### Week 9: Robustness and Generalization

输出：

- noisy retrieval test。
- adversarial test。
- out-of-domain test。
- badcase analysis。

验收：

- 至少一类 robustness 条件下 GRPO 更稳。

风险：

- out-of-domain 不显著。

Pivot：

- 改成“GRPO improves controllability under verifier-aligned conditions, but does not solve retriever failure”。

### Week 10: Paper Draft and Artifact Polish

输出：

- paper draft。
- dataset card。
- model card。
- experiment tables。
- reproducibility instructions。

验收：

- Workshop submission ready。
- Repo 能复现实验子集。

风险：

- 主结果不够强。

Pivot：

- 把论文定位成 benchmark/protocol + negative findings + reward design analysis。

## 2. 最终产出

必须产出：

- research repo
- dataset card
- model card
- SFT/DPO/GRPO training scripts
- evaluation harness
- experiment tables
- badcase analysis
- paper draft

可选产出：

- Gradio demo
- leaderboard-style dashboard
- small released LoRA adapter

## 3. 如果结果不显著，如何 Pivot

### Pivot A: Reward Trade-Off Paper

主题：

> Citation-aware RL improves attribution but induces over-refusal unless calibrated.

需要证据：

- No refusal reward 时 over-refusal 上升。
- Full reward 降低 over-refusal。
- badcase 展示 citation reward 的副作用。

### Pivot B: Process Reward Paper

主题：

> Process-level rewards are necessary for reliable RAG tool use; outcome rewards alone are insufficient.

需要证据：

- process reward 提升 tool-call/query/retrieval。
- outcome reward 答案更好但工具使用不稳。
- full reward 最好。

### Pivot C: Benchmark/Protocol Paper

主题：

> A controlled benchmark for grounded tool-use QA with citation and refusal metrics.

需要证据：

- 数据构造严谨。
- 多模型多方法评测。
- 明确 badcase taxonomy。

### Pivot D: Negative Result

主题：

> GRPO under verifier noise is brittle for grounded RAG unless reward gating and leakage controls are carefully designed.

需要证据：

- reward hacking examples。
- verifier failure cases。
- 改进后稳定性提升。

## 4. 里程碑验收表

| Milestone | Minimal pass |
| --- | --- |
| Dataset | 2k train, 500 dev/test, audited subset |
| SFT | JSON validity > 90%, tool-call accuracy > 90% |
| DPO | Better than SFT on at least one fidelity/refusal metric |
| GRPO pilot | Reward variance non-zero, no collapse |
| Main result | GRPO improves hallucination or citation support |
| Ablation | At least one reward component has interpretable effect |
| Paper | Main claim supported by tables and badcases |

