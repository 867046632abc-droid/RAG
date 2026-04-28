from __future__ import annotations

from functools import lru_cache

from sentence_transformers import CrossEncoder

from utils.log_utils import log

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_TOP_N = 5
RERANKER_MAX_LEN = 512


@lru_cache(maxsize=1)
def _get_model() -> CrossEncoder:
    log.info("---加载 BGE Reranker 模型: %s---", RERANKER_MODEL)
    return CrossEncoder(RERANKER_MODEL, max_length=RERANKER_MAX_LEN)


def rerank(state: dict, top_n: int = RERANKER_TOP_N) -> dict:
    """Cross-encoder rerank: keep top_n documents scored by BGE reranker."""
    log.info("---BGE Reranker 精排（保留 top-%d）---", top_n)
    question = state["question"]
    documents = state["documents"]

    if not documents:
        log.info("---Reranker: 无候选文档，跳过---")
        return {"documents": [], "question": question}

    model = _get_model()
    pairs = [(question, doc.page_content[:RERANKER_MAX_LEN * 4]) for doc in documents]
    scores = model.predict(pairs)

    ranked = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
    top_docs = [doc for _, doc in ranked[:top_n]]

    log.info(
        "---Reranker: %d → %d 篇，top 分数 %.4f / %.4f---",
        len(documents), len(top_docs),
        ranked[0][0] if ranked else 0,
        ranked[top_n - 1][0] if len(ranked) >= top_n else 0,
    )
    return {"documents": top_docs, "question": question}
