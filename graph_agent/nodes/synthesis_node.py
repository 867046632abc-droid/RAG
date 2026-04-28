"""合成节点：将专家输出（或 Web 搜索结果）整理为最终面向用户的答案，并附置信度标注。"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from llm_models.all_llm import llm
from utils.log_utils import log

_SYNTHESIS_PROMPT = PromptTemplate(
    template=(
        "你是一个半导体技术问答系统的最终回答整合者。\n"
        "下方是专家分析结果，请将其整理为简洁、结构清晰、面向用户的最终答案。\n"
        "要求：\n"
        "- 保留所有关键数值和技术术语\n"
        "- 去除冗余的格式标签（如【】标题）只保留核心内容\n"
        "- 语气简洁专业，不超过 300 字\n"
        "- 若内容包含对比，保留表格或分项结构\n\n"
        "用户问题：{question}\n\n"
        "专家分析：\n{expert_output}\n\n"
        "最终答案："
    ),
    input_variables=["question", "expert_output"],
)

_WEB_SYNTHESIS_PROMPT = PromptTemplate(
    template=(
        "你是一个信息整合助手，基于下方网络搜索结果回答用户问题。\n"
        "【约束】：只使用搜索结果中的信息，不添加额外知识。\n\n"
        "用户问题：{question}\n\n"
        "搜索结果：\n{context}\n\n"
        "回答："
    ),
    input_variables=["question", "context"],
)

_CONFIDENCE_HINT = {
    "high": "",
    "medium": "\n\n> ⚠️ 注：当前答案基于知识库文档，但可能未完整覆盖问题所有方面，建议结合原始资料核实。",
    "low": "\n\n> ⚠️ 注：知识库中相关资料有限，以下答案为系统尽力作答，置信度较低，请谨慎参考。",
    "": "",
}


def synthesize(state: dict) -> dict:
    """合成节点：整合专家输出，生成最终答案并附置信度提示。"""
    question = state["question"]
    expert_output = state.get("expert_output", "")
    confidence = state.get("confidence", "")
    documents = state.get("documents", [])

    if expert_output.strip():
        # RAG 路径：整合专家分析
        log.info("---[合成节点] 整合专家输出，置信度=%s---", confidence or "unknown")
        chain = _SYNTHESIS_PROMPT | llm | StrOutputParser()
        answer = chain.invoke({"question": question, "expert_output": expert_output})
    else:
        # Web 搜索路径：直接从搜索结果生成
        log.info("---[合成节点] 整合 Web 搜索结果---")
        context = "\n\n".join(d.page_content for d in documents) if documents else "（无搜索结果）"
        chain = _WEB_SYNTHESIS_PROMPT | llm | StrOutputParser()
        answer = chain.invoke({"question": question, "context": context})
        confidence = "medium"  # Web 结果默认中置信度

    hint = _CONFIDENCE_HINT.get(confidence, "")
    generation = answer.strip() + hint

    log.info("---[合成节点] 最终答案生成完毕（%d 字）---", len(generation))
    return {"generation": generation, "confidence": confidence}
