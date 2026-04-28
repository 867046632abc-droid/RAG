"""专家分发节点：根据意图路由到 4 个专家 Agent，每个 Agent 使用针对性 Prompt。

专家类型
--------
- factual_expert    : 精准事实提取，原样引用数值
- comparison_expert : 结构化对比分析，多维度拆解
- formula_expert    : 符号定义 + 推导逻辑 + 物理含义
- explanation_expert: 原理机制 + 工艺流程 + 类比解释
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from llm_models.all_llm import llm
from utils.log_utils import log

_BASE_CONSTRAINT = (
    "【严格约束】所有数值、参数、结论必须来自下方上下文，"
    "不得引入上下文以外的知识，包括训练数据。"
    "若上下文不含所需信息，明确说明"根据现有资料无法回答"。\n\n"
)

# ── 事实查询专家 ──────────────────────────────────────────────────────────────

_FACTUAL_PROMPT = PromptTemplate(
    template=(
        "你是半导体领域的事实查询专家。\n"
        + _BASE_CONSTRAINT
        + "任务：从上下文中精准提取回答问题所需的具体事实。\n"
        "规则：\n"
        "- 数值/参数原样引用，不做推算或单位换算\n"
        "- 直接给出事实，无需展开分析\n"
        "- 若有多个相关数值，逐条列出并注明来源语境\n\n"
        "问题：{question}\n\n"
        "上下文：\n{context}\n\n"
        "事实答案："
    ),
    input_variables=["question", "context"],
)

# ── 对比分析专家 ──────────────────────────────────────────────────────────────

_COMPARISON_PROMPT = PromptTemplate(
    template=(
        "你是半导体领域的对比分析专家。\n"
        + _BASE_CONSTRAINT
        + "任务：对用户提出的对比问题，按以下结构输出分析：\n\n"
        "【核心差异】（1-2句，直接点明最关键的不同点）\n"
        "【多维对比】（从结构、性能指标、工艺特点、适用场景等维度分项对比，"
        "每个维度一行，格式：维度 | A的特点 | B的特点）\n"
        "【结论】（在何种场景下选择哪种方案，以及依据）\n\n"
        "问题：{question}\n\n"
        "上下文：\n{context}\n\n"
        "对比分析："
    ),
    input_variables=["question", "context"],
)

# ── 公式推导专家 ──────────────────────────────────────────────────────────────

_FORMULA_PROMPT = PromptTemplate(
    template=(
        "你是半导体领域的公式分析专家。\n"
        + _BASE_CONSTRAINT
        + "任务：针对涉及公式、符号或量化关系的问题，按以下结构输出：\n\n"
        "【符号定义】（列出问题中涉及的所有符号及其物理含义）\n"
        "【核心关系】（用文字描述公式表达的定量关系，引用上下文中的原始表达式）\n"
        "【物理机制】（解释该公式反映的物理原理或工艺机制）\n"
        "【参数影响】（说明关键参数如何影响结果，数值来自上下文）\n\n"
        "问题：{question}\n\n"
        "上下文：\n{context}\n\n"
        "公式分析："
    ),
    input_variables=["question", "context"],
)

# ── 概念解释专家 ──────────────────────────────────────────────────────────────

_EXPLANATION_PROMPT = PromptTemplate(
    template=(
        "你是半导体领域的概念解释专家。\n"
        + _BASE_CONSTRAINT
        + "任务：深入解释技术概念的工作原理和工艺机制，按以下结构输出：\n\n"
        "【是什么】（一句话定义该概念/技术）\n"
        "【为什么】（引入该技术的动机：解决了什么问题）\n"
        "【怎么做】（工作原理或工艺步骤，引用上下文中的关键描述）\n"
        "【效果】（量化指标或实际效果，原样引用上下文中的数值）\n\n"
        "问题：{question}\n\n"
        "上下文：\n{context}\n\n"
        "概念解释："
    ),
    input_variables=["question", "context"],
)

# ── 内部辅助 ─────────────────────────────────────────────────────────────────

def _format_docs(docs: list) -> str:
    return "\n\n".join(d.page_content for d in docs) if docs else "（无上下文文档）"


def _run_expert(prompt: PromptTemplate, state: dict) -> str:
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "question": state["question"],
        "context": _format_docs(state["documents"]),
    })


# ── 公开分发函数 ──────────────────────────────────────────────────────────────

def expert_dispatch(state: dict) -> dict:
    """专家分发节点：按 state['intent'] 调用对应专家 Agent。"""
    intent = state.get("intent", "factual")
    question = state["question"]

    _PROMPT_MAP = {
        "factual": (_FACTUAL_PROMPT, "事实查询"),
        "comparison": (_COMPARISON_PROMPT, "对比分析"),
        "formula": (_FORMULA_PROMPT, "公式推导"),
        "explanation": (_EXPLANATION_PROMPT, "概念解释"),
    }

    prompt, label = _PROMPT_MAP.get(intent, (_FACTUAL_PROMPT, "事实查询（默认）"))
    log.info("---[%s 专家 Agent] 开始分析，问题：%s---", label, question[:60])

    expert_output = _run_expert(prompt, state)

    log.info("---[%s 专家 Agent] 输出 %d 字---", label, len(expert_output))
    return {
        "expert_output": expert_output,
        "question": question,
        "documents": state["documents"],
    }
