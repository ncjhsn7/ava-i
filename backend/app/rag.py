import hashlib
import math
import re
from collections import Counter
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


_BULLET = re.compile(r"^[\s]*[•▪▫◦‣·●○∙◆➤▸▹■-◿�]+\s*(.+)$")
_FIM_FRASE = re.compile(r"[.:;!?]$")


def limpar_texto(texto: str) -> str:
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"-\n(?=[a-zà-ÿ])", "", texto)
    itens: list[str] = []
    for bruta in texto.split("\n"):
        linha = bruta.strip()
        if not linha:
            continue
        marcador = _BULLET.match(linha)
        if marcador:
            corpo = marcador.group(1).strip()
            if corpo:
                itens.append("• " + corpo)
        elif itens and not _FIM_FRASE.search(itens[-1]):
            itens[-1] += " " + linha
        else:
            itens.append(linha)
    vistos: set[str] = set()
    saida: list[str] = []
    for linha in itens:
        chave = linha.lower()
        if not linha.startswith("• ") and chave in vistos:
            continue
        vistos.add(chave)
        saida.append(re.sub(r"\s{2,}", " ", linha).strip())
    return "\n".join(saida)


def extrair_texto(conteudo: bytes) -> str:
    leitor = PdfReader(BytesIO(conteudo))
    return "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)


def _eh_tabela(linha: str) -> bool:
    if linha.startswith("• "):
        return False
    if " " not in linha:
        return True
    if re.match(r"^[\w./-]+\s*\(\d+\)$", linha):
        return True
    if re.match(r"^[\w./-]+:?\s*[\d.]+$", linha):
        return True
    if re.search(r"::=|OBJECT-TYPE|SYNTAX|\bIpAddress\b|[{}]", linha):
        return True
    if len(re.findall(r"\w+\s*\(\d+\)", linha)) >= 2:
        return True
    return False


def _candidato_titulo(s: str) -> bool:
    return bool(
        s and not s.startswith("• ") and len(s) <= 80 and not _FIM_FRASE.search(s)
        and re.search(r"[A-Za-zÀ-ÿ]", s) and not _eh_tabela(s)
    )


def segmentar_topicos(texto: str) -> list[tuple[str, str]]:
    texto = re.sub(r"-\n(?=[a-zà-ÿ])", "", texto.replace("\r", "\n"))
    linhas = []
    for bruta in texto.split("\n"):
        if not bruta.strip():
            continue
        marcador = _BULLET.match(bruta.strip())
        linhas.append("• " + marcador.group(1).strip() if marcador else bruta.strip())
    contagem: Counter = Counter()
    for s in linhas:
        if _candidato_titulo(s):
            contagem[s] += 1
    titulos = {s for s, c in contagem.items() if c >= 2}
    topicos: list[tuple[str, list[str]]] = []
    titulo_atual: str | None = None
    corpo: list[str] = []
    for s in linhas:
        if s in titulos:
            if titulo_atual is not None or corpo:
                topicos.append((titulo_atual or "", corpo))
            titulo_atual, corpo = s, []
        elif not _eh_tabela(s):
            corpo.append(s)
    if titulo_atual is not None or corpo:
        topicos.append((titulo_atual or "", corpo))
    unidos: list[tuple[str, list[str]]] = []
    for t, c in topicos:
        if unidos and unidos[-1][0] == t and t:
            unidos[-1][1].extend(c)
        else:
            unidos.append((t, list(c)))
    return [
        (t, limpar_texto("\n".join(c)))
        for t, c in unidos
        if len(re.findall(r"[A-Za-zÀ-ÿ]{2,}", " ".join(c))) >= 8
    ]


def fragmentar(texto: str) -> list[str]:
    divisor = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    return [c for c in divisor.split_text(texto) if len(c.strip()) > 80]


def indexar(material_id: int, chunks: list[str]) -> None:
    col = _colecao(material_id)
    col.add(documents=chunks, ids=[f"c{i}" for i in range(len(chunks))])


def indexar_topicos(material_id: int, topicos: list[tuple[str, str]]) -> None:
    col = _colecao(material_id)
    col.add(
        documents=[c for _, c in topicos],
        metadatas=[{"titulo": t} for t, _ in topicos],
        ids=[f"t{i}" for i in range(len(topicos))],
    )


def obter_topicos(material_id: int) -> list[tuple[str, str]]:
    col = _colecao(material_id)
    dados = col.get(include=["documents", "metadatas"])
    ids = dados.get("ids") or []
    docs = dados.get("documents") or []
    metas = dados.get("metadatas") or [{} for _ in docs]
    trios = sorted(zip(ids, docs, metas), key=lambda p: int(re.sub(r"\D", "", p[0]) or 0))
    return [((m or {}).get("titulo", ""), d) for _, d, m in trios]


def vizinhos(material_id: int, trecho: str, k: int = 2) -> str:
    col = _colecao(material_id)
    res = col.query(query_texts=[trecho], n_results=min(k + 1, max(1, col.count())))
    docs = res["documents"][0] if res["documents"] else []
    return "\n---\n".join(d for d in docs if d != trecho)[:1500]


def remover_indice(material_id: int) -> None:
    try:
        _cliente.delete_collection(f"material_{material_id}")
    except Exception:
        pass


def _chunk_util(texto: str) -> bool:
    palavras = re.findall(r"[A-Za-zÀ-ÿ]{2,}", texto)
    if len(palavras) < 15:
        return False
    maiusculas = sum(1 for p in palavras if p.isupper())
    return maiusculas / len(palavras) < 0.4


def bons_chunks(chunks: list[str]) -> list[str]:
    bons = [c for c in chunks if _chunk_util(c)]
    return bons or chunks


def obter_chunks(material_id: int) -> list[str]:
    col = _colecao(material_id)
    dados = col.get()
    ids = dados.get("ids") or []
    docs = dados.get("documents") or []
    pares = sorted(zip(ids, docs), key=lambda p: int(re.sub(r"\D", "", p[0]) or 0))
    return [d for _, d in pares]


def _bom_trecho(texto: str) -> bool:
    palavras = re.findall(r"[A-Za-zÀ-ÿ]{2,}", texto)
    if len(palavras) < 12:
        return False
    pontuacao = len(re.findall(r"[.!?]", texto))
    densidade = len({p.lower() for p in palavras}) / len(palavras)
    return pontuacao >= 2 and densidade >= 0.5


def selecionar_chunks(chunks: list[str], n: int) -> list[tuple[int, str]]:
    bons = [c for c in chunks if _bom_trecho(c)]
    base = bons if len(bons) >= n else (bons or chunks)
    if len(base) <= n:
        return list(enumerate(base))
    passo = len(base) / n
    return [(int(i * passo), base[int(i * passo)]) for i in range(n)]
