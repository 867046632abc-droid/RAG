# RAG 项目改进建议报告

> 基于第7、8、10次 RAGAS 评测数据，结合 `graph2` 与 `documents` 全部源码分析生成
> 生成日期：2026-04-25

---

## 评测数据横向对比

| 指标 | 第7次（旧测试集） | 第8次（旧测试集） | 第10次（人工测试集） | 趋势 |
|------|----------|----------|-----------|------|
| faithfulness | 0.788 | **0.922** | 0.850 | 第10次下降，测试集更难 |
| answer_relevancy | 0.643 | 0.870 | **0.877** | 持续改善 |
| context_precision | 0.800 | 0.864 | **0.981** | 显著跃升 |
| context_recall | 0.800 | 0.900 | 0.900 | 趋于瓶颈 |
| 空检索率 | 30% | 10% | **0%** | 人工测试集规避了空检索 |

### 一、核心问题定位

1. **faithfulness 衰退**（第10次 HKMG=0.5，DSA=0.25）：检索到了正确主题但错误文档（同主题多版本文章混入），模型基于检索内容作答却与 reference_context 不对齐，RAGAS 判为幻觉。
2. **context_recall 瓶颈**（FinFET=0.667，EUV=0.333）：问题涉及跨段落多知识点，k=4 检索不够覆盖。
3. **历史空检索**："掺杂浓度范围"、"源材料利用率" 等关键词问题检索持续为空，根因是 `cnalphanumonly` 过滤器损坏化学符号 + BM25 专业词典缺失。


## 二、文档解析与切片优化（`documents/markdown_parser.py`）

### 2.1 当前问题

- `UnstructuredMarkdownLoader` 使用 `strategy='fast'`，对嵌套列表、表格、公式等结构解析质量差
- `SemanticChunker` 在段落少的短文档上会切出过多微小碎片
- `merge_title_content` 的拼接逻辑会将所有子内容堆入同一 chunk，造成单 chunk 过长（可能超过 Milvus 6000 字上限）
- 无 chunk overlap，跨 chunk 边界的知识被截断
- 语义切分阈值 500 字对纯短段落文档无效，会全部跳过

### 2.2 改进建议

**① 增加 chunk overlap**

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

fallback_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=80,          # 新增 80 字 overlap
    separators=["\n\n", "\n", "。", "；", " "]
)
```

**② merge_title_content 增加长度保护**

当 `parent_dict[parent_id].page_content` 超过 1500 字时，将当前子块单独存为独立 Document 并携带父标题作为 metadata，而不是继续拼接。

**③ 增强元数据提取**

```python
document.metadata['title_path'] = ' -> '.join(title_hierarchy)  # 标题层级路径
document.metadata['section_level'] = depth                       # 段落深度
document.metadata['char_count'] = len(document.page_content)    # 字数统计
```

**④ 增加文档质量过滤**

```python
def _is_quality_chunk(doc: Document) -> bool:
    text = doc.page_content.strip()
    if len(text) < 50:        # 过短，无实质内容
        return False
    if text.count('->') > 5: # 纯标题路径拼接，无正文
        return False
    return True
```

**⑤ 针对半导体技术文档的分块策略**

- 含数值/公式的段落（含 `eV`、`cm⁻²`、`nm`、`%` 等单位）保持完整，不做进一步切分
- 叙述性长段落（NarrativeText 类型）再做语义切分

---

## 三、Milvus 索引参数优化（`documents/milvus_db.py`）

### 3.1 最严重问题：`cnalphanumonly` 过滤器破坏专业符号

```python
# 当前（有问题）
analyzer_params={"tokenizer": "jieba", "filter": ["cnalphanumonly"]}
```

`cnalphanumonly` 会删除所有非中文/英文/数字字符，导致：
- 化学下标（₂、₃）→ H₂O 变成 H2O，BM25 索引错乱
- 指数符号（¹³）→ 10¹³ cm⁻² 的上标被破坏
- 希腊字母（χ、λ、μ）→ 专业术语完全无法匹配

这是"掺杂浓度 10¹⁴~10¹⁹"、"bm25_k1=1.2"等数值型问题检索为空的**根本原因**。

```python
# 建议修改为
analyzer_params={
    "tokenizer": "jieba",
    "filter": ["lowercase"]   # 去掉 cnalphanumonly，改用 lowercase
}
```

### 3.2 HNSW 参数优化

```python
# 当前：efConstruction 偏低，索引质量差
params={"M": 35, "efConstruction": 64}

