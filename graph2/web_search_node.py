from typing import Any

from langchain_core.documents import Document

from llm_models.all_llm import web_search_tool
from utils.log_utils import log


def web_search(state):
    """
    基于优化后的问题进行网络搜索

    Args:
        state (dict): 当前图状态，包含优化后的问题

    Returns:
        state (dict): 更新后的状态，documents字段替换为网络搜索结果
    """
    log.info("---WEB SEARCH---")  # 阶段标识
    question = state["question"]  # 获取优化后的问题

    # 执行网络搜索并统一为 Document 列表，避免不同返回结构导致类型错误
    docs = web_search_tool.invoke({"query": question})  # 调用网络搜索工具
    normalized_docs = _normalize_web_results(docs)

    return {"documents": normalized_docs, "question": question}  # 返回更新状态


def _normalize_web_results(raw_docs: Any) -> list[Document]:
    if raw_docs is None:
        return []

    items = raw_docs if isinstance(raw_docs, list) else [raw_docs]
    normalized: list[Document] = []
    for item in items:
        if isinstance(item, Document):
            if (item.page_content or "").strip():
                normalized.append(item)
            continue

        if isinstance(item, dict):
            content = (
                item.get("content")
                or item.get("snippet")
                or item.get("page_content")
                or item.get("raw_content")
                or item.get("answer")
                or ""
            )
            if isinstance(content, list):
                content = "\n".join(str(x) for x in content)
            text = str(content).strip()
            if not text:
                continue

            metadata = {}
            for key in ("url", "title", "source", "score"):
                if key in item:
                    metadata[key] = item[key]
            normalized.append(Document(page_content=text, metadata=metadata))
            continue

        text = str(item).strip()
        if text:
            normalized.append(Document(page_content=text))

    return normalized
