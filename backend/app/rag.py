import hashlib
import math
import os
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


# ---------- PDF original e localização da página de origem ----------

_cache_paginas: dict[int, list[str]] = {}


def caminho_pdf(material_id: int) -> str:
    return os.path.join(config.UPLOADS_DIR, f"{material_id}.pdf")


def salvar_pdf(material_id: int, conteudo: bytes) -> None:
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    with open(caminho_pdf(material_id), "wb") as f:
        f.write(conteudo)


def remover_pdf(material_id: int) -> None:
    _cache_paginas.pop(material_id, None)
    try:
        os.remove(caminho_pdf(material_id))
    except FileNotFoundError:
        pass


def _compacto(texto: str) -> str:
    return re.sub(r"[^0-9a-zà-ÿ]", "", (texto or "").lower())


def _paginas(material_id: int) -> list[str]:
    if material_id not in _cache_paginas:
        caminho = caminho_pdf(material_id)
        if not os.path.exists(caminho):
            return []
        leitor = PdfReader(caminho)
        _cache_paginas[material_id] = [_compacto(p.extract_text() or "") for p in leitor.pages]
    return _cache_paginas[material_id]


def localizar_pagina(material_id: int, evidencia: str, chunk: str) -> int | None:
    """Página (1-based) do PDF onde está a evidência; se não achar, a página com mais
    sobreposição com o trecho. None se o PDF original não estiver salvo."""
    try:
        paginas = _paginas(material_id)
    except Exception:
        return None
    if not paginas:
        return None
    alvo = _compacto(evidencia)
    if len(alvo) >= 12:
        for i, pagina in enumerate(paginas):
            if alvo in pagina:
                return i + 1
    palavras = re.findall(r"[0-9A-Za-zÀ-ÿ]+", (chunk or "").lower())
    blocos = {"".join(palavras[i:i + 4]) for i in range(max(0, len(palavras) - 3))}
    blocos = {b for b in blocos if len(b) >= 12}
    if not blocos:
        return None
    pontos = [sum(1 for b in blocos if b in pagina) for pagina in paginas]
    melhor = max(range(len(paginas)), key=lambda i: pontos[i])
    return melhor + 1 if pontos[melhor] > 0 else None


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


def proporcao_texto(texto: str) -> float:
    """Fração dos tokens que são palavras. Trechos dominados por fórmulas/números
    quebrados pela extração do PDF ficam abaixo de ~0.3 e geram questões ruins."""
    tokens = texto.split()
    if not tokens:
        return 0.0
    palavras = [t for t in tokens if re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{2,}[.,:;!?]?", t)]
    return len(palavras) / len(tokens)


_PADROES_REFERENCIA = [
    r"\b[A-ZÀ-Ý]{3,}(?:-[A-ZÀ-Ý]{2,})?,\s+[A-ZÀ-Ý][a-zà-ÿ]",  # SOBRENOME, Nome
    r"\bet al\.?",
    r"\bISBN\b",
    r"\b(?:Press|Pearson|Springer|Elsevier|Wiley|O'Reilly|Prentice|McGraw|AMLBook|Bookman|Editora)\b",
    r"\bslides adaptados\b",
    r"\b(?:refer[êe]ncias|bibliografia|agradecimentos)\b",
    r"\b(?:[Cc]ap\.|pp\.|v\.\s*\d|n\.\s*\d|ed\.)",
    r"\b(?:19|20)\d{2}\.",
    r"https?://|doi\.org|\bdoi:",
]


def _sinais_referencia(texto: str) -> int:
    return sum(len(re.findall(p, texto, re.I if "refer" in p or "slides" in p else 0)) for p in _PADROES_REFERENCIA)


def remover_referencias(texto: str) -> str:
    """Tira do trecho as linhas/itens que são citação bibliográfica ou créditos
    (ex.: "BERGSTRA, James; BENGIO, Yoshua. ... 2012."), mantendo o conteúdo."""
    partes = re.split(r"(\n|•)", texto)
    saida = []
    for parte in partes:
        if parte in ("\n", "•"):
            saida.append(parte)
        elif _sinais_referencia(parte) < 2 and not re.search(r"slides? adaptad|adaptad[oa]s? d[oea]s? origin|cr[ée]ditos", parte, re.I):
            saida.append(parte)
    limpo = "".join(saida)
    limpo = re.sub(r"(?:•\s*){2,}", "• ", limpo)
    return re.sub(r"\n{2,}", "\n", limpo).strip()


def parece_metadados(texto: str) -> bool:
    """Trecho que, sem as referências/créditos, não tem conteúdo suficiente."""
    return len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", remover_referencias(texto))) < 15


def bons_chunks(chunks: list[str], minimo_texto: float = 0.3) -> list[str]:
    chunks_sem_meta = [c for c in chunks if not parece_metadados(c)] or chunks
    bons = [c for c in chunks_sem_meta if _chunk_util(c)]
    textuais = [c for c in bons if proporcao_texto(c) >= minimo_texto]
    if len(textuais) >= 3:
        return textuais
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
