# Arquitetura — T22 distribuidor de plantões

Padrões: **Hexagonal (Ports & Adapters)** · **KISS + YAGNI** · **single-threaded**
· **Domain Model** (Fowler) · **Repository** (Fowler) · nenhum GoF nomeado.
Stack: Python 3.12 · OR-Tools CP-SAT 9.15 · JSON em disco · `argparse`.

## V(1) — Decomposição

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | dominio | entidades e objetos de valor do domínio; sem I/O, sem solver | `Pessoa, Contrato, TipoDeTurno, Plantao, Preferencia, RegraInterna, Alocacao, Escala, Troca, Violacao, Fronteira` | — |
| M-02 | catalogo-restricoes | declara cada restrição UMA vez (H1-H4, L1-L8, S1-S7, internas) com dois modos de uso | `aplicar(modelo, vars, ctx) -> None` · `verificar(escala, ctx) -> [Violacao]` · `catalogo(instancia) -> [Restricao]` | dominio |
| M-03 | avaliador | custo e violações de uma escala concreta | `avaliar(escala, ctx) -> Avaliacao{violacoes, custo, custo_por_restricao}` | dominio, catalogo-restricoes |
| M-04 | troca | máquina de estados da troca e regra de revalidação no aceite | `solicitar(escala, sol, dest, p1, p2) -> Troca` · `responder(troca, aceite, escala) -> ResultadoTroca` | dominio, avaliador |
| M-05 | fronteira | deriva contadores de fronteira da escala do mês anterior | `derivar(escala_anterior, pessoas) -> {pessoa_id: Fronteira}` | dominio |
| M-06 | solver-cpsat | adaptador do solver: monta o modelo CP-SAT a partir do catálogo, resolve, devolve Escala | `gerar(instancia, fronteira, limite_s) -> ResultadoGeracao{escala, status, otimalidade_provada}` | dominio, catalogo-restricoes, fronteira |
| M-07 | diagnostico | detecção estrutural de inviabilidade antes do solve, com conflito localizado | `analisar(instancia) -> [Conflito{plantao, exigidos, elegiveis}]` | dominio |
| M-08 | repositorio-json | adaptador de persistência em arquivos JSON | `salvar_escala/carregar_escala(id)` · `listar_trocas/salvar_troca` | dominio |
| M-09 | carregador | parse e validação da instância de entrada; aplica L4 (art. 59) como validação de configuração | `carregar(caminho) -> Instancia` (levanta `ErroDeValidacao`) | dominio |
| M-10 | gerador-sintetico | gera instâncias de teste reprodutíveis, incluindo instâncias inviáveis deliberadas | `gerar(n_pessoas, n_dias, semente, inviavel=False) -> Instancia` | dominio |
| M-11 | cli | adaptador de entrada: os 5 casos de uso como comandos | `gerar · consultar · trocar · responder · conformidade` | todos |

**Fronteira arquitetural:** M-01…M-05 são núcleo puro — não importam `ortools`
nem tocam disco. M-06, M-08, M-09, M-11 são adaptadores. M-07 e M-10 são
serviços de domínio sem dependência externa.

**Invariante que sustenta a decomposição:** `catalogo-restricoes` é o **único
dono das regras**. `solver-cpsat` (modo *aplicar*) e `avaliador` (modo
*verificar*) são clientes iguais dele. Se uma regra passar a existir em dois
lugares, esta arquitetura falhou no ponto em que foi desenhada para não falhar.

## Mapa caso de uso → módulos

| UC | Fluxo |
|---|---|
| UC-1 gerar | cli → carregador → repositorio-json (mês anterior) → fronteira → diagnostico → solver-cpsat → repositorio-json (rascunho) |
| UC-2 consultar | cli → repositorio-json |
| UC-3 solicitar troca | cli → repositorio-json → troca (cria PENDENTE) |
| UC-4 responder troca | cli → repositorio-json → troca → avaliador → repositorio-json |
| UC-5 conformidade | cli → repositorio-json → avaliador |

## Premissas (AP4 — o que o sistema assume verdadeiro sem declarar em código)