# 建议
params={"M": 32, "efConstruction": 200}  # efConstruction 提升到 200，显著改善 recall
```

### 3.3 BM25 参数优化

```python
# 当前：通用中文参数
params={"bm25_k1": 1.2, "bm25_b": 0.75}

# 建议：适配专业技术文档
params={
    "bm25_k1": 1.5,                      # 提升词频饱和度，有利于精确术语匹配
    "bm25_b": 0.5,                       # 降低文档长度归一化，减少对长技术段落的惩罚
    "inverted_index_algo": "DAAT_WAND"   # WAND 算法在 top-k 场景更高效
}
```

### 3.4 升级 Embedding 模型维度

```python
# 当前：bge-small-zh-v1.5，dim=512（最轻量版本）
schema.add_field(field_name='dense', datatype=DataType.FLOAT_VECTOR, dim=512)

# 建议：升级到 bge-base-zh-v1.5，dim=768，语义理解质量显著提升
schema.add_field(field_name='dense', datatype=DataType.FLOAT_VECTOR, dim=768)
```

同步修改 `llm_models/embeddings_model.py`：

```python
model_name = "BAAI/bge-base-zh-v1.5"   # 从 small 升级到 base
encode_kwargs = {
    "normalize_embeddings": True,
    "query_instruction": "为半导体技术问题生成检索向量："  # BGE 系列支持 instruction
}
```

---

## 四、检索策略优化（`tools/retriever_tools.py`）

### 4.1 当前问题

```python
retriever = mv.vector_store_saved.as_retriever(
    search_kwargs={
        "k": 4,
        "score_threshold": 0.1,             # 过于宽松，无效过滤
        "filter": {"category": "content"},  # 排除了含子内容的 Title 文档
    },
)
```

- `category == "content"` 过滤器排除了 Title 类型文档，但 `merge_title_content` 处理后 Title 文档已包含子内容（如"MOCVD -> 高频电子器件 GaN HEMT..."），过滤导致召回损失
- k=4 不足以覆盖 EUV 光刻胶（三类挑战）、HKMG（多机制）等多知识点问题
- score_threshold=0.1 几乎没有过滤效果

### 4.2 改进建议

**① 提高 top_k，调整 score_threshold**

```python
retriever = mv.vector_store_saved.as_retriever(
    search_kwargs={
        "k": 8,                      # 从 4 提升到 8
        "score_threshold": 0.3,      # 适度提升过滤阈值
        "ranker_type": "rrf",
        "ranker_params": {"k": 60},  # RRF k 降低，增大头部文档权重
        "filter": {"category": "content"},
    },
)
```

**② 增加空检索 Fallback 机制**（修改 `graph2/retriever_node.py`）

```python
def retrieve(state):
    question = state["question"]
    transform_count = state.get("transform_count", 0)
    documents = retriever.invoke(question)

    # Fallback：无结果时去掉 score_threshold 重试
    if not documents:
        log.warning("首次检索无结果，使用宽松策略重试")
        fallback_retriever = mv.vector_store_saved.as_retriever(
            search_kwargs={"k": 6, "filter": {"category": "content"}}
        )
        documents = fallback_retriever.invoke(question)

    return {"documents": documents, "question": question, "transform_count": transform_count}
```

**③ 增加查询扩展（Query Expansion）**

```python
TERM_ALIASES = {
    "HKMG": "高介电常数金属栅",
    "FinFET": "鳍式场效应晶体管",
    "MOCVD": "金属有机化学气相沉积",
    "EUV": "极紫外光刻",
    "DSA": "定向自组装",
    "WLP": "晶圆级封装",
    "GAAFET": "全环绕栅极晶体管",
    "SADP": "自对准双重曝光",
    "LELE": "双重曝光双重刻蚀",
    "CMP": "化学机械抛光",
    "ALD": "原子层沉积",
}

def expand_query(question: str) -> str:
    for abbr, full in TERM_ALIASES.items():
        if abbr in question and full not in question:
            question = question + f"（{full}）"
    return question
```

---

## 五、提示词全面优化

### 5.1 生成提示词（`graph2/generate_node2.py`）

**问题**："只回答问题本身，不要扩展背景" 与 faithfulness 要求矛盾，LLM 会用训练数据补充上下文未有的知识，导致 faithfulness 被判低（第10次 HKMG=0.5、DSA=0.25 的根因）。

```python
# 当前
template="你是一个高智商问答任务助手。请利用以下检索到的上下文内容，先理解问题再回答问题。只回答问题本身，不要扩展背景，不确定就说不知道。回答保持简洁。\n问题：{question} \n上下文：{context} \n回答："

