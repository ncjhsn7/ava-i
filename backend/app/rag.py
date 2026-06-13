import hashlib
import math
import re
from io import BytesIO
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from . import config


class EmbeddingHashSimples:
    def __init__(self, dim: int = 384):
        self.dim = dim

    def name(self) -> str:
        return "hash-simples"

    def embed_query(self, input):
        return self(input)

    def embed_documents(self, input):
        return self(input)

    def __call__(self, input: list[str]) -> list[list[float]]:
        vetores = []
        for texto in input:
            v = [0.0] * self.dim
            for token in re.findall(r"\w+", texto.lower()):
                h = int(hashlib.md5(token.encode()).hexdigest(), 16)
                v[h % self.dim] += 1.0
            norma = math.sqrt(sum(x * x for x in v)) or 1.0
            vetores.append([x / norma for x in v])
        return vetores


_cliente = chromadb.PersistentClient(path=config.CHROMA_DIR)
_fn = EmbeddingHashSimples() if config.EMBEDDINGS == "simple" else None


def _colecao(material_id: int):
    nome = f"material_{material_id}"
    if _fn:
        return _cliente.get_or_create_collection(nome, embedding_function=_fn)
    return _cliente.get_or_create_collection(nome)


def extrair_texto(conteudo: bytes) -> str:
    leitor = PdfReader(BytesIO(conteudo))
    return "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)


def fragmentar(texto: str) -> list[str]:
    divisor = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    return [c for c in divisor.split_text(texto) if len(c.strip()) > 80]


def indexar(material_id: int, chunks: list[str]) -> None:
    col = _colecao(material_id)
    col.add(documents=chunks, ids=[f"c{i}" for i in range(len(chunks))])


def vizinhos(material_id: int, trecho: str, k: int = 2) -> str:
    col = _colecao(material_id)
    res = col.query(query_texts=[trecho], n_results=min(k + 1, max(1, col.count())))
    docs = res["documents"][0] if res["documents"] else []
    return "\n---\n".join(d for d in docs if d != trecho)[:1500]


def selecionar_chunks(chunks: list[str], n: int) -> list[tuple[int, str]]:
    if len(chunks) <= n:
        return list(enumerate(chunks))
    passo = len(chunks) / n
    return [(int(i * passo), chunks[int(i * passo)]) for i in range(n)]