| id | Premissa | Consequência se falsa |
|---|---|---|
| A1 | Tipos de turno têm horários fixos | a compilação de L1 em sucessões proibidas (`specs/technical/modelo-cpsat.md` §4) deixa de valer |
| A2 | Uma pessoa tem exatamente um contrato no horizonte | a natureza das restrições legais, que depende do regime, fica indefinida para ela |
| A3 | A escala do mês anterior, se existe, está publicada e cobre o mês inteiro | contadores S6/S7 sub-representados na virada (PR-4, aberta) |
| A4 | CP-SAT resolve 30×3×30 em ≤ 60 s | SC-2 falha (PR-2, aberta) |
| A5 | A identidade informada no comando é verdadeira | sem autenticação, qualquer um aceita troca em nome de qualquer um |
| A6 | O arquivo de instância não é hostil | entrada maliciosa não é modelada |
| A7 | Um operador por vez | sem trava de arquivo, execuções simultâneas se sobrescrevem |
| A8 | Os pesos do INRC-II são adequados ao contexto brasileiro | a escala é "ótima" segundo prioridades calibradas em outro país |

## Escopo negativo de V(1) (o que o sistema deliberadamente NÃO faz)

autenticação e permissões · UI gráfica, web ou API HTTP · notificações (e-mail,
push) · cálculo de remuneração ou folha · papel de gestor e homologação em duplo
estágio · calendário de feriados dedicado · otimização entre múltiplas unidades ·
linguagem genérica de regras (regras internas são parametrizadas, não
programáveis) · trava de arquivo contra execução concorrente · horizonte
diferente do mensal · equidade como critério de aceite (permanece termo flexível
com peso publicado).

---

# V(2) — Simplificação (Fase 3, iteração 1)

Resposta unificada aos 50 achados de `specs/design/coverage-matrix.md`.
V(1) permanece acima, intacta: um achado da iteração 1 nomeia módulos que V(2)
removeu, e a rastreabilidade depende de os dois textos coexistirem.

## Decisões estruturantes

**D1 — Escala publicada é IMUTÁVEL; trocas viram eventos num diário append-only.**
A escala vigente passa a ser `escala publicada + eventos aplicados`. Um único
mecanismo resolve sete achados de cinco lentes diferentes: GOV-01 (trilha de
auditoria existe por construção), GOV-02 (cada evento grava quem executou),
GOV-03 (a sequência de eventos é a versão), PRO-01 (troca órfã é detectável
porque a escala-base é identificável e imutável), PRO-02 (a expiração vira
evento datado em vez de derivação no momento da consulta), RES-02 (append-only
+ escrita atômica por arquivo temporário e renomeação), SEC-01 (a ação passa a
ser atribuível à identidade declarada).

**D2 — `catalogo-restricoes` dividido por ORIGEM.** O epicentro da crítica
(10 achados, 9 lentes, 4 críticos) some como módulo único. Vira
`restricoes-legais` (L1-L4 + regime de contrato) e `restricoes-modelo`
(H1-H4, S1-S7 e as regras internas, que têm a mesma forma paramétrica).
Resolve IMP-01 (cada um cabe numa interação), REG-01 (L3 passa a ser restrição
VERIFICÁVEL — 12h seguidas de ≥36h ininterruptas — e não apenas um modificador
da natureza das outras) e CIE-01 (o carregador recusa peso de regra interna
acima do maior peso publicado do INRC-II, 30, impedindo que uma regra sem fonte
domine as calibradas).

**D3 — `Contexto` obrigatório e invariante de consistência declarada.**
`Contexto` só é construído por uma fábrica única que sempre inclui a fronteira;
não há caminho para verificar sem ele (ASS-01). E a propriedade que faltava vira
contrato explícito, verificada por teste de propriedade na Fase 6:

> **INV-1:** toda escala produzida por `solver-cpsat` com um conjunto de
> restrições aplicado DEVE ser verificada por `avaliador` com zero violações
> rígidas desse mesmo conjunto.

INV-1 é o que impede `aplicar` e `verificar` de divergirem em silêncio
(ARQ-02, LIN-01) e, de quebra, valida empiricamente a derivação de fronteira que
não tem fonte bibliográfica (CIE-03).

**D4 — `fronteira` absorvida por `avaliador`.** Derivar contadores é percorrer a
escala por pessoa: a mesma computação da verificação (ARQ-03). Ao derivar, o
avaliador **verifica a escala anterior** e recusa-se a propagar estado de uma
escala com violações rígidas, quebrando a propagação cega de erro entre meses
(CTL-01); lê tantos meses quanto o horizonte contratual exigir, não apenas um
(CTL-02); e distingue "não existe mês anterior" de "não encontrei o arquivo"
(ASS-02).

