# Pontos de melhoria do TCC — plano de ação e ideias

Documento de trabalho baseado nas duas avaliações recebidas (notas 7,5 e 8,5) sobre a versão atual da proposta "Análise Comportamental e Avaliação Formativa: Proposta de um Ambiente Virtual de Aprendizagem Inteligente".

---

## 1. A questão central: parar de chamar a ferramenta de AVA

> "Acho ambicioso denominar a ferramenta de Ambiente Virtual de Aprendizagem (AVA). Os AVA costumam integrar uma gama bem maior de funcionalidades de apoio às atividades de ensino e de aprendizagem."

> "Uso de nomenclaturas que não agregam na compreensão do texto (como AVA-I, por exemplo)."

Os dois avaliadores convergiram no mesmo ponto, por ângulos diferentes. O primeiro diz que o termo AVA promete demais; o segundo diz que a sigla AVA-I atrapalha a leitura. A crítica é procedente e vale entender o porquê antes de decidir o que fazer.

### 1.1 Por que a crítica é procedente

Um AVA (Moodle, Canvas, Blackboard, Google Classroom) é uma plataforma institucional multiusuário que integra, no mínimo: gestão de cursos, turmas e matrículas; papéis distintos (professor, aluno, tutor, administrador); distribuição de conteúdo pelo docente; entrega e correção de atividades; livro de notas; ferramentas de comunicação (fóruns, mensagens, avisos); calendário e acompanhamento administrativo do percurso do aluno.

A ferramenta proposta não tem nada disso — e não precisa ter. Ela é centrada em um único usuário (o estudante), que traz o próprio material, estuda de forma autônoma e acompanha o próprio desempenho. Não há professor no sistema, não há turma, não há curso. Chamá-la de AVA cria uma expectativa que o texto depois não cumpre, e dá ao leitor (e à banca) munição para cobrar funcionalidades que nunca estiveram no escopo.

### 1.2 O que a ferramenta realmente é

Olhando para o que foi construído, a ferramenta se encaixa muito melhor em outras categorias já estabelecidas na literatura:

- **Ferramenta de apoio ao estudo autônomo / autorregulado** — categoria guarda-chuva que conversa diretamente com a Seção 2.1 (automonitoramento da aprendizagem). É a descrição mais honesta do artefato.
- **Sistema de tutoria inteligente (ITS) de escopo restrito** — o trabalho já cita VanLehn e os ITS no referencial; a geração de perguntas formativas com feedback imediato é exatamente o tipo de interação de granularidade fina que essa literatura descreve. Dá para se posicionar como "uma ferramenta com características de ITS, sem modelagem completa do aluno".
- **Ambiente inteligente de estudo** — variação que mantém a palavra "ambiente" sem carregar a sigla institucional AVA.

### 1.3 Opções concretas (da mais recomendada à mais conservadora)

**Opção A — Renomear e reposicionar (recomendada).** Trocar "Ambiente Virtual de Aprendizagem Inteligente (AVA-I)" por algo como "ferramenta inteligente de apoio ao estudo autônomo" ou "plataforma de estudo autônomo com avaliação formativa e monitoramento de engajamento". No título, algo como:

- "Análise comportamental e avaliação formativa: uma ferramenta inteligente de apoio ao estudo autônomo"
- "Avaliação formativa automática e monitoramento de engajamento: uma plataforma de apoio ao estudo autônomo"

Dar um nome próprio ao protótipo (um nome de produto, curto, sem sigla explicativa) resolve também a crítica do segundo avaliador: em vez de repetir "AVA-I" o texto passa a dizer "a ferramenta" ou o nome próprio. Exemplos de nomes possíveis: *Foco*, *Estuda+*, *Lumen*, *Kairos* — qualquer um serve, desde que o texto o trate como nome, não como categoria.

**Opção B — Manter "ambiente", abandonar a sigla AVA.** Usar "ambiente inteligente de estudo" em vez de "Ambiente Virtual de Aprendizagem". Mantém a sonoridade do título original, elimina a comparação com Moodle e afins. Exige um parágrafo no Capítulo 3 delimitando explicitamente: "não se trata de um AVA no sentido institucional do termo; trata-se de um ambiente de estudo individual".

**Opção C — Manter AVA com defesa explícita (não recomendada).** Argumentar que o termo é usado em sentido amplo. É a opção mais frágil: os dois avaliadores já sinalizaram desconforto, e a banca final provavelmente repetirá a cobrança.

### 1.4 Como transformar a crítica em ponto forte

Independentemente da opção, há um movimento argumentativo que vale incluir no texto:

