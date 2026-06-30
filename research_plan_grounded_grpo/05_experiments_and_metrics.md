# 05. Experiments and Metrics

## 1. 主实验矩阵

| ID | System | Description |
| --- | --- | --- |
| E0 | Existing RAG baseline | 当前 `graph2` Agentic RAG |
| E1 | Base instruct + RAG tool prompt | 不训练，只给工具调用 prompt |
| E2 | SFT | tool-use traces supervised fine-tuning |
| E3 | SFT + DPO | retrieval-aware preference pairs |
| E4 | SFT + GRPO | verifier reward, no DPO |
| E5 | SFT + DPO + GRPO | full pipeline |

主结果表按以下维度拆分：

- answerable
- unanswerable
- multi-hop
- adversarial
- clean retrieval
- noisy retrieval
- in-domain
- out-of-domain

## 2. Ablation

### Reward ablation

| Variant | Removed component | Purpose |
| --- | --- | --- |
| Full reward | none | main |
| No citation reward | `R_citation` | 测 citation fidelity 来源 |
| No refusal reward | `R_refusal`, `P_over_refusal` | 测 over-refusal |
| No retrieval reward | `R_retrieval` | 测工具 query/retrieval |
| No hallucination penalty | `P_hallucination` | 测幻觉控制 |
| JSON/tool only | answer/citation/refusal removed | 测过程格式是否足够 |

### Group size ablation

- group size 2
- group size 4
- group size 8

报告：

- reward variance
- training stability
- end-to-end success
- compute cost

### Process vs outcome reward

| Variant | Reward |
| --- | --- |
| Process only | JSON, tool, retrieval |
| Outcome only | answer, citation, refusal, hallucination |
| Process + outcome | full |

预期：

- Process only 提升 tool-call 和 JSON，但答案质量有限。
- Outcome only 答案更好但工具调用不稳定。
- Full 最稳。

## 3. Robustness Experiments

### Answerable vs Unanswerable

测试模型是否能同时做到：

- 有证据时回答。
- 无证据时拒答。
- 不把拒答当作万能安全策略。

### In-Domain vs Out-of-Domain

设置：

- Train: enterprise policy docs 或半导体 docs 的部分主题。
- Test in-domain: 未见文档但同类主题。
- Test out-of-domain: 新政策类型或半导体真实文档。

### Adversarial Robustness

条件：

- distractor chunk with similar keywords
- outdated policy version
- conflicting evidence
- irrelevant high-score retrieval
- prompt injection inside retrieved chunk

### Retrieval Noise Sensitivity

人为控制检索结果：

- clean top-k
- add 1 distractor
- add 3 distractors
- remove top-1 gold evidence
- shuffle evidence order

指标：

- answer correctness drop
- citation precision drop
- refusal rate change
- distractor adoption rate

## 4. Metrics

| Metric | Meaning | Method |
| --- | --- | --- |
| JSON validity | 输出是否符合 schema | Rule |
| Tool-call accuracy | 是否正确调用检索工具 | Rule |
| Query quality | query 是否覆盖关键条件 | Rule/verifier |
| Retrieval recall@k | gold evidence 是否被检索到 | Rule |
| Citation precision | 引用中真正支持 claim 的比例 | Verifier |
| Citation recall | 需要支持的 claims 被引用覆盖比例 | Verifier |
| Evidence support score | answer claims 被 evidence 支持程度 | Verifier/NLI |
| Answer correctness | gold facts 覆盖和无矛盾 | Verifier + LLM judge |
| Refusal accuracy | unanswerable 正确拒答比例 | Rule |
| Over-refusal rate | answerable 被错误拒答比例 | Rule |
| Hallucination rate | unsupported/contradictory claims | Verifier + LLM judge |
| End-to-end success | 格式、工具、答案、引用同时达标 | Composite rule |
| Calibration | confidence 与 correctness 一致性 | ECE/Brier |
| Cost/latency | tokens、tool calls、wall time | Logging |

## 5. Rule, Verifier, LLM Judge 分工

### Rule-based

- JSON validity
- required keys
- tool name
- citation ID exists
- citation from current retrieval
- refusal flag
- retrieval recall@k
- latency/cost

### Verifier-based

- claim-evidence support
- contradiction detection
- gold fact coverage
- citation precision/recall
- hallucination count

可以先用：

- embedding similarity + lexical matching for pilot
- NLI/cross-encoder for main
- LLM judge for audit

### LLM Judge

只建议用于：

- answer correctness 最终评测
- badcase 分类
- verifier calibration
- human-audit subset 辅助

不建议直接用昂贵 LLM judge 作为 GRPO 主训练 reward。

## 6. 论文主表建议

Table 1: Main results across systems。

列：

- JSON validity
- tool-call accuracy
- answer correctness
- citation precision
- evidence support
- refusal accuracy
- over-refusal rate
- hallucination rate
- end-to-end success

Table 2: Reward ablation。

Table 3: Process vs outcome reward。

Table 4: Retrieval noise sensitivity。

Figure 1: Method diagram。

Figure 2: Citation vs refusal trade-off。

Figure 3: Reward component distribution during GRPO。

Figure 4: Badcase taxonomy before/after GRPO。

