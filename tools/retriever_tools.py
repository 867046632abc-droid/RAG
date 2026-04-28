from langchain_core.tools import create_retriever_tool

from documents.milvus_db import MilvusVectorSave


mv = MilvusVectorSave()
mv.create_connection()

retriever = mv.vector_store_saved.as_retriever(
    search_type="similarity",
    search_kwargs={
        "k": 10,
        "ranker_type": "rrf",
        "ranker_params": {"k": 60},
        "filter": {"category": "content"},
    },
)

retriever_tool = create_retriever_tool(
    retriever,
    "rag_retriever",
    "Search and return relevant documents from the Milvus knowledge base.",
)


def get_retriever(k: int = 10):
    if k == 10:
        return retriever
    return mv.vector_store_saved.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": k,
            "ranker_type": "rrf",
            "ranker_params": {"k": 60},
            "filter": {"category": "content"},
        },
    )