# 建议改为
template=(
    "你是一名严谨的半导体技术问答助手。\n"
    "【强制约束】：你的回答必须完全基于且仅基于下方提供的上下文内容，"
    "不得引入上下文以外的任何知识，包括你的训练数据。\n"
    "【处理规则】：\n"
    "- 若上下文中包含问题的答案：直接引用原文关键信息，简洁作答\n"
    "- 若上下文中含有数值/参数：原样引用，不推算、不补充\n"
    "- 若上下文为空或不包含回答所需信息：回答'根据现有资料无法回答此问题'\n"
    "- 不得因问题未提及就省略上下文中已有的关键数值\n\n"
    "问题：{question}\n\n"
    "上下文：\n{context}\n\n"
    "回答："
)
```

### 5.2 文档相关性评分提示词（`graph2/grader_chain.py`）

**问题**："不需要非常严格的测试" 导致大量低质量文档通过，拉低 faithfulness。

```python
# 当前
system = """你是一个评估检索文档与用户问题相关性的评分器。\n 
    如果文档包含与用户问题相关的关键词或语义含义，则评为相关。\n
    不需要非常严格的测试，目的是过滤掉错误的检索结果。\n
    给出'yes'或'no'的二元评分来表示文档是否与问题相关。"""

# 建议改为
system = """你是一个专业的半导体技术文档相关性评分器。
判断标准：文档内容是否直接包含回答该问题所需的技术信息。
- "yes"：文档包含与问题直接相关的技术术语、数值、机制描述，能够为回答提供具体依据
- "no"：文档仅主题相关但不含具体答案信息，或属于引言/结论等泛泛描述，或内容与问题无关
请给出严格的 yes/no 二元评分。"""
```

### 5.3 幻觉检测提示词（`graph2/grade_hallucinations_chain.py`）

**问题**：未对数值型答案做严格要求，导致模型补充推算值（如 x=0/1）通过幻觉检测。

```python
# 建议改为
system = """你是一个严格的事实核查评分器。
评判标准：生成内容中的每一个具体事实（尤其是数值、参数、材料名称）必须能在给定事实集中找到明确依据。
- "yes"：所有具体陈述均可在事实集中找到原文支撑（合理总结和改写允许）
- "no"：存在任何事实集未提及的具体数值、参数或机制描述（包括推算和补充）
注意：对事实集内容的合理总结允许判 yes，但补充事实集以外的具体数字必须判 no。"""
```

### 5.4 问题路由提示词（`graph2/query_route_chain.py`）

**问题**：路由词典范围窄（"半导体材料、芯片制造、光刻技术"），DSA、WLP、GAAFET 等主题可能被误路由到 web_search。

```python
# 建议改为
system = """你是一个擅长将用户问题路由到向量知识库或网络搜索的专家。
向量知识库包含以下主题的专业文档：
- 半导体材料与器件（HKMG、FinFET、GAAFET、量子点、量子阱）
- 芯片制造工艺（等离子体刻蚀、MOCVD、ALD、CMP、薄膜沉积）
- 光刻技术（EUV、多重曝光、DSA、光刻胶、SADP、SAQP）
- 封装技术（WLP、晶圆级封装、异构集成、RDL）
- 半导体测试与可靠性评估
对于上述主题的问题，优先使用向量知识库。
仅对时事新闻、价格行情、具体产品发布等实时信息使用网络搜索。"""
```

### 5.5 查询重写提示词（`graph2/transform_query_node.py`）

**问题**：重写后可能丢失原始专业术语；提示词在函数内部创建，每次调用都重建（性能浪费）。

```python
# 建议：移至模块级别预创建
_rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "你是专门为半导体技术知识库检索优化问题的专家。\n"
        "规则：\n"
        "1. 保留原始问题中的所有专业术语（如 HKMG、EUV、FinFET）和数值\n"
        "2. 补充问题中可能的隐含条件（如工艺节点、材料类型）\n"
        "3. 将口语化描述改为技术文档中常见的表达方式\n"
        "4. 输出单一优化后的问题，不加解释"
    )),
    ("human", "原始问题：{question}\n\n优化后的问题："),
])
_question_rewriter = _rewrite_prompt | llm | StrOutputParser()
```

---

## 六、CRAG 流程逻辑优化（`graph2/graph_2.py` + `graph2/graph_state2.py`）

### 6.1 generation 无限循环风险

```python
# 当前：幻觉时重新生成，但没有次数限制
{
    "not supported": "generate",  # ← 可能死循环
    "useful": END,
    "not useful": "transform_query",
}
```

**建议在 GraphState 中增加 generation_count**：

```python
class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[Document]
    transform_count: int
    generation_count: int    # 新增：跟踪生成重试次数
    original_question: str  # 新增：保留用户原始问题
