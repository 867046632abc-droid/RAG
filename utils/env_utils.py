import os

from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
QWEN_API_KEY=os.getenv('QWEN_API_KEY')
SEED_API_KEY=os.getenv('SEED_API_KEY')

_raw_milvus_uri = os.getenv('MILVUS_URI', '47.121.139.76:19530')
if '://' not in _raw_milvus_uri and not _raw_milvus_uri.endswith('.db'):
    _raw_milvus_uri = f"tcp://{_raw_milvus_uri}"
MILVUS_URI = _raw_milvus_uri

COLLECTION_NAME = 't_collection01'

os.environ['TAVILY_API_KEY'] = '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'