- **Delimitação de escopo como decisão de projeto.** Um parágrafo no Capítulo 3 (ou na Introdução) dizendo explicitamente o que a ferramenta não é e por quê: o foco é o momento do estudo autônomo, justamente a lacuna que os AVAs tradicionais não cobrem. Isso inverte a crítica — em vez de "prometeu AVA e entregou menos", o trabalho passa a dizer "os AVAs cobrem a gestão do ensino, mas deixam o estudo autônomo descoberto; esta ferramenta ataca exatamente essa lacuna".
- **Integração futura como trabalho futuro.** Nas Considerações Finais, mencionar que a ferramenta poderia, em trabalhos futuros, ser integrada a AVAs existentes (por exemplo, via LTI — *Learning Tools Interoperability*, o padrão que o Moodle e o Canvas usam para acoplar ferramentas externas). Isso mostra que o autor conhece o ecossistema e situa o artefato corretamente dentro dele.
- **Atualizar o referencial.** Se houver espaço, uma ou duas referências sobre taxonomia de tecnologias educacionais (AVA/LMS vs. ITS vs. ferramentas de aprendizagem) fundamentam a escolha do novo termo e mostram domínio conceitual.

### 1.5 Checklist de renomeação (impacto no texto)

- Título, resumo, abstract e palavras-chave (retirar "ambiente virtual de aprendizagem" das palavras-chave ou trocar por "estudo autônomo").
- Lista de siglas (remover AVA-I; avaliar se AVA permanece, já que continuará citado no referencial ao falar de Moodle e afins).
- Legendas das Figuras 3.1 a 3.7 (todas citam "AVA-I").
- Capítulo 1 (parágrafo final da introdução e objetivo geral), Capítulo 3 (abertura da Seção 3.1), Capítulo 5 (Seção 5.0, "protótipo funcional do AVA-I") e Capítulo 8 (item iii das contribuições, "trabalhos futuros em AVAs inteligentes" — este pode manter AVA, pois se refere à literatura, não à ferramenta).
- Nome do repositório/projeto, se aparecer em figuras ou referências ao código.

---

## 2. Avaliação com usuários: decidir o desenho e resolver as inconsistências

Aqui as duas avaliações apontam em direções diferentes e é preciso alinhar com o orientador antes de reescrever.

**Avaliador 1 (7,5):** retirar completamente a avaliação com usuários — o ciclo CEP (planejamento, submissão, análise, recrutamento, coleta, análise de dados) não cabe em um semestre de TCC, e o método exigiria muito mais participantes para ter validade. Focar em testes funcionais e métodos de inspeção de usabilidade.

**Avaliador 2 (8,5):** mantém a discussão da avaliação, mas critica o desenho: os dois grupos/condições não estão bem justificados, a análise qualitativa está confusa e falta métrica ligada ao aprendizado.

### Caminho A — Retirar usuários (alinhado ao avaliador 1; provavelmente o mais seguro)

Substituir o Capítulo 6 por um plano de avaliação sem seres humanos, que continua respondendo perguntas de pesquisa legítimas:

- **Avaliação da qualidade das questões geradas (RAG).** Selecionar dois ou três materiais de referência de domínio conhecido (capítulos de livros abertos, como já previsto na Fase 2), gerar um lote de questões e avaliá-las com critérios objetivos: ancoragem no trecho recuperado (a resposta está de fato no material?), correção factual, plausibilidade dos distratores, clareza do enunciado. A avaliação pode ser feita pelo autor e pelo orientador com um protocolo definido a priori — e isso resolve de tabela a crítica da "revisão de cada pergunta" (ver Seção 3 abaixo).
- **Testes funcionais e de desempenho técnico.** Métricas que a própria arquitetura já sugere: latência de geração das questões, taxa de sucesso da inicialização do YOLO em diferentes máquinas, FPS do Face Mesh, frequência de ativação do modo degradado, consumo de memória no navegador. Isso transforma a seção 4.1.1 (limitação de hardware) em resultado mensurável, não só em ressalva.
- **Avaliação de usabilidade por inspeção.** Avaliação heurística (Nielsen) com três a cinco avaliadores especialistas (colegas de curso ou o próprio orientador servem como inspetores — inspeção não é pesquisa com seres humanos no sentido do CEP) e/ou percurso cognitivo (*cognitive walkthrough*) das três tarefas principais: enviar material, fazer uma sessão de estudo, ler o painel.
- **Validação do focusScore em cenário controlado.** O próprio autor pode gravar sessões suas simulando estados conhecidos (olhando para a tela, olhando para o lado, com celular no quadro) e verificar se o indicador responde como esperado. É teste funcional, não experimento com participantes.

