# 00. Research Overview

## 1. 一句话定位

本项目研究一个问题：当 LLM 在固定 RAG 工具环境中回答专业问题时，能否通过 evidence-grounded GRPO 学会更可靠地调用检索工具、更忠实地引用证据、更准确地拒答，而不是仅靠 SFT/DPO 模仿答案格式。

## 2. 最小可发表版本

最小可发表版本不是“做一遍 SFT+DPO+GRPO”，而是一个受控实验：

1. 固定已有 RAG baseline 作为工具环境。
2. 构造可验证的 RAG-grounded QA 数据集，包含 answerable、unanswerable、multi-hop、adversarial、retrieval-noise 条件。
3. 对比 base instruct、RAG baseline、SFT、SFT+DPO、SFT+GRPO、SFT+DPO+GRPO。
4. 系统分析 multi-objective verifiable reward 对四类行为的影响：
   - tool-use correctness
   - citation fidelity
   - answer correctness
   - refusal calibration
5. 做 reward ablation、group size ablation、process reward vs outcome reward 对比。

如果结果显著，主 claim 可以落在：

> Evidence-grounded GRPO improves faithful citation and hallucination control in tool-using RAG QA beyond SFT/DPO, while refusal calibration reward prevents the common side effect of over-refusal.

如果结果不显著，也可以 pivot 到：

> Citation-aware rewards improve evidence fidelity but expose a measurable answerability/refusal trade-off; process-level tool rewards are necessary for stable optimization in RAG tool-use tasks.

## 3. 与现有仓库的关系

当前仓库已有：

- `documents/`: Markdown/PDF 入库与切分
- `tools/retriever_tools.py`: Milvus RAG retriever tool
- `graph2/`: Agentic RAG 主流程、reranker、grader、query transform
- `graph2/ragas_eval.py`: RAGAS 基础评测
- `datas/md/`, `datas/PDF/`, `datas/evaluation/`: 知识库和历史评测结果

研究方案中不重写 RAG。现有 RAG 作为：

1. 固定检索环境：模型只能通过定义好的 `rag_retriever` 获取证据。
2. 评测环境：所有后训练模型使用同一 retrieval index、chunking、top-k、reranker 配置。
3. 数据生产器：生成 tool-use traces、negative retrieval cases、badcase-driven preference pairs。
4. 对照 baseline：作为非训练增强的 Agentic RAG baseline。

## 4. 推荐研究假设

H1. 在 grounded RAG QA 中，GRPO 比 DPO 更适合优化可验证行为，因为它能直接利用 rollout 级 reward，而不是只学习 pairwise preference。

H2. citation-aware reward 能提升 citation precision 和 evidence support，但单独使用会诱发 over-refusal，需要 refusal calibration reward 平衡。

H3. process-level reward 能更稳定地提升工具调用和检索相关性；outcome-level reward 更直接提升最终答案质量。两者组合最强。

H4. retrieval-aware group sampling 能提高 GRPO 的有效梯度信号，因为同一问题下不同 retrieval/noise 条件会暴露模型是否真正依据证据回答。

## 5. 推荐最终系统

系统名可暂定为 E-GRPO-RAG：

- Environment: fixed Milvus RAG tool and optional web-search disabled in main experiments.
- Policy model: Qwen2.5/Qwen3 7B or 14B instruct with LoRA.
- Warm start: SFT on high-quality tool-use traces.
- Optional preference stage: DPO on retrieval-aware preference pairs.
- RL stage: GRPO with group rollouts and verifier-based reward.
- Evaluation: rule/verifier/LLM-judge hybrid, with human audit subset.

## 6. 资源约束下的优先级

H20 显存通常足够容纳 7B/14B LoRA 或 QLoRA 训练，但 GRPO 的瓶颈是 rollout 生成和多样本采样，不只是显存。

优先路线：

1. 先用 7B instruct 做完整 pipeline，跑通实验矩阵。
2. 14B 做主结果或补充结果。
3. 32B 只做 inference baseline 或少量 LoRA sanity check，不作为主训练目标。
4. GRPO group size 从 4 起步，最高 8；不要一开始追求 16。
5. reward model 不作为第一选择，优先使用 rule-based 和 verifier-based reward。

## 7. 论文贡献写法

建议贡献点写成三条：

1. 提出 evidence-grounded GRPO：面向工具调用 RAG QA 的多目标可验证 reward，统一优化 tool-use、citation fidelity、answer correctness 和 refusal calibration。
2. 构造 retrieval-aware post-training 数据协议：包含 answerable/unanswerable/multi-hop/adversarial/noisy retrieval 条件，并支持 SFT、DPO、GRPO 公平对比。
3. 系统实验发现：GRPO 在降低 hallucination 和改善 citation support 上优于 SFT/DPO，但 reward 设计不当会导致 over-refusal；process+outcome reward 是更稳健的组合。

