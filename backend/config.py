import os
from pathlib import Path
from dotenv import load_dotenv



load_dotenv()
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
VECTOR_DIR = BASE_DIR / "vectors"
DB_PATH = BASE_DIR / "research_assistant.db"

UPLOAD_DIR.mkdir(exist_ok=True)
VECTOR_DIR.mkdir(exist_ok=True)

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-please")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LLM_MODEL = "openai/gpt-oss-120b:free"

# RAG
CHUNK_SIZE = 800           # characters per chunk
CHUNK_OVERLAP = 100        # overlap between chunks
TOP_K_RESULTS = 5          # top chunks to retrieve
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # fast, accurate, 384-dim

# Reranking
INITIAL_RETRIEVAL_K = 15
FINAL_RERANK_K = 5
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