**D5 — Contratos desambiguados.** `Preferencia` passa a ter UMA forma
(`data` + `tipo_de_turno_id` opcional; sem `plantao_id`) — LIN-02. `TipoDeTurno`
ganha `vira_o_dia` explícito em vez de deduzir de `fim < inicio` — LIN-03.
`estado` vira `estado_escala` e `estado_troca` — LIN-04.

**D6 — Simplificações por REMOÇÃO (AP2: a iteração simplifica, não complexifica).**
- `diagnostico`: a abordagem (2), relaxação por camadas, é **removida**. Fica só
  a verificação estrutural pré-solve, que é barata, determinística e cobre o caso
  real (IMP-03).
- L6/L7 (adicional noturno, hora ficta) são **removidas do catálogo**: sem
  cálculo de remuneração no escopo, eram requisito normativo sem módulo dono
  (REG-02). Permanecem em `specs/references/clt-jornada.md` como classificação.
- `fronteira` deixa de ser módulo (D4).

## Decisões arbitradas pelo operador (trade-offs de escopo)

| Achado | Decisão do operador |
|---|---|
| SEC-01 🔴 | Autenticação segue **fora de escopo**. A premissa A5 é promovida a **fronteira de segurança declarada**, e o diário (D1) grava o executor de cada comando: a ação vira atribuível à identidade declarada. É mitigação, não correção — e está registrada como tal |
| ETI-01 🔴 | O recurso *antes* do fato já existe (indisponibilidade rígida, preferência S4) e o recurso *depois* é a troca. O que faltava era visibilidade: o UC-5 passa a incluir **distribuição por pessoa** (noturnos, fins de semana, feriados), resolvendo ETI-03 e dando base fatual para contestar. Não é UC novo — é conteúdo do UC-5 já aprovado |
| UX-01 🟡 | `trocas --pessoa <id>` lista as pendentes dirigidas a alguém. É o passo de **tomada de ciência** sem o qual UC-3 e UC-4 não se conectam — completa um fluxo aprovado, não acrescenta caso de uso |

## V(2) — Decomposição

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | dominio | entidades e objetos de valor; sem I/O, sem solver. `Escala` é entidade de dados — o cálculo de custo mora em `avaliador` (resolve a contradição ARQ-04); Domain Model aplica-se a `Troca` e `Restricao`, que têm comportamento próprio | `Pessoa, Contrato, TipoDeTurno, Plantao, Preferencia, RegraInterna, Alocacao, Escala, Troca, Violacao, Contexto, Evento` | — |
| M-02 | restricoes-legais | restrições de origem legal (L1 interjornada, L2 RSR, L3 regime 12×36 verificável, L4 limite de jornada) e a lógica de natureza-por-regime | `aplicar(modelo, vars, ctx)` · `verificar(escala, ctx) -> [Violacao]` · `fonte -> 'CLT art. N'` | dominio |
| M-03 | restricoes-modelo | restrições do INRC-II (H1-H4, S1-S7 com pesos publicados) e regras internas paramétricas, que têm a mesma forma | mesma interface de M-02 · `peso` · `origem ∈ {modelo, interna}` | dominio |
| M-04 | avaliador | custo, violações e distribuição por pessoa de uma escala concreta; deriva a fronteira validando a escala de origem | `avaliar(escala, ctx) -> Avaliacao{violacoes, custo, custo_por_restricao, distribuicao}` · `derivar_fronteira(escalas_anteriores, pessoas) -> {pessoa_id: Fronteira}` · `montar_contexto(...) -> Contexto` | dominio, restricoes-legais, restricoes-modelo |
| M-05 | troca | máquina de estados (PENDENTE → EFETIVADA/REJEITADA/RECUSADA/EXPIRADA/CANCELADA/ORFA) e revalidação contra a escala vigente no aceite | `solicitar(...)` · `responder(troca, aceite, escala, quem)` · `cancelar(troca, quem)` · `pendentes_de(pessoa)` | dominio, avaliador |
| M-06 | solver-cpsat | adaptador do solver: monta o modelo a partir das duas famílias de restrições, resolve, traduz status | `gerar(instancia, fronteira, limite_s) -> ResultadoGeracao{escala, status, otimalidade_provada, motivo}` | dominio, restricoes-legais, restricoes-modelo, avaliador |
| M-07 | diagnostico | inviabilidade estrutural pré-solve, com conflito localizado (só a verificação de elegibilidade; sem relaxação por camadas) | `analisar(instancia) -> [Conflito{plantao, exigidos, elegiveis}]` | dominio |
| M-08 | repositorio-json | persistência de snapshots imutáveis, com escrita atômica e id sanitizado | `salvar_escala/carregar_escala(id)` · `carregar_instancia` | dominio |
| M-09 | diario | log append-only de eventos com autor e carimbo; reconstrói a escala vigente | `registrar(evento, quem) -> Evento` · `eventos_de(escala_id)` · `escala_vigente(escala_id) -> Escala` | dominio |
| M-10 | carregador | parse e validação da instância: L4 como validação de configuração, limites de tamanho, erro por campo, guarda de peso de regra interna | `carregar(caminho) -> Instancia` (levanta `ErroDeValidacao` com campo e artigo) | dominio, restricoes-legais |
| M-11 | gerador-sintetico | instâncias reprodutíveis por semente, incluindo inviáveis deliberadas | `gerar(n_pessoas, n_dias, semente, inviavel=False) -> Instancia` | dominio |
| M-12 | cli | adaptador de entrada: os 5 UCs mais `trocas` (tomada de ciência), com saída legível e mensagens citando a regra e o artigo | `gerar · consultar · trocar · responder · trocas · conformidade` | todos |

