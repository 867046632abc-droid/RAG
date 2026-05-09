多模态RAG企业知识库问答系统

一个面向半导体技术问答场景的 `Agentic RAG` 项目，基于 `LangGraph + Milvus + RAGAS`，支持：

- 路由决策（向量库 / Web Search）
- 查询改写与循环检索
- 文档相关性过滤（grader）
- 生成后事实一致性与答案可用性校验
- 可切换的 Reranker 实验方案（replace / coexist）
- 批量评测与 badcase 分析
- **多模态检索**（图片 / 视频帧入库 + 视频生成节点）
- **Gradio 可视化前端**（支持文字 + 语音提问）

---

## 1. 项目目标

围绕真实技术文档（`datas/md`、`datas/PDF`）构建一个可迭代的 RAG 系统，不只追求“能回答”，而是追求：

- 可复现：数据入库、检索、生成、评测链路可一键跑通
- 可解释：每轮评测都有指标、样本、坏例分析输出
- 可迭代：支持多种图流程 A/B 对比（原版 / reranker 替换 / reranker 并存）
- 可演示：支持 Gradio 端到端 Demo，并可在回答后生成讲解视频

---

## 2. 核心架构

主流程在 [`graph2/graph_2.py`](graph2/graph_2.py)：

1. `route_question`：先判断走 `vectorstore` 还是 `web_search`
2. `retrieve`：从 Milvus 混合检索（dense + BM25）召回候选文档
3. `grade_documents`：用 LLM 对文档相关性做二分类过滤
4. `generate`：基于上下文生成答案
5. `grade_generation_v_documents_and_question`：检查幻觉与答题有效性
6. 不通过则 `transform_query` 重写问题并重试，最多多轮后可回退 web search

Reranker 实验版：

- `graph2/graph_2_replace.py`：`retrieve -> rerank -> generate`
- `graph2/graph_2_coexist.py`：`retrieve -> rerank -> grade_documents -> generate`

多模态扩展：

- `multimodal_RAG/graph_video.py`：将 `graph2` 作为黑盒整体 `run_rag`，
  在文字回答后按需进入 `video_generate` 节点，输出讲解视频
- `multimodal_RAG/multimodal_ingest.py`：图片 / 视频帧统一入库到 Milvus

---

## 3. 技术栈

- LLM 编排：`langchain`, `langgraph`
- 向量数据库：`Milvus`（dense + sparse/BM25）
- 模型：
  - dense embedding：`BAAI/bge-base-zh-v1.5`
  - reranker：`BAAI/bge-reranker-v2-m3`
- Web 检索：`Tavily`
- 评测：`RAGAS`（faithfulness / answer_relevancy / context_precision / context_recall）
- 多模态：图片解析、视频按帧采样、视频生成（Sora / Kling 可切换）
- 前端：`Gradio` + `Whisper` 语音识别
- 可视化：`matplotlib`

---

## 4. 快速开始

### 4.1 环境准备

建议：

- Python `3.10 - 3.13`
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
  - `TAVILY_API_KEY`

另外请确认以下配置符合你的环境：

- `MILVUS_URI`（Milvus 地址）
- `COLLECTION_NAME`（集合名）

> 建议：把所有密钥与 URI 都迁移到 `.env`，避免硬编码。

### 4.3 数据入库

文本（Markdown -> Milvus），脚本：[`documents/write_milvus.py`](documents/write_milvus.py)

```bash
python -m documents.write_milvus
```

该脚本会扫描 `datas/md/*.md` → 解析并语义切块（`MarkdownParser`） → 写入 Milvus。

多模态（图片 / 视频 -> Milvus）：

```python
from multimodal_RAG.multimodal_ingest import MultimodalIngest

ingest = MultimodalIngest(frame_interval_sec=30)
ingest.ingest_image("datas/image_input/foo.png")
ingest.ingest_video("datas/videos_output/bar.mp4")
ingest.ingest_directory("datas/image_input")
```

支持扩展名：图片 `.jpg/.jpeg/.png/.gif/.webp/.bmp`，视频 `.mp4/.avi/.mov/.mkv/.flv/.wmv`。

---

## 5. 运行问答系统

### 5.1 命令行：原版流程（grader）

```bash
python -m graph2.graph_2
```

### 5.2 命令行：Reranker 替换 grader

```bash
python -m graph2.graph_2_replace
```

### 5.3 命令行：Reranker 与 grader 并存

```bash
python -m graph2.graph_2_coexist
```

### 5.4 命令行：多模态（文字回答 + 视频生成）

```bash
python -m multimodal_RAG.graph_video
```

可在问题中显式带 “生成视频/制作视频/动画讲解” 等关键词触发视频节点；
也可在状态里显式传 `video_requested=True`，以及 `video_provider="sora" | "kling"`。

### 5.5 Gradio Web Demo

```bash
python app_graph2.py
# 浏览器打开 http://127.0.0.1:7860
```

支持：

- 文字提问 → 实时显示节点执行轨迹 + 最终答案
- 语音提问 → Whisper 转文字 → 自动提交问答

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

## 7. 当前结果（最新一次评测）

来自 `datas/evaluation/第22次结果/graph2_ragas_summary_20260507_184444.json`（10 样本）：

| 指标 | mean | min | max | pass_rate |
| ---- | ---- | --- | --- | --------- |
| `faithfulness`        | 0.9573 | 0.7778 | 1.0 | 1.00 |
| `answer_relevancy`    | 0.8774 | 0.8163 | 0.92 | 1.00 |
| `context_precision`   | 0.8139 | 0.3250 | 1.0 | 0.60 |
| `context_recall`      | 0.8167 | 0.0000 | 1.0 | 0.80 |

历史最佳曾达到（第 16 次）：`faithfulness 1.0000 / answer_relevancy 0.8741 / context_precision 0.9944 / context_recall 0.8750`。
当前忠实性与相关性稳定，**召回与上下文精度仍是主要优化空间**。

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
├─ multimodal_RAG/
│  ├─ graph_video.py             # graph2 + 视频生成 的多模态图
│  ├─ video_state.py             # 多模态扩展 state
│  ├─ video_generate_node.py     # 视频生成节点（Sora / Kling）
│  ├─ video_parser.py            # 视频按帧采样解析
│  ├─ image_parser.py            # 图片解析
│  ├─ pdf_image_extractor.py     # PDF 图片抽取
│  └─ multimodal_ingest.py       # 多模态统一入库
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
│  ├─ PDF/                       # 原始 PDF 论文
│  ├─ image_input/               # 图片入库源
│  ├─ videos_output/             # 视频生成输出
│  └─ evaluation/                # 多轮评测输出（第 1~22 次）
├─ utils/
│  ├─ env_utils.py
│  ├─ log_utils.py
│  └─ draw_png.py                # 图结构可视化
├─ app_graph2.py                 # Gradio Web Demo（文字 + 语音）
└─ requirements.txt
```

---

## 9. 后续改进建议

- 提升召回与上下文精度（当前 `context_precision pass_rate=0.6`）
- 引入更系统的 badcase 标签体系（RET / TOOL / PLAN / GEN / SAFE）
- 增加引用命中率、工具调用成功率等业务指标
- 把 `env_utils.py` 中硬编码配置完全迁移到 `.env`
- 把 Gradio Demo 升级为 FastAPI + 前端，对外暴露稳定 API
- 多模态侧补充“图问答 / 视频问答”的端到端评测
