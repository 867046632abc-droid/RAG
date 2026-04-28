from tools.retriever_tools import get_retriever
from utils.log_utils import log


def retrieve(state):
    """Retrieve related documents from the vector store."""
    log.info("---去知识库中检索文档---")
    question = state["question"]
    transform_count = state.get("transform_count", 0)
    retriever = get_retriever()
    documents = retriever.invoke(question)
    return {
        "documents": documents,
        "question": question,
        "transform_count": transform_count,
    }
