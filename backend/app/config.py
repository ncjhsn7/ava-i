import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ava.db")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
LLM_MODEL = os.getenv("LLM_MODEL") or "claude-sonnet-4-6"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
EMBEDDINGS = os.getenv("EMBEDDINGS", "default")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_data")
QUESTOES_POR_MATERIAL = int(os.getenv("QUESTOES_POR_MATERIAL", "3"))
