from typing import List
from langchain_experimental.text_splitter import SemanticChunker

from llm_models.embeddings_model import openai_embedding
from utils.log_utils import log
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document


class MarkdownParser:
    """
    专门负责markdown文件的解析和切片
    """
    def __init__(self, chunk_overlap: int = 80):
        self.chunk_overlap = chunk_overlap
        self.text_splitter = SemanticChunker(
            openai_embedding, breakpoint_threshold_type="percentile"
        )

    def _add_chunk_overlap(self, docs: List[Document]) -> List[Document]:
        if self.chunk_overlap <= 0:
            return docs

        overlap_docs = []
        prev_content = ""
        for doc in docs:
            content = doc.page_content
            if prev_content:
                overlap_text = prev_content[-self.chunk_overlap:]
                content = overlap_text + "\n" + content
            overlap_docs.append(
                Document(page_content=content, metadata=dict(doc.metadata) if doc.metadata else {})
            )
            prev_content = doc.page_content
        return overlap_docs

    def text_chunker(self, datas: List[Document]) -> List[Document]:
        new_docs = []
        for d in datas:
            if len(d.page_content) > 300:  # 内容超出了阈值，则按照语义再切割
                split_docs = self.text_splitter.split_documents([d])
                new_docs.extend(self._add_chunk_overlap(split_docs))
                continue
            new_docs.append(d)
        return new_docs


    def parse_markdown(self, md_file: str) -> List[Document]:
        loader = UnstructuredMarkdownLoader(
            file_path=md_file,
            mode='elements',
            strategy='hi-res'
        )
        docs = []
        for doc in loader.lazy_load():
            docs.append(doc)

        return docs

    def merge_title_content(self, datas: List[Document]) -> List[Document]:
        merged_data = []
        parent_dict = {}  # 是一个字典，保存所有的父document， key为当前父document的ID
        for document in datas:
            metadata = document.metadata
            if 'languages' in metadata:
                metadata.pop('languages')

            parent_id = metadata.get('parent_id', None)
            category = metadata.get('category', None)
            element_id = metadata.get('element_id', None)

            if category == 'NarrativeText' and parent_id is None:  # 是否为：内容document
                merged_data.append(document)
            if category == 'Title':
                document.metadata['title'] = document.page_content
                if parent_id in parent_dict:
                    document.page_content = parent_dict[parent_id].page_content + ' -> ' + document.page_content
                parent_dict[element_id] = document
            if category != 'Title' and parent_id:
                parent_dict[parent_id].page_content = parent_dict[parent_id].page_content + ' ' + document.page_content
                parent_dict[parent_id].metadata['category'] = 'content'

        # 处理字典
        if parent_dict is not None:
            merged_data.extend(parent_dict.values())

        return merged_data

    def parse_markdown_to_documents(self, md_file: str, encoding='utf-8') -> List[Document]:
        documents = self.parse_markdown(md_file)
        log.info(f'文件解析后的docs长度: {len(documents)}')

        merged_documents = self.merge_title_content(documents)

        log.info(f'文件合并后的长度: {len(merged_documents)}')

        chunk_documents = self.text_chunker(merged_documents)
        log.info(f'语义切割后的长度: {len(chunk_documents)}')
        return chunk_documents




if __name__ == '__main__':
    file_path = r'C:\Users\20661\Desktop\myproject\RAG_PROJECT\RAG_PROJECT\datas\md\tech_report_7wc7z3ar.md'
    parser = MarkdownParser()
    docs = parser.parse_markdown_to_documents(file_path)
    for item in docs:
        print(f"元数据: {item.metadata}")
        print(f"标题: {item.metadata.get('title', None)}")
        print(f"doc的内容: {item.page_content}\n")
        print("------" * 10)
