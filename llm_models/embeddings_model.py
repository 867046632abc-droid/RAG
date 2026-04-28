from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from utils.env_utils import OPENAI_API_KEY

openai_embedding = OpenAIEmbeddings(
    openai_api_key=OPENAI_API_KEY,
)

model_name = "BAAI/bge-base-zh-v1.5"
model_kwargs = {"device": "cpu"}
encode_kwargs = {"normalize_embeddings": True}
bge_embedding = HuggingFaceEmbeddings(
    model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
)
