import json
import random
import re
from . import config

PROMPT = """Você é um gerador de avaliações formativas para um Ambiente Virtual de Aprendizagem.
A partir do trecho de material didático abaixo, gere exatamente 1 questão de múltipla escolha em português, com 4 alternativas, ancorada exclusivamente no trecho.

TRECHO-FONTE:
{trecho}
{contexto}
Responda SOMENTE com um JSON válido no formato:
{{"pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "..."}}"""

PROMPT_TOPICO = """Você é um professor que prepara material de estudo para um Ambiente Virtual de Aprendizagem.
Recebe o título de um tópico e o conteúdo bruto extraído de um material didático (em formato de tópicos/slides).

Sua tarefa:
1. Escreva uma EXPLICAÇÃO didática e coerente do tópico, em português, em prosa corrida (2 a 4 parágrafos curtos), conectando as ideias de forma fluida. Não copie a lista de tópicos: explique como um professor explicaria, baseando-se apenas no conteúdo fornecido.
2. Em seguida, crie 1 questão de múltipla escolha (4 alternativas, exatamente 1 correta) que avalie a compreensão da explicação. As 4 alternativas devem ser plausíveis e sobre o tema.

TÍTULO DO TÓPICO:
{titulo}

CONTEÚDO BRUTO:
{conteudo}

Responda SOMENTE com um JSON válido no formato:
{{"explicacao": "...", "pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "..."}}"""

PROMPT_EXTRAIR = """Você é um professor analisando o conteúdo de um material didático extraído de um PDF.
Identifique os principais tópicos REALMENTE abordados no material e, para cada um, escreva uma explicação didática clara em português, em prosa corrida (2 a 4 parágrafos), baseada SOMENTE no conteúdo fornecido.

Regras:
- Não invente tópicos que não estão no material.
- Use entre 3 e 8 tópicos, conforme a extensão e a variedade do conteúdo. Materiais curtos podem ter menos.
- O título de cada tópico deve refletir o assunto tratado.
- A explicação deve ensinar o conteúdo, não apenas listar palavras.

CONTEÚDO DO MATERIAL:
{conteudo}

Responda SOMENTE com um JSON válido no formato:
{{"topicos": [{{"titulo": "...", "explicacao": "..."}}]}}"""

PROMPT_PERGUNTA = """Com base na explicação a seguir sobre o tópico "{titulo}", crie 1 questão de múltipla escolha em português que avalie a compreensão do conteúdo.
A questão deve ter enunciado claro e contextualizado, 4 alternativas plausíveis e exatamente 1 correta.

EXPLICAÇÃO:
{explicacao}

Responda SOMENTE com um JSON válido no formato:
{{"pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "..."}}"""


_STOP = set(
    "a o e de da do das dos para por com sem que se na no nas nos um uma uns umas "
    "em ao aos as os ou como mais menos entre sobre sob ate apos antes cada qual quais "
    "este esta estes estas esse essa essas esses isso aquilo seu sua seus suas pela pelo "
    "the and of to in is are be by an as at it this that".split()
)


def _termos_salientes(texto: str) -> list[str]:
    palavras = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9/-]{3,}", texto)
    surface: dict[str, str] = {}
    freq: dict[str, int] = {}
    for p in palavras:
        chave = p.lower()
        if chave in _STOP:
            continue
        freq[chave] = freq.get(chave, 0) + 1
        surface.setdefault(chave, p)
    ordenados = sorted(freq, key=lambda c: (freq[c], surface[c][0].isupper(), len(c)), reverse=True)
    return [surface[c] for c in ordenados]


def _janela(texto: str, termo: str) -> str:
    for frase in re.split(r"(?<=[.!?])\s+", texto):
        if re.search(r"\b" + re.escape(termo) + r"\b", frase) and len(frase.strip()) > 25:
            return frase.strip()
    pos = texto.lower().find(termo.lower())
    ini = max(0, pos - 70)
    fim = min(len(texto), pos + len(termo) + 70)
    return ("…" if ini > 0 else "") + texto[ini:fim].strip() + ("…" if fim < len(texto) else "")


