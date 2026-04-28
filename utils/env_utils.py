import os

from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

MILVUS_URI = 'http://47.120.10.76:19530'

COLLECTION_NAME = 't_collection01'

os.environ['TAVILY_API_KEY'] = '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'