## Premissas de V(2) (alteradas em relação a V(1))

| id | Premissa | Estado em V(2) |
|---|---|---|
| A1 | Tipos de turno têm horários fixos | mantida; `vira_o_dia` agora explícito (LIN-03) |
| A2 | Um contrato por pessoa no horizonte | mantida |
| A3 | Escala anterior publicada e completa | **relaxada**: o avaliador distingue ausência de falha e lê N meses conforme o horizonte contratual |
| A4 | CP-SAT resolve 30×3×30 em ≤ 60 s | mantida, aberta (PR-2) |
| A5 | A identidade informada no comando é verdadeira | **promovida a fronteira de segurança declarada** — decisão do operador sobre SEC-01 |
| A6 | Arquivo de instância não hostil | **relaxada**: limites de tamanho e sanitização de id (SEC-02, SEC-03) |
| A7 | Um operador por vez | mantida |
| A8 | Pesos do INRC-II adequados ao contexto brasileiro | mantida; guarda de peso impede regra interna de dominá-los (CIE-01) |
| A9 | **NOVA** — instância cobre uma única unidade/setor | declarada a partir de ASS-04 |

## Achados aceitos com justificativa (não corrigidos em V(2))

| Achado | Justificativa |
|---|---|
| ARQ-01 🟡 | a orquestração fica no `cli`, mas escrita como funções puras chamáveis sem `argparse`. Extrair um módulo de casos de uso acrescentaria indireção sem remover acoplamento (AP2) |
| PER-01 🟡 | só cai com medição no porte real — é trabalho da Fase 6, não de mais design |
| PER-02, SUS-02 🟡🟢 | avaliação incremental é otimização prematura no porte alvo (KISS); medir antes |
| PER-03, SUS-01 🟢🟡 | idem: custo aceitável em 30×3×30 |
| GAM-01, GAM-02 🟡 | limitar propostas de troca ou racionar preferências exige uma política que pertence ao operador, não ao design; e qualquer limite seria número sem fonte |
| ETI-02 🟡 | mitigado por ETI-03 (distribuição por pessoa torna o viés mensurável); reponderar S4 contrariaria os pesos publicados sem base |
| ASS-03 🟡 | troca é restrita a plantões da mesma escala, agora validado explicitamente |
| ASS-04 🟢 | vira a premissa A9 |
| CIE-02 🟢 | premissa A8 sem plano de verificação: verificá-la exigiria estudo empírico fora do escopo |

---

# V(3) — Simplificação (Fase 3, iteração 2)

Resposta aos 21 achados da iteração 2. A rodada anterior corrigiu por ADIÇÃO —
um módulo novo, dois estados novos — e a crítica mostrou o preço disso
(RES-04, ARQ-06, PRO-06 são AP2 no flagrante). **V(3) corrige por REMOÇÃO.**

## Decisões estruturantes