def _gerar_mock(trecho: str) -> dict:
    texto = re.sub(r"\s+", " ", trecho).strip()
    termos = _termos_salientes(texto)
    distintos: list[str] = []
    for t in termos:
        if t.lower() not in {d.lower() for d in distintos}:
            distintos.append(t)
    if distintos:
        correta = random.choice(distintos[:6])
        usados = {correta.lower()}
        candidatos = [d for d in distintos if d.lower() != correta.lower()]
        candidatos += re.findall(r"[A-Za-zÀ-ÿ]{3,}", texto)
        distratores: list[str] = []
        for cand in candidatos:
            chave = cand.lower()
            if chave in usados or chave in _STOP:
                continue
            distratores.append(cand)
            usados.add(chave)
            if len(distratores) == 3:
                break
        if len(distratores) == 3:
            janela = re.sub(r"\b" + re.escape(correta) + r"\b", "_____", _janela(texto, correta), count=1)
            return {
                "pergunta": f"Leia a passagem e escolha o termo que completa corretamente a lacuna:\n\n«{janela}»",
                "opcoes": [correta, *distratores],
                "correta": 0,
                "justificativa": f"Na passagem-fonte, o termo que preenche a lacuna é «{correta}».",
            }
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", texto) if len(f.strip()) > 40]
    base = (frases[0] if frases else texto[:160])[:150]
    return {
        "pergunta": "Assinale a alternativa que reproduz uma informação presente na passagem-fonte.",
        "opcoes": [
            base,
            "A passagem não apresenta nenhuma informação sobre o tema da disciplina.",
            "A passagem trata de um assunto sem relação com o conteúdo estudado.",
            "A passagem apresenta o tema apenas como exemplo a ser evitado.",
        ],
        "correta": 0,
        "justificativa": "A alternativa correta reproduz o conteúdo da passagem-fonte (modo de demonstração sem LLM).",
    }


def _gerar_anthropic(trecho: str, contexto: str) -> dict:
    import anthropic

    cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    ctx = f"\nCONTEXTO ADICIONAL (cenário expandido):\n{contexto}\n" if contexto else "\n"
    msg = cliente.messages.create(
        model=config.LLM_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": PROMPT.format(trecho=trecho, contexto=ctx)}],
    )
    texto = msg.content[0].text
    bruto = re.search(r"\{.*\}", texto, re.S)
    return json.loads(bruto.group(0)) if bruto else _gerar_mock(trecho)


def _embaralhar(questao: dict) -> dict:
    opcoes = list(questao.get("opcoes", []))
    correta = int(questao.get("correta", 0))
    if not 0 <= correta < len(opcoes):
        return questao
    texto_correto = opcoes[correta]
    random.shuffle(opcoes)
    questao["opcoes"] = opcoes
    questao["correta"] = opcoes.index(texto_correto)
    return questao


def gerar_questao(trecho: str, contexto: str = "") -> dict:
    if config.LLM_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        try:
            return _embaralhar(_gerar_anthropic(trecho, contexto))
        except Exception:
            return _embaralhar(_gerar_mock(trecho))
    return _embaralhar(_gerar_mock(trecho))


def _topico_anthropic(titulo: str, conteudo: str) -> dict:
    import anthropic

    cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = cliente.messages.create(
        model=config.LLM_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": PROMPT_TOPICO.format(titulo=titulo or "(sem título)", conteudo=conteudo)}],
    )
    texto = msg.content[0].text
    bruto = re.search(r"\{.*\}", texto, re.S)
    dados = json.loads(bruto.group(0)) if bruto else {}
    if not dados.get("opcoes") or not dados.get("explicacao"):
        raise ValueError("resposta do modelo incompleta")
    return dados


def gerar_topico(titulo: str, conteudo: str) -> dict:
    if config.LLM_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        try:
            return _embaralhar(_topico_anthropic(titulo, conteudo))
        except Exception:
            pass
    questao = _embaralhar(_gerar_mock(conteudo))
    explicacao = f"{titulo}\n\n{conteudo}" if titulo else conteudo
    return {
        "explicacao": explicacao,
        "pergunta": questao["pergunta"],
        "opcoes": questao["opcoes"],
        "correta": questao["correta"],
        "justificativa": questao["justificativa"],
    }


def disponivel() -> bool:
    if config.LLM_PROVIDER == "anthropic":
        return bool(config.ANTHROPIC_API_KEY)
    if config.LLM_PROVIDER == "gemini":
        return bool(config.GEMINI_API_KEY)
    return False


def _gemini(prompt: str, max_tokens: int, json_mode: bool = True) -> str:
    import urllib.request
    import urllib.error

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    gen = {
        "temperature": 0.8,
        "maxOutputTokens": max(max_tokens, 2048),
        "thinkingConfig": {"thinkingBudget": 0},
    }
    if json_mode:
        gen["responseMimeType"] = "application/json"
    corpo = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=corpo,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": config.GEMINI_API_KEY,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", "ignore")
        if e.code == 429:
            raise RuntimeError("limite de uso da camada gratuita do Gemini atingido (429). Aguarde um minuto e tente de novo.") from None
        raise RuntimeError(f"HTTP {e.code}: {detalhe[:200]}") from None
    candidato = (dados.get("candidates") or [{}])[0]
    partes = candidato.get("content", {}).get("parts", [])
    texto = "".join(p.get("text", "") for p in partes)
    if not texto:
        raise ValueError(f"resposta vazia (finishReason={candidato.get('finishReason')})")
    return texto


