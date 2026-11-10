import os
from dotenv import load_dotenv

# O .env do backend sempre prevalece sobre variáveis já definidas no sistema/terminal.
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ava.db")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
LLM_MODEL = os.getenv("LLM_MODEL") or "claude-sonnet-4-6"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
# Modelo para tarefas leves (ex.: classificar a área do PDF); tem cota gratuita própria.
GEMINI_MODEL_LEVE = os.getenv("GEMINI_MODEL_LEVE") or "gemini-2.5-flash-lite"
# Modelo multimodal que transcreve páginas de PDF que são só imagem (slides exportados como figura).
GEMINI_MODEL_VISAO = os.getenv("GEMINI_MODEL_VISAO") or GEMINI_MODEL
# Páginas com imagem e menos palavras extraíveis que isto são lidas por visão (0 desliga).
VISAO_MIN_PALAVRAS = int(os.getenv("VISAO_MIN_PALAVRAS", "10"))
EMBEDDINGS = os.getenv("EMBEDDINGS", "default")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_data")
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "./uploads")
QUESTOES_POR_MATERIAL = int(os.getenv("QUESTOES_POR_MATERIAL", "3"))