```

**在条件判断中增加上限**：

```python
def grade_generation_v_documents_and_question(state):
    generation_count = state.get("generation_count", 0)

    # 超过重试上限时强制输出
    if generation_count >= 3:
        log.warning("生成重试次数超过上限，强制输出当前结果")
        return "useful"

    # ... 原有逻辑不变 ...
```

### 6.2 web_search 结果缺少质量过滤

当前 `web_search → generate` 直连，网络搜索结果未经相关性过滤。建议改为经过 grade_documents：

```python
# 当前
workflow.add_edge("web_search", "generate")

# 建议
workflow.add_edge("web_search", "grade_documents")
```

### 6.3 transform_query 后保留原始问题

```python
def transform_query(state):
    original_question = state.get("original_question") or state["question"]
    # ... 重写逻辑 ...
    return {
        "documents": documents,
        "question": better_question,
        "original_question": original_question,   # 新增，防止多轮改写后意图漂移
        "transform_count": transform_count + 1
    }
```

---

## 七、write_milvus.py 写入管道优化

**当前问题：**
- 批次大小固定为 20，未考虑单文档大小
- 写入失败仅记录日志，无重试机制
- 子进程崩溃后无法从断点续写

```python
def milvus_writer_process(input_queue: Queue, max_retries: int = 3):
    mv = MilvusVectorSave()
    mv.create_connection()
    total_count = 0

    while True:
        datas = input_queue.get()
        if datas is None:
            break

        for retry in range(max_retries):
            try:
                mv.add_documents(datas)
                total_count += len(datas)
                log.info(f"累计已写入: {total_count} 个文档")
                break
            except Exception as e:
                log.error(f"写入失败（第{retry+1}次）: {e}")
                if retry == max_retries - 1:
                    _save_failed_batch(datas)  # 持久化失败批次供后续重试
```

---

## 八、综合优先级排序

| 优先级 | 问题描述 | 涉及文件 | 预期收益 |
|-------|---------|---------|--------|
| P0 紧急 | 修复模型 ID 的非标准破折号（U+2011） | `llm_models/all_llm.py` | 解决第9次崩溃，恢复正常运行 |
| P0 紧急 | 去掉 `cnalphanumonly` 过滤器，改为 `lowercase` | `documents/milvus_db.py` | 修复数值型问题空检索，预计 context_recall +10% |
| P1 高 | 生成提示词增加"仅基于上下文"强制约束 | `graph2/generate_node2.py` | faithfulness 0.85 → 0.92+ |
| P1 高 | 检索 top_k 从 4 → 8，增加 Fallback 机制 | `tools/retriever_tools.py` | context_recall 0.90 → 0.95+ |
| P1 高 | 幻觉检测提示词强化数值核查 | `graph2/grade_hallucinations_chain.py` | 减少 faithfulness 误判 |
| P2 中 | 升级 embedding 到 bge-base-zh-v1.5（dim=768） | `llm_models/embeddings_model.py` + `milvus_db.py` | 整体语义匹配质量提升，需重建索引 |
| P2 中 | HNSW efConstruction 64 → 200 | `documents/milvus_db.py` | dense 检索 recall 提升，需重建索引 |
| P2 中 | 增加 generation_count 限制，防止无限循环 | `graph2/graph_2.py` + `graph_state2.py` | 系统稳定性保障 |
| P2 中 | 路由提示词扩展主题范围 | `graph2/query_route_chain.py` | 减少 DSA/WLP/GAAFET 等误路由 |
| P3 低 | Chunk overlap 80 字 | `documents/markdown_parser.py` | 跨 chunk 边界知识恢复 |
| P3 低 | transform_query 保留 original_question | `graph2/transform_query_node.py` | 多轮改写后防意图漂移 |
| P3 低 | 查询扩展：缩略词 ↔ 全称映射 | `tools/retriever_tools.py` | 改善专业缩写的 BM25 召回 |
| P3 低 | web_search 结果经过 grade_documents 过滤 | `graph2/graph_2.py` | 减少网络噪音进入生成阶段 |