As questões de pesquisa precisariam ser reformuladas para caber nesse desenho, por exemplo: QP1 — as questões geradas por RAG a partir de materiais reais são ancoradas e corretas em que proporção? QP2 — o processamento de visão computacional no navegador é viável em hardware heterogêneo, e com que frequência o modo degradado é acionado? QP3 — a interface atende às heurísticas de usabilidade estabelecidas?

Ganhos colaterais: o cronograma libera os meses 4 e 5 (hoje ocupados por CEP e coleta), a Fase 4 da metodologia é substituída por avaliação técnica, e as seções 6.1 (CEP/TCLE), 6.2 (desenho experimental), 6.3 (participantes) e 6.5/6.6 (análises) encolhem ou desaparecem.

### Caminho B — Manter usuários (se o orientador insistir), corrigindo o desenho

Se a decisão for manter, os ajustes mínimos exigidos pelo avaliador 2 são:

- **Justificar ou eliminar a condição de controle.** A condição A (leitura sem perguntas formativas) só faz sentido se a QP1 comparasse aprendizagem entre condições — mas a QP1 atual correlaciona engajamento e acerto dentro da condição B, o que não exige controle. Ou se reformula a QP para justificar as duas condições (por exemplo, comparar retenção com e sem perguntas, medida por pós-teste), ou se elimina a condição A e simplifica o estudo.
- **Explicar a análise qualitativa em termos operacionais.** "Codificação por dois autores e consenso por triangulação" é problemática em dobro: um TCC tem um autor só, e a frase não explica o procedimento. Reescrever descrevendo o processo real: quem codifica (autor e orientador, por exemplo), como as categorias emergem, o que acontece em caso de divergência.
- **Incluir perguntas de benefício percebido na entrevista.** Sugestão direta do avaliador 2: itens como "Você acredita que a ferramenta contribuiu para o seu aprendizado?", "As perguntas ajudaram você a perceber o que não tinha entendido?", "Você usaria a ferramenta para estudar para uma prova?". Cria ao menos uma métrica ligada ao objetivo final (aprendizagem), ainda que autorrelatada.

Mesmo no Caminho B, vale registrar no texto o risco de cronograma (CEP pode não aprovar a tempo) e definir um plano de contingência explícito — que, na prática, é o Caminho A.

---

## 3. A "revisão de cada pergunta": remover ou reformular

> "Se o usuário irá subir os pdfs que serão analisados, não faz sentido que cada pergunta seja revisada."

A crítica pega uma contradição real do texto (Seção 6.4: "cada pergunta é revisada pelos autores e pelo orientador antes da sessão"). Em produção, ninguém revisa as perguntas do material que o próprio estudante subiu — nem teria competência para isso em qualquer domínio.

Como resolver:

- **Separar os dois cenários no texto.** No uso real da ferramenta, as questões são geradas automaticamente e o controle de qualidade é arquitetural (ancoragem via RAG, que já está bem explicada na Seção 2.2) mais o recurso de o próprio estudante editar/descartar questões (que o Módulo 1 já prevê — vale dar destaque a isso como mecanismo de qualidade). Na avaliação/validação do TCC, usa-se um corpus fixo e conhecido pelos avaliadores, e aí sim cabe inspeção humana das questões — porque o objetivo é medir a qualidade do gerador, não curar conteúdo para o usuário.
- **Transformar a limitação em resultado.** Reportar a taxa de questões aprovadas/reprovadas na inspeção do corpus conhecido é um resultado quantitativo interessante por si só (por exemplo: "de N questões geradas, X% estavam corretamente ancoradas").
- **Mencionar mecanismos automáticos como trabalho futuro.** Verificação automática de ancoragem (conferir se a resposta consta no chunk recuperado), filtros de autoconsistência, ou um segundo modelo como juiz — não precisa implementar, mas citar mostra consciência do problema.

---

## 4. Fundamentação teórica: fluidez e limpeza

- **Fluidez entre parágrafos.** Revisar cada seção do Capítulo 2 garantindo transições explícitas: fechar cada parágrafo apontando para o próximo assunto ou abrir o seguinte retomando o anterior. Teste prático: ler só a primeira e a última frase de cada parágrafo em sequência — se a história não se sustenta, falta transição.
- **Retirar as menções ao TCC/proposta de dentro do referencial.** Frases como "essa constatação motiva, na proposta, intercalar a leitura com perguntas formativas" (fim da 2.1) e "a proposta trata explicitamente essa restrição na Seção 4.1.1" (fim da 2.3) devem sair — a conexão com a proposta é feita no Capítulo 3, que existe para isso. O Capítulo 2 deve se sustentar como revisão de literatura pura.
- **Conferir também a Seção 2.4**, que fecha descrevendo a decisão de arquitetura da proposta ("a proposta executa toda a visão computacional no navegador") — mesma correção.