**E1 — `diario` deixa de existir; o histórico vira parte do arquivo da escala.**
Cada escala é UM artefato: `snapshot_publicado` + `eventos[]`. Três críticos caem
de uma vez, e nenhum mecanismo novo entra:
- **LIN-05** — a ordem dos eventos é a **posição na lista**, definida por
  construção. Não há carimbo de tempo arbitrando nada.
- **RES-04** — não existe append parcial: o arquivo inteiro é reescrito por
  temporário + renomeação, que é atômico no sistema de arquivos. No porte alvo o
  arquivo tem poucos KB, então reescrever é barato. Some a assimetria perigosa
  que V(2) criou (log append-only sem redundância).
- **ARQ-05** — só existe UMA leitura pública, `carregar_escala(id)`, que devolve
  a escala **vigente**. O snapshot não é exposto: não há como chamar a errada.

**E2 — a máquina de trocas volta de 7 para 5 estados.** PRO-06 estava certo: a
resposta à crítica de processo foi acrescentar estados.
- **ORFA some.** Com E1 a escala publicada é imutável e identificada; re-gerar
  com `--force` produz uma escala NOVA, com id novo, e a antiga continua
  existindo. Uma troca pendente não fica órfã — ela referencia uma escala que
  deixou de ser a vigente, e **a revalidação no aceite, que já existe desde
  V(1), rejeita com motivo claro**. O estado era redundante com uma regra que já
  estava lá (PRO-05 cai junto).
- **CANCELADA some.** O cancelamento pelo solicitante (PRO-03, legítimo)
  termina em RECUSADA, e o evento registra quem encerrou. A capacidade fica; o
  estado, não.

**E3 — `Contexto` vira dataclass do `dominio` com construtor que exige a
fronteira.** A garantia de ASS-01 passa a ser de TIPO, não de disciplina de
chamada: nenhum módulo consegue construir um `Contexto` incompleto, e nenhum
precisa ser "o dono da fábrica". O `avaliador` volta a ter três
responsabilidades coesas — custo, distribuição e fronteira — todas "percorrer a
escala por pessoa" (ARQ-07).

**E4 — a guarda de peso muda de módulo.** De `carregador` para
`restricoes-modelo`, que é o dono da semântica de peso: agora vale por qualquer
caminho, inclusive o `gerador-sintetico` (REG-04).

## Invariantes declaradas (contratos, não código)

> **INV-1** (de V(2)): toda escala produzida por `solver-cpsat` com um conjunto
> de restrições aplicado deve ser verificada por `avaliador` com zero violações
> rígidas desse mesmo conjunto.
>
> **INV-2** (nova, LIN-06): restrição de `origem = legal` tem sempre
> `natureza = rigida` e `peso = None`; restrição de `origem ∈ {modelo, interna}`
> tem sempre `peso` definido quando `natureza = flexivel`. O contrato deixa de
> permitir perguntar o peso de uma regra legal.
>
> **INV-3** (nova, E1): a escala vigente é função determinística de
> `(snapshot, eventos)` aplicados na ordem da lista. Mesma dupla, mesma escala,
> em qualquer implementação.

## Ajustes pontuais

| Achado | Ajuste |
|---|---|
| ASS-05 | `--aceitar-historico` permite propagar fronteira de escala anterior com violações, registrando a decisão como evento. Sem a flag, UC-1 recusa e explica — mas deixa de haver beco sem saída |
| CTL-03 | a janela de meses lidos é o `horizonte_meses` declarado no contrato (default 1), não "quantos forem necessários". O limite vem do dado, não de um número inventado |
| CIE-04 | tolerância de L3 é **zero**: ≥36h ininterruptas, leitura literal do art. 59-A. Nenhum número sem fonte entra |
| UX-04 | `trocas --pessoa X` lista recebidas **e** enviadas |
| ETI-04 | o relatório de distribuição é agregado (mediana, mínimo, máximo, desvio) e só detalha nominalmente a linha da própria pessoa quando `--pessoa` é informado |
| IMP-02 / IMP-05 | pseudocódigo de S2/S3 depositado em `specs/technical/modelo-cpsat.md` §11 — dívida da iteração 1 que atravessou V(2) sem tratamento, agora paga |
| IMP-04 | formato do evento especificado: lista JSON dentro do arquivo da escala, com `tipo ∈ {troca_efetivada, expiracao, historico_aceito}`, `quem`, `quando`, `dados` |

