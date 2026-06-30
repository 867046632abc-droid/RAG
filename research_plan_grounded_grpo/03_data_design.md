# 03. Data Design

## 1. 数据源策略

推荐两条数据线并行：

### A. 当前半导体技术文档

来自现有 `datas/md/` 和 `datas/PDF/`。

优势：

- 已有切分、入库、baseline 和评测。
- 领域专业，能体现 grounded QA 难度。
- 与当前项目连续，工程成本低。

风险：

- 公开论文读者可能难以复现私有/合成文档。
- 数据规模和标注质量可能不足。

### B. Synthetic Enterprise Policy Docs

构造可公开释放的企业政策文档，例如：

- expense policy
- travel policy
- data security policy
- procurement policy
- HR leave policy
- incident response policy

优势：

- 可控 answerability、冲突条款、版本变化、多跳推理。
- 容易构造 unanswerable 和 adversarial。
- 可公开 dataset card。

建议论文主数据用 B，半导体数据作为 domain transfer 或真实场景补充。

## 2. 问题类型

| Type | Definition | Example |
| --- | --- | --- |
| Answerable single-hop | 单个 chunk 足够回答 | 某项报销上限是多少 |
| Answerable multi-hop | 需要多个 chunk/文档组合 | 出差餐补和地区等级共同决定金额 |
| Unanswerable missing | 文档无答案 | 公司是否报销宠物托运 |
| Unanswerable insufficient | 有相关信息但不足以确定 | 只说需审批，未说明额度 |
| Ambiguous | 问题缺关键条件 | “我能报销吗”但无城市/职级/日期 |
| Adversarial distractor | 检索中有相似但错误证据 | 旧政策或另一个地区政策 |
| Citation stress | 答案需要引用多个具体条款 | 多个限制条件并列 |
| Tool-use stress | 初始 query 不佳，需要改写 | 缩写、别名、跨文档术语 |

## 3. Tool-Use Trace Schema

每条 SFT trace 建议统一为：

```json
{
  "id": "train_000001",
  "question": "...",
  "answerability": "answerable|unanswerable|ambiguous",
  "messages": [
    {"role": "system", "content": "You are a grounded RAG QA assistant..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "{\"action\":\"tool_call\",\"tool\":\"rag_retriever\",\"query\":\"...\",\"top_k\":5}"},
    {"role": "tool", "name": "rag_retriever", "content": "[{\"chunk_id\":\"...\",\"text\":\"...\"}]"},
    {"role": "assistant", "content": "{\"action\":\"final\",\"answer\":\"...\",\"citations\":[\"chunk_1\"],\"refusal\":false}"}
  ],
  "gold_evidence": ["chunk_1", "chunk_7"],
  "gold_answer": "...",
  "reward_labels": {
    "tool_call_correct": true,
    "citation_supported": true,
    "refusal_correct": false
  }
}
```

## 4. Preference Pair 构造

每个 pair 需要明确 rejected 为什么差。

| Pair type | Chosen | Rejected |
| --- | --- | --- |
| Citation support | 答案和引用均被证据支持 | 答案对但 citation 错 |
| Refusal calibration | 无答案时拒答并说明证据不足 | 无答案时编造 |
| Over-refusal | 有证据时正常回答 | 有证据时拒答 |
| Retrieval query | 工具 query 覆盖关键条件 | query 太泛或漏约束 |
| Noise robustness | 忽略 distractor | 采信 distractor |
| Multi-hop | 合并多个证据 | 只回答其中一半 |

推荐 pair 数量：

- 3k 起步可用。
- 10k 可作为主实验。
- 每个问题最多保留 2-3 个高质量 pair，避免模板重复。

## 5. GRPO Prompt 数据

GRPO prompt 不需要 gold trace，但需要 reward 可计算。

每条包含：

```json
{
  "id": "grpo_000001",
  "question": "...",
  "answerability": "answerable",
  "gold_evidence": ["doc_a#chunk_03", "doc_b#chunk_11"],
  "gold_answer_facts": [
    "expense limit is 200 USD",
    "manager approval is required for international travel"
  ],
  "retrieval_condition": "clean|noisy|missing_top1|distractor",
  "split": "train"
}
```

注意：训练时 gold 信息只给 reward，不进 prompt。

## 6. Reward Annotation

优先自动标注：

- answerability：由生成数据时的 evidence coverage 决定。
- gold evidence：生成问题时绑定文档条款。
- gold facts：从 evidence 中抽取 atomic facts。
- adversarial labels：标记 distractor chunk。

人工审计：

- 每类问题抽 50-100 条。
- 检查 answerability、gold evidence、gold facts 是否正确。
- 估计自动 verifier 的 precision/recall。

## 7. Train/Dev/Test Split

必须按文档和主题划分，而不是随机按问题划分。

推荐：

```text
Train: 70% documents / policies
Dev:   10% documents / policies
Test:  20% documents / policies
```

更强设置：

- In-domain test：同一 policy family，不同文档或版本。
- Out-of-domain test：未见过的 policy family，例如 train 用 HR/travel，test 用 security/procurement。
- Temporal test：训练用 v1/v2，测试用 v3，新条款和旧条款冲突。

## 8. 防止数据泄漏

规则：

1. 文档级 split 先于问题生成。
2. train prompt 中不出现 test 文档标题、chunk ID、gold facts。
3. synthetic generator 使用 split-specific seeds。
4. 对 train/test question 做 near-duplicate 检测。
5. 对 gold answer 做 n-gram overlap 检查。
6. Test retrieval index 可以包含 test docs，但训练数据不能包含 test QA。
7. 如果测试泛化到未见 corpus，则 train index 和 test index 分开构建。

## 9. 如何证明泛化

需要至少三种泛化证据：

1. Unseen documents：测试问题来自训练未见文档。
2. Unseen answerability mix：测试包含更高比例 unanswerable/adversarial。
3. Retrieval perturbation：同一问题在 clean/noisy/missing-top1 检索条件下评估。

可选第四种：

- Cross-domain：半导体文档作为真实领域 transfer test。

## 10. Dataset Card 要点

Dataset card 应包含：

- 数据来源和生成方法。
- 文档类型和 split。
- 问题类型分布。
- answerability 分布。
- gold evidence 标注方式。
- 自动 verifier 和人工审计结果。
- 已知偏差：synthetic style、policy domain、英文/中文比例。
- 不适用场景：法律/医疗等高风险事实判断。

