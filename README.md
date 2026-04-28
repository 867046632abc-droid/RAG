# RAG_PROJECT

一个面向半导体技术问答场景的 `Agentic RAG` 项目，基于 `LangGraph + Milvus + RAGAS`，支持：

- 路由决策（向量库 / Web Search）
- 查询改写与循环检索
- 文档相关性过滤（grader）
- 生成后事实一致性与答案可用性校验
- 可切换的 Reranker 实验方案（replace / coexist）
- 批量评测与 badcase 分析

---

## 1. 项目目标

围绕真实技术文档（`datas/md`）构建一个可迭代的 RAG 系统，不只追求“能回答”，而是追求：

- 可复现：数据入库、检索、生成、评测链路可一键跑通
- 可解释：每轮评测都有指标、样本、坏例分析输出
- 可迭代：支持多种图流程 A/B 对比（原版 / reranker 替换 / reranker 并存）

---

## 2. 核心架构

主流程在 [`graph2/graph_2.py`](graph2/graph_2.py)：

1. `route_question`：先判断走 `vectorstore` 还是 `web_search`
2. `retrieve`：从 Milvus 混合检索召回候选文档
3. `grade_documents`：用 LLM 对文档相关性做二分类过滤
4. `generate`：基于上下文生成答案
5. `grade_generation_v_documents_and_question`：检查幻觉与答题有效性
6. 不通过则 `transform_query` 重写问题并重试，最多多轮后可回退 web search

Reranker 实验版：

- `graph2/graph_2_replace.py`：`retrieve -> rerank -> generate`
- `graph2/graph_2_coexist.py`：`retrieve -> rerank -> grade_documents -> generate`

---

## 3. 技术栈

- LLM 编排：`langchain`, `langgraph`
- 向量数据库：`Milvus`（dense + sparse/BM25）
- 向量模型：
  - dense：`BAAI/bge-base-zh-v1.5`
  - reranker：`BAAI/bge-reranker-v2-m3`
- Web 检索：`Tavily`
- 评测：`RAGAS`（faithfulness / answer_relevancy / context_precision / context_recall）
- 可视化：`matplotlib`

---

## 4. 快速开始

### 4.1 环境准备

建议：

- Python `3.10 - 3.12`
- 可访问 Milvus 服务
- 可用的 OpenAI / Tavily Key

安装依赖：

```bash
pip install -r requirements.txt
```

### 4.2 配置项

当前代码使用 [`utils/env_utils.py`](utils/env_utils.py) + `.env`：

- `.env` 中至少包含：
  - `OPENAI_API_KEY`
  - `DEEPSEEK_API_KEY`（可选）

另外请确认以下配置符合你的环境：

- `MILVUS_URI`（Milvus 地址）
- `COLLECTION_NAME`（集合名）
- `TAVILY_API_KEY`

> 建议：把所有密钥与 URI 都迁移到 `.env`，避免硬编码。

### 4.3 数据入库（Markdown -> Milvus）

脚本：[`documents/write_milvus.py`](documents/write_milvus.py)

```bash
python -m documents.write_milvus
```

该脚本会：

- 扫描 `datas/md/*.md`
- 解析并语义切块（`MarkdownParser`）
- 写入 Milvus 集合

---

## 5. 运行问答系统

### 5.1 原版流程（grader）

```bash
python -m graph2.graph_2
```

### 5.2 Reranker 替换 grader

```bash
python -m graph2.graph_2_replace
```

### 5.3 Reranker 与 grader 并存

```bash
python -m graph2.graph_2_coexist
```

---

## 6. 评测与分析

评测脚本：[`graph2/ragas_eval.py`](graph2/ragas_eval.py)

### 6.1 执行评测

```bash
python -m graph2.ragas_eval --mode original --case-count 10 --workers 4 --threshold 0.6
python -m graph2.ragas_eval --mode replace  --case-count 10 --workers 4 --threshold 0.6
python -m graph2.ragas_eval --mode coexist  --case-count 10 --workers 4 --threshold 0.6
```

参数说明：

- `--mode`: `original | replace | coexist`
- `--case-count`: 测试样本数量
- `--workers`: 并发执行样本数
- `--threshold`: badcase 阈值

### 6.2 输出文件

每次评测会在 `datas/evaluation/第N次结果*` 下生成：

- `graph2_ragas_testcases_*.json`：完整样本
- `graph2_ragas_cases_only_*.json`：仅题目/参考答案
- `graph2_ragas_detail_*.csv`：逐样本指标
- `graph2_ragas_summary_*.json`：汇总指标
- `run_status.json`：运行状态追踪

`detail.csv` 末尾还会追加两行自动分析：

- `[BADCASE_REASON]`
- `[IMPROVEMENT_SUGGESTION]`

### 6.3 可视化看板

脚本：[`datas/evaluation/visualize_evaluation.py`](datas/evaluation/visualize_evaluation.py)

```bash
python -m datas.evaluation.visualize_evaluation
```

输出图：`datas/evaluation/figures/rag_evaluation_dashboard.png`

---

## 7. 当前结果（示例）

来自 `datas/evaluation/第16次结果/graph2_ragas_summary_20260427_133708.json`：

- `faithfulness`: `1.0000`
- `answer_relevancy`: `0.8741`
- `context_precision`: `0.9944`
- `context_recall`: `0.8750`

可用于展示“系统在忠实性和上下文精度上的稳定性，以及召回侧仍有优化空间”。

---

## 8. 目录结构（核心部分）

```text
RAG_PROJECT/
├─ graph2/
│  ├─ graph_2.py                 # 原版 CRAG 图
│  ├─ graph_2_replace.py         # reranker 替换 grader
│  ├─ graph_2_coexist.py         # reranker + grader 并存
│  ├─ ragas_eval.py              # 批量评测主脚本
│  └─ test_ragas_parallel.py     # 并发性能测试
├─ documents/
│  ├─ markdown_parser.py         # 解析 + 语义切块
│  ├─ milvus_db.py               # Milvus schema / connection
│  └─ write_milvus.py            # 入库流水线
├─ tools/retriever_tools.py      # 检索器封装（hybrid + filter）
├─ llm_models/
│  ├─ all_llm.py                 # LLM 与 Web Search 工具
│  └─ embeddings_model.py        # embedding 模型
├─ datas/
│  ├─ md/                        # 知识库 markdown
│  └─ evaluation/                # 多轮评测输出
└─ utils/
   ├─ env_utils.py
   └─ log_utils.py
```

---



## 9. 后续改进建议

- 引入更系统的 badcase 标签体系（RET / TOOL / PLAN / GEN / SAFE）
- 增加引用命中率、工具调用成功率等业务指标
- 将 `env_utils.py` 中硬编码配置完全迁移到 `.env`
- 增加 API 服务层（FastAPI）与前端 Demo，形成端到端产品形态