## Aceitos com justificativa em V(3)

| Achado | Justificativa |
|---|---|
| SEC-04 🟡 | o arquivo continua editável à mão. Encadeamento por hash detectaria adulteração, mas contra um adversário local com acesso ao disco e sem autenticação (A5, A6) daria garantia aparente, não real. A fronteira de segurança está declarada; fingir mais seria pior |
| GOV-04 🟡 | autoria auto-declarada é consequência direta de SEC-01, já arbitrado pelo operador. O diário é honesto sobre O QUE mudou; a limitação sobre o QUEM está registrada, não disfarçada |
| PER-04, SUS-03 🟡🟢 | reprocessar os eventos custa microssegundos num arquivo de poucos KB. Compactação é otimização prematura (KISS) |
| ARQ-06 🟡 | separar regras internas num terceiro módulo custaria um módulo para distinguir o que o campo `origem` já distingue — e a Fase 3 deve simplificar, não multiplicar |

## V(3) — Decomposição (11 módulos)

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | dominio | entidades, objetos de valor e `Contexto` (construtor exige fronteira) | `Pessoa, Contrato, TipoDeTurno, Plantao, Preferencia, RegraInterna, Alocacao, Escala, Evento, Troca, Violacao, Contexto, Fronteira` | — |
| M-02 | restricoes-legais | L1 interjornada, L2 RSR, L3 regime 12×36 verificável, L4 jornada; natureza-por-regime. INV-2: sempre rígidas, sem peso | `aplicar(modelo, vars, ctx)` · `verificar(escala, ctx) -> [Violacao]` · `fonte -> 'CLT art. N'` | dominio |
| M-03 | restricoes-modelo | H1-H4, S1-S7 com pesos publicados, e regras internas paramétricas; dona da semântica de peso, inclusive a guarda ≤ 30 | mesma interface de M-02 · `peso` · `origem ∈ {modelo, interna}` | dominio |
| M-04 | avaliador | custo, violações, distribuição agregada e derivação de fronteira — tudo "percorrer a escala por pessoa" | `avaliar(escala, ctx) -> Avaliacao` · `derivar_fronteira(escalas, pessoas, horizonte_meses) -> {pessoa_id: Fronteira}` | dominio, restricoes-legais, restricoes-modelo |
| M-05 | troca | máquina de 5 estados (PENDENTE → EFETIVADA/REJEITADA/RECUSADA/EXPIRADA) e revalidação contra a escala vigente no aceite | `solicitar(...)` · `responder(troca, aceite, escala, quem)` · `cancelar(troca, quem)` → RECUSADA · `de(pessoa) -> {recebidas, enviadas}` | dominio, avaliador |
| M-06 | solver-cpsat | adaptador do solver: modelo a partir das duas famílias, resolve, traduz status | `gerar(instancia, fronteira, limite_s) -> ResultadoGeracao{escala, status, otimalidade_provada, motivo}` | dominio, restricoes-legais, restricoes-modelo |
| M-07 | diagnostico | inviabilidade estrutural pré-solve com conflito localizado | `analisar(instancia) -> [Conflito]` | dominio |
| M-08 | repositorio-json | dono do artefato único `snapshot + eventos`; escrita atômica; id sanitizado; expõe apenas a escala vigente | `carregar_escala(id) -> Escala` (vigente) · `criar_escala(escala)` · `anexar_evento(id, evento)` · `carregar_instancia(caminho)` | dominio |
| M-09 | carregador | parse e validação da instância: L4 como validação de configuração, limites de tamanho, erro por campo com artigo citado | `carregar(caminho) -> Instancia` | dominio, restricoes-legais |
| M-10 | gerador-sintetico | instâncias reprodutíveis por semente, incluindo inviáveis deliberadas | `gerar(n_pessoas, n_dias, semente, inviavel=False) -> Instancia` | dominio |
| M-11 | cli | 5 UCs + `trocas` (ciência), saída legível, mensagens citando regra e artigo | `gerar · consultar · trocar · responder · trocas · conformidade` | todos |

**Trajetória:** V(1) 11 módulos → V(2) 12 → V(3) 11. Estados da troca: 5 → 7 → 5.
A segunda volta do laço desfez o que a primeira acrescentou em excesso e manteve
o que ela resolveu de fato: imutabilidade, auditoria, divisão do catálogo por
origem e as três invariantes declaradas.