## 5. Questões de pesquisa desconectadas

A Seção 3.2 aparece solta no fim do Capítulo 3, depois das figuras, sem ligação com a visão geral. Alternativas:

- **Movê-la** para o início do capítulo de avaliação (as QPs orientam a avaliação, então podem abrir o Capítulo 6) ou para logo após os objetivos no Capítulo 1, criando a cadeia clássica problema → objetivos → questões de pesquisa.
- **Se ficar no Capítulo 3, costurar**: encerrar a Seção 3.1 anunciando que os módulos levantam duas questões verificáveis, e abrir a 3.2 amarrando cada QP ao módulo correspondente (QP1 nasce do cruzamento Módulo 2 × Módulo 3; QP2 nasce da decisão arquitetural de rodar VC no navegador).
- Lembrando: se o Caminho A da Seção 2 for adotado, as QPs mudam de conteúdo — resolver as duas coisas juntas.

## 6. Cronograma realista

- Reduzir de seis para quatro meses e meio (agosto a mieados de dezembro, na prática). Refazer a Tabela 7.1 com colunas quinzenais ou mensais reais (Ago, Set, Out, Nov, Dez/1ªq) em vez de M1–M6 genéricos.
- Se o Caminho A for adotado, remover as linhas de CEP e coleta com participantes e substituí-las por: avaliação da qualidade das questões, testes funcionais/desempenho e inspeção de usabilidade.
- Manter a redação do TCC II como faixa contínua e reservar as duas últimas semanas exclusivamente para revisão e entrega — a versão atual já faz isso, preservar.
- Dica de defesa: incluir uma frase no texto reconhecendo a restrição de calendário e mostrando que o plano foi dimensionado para ela. Antecipa a crítica em vez de recebê-la.

## 7. Forma e redação

- **Figuras ilegíveis no impresso.** As capturas de tela inteira em fundo escuro não funcionam em papel. Soluções combináveis: recortar apenas a região relevante de cada tela (não a janela inteira do navegador); usar o tema claro da aplicação para as capturas, se existir (ou criar um tema claro simples só para documentação); aumentar o zoom da interface antes de capturar; exportar em resolução alta (2x) e ocupar a largura total da página; testar imprimindo em preto e branco antes de fechar o documento.
- **Itálico em palavras estrangeiras.** Fazer varredura completa: frontend, backend, pipeline, chunks, embeddings, smartphone, feedback, slides, notebook, ranking, bootstrap, focusScore, privacy by design, cyber-slacking, dashboard, single page application etc. Atenção especial a legendas de figuras e tabelas, onde é mais fácil escapar. No LaTeX, vale criar um comando (por exemplo, um \estrangeiro{}) para padronizar e facilitar revisão futura.
- **Siglas.** Revisar a lista de siglas após a renomeação (Seção 1.5). Verificar também siglas definidas mas pouco usadas (POC aparece como "PoC" no texto — padronizar).
- **Erro pontual identificado:** na Seção 6.4, "pela (System Usability Scale)" tem parênteses duplicados com o itálico.

## 8. Ordem sugerida de ataque

1. Decidir com o orientador: Caminho A ou B da avaliação (Seção 2) — essa decisão condiciona QPs, metodologia, Capítulo 6 e cronograma.
2. Decidir a renomeação (Seção 1) — mexe em título, resumo e texto inteiro, então quanto antes, melhor.
3. Reescrever Capítulo 6 + Seção 3.2 + cronograma de forma coerente com as decisões acima.
4. Passar a limpo o Capítulo 2 (fluidez + remoção das menções à proposta).
5. Refazer as figuras.
6. Varredura final de forma: itálicos, siglas, parênteses, padronização.

---

*Resumo executivo: as duas bancas concordam que o trabalho evoluiu muito e que o protótipo funcional é um diferencial. Os dois riscos reais para a nota final são a promessa excessiva do termo AVA e um plano de avaliação que não cabe no calendário. Resolver esses dois pontos — reposicionando a ferramenta como apoio ao estudo autônomo e trocando o experimento com usuários por avaliação técnica e por inspeção — deixa o TCC II com escopo defensável e executável.*
