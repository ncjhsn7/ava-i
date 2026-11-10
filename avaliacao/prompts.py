"""Prompts da coleta. Vão para o Apêndice de prompts do TCC.

A condição COM trecho usa exatamente o prompt da ferramenta (backend/app/llm.py),
importado em comum.py. Aqui ficam os prompts exclusivos do experimento.
"""

PROMPT_TEMA = """Leia o trecho de material didático abaixo e dê a ele um título de no máximo cinco palavras, em português, que diga o assunto tratado. Não use aspas.

TRECHO:
{trecho}

Responda SOMENTE com um JSON válido: {{"tema": "..."}}"""

DIRETRIZES_SEM_TRECHO = """Regras para a questão:
- Avalie a COMPREENSÃO de um conceito, definição, relação, propriedade ou procedimento do tema. Prefira questões de aplicar, interpretar, comparar ou calcular a questões de memorização literal.
- O enunciado deve ser autossuficiente e não deve mencionar "material", "texto", "slides" ou "PDF".
- PROIBIDO perguntar sobre autor, professor, instituição, disciplina, datas, título do documento ou bibliografia.
- 4 alternativas da mesma natureza, com tamanho e nível de detalhe parecidos: a correta NÃO pode ser a mais longa nem a mais detalhada. Exatamente 1 correta. Distratores refletem erros conceituais plausíveis de um estudante. Não use "todas/nenhuma das anteriores".
- "justificativa": 1 a 2 frases explicando POR QUE a alternativa correta está certa.
- "explicacoes": lista com 4 frases curtas, na MESMA ordem de "opcoes", dizendo por que cada alternativa está certa ou errada.
- "evidencia": deixe vazio ("")."""

PROMPT_SEM_TRECHO = """Você é um professor criando uma questão de estudo para uma disciplina de graduação em Ciência da Computação.
Crie 1 questão de múltipla escolha em português sobre o tema abaixo, usando o seu conhecimento sobre o assunto.

{diretrizes}

MATERIAL: {titulo}
TEMA: {tema}

Responda SOMENTE com um JSON válido:
{{"pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "...", "explicacoes": ["...", "...", "...", "..."], "evidencia": ""}}"""

PROMPT_JUIZ = """Você é um avaliador especialista em elaboração de itens de múltipla escolha para o ensino superior. Avalie a questão abaixo usando SOMENTE os critérios a seguir. O trecho do material é a referência para decidir o que o material sustenta.

CRITÉRIOS
- c1 (ancoragem): a alternativa indicada como correta é sustentada pelo TRECHO DO MATERIAL? Responda "sim" se o trecho a sustenta, "parcialmente" se o trecho sustenta só parte dela ou exige conhecimento externo relevante, e "nao" se o trecho não a sustenta ou a contradiz.
- c2 (correção): a alternativa indicada como correta está de fato correta E é a única correta? ("sim" ou "nao")
- c3 (distratores): quantas das três alternativas incorretas são plausíveis para um estudante que não domina o conteúdo? (inteiro de 0 a 3; um distrator absurdo, óbvio ou de outro assunto não é plausível)
- c4 (clareza): o enunciado é inequívoco e gramaticalmente correto? ("sim" ou "nao")
- c5 (nível cognitivo, taxonomia revisada de Bloom): "lembrar" (reconhecer ou recordar um fato), "compreender" (explicar, interpretar, classificar, comparar) ou "aplicar_ou_superior" (usar um procedimento, calcular, analisar, avaliar).

TRECHO DO MATERIAL:
{trecho}

QUESTÃO:
{enunciado}

{alternativas}

ALTERNATIVA INDICADA COMO CORRETA: {gabarito}

Responda SOMENTE com um JSON válido, sem texto fora dele:
{{"c1": "sim|parcialmente|nao", "c2": "sim|nao", "c3": 0, "c4": "sim|nao", "c5": "lembrar|compreender|aplicar_ou_superior", "justificativa": "até 2 frases"}}"""

SISTEMA = "Você responde somente com um objeto JSON válido, sem texto antes ou depois e sem blocos de código."
