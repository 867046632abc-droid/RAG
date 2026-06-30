# 04. GRPO Design

## 1. Rollout 格式

推荐强制两阶段输出：

### Step 1: Tool call

```json
{
  "action": "tool_call",
  "tool": "rag_retriever",
  "query": "specific retrieval query",
  "top_k": 5
}
```

### Step 2: Final answer

```json
{
  "action": "final",
  "answer": "answer grounded in retrieved evidence, or refusal",
  "citations": ["doc_12#chunk_03", "doc_18#chunk_02"],
  "refusal": false,
  "confidence": 0.78
}
```

Unanswerable final:

```json
{
  "action": "final",
  "answer": "I cannot answer this from the retrieved documents because ...",
  "citations": [],
  "refusal": true,
  "confidence": 0.21
}
```

## 2. Prompt 设计

System prompt 核心约束：

- You must call `rag_retriever` before answering.
- Use only retrieved evidence.
- Cite chunk IDs for every factual claim.
- If retrieved evidence is insufficient, refuse.
- Return valid JSON only.

User prompt：

```text
Question:
{question}

You may use the rag_retriever tool. Return one JSON object for the tool call.
```

Tool response：

```json
{
  "results": [
    {
      "chunk_id": "policy_travel_v2#chunk_014",
      "source": "travel_policy_v2.md",
      "score": 0.82,
      "text": "..."
    }
  ]
}
```

Final prompt：

```text
Using only the retrieved evidence above, answer the question.
Return one JSON object with action, answer, citations, refusal, confidence.
```

## 3. Group Size

推荐从小到大：

| Stage | Group size | Purpose |
| --- | ---: | --- |
| Pilot | 4 | 检查 reward 是否有区分度 |
| Main | 6 or 8 | 平衡稳定性和成本 |
| Ablation | 2/4/8 | 研究 group size 影响 |
| Avoid initially | 16 | rollout 成本高，收益不确定 |

采样参数：

- temperature: 0.7-1.0
- top_p: 0.9-0.95
- max tokens: tool call 256, final 768-1200
- KL coefficient: 先用 TRL 默认或小范围搜索

## 4. Composite Reward

总 reward：

```text
R_total =
  0.10 R_json
+ 0.10 R_tool
+ 0.10 R_retrieval
+ 0.20 R_citation
+ 0.25 R_answer
+ 0.20 R_refusal
- 0.20 P_hallucination
- 0.15 P_over_refusal
- 0.10 P_hacking
```

权重不是最终答案，需要在 dev set 上调。建议先固定一组，做 ablation。

## 5. Reward Components

### 5.1 JSON Validity Reward

规则：

- valid JSON: +1
- required keys present: +0.5
- wrong schema/action: 0 or negative
- non-JSON natural language: -1

Gating：

- JSON 无效时，tool/citation/answer/refusal reward 大部分置零。

### 5.2 Tool-Call Correctness Reward

奖励：

- 调用 `rag_retriever`: +1
- top_k 合法: +0.2
- query 包含关键实体/约束: +0.5
- 不提前回答: +0.3

惩罚：

- 不调用工具直接回答: -1
- 调用不存在工具: -1
- query 为空或过泛: -0.5

### 5.3 Retrieval Relevance Reward

如果有 gold evidence：

- retrieved top-k 命中 gold evidence: recall@k
- gold evidence 排名越靠前越高
- distractor 被模型采信则扣分

如果无 gold evidence：

- 只评估 query 是否合理，不因没有命中而惩罚。

### 5.4 Citation Support Reward

分解为：

```text
R_citation = 0.5 citation_precision + 0.3 citation_recall + 0.2 citation_format
```

规则：

- citation ID 必须来自 current retrieval output。
- 每个关键 claim 至少一个 citation。
- 引用过多且无必要时扣 redundancy penalty。
- answerable 问题无 citation，不能拿高 answer reward。

Verifier：

- claim extraction: rule/LLM offline or lightweight model。
- support check: NLI/verifier or LLM judge for eval。
- training reward 可先用 lexical/semantic overlap + gold evidence matching，避免昂贵 LLM judge。

### 5.5 Answer Correctness Reward

对 answerable：

- gold facts covered: fact recall。
- no contradiction: entailment score。
- no unsupported extra facts: precision。

对 multi-hop：

- 每个 required fact 单独计分。
- 只答一跳只能拿部分分。

Evidence gating：

- 如果答案事实正确但未被 retrieved evidence 支持，answer reward capped at 0.4。
- 如果 citation 错误，answer reward capped at 0.7。

### 5.6 Refusal Correctness Reward

对 unanswerable：

- refusal=true: +1
- 明确说明证据不足: +0.5
- 不编造替代事实: +0.5

对 answerable：

- refusal=true: over-refusal penalty
- partial evidence 情况允许 cautious answer，但不能完全拒答。

### 5.7 Hallucination Penalty

惩罚：

- unsupported named entities, numbers, dates, policies。
- contradictions with retrieved evidence。
- citation does not support claim。
- answer from model prior when evidence missing。

建议：

- 对数字和实体 hallucination 加重，因为最容易被 verifier 检出。
- hallucination penalty 不宜无限大，否则模型会学会拒答。

### 5.8 Over-Refusal Penalty

只对 answerable 或 partially answerable 生效：

- answerable 且 refusal=true: -1
- answerable 且 answer 过短/无实质信息: -0.5
- 有足够证据却说“无法判断”: -1

## 6. Reward Hacking 风险

| Risk | Symptom | Mitigation |
| --- | --- | --- |
| 引用所有 chunk | citation recall 高但 precision 低 | citation precision、引用数量上限 |
| 全部拒答 | hallucination 低但 answer success 低 | over-refusal penalty、answerability-balanced batches |
| 极短答案 | unsupported claims 少但无用 | answer completeness reward |
| 编造 chunk ID | 看似有引用 | current retrieval ID check |
| 模板化解释 | “根据资料”但无具体支持 | claim-level support verifier |
| 只优化 JSON | 格式好但任务失败 | JSON reward 低权重且只做 gate |

## 7. 与 SFT/DPO 的公平对比

必须控制：

- 同一个 base model。
- 同一个 tokenizer/chat template。
- 同一个 RAG retrieval environment。
- 同一个 train/dev/test split。
- 同一推理解码参数。
- 同一 evaluation harness。
- SFT、DPO、GRPO 使用可比训练样本预算。

预算公平有两种口径：

1. Prompt budget：每个方法看同样数量训练 questions。
2. Token budget：GRPO rollout 多，按总生成 token 对齐。

建议主文使用 prompt budget，appendix 报告 token budget。

## 8. GRPO Pilot Checklist

正式训练前先跑 500 prompt pilot：

- Reward mean/std 是否非零。
- 各 reward component 是否有区分度。
- group 内 reward 是否有 ranking。
- JSON invalid rate 是否快速下降。
- refusal rate 是否异常升高。
- KL 是否稳定。
- 训练后 dev hallucination 是否下降。

