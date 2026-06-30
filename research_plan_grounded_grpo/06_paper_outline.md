# 06. Paper Outline

## 1. Title Options

1. Evidence-Grounded GRPO for Reliable Tool-Using RAG Question Answering
2. Learning to Cite and Refuse: Verifiable GRPO Rewards for Grounded RAG QA
3. Calibrated Grounding: Post-Training Tool-Using LLMs for Faithful Citation and Refusal

推荐第 1 个，简洁并突出方法。

## 2. Abstract Draft

Retrieval-augmented generation systems are often evaluated as fixed pipelines, while the behavior of the generator policy remains weakly optimized for reliable tool use, faithful citation, and calibrated refusal. We study post-training for tool-using RAG question answering under a fixed retrieval environment. We propose evidence-grounded GRPO, a multi-objective verifiable reward framework that jointly optimizes JSON-valid tool calls, retrieval-aware behavior, citation support, answer correctness, hallucination avoidance, and refusal calibration. We construct a controlled dataset with answerable, unanswerable, multi-hop, adversarial, and noisy-retrieval questions, and compare SFT, DPO, GRPO, and their combinations. Experiments show that GRPO improves citation fidelity and reduces hallucination beyond SFT/DPO, while explicit refusal calibration mitigates over-refusal induced by citation-aware rewards. Ablations reveal that process-level rewards stabilize tool use, whereas outcome-level rewards are necessary for answer quality, and their combination yields the best end-to-end success.

## 3. Introduction

要回答的问题：

- RAG pipeline 已经很常见，但 generator policy 仍可能：
  - 不可靠调用工具
  - 引用看似存在但不支持答案
  - 检索不到时编造
  - 为避免错误而过度拒答
- SFT 主要学习格式和示范。
- DPO 主要学习相对偏好。
- GRPO 可以直接利用可验证 reward 优化行为，但在 RAG/tool-use/citation/refusal 场景下如何设计 reward 仍不清楚。

贡献：

1. Evidence-grounded GRPO reward。
2. Retrieval-aware data and evaluation protocol。
3. Systematic comparison and ablation。

## 4. Related Work

组织方式：

- RAG and grounded QA
- Tool-using LLMs and agentic RAG
- Citation faithfulness and attribution
- Refusal and selective generation
- Post-training: SFT, preference optimization, RL, GRPO/RLVR
- Verifier-based reward and reward hacking

## 5. Method

### 5.1 Problem Formulation

定义：

- Question `q`
- Tool environment `E`
- Retrieved evidence `D = E(q')`
- Policy `pi_theta`
- Final answer `a`
- Citations `c`
- Answerability label `y`
- Reward `R(q, D, a, c, y)`

### 5.2 Fixed RAG Tool Environment

说明：

- 当前 Milvus retriever
- top-k retrieval
- evidence schema
- retrieval noise injection for experiments

### 5.3 Post-Training Pipeline

描述：

- SFT traces
- DPO preference pairs
- GRPO rollouts

### 5.4 Evidence-Grounded Reward

重点展开：

- JSON/tool reward
- retrieval reward
- citation support verifier
- answer correctness verifier
- refusal calibration
- hallucination/over-refusal penalty
- gating and anti-hacking

### 5.5 Process vs Outcome Reward

把 reward 分为：

- Process-level: format/tool/retrieval
- Outcome-level: answer/citation/refusal

## 6. Dataset

内容：

- 文档构造
- answerable/unanswerable/multi-hop/adversarial
- tool traces
- preference pairs
- GRPO prompts
- train/dev/test split
- leakage prevention
- human audit

## 7. Experiments

实验问题：

1. GRPO vs SFT/DPO。
2. Citation reward 和 refusal trade-off。
3. Process vs outcome。
4. Robustness to retrieval noise。
5. Generalization to unseen documents/domains。

## 8. Results

主表要突出：

- hallucination rate 下降
- citation precision/evidence support 上升
- end-to-end success 上升
- over-refusal 在 full reward 下受控

## 9. Ablation and Analysis

分析：

- 去掉 citation reward 的影响。
- 去掉 refusal calibration 后 over-refusal 的变化。
- group size 对稳定性影响。
- badcase taxonomy。
- reward hacking cases。

## 10. Limitations

务实写法：

- Synthetic data may not fully represent real enterprise or scientific corpora。
- Verifier errors can bias GRPO。
- Fixed retrieval environment isolates policy learning but does not optimize retriever。
- H20-constrained experiments limit model scale。
- LLM judge/human audit subset still needed for high-confidence factuality measurement。

## 11. Conclusion

重申：

- RAG post-training 应该优化可验证的 evidence-grounded 行为，而不是只模仿答案。
- GRPO 在这个设置中有价值，但 reward 设计必须显式处理 citation-refusal trade-off。

## 12. Figure and Table Plan

Figures：

1. Fixed RAG environment + GRPO loop。
2. Reward decomposition。
3. Citation precision vs over-refusal trade-off。
4. Retrieval noise sensitivity。

Tables：

1. Main results。
2. Reward ablation。
3. Process vs outcome。
4. Group size ablation。
5. Dataset statistics。