def _completar(prompt: str, max_tokens: int = 900, json_mode: bool = True) -> str:
    if config.LLM_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        import anthropic

        cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = cliente.messages.create(
            model=config.LLM_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    if config.LLM_PROVIDER == "gemini" and config.GEMINI_API_KEY:
        return _gemini(prompt, max_tokens, json_mode)
    raise RuntimeError("Nenhum LLM configurado")


PROMPT_ESTUDO = """Você é um professor preparando material de estudo para um aluno, com base no conteúdo de PDFs da disciplina.

Perfil do aluno:
- Nível de conhecimento na matéria: {nivel}
- Objetivo do estudo: {objetivo}
- Tempo disponível: {tempo}

Adapte o material ao perfil: ajuste a linguagem ao nível, o foco ao objetivo e o tamanho ao tempo disponível.

Produza um material de estudo em português assim:
1. Uma explicação clara e didática do conteúdo, em prosa, organizada em seções com títulos curtos.
2. No final, uma seção "Pontos-chave" com os principais itens, um por linha.

Use TEXTO SIMPLES (sem markdown, sem asteriscos, sem #): cada título numa linha própria, e cada item de lista começando com "• ". Baseie-se SOMENTE no conteúdo abaixo.

CONTEÚDO:
{conteudo}"""


def gerar_material_estudo(conteudo: str, nivel: str, objetivo: str, tempo: str) -> str:
    prompt = PROMPT_ESTUDO.format(nivel=nivel, objetivo=objetivo, tempo=tempo, conteudo=conteudo[:24000])
    return _completar(prompt, 4096, json_mode=False)


PROMPT_PERGUNTA_CONTEUDO = """Você é um professor criando uma questão de estudo a partir de um material didático.
Com base APENAS no trecho abaixo, crie 1 questão de múltipla escolha em português que avalie a compreensão do conteúdo.

Requisitos:
- Enunciado claro, contextualizado e respondível somente com o conteúdo do trecho.
- Exatamente 4 alternativas plausíveis, sendo apenas 1 correta.
- Evite alternativas obviamente erradas ou sem sentido.

TRECHO:
{conteudo}

Responda SOMENTE com um JSON válido no formato:
{{"pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "..."}}"""


def pergunta_llm(conteudo: str) -> dict:
    texto = _completar(PROMPT_PERGUNTA_CONTEUDO.format(conteudo=conteudo[:6000]), 900)
    bruto = re.search(r"\{.*\}", texto, re.S)
    dados = json.loads(bruto.group(0)) if bruto else {}
    if not dados.get("opcoes") or len(dados["opcoes"]) < 2:
        raise ValueError("resposta do modelo inválida")
    return _embaralhar(dados)


def gerar_pergunta_conteudo(conteudo: str) -> dict:
    return pergunta_llm(conteudo)


PROMPT_LOTE = """Você é um professor criando questões de estudo a partir de um material didático.
Para CADA trecho numerado abaixo, crie 1 questão de múltipla escolha em português (4 alternativas plausíveis, exatamente 1 correta), respondível apenas com o conteúdo daquele trecho.

TRECHOS:
{trechos}

Responda SOMENTE com um JSON válido no formato, com exatamente {n} itens na ordem dos trechos:
{{"questoes": [{{"pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "..."}}]}}"""


def perguntas_lote(conteudos: list[str]) -> list[dict]:
    if not conteudos:
        return []
    trechos = "\n\n".join(f"[{i + 1}] {c[:1500]}" for i, c in enumerate(conteudos))
    texto = _completar(PROMPT_LOTE.format(trechos=trechos, n=len(conteudos)), 4096)
    bruto = re.search(r"\{.*\}", texto, re.S)
    dados = json.loads(bruto.group(0)) if bruto else {}
    saida = []
    for q in dados.get("questoes", []):
        if q.get("opcoes") and len(q["opcoes"]) >= 2:
            saida.append(_embaralhar(q))
    if not saida:
        raise ValueError("o modelo não retornou questões válidas")
    return saida


def extrair_topicos(texto: str) -> list[tuple[str, str]]:
    if not disponivel():
        return []
    import anthropic

    cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = cliente.messages.create(
        model=config.LLM_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": PROMPT_EXTRAIR.format(conteudo=texto[:16000])}],
    )
    bruto = re.search(r"\{.*\}", msg.content[0].text, re.S)
    dados = json.loads(bruto.group(0)) if bruto else {}
    saida = [
        (t.get("titulo", "").strip(), t.get("explicacao", "").strip())
        for t in dados.get("topicos", [])
        if t.get("explicacao", "").strip()
    ]
    if not saida:
        raise ValueError("o modelo não retornou tópicos válidos")
    return saida


def gerar_pergunta(titulo: str, explicacao: str) -> dict:
    if disponivel():
        try:
            import anthropic

            cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            msg = cliente.messages.create(
                model=config.LLM_MODEL,
                max_tokens=900,
                messages=[{"role": "user", "content": PROMPT_PERGUNTA.format(titulo=titulo or "(tópico)", explicacao=explicacao)}],
            )
            bruto = re.search(r"\{.*\}", msg.content[0].text, re.S)
            dados = json.loads(bruto.group(0)) if bruto else {}
            if dados.get("opcoes"):
                return _embaralhar(dados)
        except Exception:
            pass
    return _embaralhar(_gerar_mock(explicacao))
