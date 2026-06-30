# 01. Research Questions and Innovations

## 1. 研究问题

RQ1. GRPO 是否比 SFT/DPO 更有效降低 RAG-grounded QA 中的 hallucination？

- 对比对象：base instruct、RAG baseline、SFT、SFT+DPO、SFT+GRPO、SFT+DPO+GRPO。
- 主要指标：hallucination rate、evidence support score、citation precision、answer correctness。
- 关键控制：相同检索环境、相同训练问题集合、相同 test split。

RQ2. citation-aware reward 是否提升 evidence fidelity，但导致 over-refusal？

- 假设：引用 reward 会鼓励模型只回答证据充分的问题，但可能把可回答问题错误拒答。
- 主要指标：citation precision、citation recall、refusal accuracy、over-refusal rate。
- 关键实验：移除 refusal calibration reward，观察 over-refusal。

RQ3. process-level reward 和 outcome-level reward 在工具调用型 RAG 任务中哪个更有效？

- process reward：JSON 格式、工具名、query reformulation、检索相关性、引用文档是否来自 tool output。
- outcome reward：最终答案正确性、引用支持、拒答正确性、幻觉惩罚。
- 关键实验：process only、outcome only、process+outcome。

RQ4. 如何设计可验证 reward 来同时优化 tool-use、citation fidelity、answer correctness 和 refusal calibration？

- 关键难点：多个目标互相冲突。
- 研究点：reward normalization、gating、penalty cap、answerable-aware reward、anti-hacking checks。

RQ5. retrieval-aware preference construction 是否比普通 preference pair 更适合 RAG post-training？

- 普通 preference：chosen answer 比 rejected answer 好。
- retrieval-aware preference：chosen/rejected 的差异来自检索证据使用、引用质量、拒答校准、噪声抵抗。
- 关键实验：DPO 数据来源 ablation。

## 2. 创新点设计

### 2.1 Multi-Objective Verifiable Reward for RAG Tool-Use

设计一个不依赖大型 reward model 的 reward family：

```text
R = w_json R_json
  + w_tool R_tool
  + w_ret R_retrieval
  + w_cite R_citation
  + w_ans R_answer
  + w_ref R_refusal
  - w_hall P_hallucination
  - w_over P_over_refusal
  - w_hack P_reward_hacking
```

重点不是线性加权本身，而是 reward 的 gating：

- 如果输出 JSON 无效，则大多数下游 reward 置零。
- 如果问题 unanswerable，则 answer correctness 不奖励编造答案，只奖励正确拒答。
- 如果 citation 不来自 retrieved evidence，则 answer reward 上限被截断。
- 如果答案正确但引用错误，不能拿满分。

### 2.2 Evidence-Grounded GRPO

把 GRPO rollout 限制在固定工具环境：

1. 模型先输出 tool call。
2. 环境返回 top-k evidence chunks。
3. 模型输出 final answer with citations/refusal。
4. verifier 基于 retrieved evidence 计算 reward。

这个设计让 RL 信号绑定到证据，而不是仅靠最终答案语义相似度。

### 2.3 Citation Support Verifier

构建 citation verifier，判断每个 answer span 是否被引用 chunk 支持。

分三层：

1. Rule layer：引用 ID 是否存在、格式是否合法、引用是否来自本次检索。
2. NLI/semantic layer：claim 是否由 cited evidence entail/support。
3. LLM audit layer：只用于 dev/test 或抽样校验，不直接作为主要训练 reward。

输出：

- citation precision：被引用证据中真正支持答案的比例。
- citation recall：答案中需要支持的 claims 被引用覆盖的比例。
- unsupported claim count：无证据支持的断言数量。

### 2.4 Refusal Calibration Reward

拒答不是越多越好。定义三类问题：

- Answerable: evidence 足够，应该回答。
- Unanswerable: corpus 不包含答案，应该拒答。
- Ambiguous/underspecified: 可以请求澄清或给条件性回答。

reward 设计：

- 对 unanswerable 正确拒答给正奖励。
- 对 answerable 错误拒答给 over-refusal penalty。
- 对 unanswerable 编造答案给 hallucination penalty。
- 对 ambiguous 问题鼓励说明不确定性和证据边界。

### 2.5 Retrieval-Aware Preference Construction

Preference pairs 不只比较“回答好不好”，而是围绕 RAG 行为构造：

- Good retrieval query vs vague retrieval query。
- Supported citation vs decorative citation。
- Correct refusal vs fabricated answer。
- Robust answer under noisy retrieval vs answer copied from distractor。
- Multi-hop evidence aggregation vs single-chunk shortcut。

这使 DPO 成为强 baseline，而不是弱 demo。

### 2.6 Process Reward vs Final-Answer Reward Systematic Comparison

论文可以把这个作为主要分析点：

- Process reward 更能改善 tool-call accuracy、JSON validity、retrieval relevance。
- Outcome reward 更能改善 answer correctness 和 refusal accuracy。
- 组合 reward 在 end-to-end success 上最稳。

### 2.7 Group Sampling and Reward Shaping

GRPO group sampling 策略：

- Same question, different decoding seeds。
- Same question, different retrieval noise levels。
- Same answerability type, batched together for stable normalization。

Reward shaping：

- 分阶段打开 reward 项：先格式/工具，再引用/答案，再拒答校准。
- 对容易 hack 的 reward 加 cap。
- 对 answer correctness 引入 evidence gating，避免模型凭常识答对但不 grounded。

### 2.8 Reward Hacking 防控

常见 hacking：

- 引用所有 chunk 来提高 recall。
- 输出极短答案规避 unsupported claims。
- 对大量问题拒答以避免幻觉。
- 编造 citation IDs。
- 用模板化“根据资料”掩盖无证据回答。

防控：

- citation precision 和 citation recall 同时评估。
- 引用数量上限和冗余 citation penalty。
- answerable-aware over-refusal penalty。
- citation ID 必须来自 current tool output。
- unsupported claim penalty 高于 answer fluency reward。

