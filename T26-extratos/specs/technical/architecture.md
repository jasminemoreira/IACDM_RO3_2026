# Arquitetura — T26 (importador de extratos com deduplicação e conciliação)

Padrão: **Hexagonal (Ports & Adapters)** · Princípios: KISS+YAGNI, SOLID (ênfase DIP/OCP),
DDD tático · Concorrência: single-threaded · GoF: Strategy, Chain of Responsibility, Adapter ·
Fowler: Domain Model + Repository/Data Mapper.

**Regra de nomes:** os nomes na coluna `module` são a chave estável entre fases. A Fase 2 usa
exatamente estes nomes na matriz de cobertura; a Fase 5 implementa com estes nomes.

---

## V(1) — Módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | domain-model | Entidades, value objects e os 5 estados terminais de conciliação. Garante os invariantes I1-I8 na construção do objeto | `Dinheiro(Decimal,2)`, `Transacao`, `Lancamento`, `Casamento`, `Pendencia`, `Resolucao`, `EstadoConciliacao{casado, casado-com-divergencia, orfao-no-extrato, orfao-no-livro, pendente-de-revisao}` | — |
| M-02 | canonicalizer | Normalização (descrição, data, sinal, encoding) e cálculo do hash canônico | `normalizar(bruto, perfil) -> Transacao\|Lancamento`; `hash_canonico(item) -> str` | domain-model |
| M-03 | ofx-adapter | Adapta OFX (v1 SGML / v2 XML) à porta FonteDeExtrato, via ofxtools | `ler(caminho, fonte) -> Iterable[RegistroBruto]` | domain-model |
| M-04 | csv-adapter | Parser CSV dirigido por perfil declarativo; 3 perfis de banco + perfil do livro | `carregar_perfil(nome) -> PerfilCSV`; `validar_perfil(p) -> [Erro]`; `ler(caminho, perfil) -> Iterable[RegistroBruto]` | domain-model |
| M-05 | repository | Portas de persistência + Data Mapper SQLite. UNIQUE sobre a identidade; import atômico | `salvar_transacoes(lote) -> ResultadoImport`; `buscar_por_identidade(chave)`; `salvar_casamentos(cs)`; `salvar_pendencia(p)`; `buscar_resolucao(par) -> Resolucao\|None` | domain-model |
| M-06 | matcher | Geração de candidatos por blocking + score de similaridade par-a-par (pesos estilo Fellegi-Sunter, rapidfuzz) | `candidatos(a, b, chave_bloco) -> Iterable[Par]`; `score(par) -> float` | domain-model |
| M-07 | dedup-engine | Chain of Responsibility L0→L5: decide duplicata, pendência ou distinta, registrando a camada que decidiu e a evidência | `classificar(nova, existentes) -> DecisaoDedup{veredito, camada, evidencia}` | domain-model, matcher, repository |
| M-08 | reconcile-engine | Casamento 1:1 extrato × livro; atribui exatamente um dos 5 estados; janela de data e tolerância de valor configuráveis | `conciliar(transacoes, lancamentos, config) -> ResultadoConciliacao` | domain-model, matcher, repository |
| M-09 | review-queue | Fila de pendências e resoluções humanas persistidas; alimenta a camada L0 do dedup-engine | `listar(filtro) -> [Pendencia]`; `resolver(id, acao) -> Resolucao` | domain-model, repository |
| M-10 | reporter | Relatórios: contagem por estado (soma = total) e sub-rotulação de órfão esperado vs anômalo por idade do item | `resumo(escopo) -> Relatorio`; `render(relatorio, formato)` | domain-model, repository |
| M-11 | cli | Superfície do operador: import, reconcile, review, report. Composition root — monta adapters e injeta as portas | `main(argv) -> int` | todos |
| M-12 | fixture-generator | Gerador sintético determinístico (seed fixa): fixtures OFX/CSV, duplicatas de reimportação e cross-source plantadas, colisões legítimas plantadas, carga de 50k e ground truth rotulado | `gerar(seed, n, perfil) -> (arquivos, GroundTruth)` | domain-model, csv-adapter |

### Fronteiras

O núcleo — `domain-model`, `canonicalizer`, `matcher`, `dedup-engine`, `reconcile-engine` — **não
importa** `ofxtools`, `sqlite3` nem `csv`. Os adapters (`ofx-adapter`, `csv-adapter`, `repository`)
e o composition root (`cli`) são os únicos pontos de contato com o mundo externo.

### Interfaces (Design by Contract)

- **Portas de entrada:** `FonteDeExtrato`, implementada por `ofx-adapter` e `csv-adapter`.
- **Portas de saída:** `RepositorioTransacoes`, `RepositorioCasamentos`, `RepositorioResolucoes` —
  implementadas por `repository` e por dublês em memória nos testes.
- `matcher` recebe itens já canônicos; não sabe de qual formato vieram.
- `DecisaoDedup` **sempre** carrega qual camada decidiu (L0-L5) e a evidência. Sem isso não há como
  auditar um falso positivo — e VAL-2 exige zero deles.

---

## Premissas (AP4 — declaradas, não implícitas)

| id | Premissa | Fragilidade | Origem |
|---|---|---|---|
| A1 | O `FITID` é estável entre downloads da mesma transação | **Alta** | Contra-evidência documentada em `specs/references/fontes-externas.md` §1.2. Se falso, L1 falha e o caso cai em L2/L3 |
| A2 | CSV de banco não traz ID nativo, logo a identidade depende do hash canônico | Média | Fase 0, N1 |
| A3 | O layout do CSV do livro interno é estável e declarado | Média | Fase 0, N3 |
| A4 | O blocking mantém blocos pequenos (b ≤ 50) | **Alta** | `specs/technical/parametros-matching.md` §Orçamento. Tarifas de valor redondo repetido produzem bloco degenerado e reintroduzem O(n²) |
| A5 | Todo par tem uma resposta certa quanto a "é o mesmo evento?", e o humano a conhece | Média | Fase 0, N4 |
| A6 | A descrição da contraparte é comparável entre fontes | **Alta** | O banco escreve `PIX ENVIADO JOAO`, o ERP escreve `João da Silva ME`. Se a similaridade de descrição for ruído, o score cross-source perde poder discriminante |
| A7 | `abs(valor)` como chave de bloco não confunde estorno com duplicata | **Alta** | Ambiguidade 4 da Fase 0, deixada deliberadamente em aberto para a crítica |

## Escopo negativo

O sistema deliberadamente **não**: categoriza contabilmente transações · casa 1:N/N:1
automaticamente (esses casos viram pendência) · trata multi-moeda ou câmbio · expõe UI web, rede ou
autenticação · lê CAMT.053 ou API de agregadora · funde sob evidência fraca (prefere pendência a
falso positivo) · sobrescreve decisão humana registrada.

---

# V(2) — resposta unificada à Iteração 1 da crítica

Três causas-raiz explicam a maior parte dos 76 achados. A resposta trata a causa, não cada sintoma.

- **R1 — identidade da OBSERVAÇÃO ≠ identidade do EVENTO.** V(1) usava o hash canônico para as duas
  coisas: "esta linha já foi importada" e "este é o mesmo evento financeiro". Daí a contradição
  I6↔I8 (ASM-04): UNIQUE sobre o hash garante idempotência e proíbe colisão legítima. **V(2) separa
  os dois:** a identidade da observação é `(fonte, arquivo_hash, indice_linha)` — natural, sempre
  disponível, e é sobre ela que o UNIQUE garante idempotência; a identidade do evento é a evidência
  probabilística que o dedup avalia, e **nunca** é uma constraint de banco. Isso *elimina* a
  contradição em vez de acomodá-la.
- **R2 — dois módulos acumulavam eixos distintos.** `repository` era esquema + identidade + retenção
  + fronteira transacional + proveniência + índice. `matcher` era blocking + score para duas
  semânticas incompatíveis. V(2) devolve a cada um um eixo só, e o parâmetro que faltava (perfil de
  comparação) passa a ser explícito no contrato.
- **R3 — faltava o eixo de registro.** O que o sistema decidiu, com que evidência e sob quais
  parâmetros não tinha lugar no desenho. `audit-log` não é ornamento: é a dimensão sem a qual VAL-2
  ("zero falso positivo") é inverificável, porque não há como investigar um.

**Balanço de módulos: 12 → 12.** `canonicalizer` foi absorvido por `domain-model` (a forma canônica
é a construção do value object, não um passo separado); `audit-log` entrou no lugar. Nenhum módulo
foi acrescentado por acúmulo.

## V(2) — Módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | domain-model | Entidades e value objects, com normalização canônica e hash embutidos na construção (absorve canonicalizer). Dois eixos ortogonais em vez de um enum misturado: `Resultado{casado, casado-com-divergencia, orfao-no-extrato, orfao-no-livro}` × `Situacao{automatico, pendente, resolvido}`. `Dinheiro` guarda a escala original e rejeita perda de precisão | `Dinheiro(valor, escala)`, `Transacao`, `Lancamento`, `IdentidadeObservacao(fonte, arquivo_hash, indice_linha)`, `ChaveEvento(conta, data, valor, descricao_normalizada)`, `Casamento`, `Pendencia`, `Resolucao`, `Resultado`, `Situacao`, `regra_normalizacao() -> Regra` | — |
| M-02 | ofx-adapter | Adapta OFX à porta FonteDeExtrato, com resolução de entidades externas DESABILITADA e versão de ofxtools fixada. Linha inválida ABORTA o lote com erro nomeando arquivo e linha — sem perda silenciosa. Quarentena ficou fora de escopo por decisão do operador (RES-02 aceito como dívida) | `ler(caminho, fonte) -> Iterable[RegistroBruto]` | domain-model |
| M-03 | csv-adapter | Parser dirigido por perfil declarativo com GRAMÁTICA especificada (esquema de campos, tipos, obrigatoriedade, e `sinal` como enum fechado `{valor_assinado, coluna_indicadora, colunas_debito_credito}`). Linha inválida ABORTA o lote com erro nomeando arquivo e linha (RES-03 aceito como dívida) | `carregar_perfil(nome) -> PerfilCSV`; `validar_perfil(p) -> [Erro]`; `ler(caminho, perfil) -> Iterable[RegistroBruto]` | domain-model |
| M-04 | store | SÓ persistência: esquema versionado com migração, Data Mapper, índices declarados, fronteira transacional por lote, proveniência (toda linha aponta para fonte e arquivo). UNIQUE sobre IdentidadeObservacao — nunca sobre ChaveEvento. SQL sempre parametrizado; timeout e retry em lock | `versao_esquema() -> int`; `migrar()`; `gravar_lote(itens) -> ResultadoImport{novas, ja_presentes, rejeitadas}`; `candidatos_por_bloco(chave) -> [Item]`; `salvar_casamentos(cs)`; `carregar(filtro) -> [Item]` | domain-model |
| M-05 | audit-log | Trilha append-only, nunca sobrescrita: decisão de dedup com camada e evidência, resolução humana com autor e instante, e os parâmetros efetivos de cada execução (limiares, janela, tolerância, versões de lib). Responde "quem decidiu o quê, quando, com base em quê e sob quais parâmetros" | `registrar_execucao(parametros) -> ExecucaoId`; `registrar_decisao(execucao, decisao)`; `registrar_resolucao(execucao, resolucao)`; `historico(chave) -> [Evento]` | domain-model, store |
| M-06 | matcher | Geração de candidatos por blocking COM TETO de bloco (acima do teto, refina a chave em vez de comparar tudo) e score por PERFIL DE COMPARAÇÃO explícito — quais campos, que peso, escala fixada em 0-100 crescente. Dois perfis nomeados: `dedup` (transação × transação) e `conciliacao` (transação × lançamento) | `candidatos(itens, chave, teto) -> (Iterable[Par], MetricasBloco)`; `score(par, perfil) -> Score{0..100}` | domain-model |
| M-07 | dedup-engine | Cadeia L0→L5 EM LOTE (uma passagem, sem consulta por item). Escopo de comparação declarado: mesma conta sempre, mais cross-source dentro de uma janela configurável. L0 é resolvido por ChaveEvento, não por par de identidades nativas — assim a resolução sobrevive à troca de FITID. Registra cada decisão no audit-log e oferece caminho de correção | `classificar_lote(novas, escopo) -> [DecisaoDedup{veredito, camada, evidencia}]`; `desfazer_duplicata(id, motivo)` | domain-model, matcher, store, audit-log |
| M-08 | reconcile-engine | Casamento 1:1 com algoritmo DETERMINÍSTICO especificado: guloso estável por score decrescente, desempate por menor distância de data e depois por id — sem atribuição ótima global (custo O(n³) rejeitado). Detecta o caso 1:N antes de escolher e o encaminha como pendência. Atribui Resultado × Situacao | `conciliar(transacoes, lancamentos, config) -> ResultadoConciliacao` | domain-model, matcher, store, audit-log |
| M-09 | review-queue | Duas FAMÍLIAS de pendência com conjuntos de ação distintos: `PendenciaDedup{acoes: e_a_mesma, sao_distintas}` e `PendenciaConciliacao{acoes: casar_com, nao_casa}`. Fila ordenada por impacto financeiro, com agrupamento por padrão recorrente e resolução em lote. Resolução é desfazível — o desfazer é um novo registro, nunca apagamento | `listar(familia, ordem, agrupamento) -> [Pendencia]`; `resolver(id, acao, autor) -> Resolucao`; `desfazer(resolucao_id, motivo)` | domain-model, store, audit-log |
| M-10 | reporter | Recebe DADOS, não o banco. Contagem por Resultado (soma = total), sub-rotulação de órfão esperado vs anômalo pela janela de compensação, e cabeçalho com versão e parâmetros efetivos da execução. Saneia prefixos de fórmula na exportação CSV | `resumo(dados) -> Relatorio`; `render(relatorio, formato: {texto, csv, json}) -> str` | domain-model |
| M-11 | cli | Casos de uso NOMEADOS como funções com contrato próprio (`importar`, `conciliar`, `revisar`, `relatar`), e o parser de argumentos como casca fina sobre eles. Verifica pré-condição de ordem, devolve código de saída por classe de falha, valida caminhos e cria a base com permissão restrita. SEM `--dry-run` e SEM `fechar_periodo` — fora de escopo por decisão do operador (UX-02 e PRC-03 aceitos como dívida) | `main(argv) -> CodigoSaida`; um caso de uso por comando | todos |
| M-12 | fixture-generator | Gerador determinístico (seed fixa) que emite fixtures OFX/CSV, duplicatas de reimportação e cross-source plantadas, colisões legítimas plantadas, arquivos NÃO CONFORMES deliberados, carga de 50k e o ground truth rotulado. Escreve apenas dentro do diretório de saída declarado. Não depende de csv-adapter: emite texto diretamente | `gerar(seed, n, destino) -> GroundTruth{duplicatas, colisoes, casamentos_esperados}` | domain-model |

## Resolução dos achados, por id

**Críticos (20).** ASM-01: `Dinheiro` guarda a escala original e recusa arredondamento com perda —
comparação exata preservada. ASM-02 e ASM-04: causa-raiz R1 — UNIQUE passa para
`IdentidadeObservacao`; o hash de evento vira evidência, não constraint; descrição instável deixa de
quebrar a idempotência, e a colisão legítima deixa de colidir com ela. ASM-03: `classificar_lote`
recebe `escopo` explícito (mesma conta sempre + janela cross-source configurável). ARC-01: casos de
uso viram funções nomeadas com contrato, e a CLI é casca fina. ARC-02: perfil de comparação
explícito (`dedup` | `conciliacao`) — um contrato, duas configurações declaradas. IMP-01: algoritmo
fixado (guloso estável por score, desempate por distância de data e por id). IMP-02: perfil de
comparação declara campos, pesos e tratamento de campo ausente. SCI-01 (duplica IMP-02): resolvido
pelo mesmo mecanismo, mais a exigência de estimar m/u contra o ground truth do fixture-generator e
depositar os valores em specs/technical antes de codar. SEC-01: saneamento de prefixo de fórmula na
exportação. SEC-02: resolução de entidades externas desabilitada no ofx-adapter. PRF-01: teto de
bloco com refino de chave em vez de comparação exaustiva. PRF-02: contrato em lote elimina o N+1.
RES-01: fronteira transacional declarada por lote em `gravar_lote`. UX-01: fila com ordenação por
impacto, agrupamento por padrão recorrente e resolução em lote. PRC-01: eixos separados —
`Situacao` deixa de disputar espaço com `Resultado`, e pendente deixa de ser um estado terminal
disfarçado. PRC-02: duas famílias de pendência com ações próprias. GOV-01: `audit-log` append-only;
desfazer é registro novo, nunca apagamento. CTL-01: L0 chaveado por `ChaveEvento` — a resolução
sobrevive à troca de FITID e a pendência para de reaparecer. LIN-01: `sinal` vira enum fechado de
três valores na gramática do perfil.

**Importantes (41).** ASM-05 fuso normalizado na construção · ASM-06 caso 1:N detectado antes da
escolha · ASM-07 encoding verificado com falha explícita em vez de mojibake silencioso · ARC-03
fixture-generator deixa de depender de csv-adapter · ARC-04 reporter recebe dados · ARC-05 rota
única para resoluções, via audit-log · IMP-03 esquema do perfil declarado · IMP-04 `ResultadoImport`
declarado · SCI-02 limiares calibrados contra o ground truth antes de virarem default · SCI-03 e
SCI-04 janelas por instrumento (PIX D+0, TED D+1, cartão D+30) a depositar em specs/technical com
fonte · SEC-03 SQL sempre parametrizado · SEC-04 caminhos validados e base com permissão restrita ·
SEC-05 escrita confinada ao destino declarado · PRF-03 índices declarados no store · PRF-04 ótimo
global rejeitado por custo · REG-01 e REG-02 retenção, base legal e controle de acesso a declarar em
specs/validation · RES-02 e RES-03 **NÃO resolvidos** — quarentena fora de escopo por decisão do
operador; mitigação parcial: falha explícita nomeando arquivo e linha, sem perda silenciosa · RES-04
timeout e retry em lock · UX-02 **NÃO resolvido** — `--dry-run` fora de escopo por decisão do
operador · UX-03 desfazer · UX-04 formatos enumerados · SUS-01 e
SUS-02 janela de comparação limita o custo ao valor entregue · PRC-03 **NÃO resolvido** —
`fechar_periodo` fora de escopo por decisão do operador · PRC-04
pré-condição de ordem verificada · GOV-02 evidência persistida no audit-log · GOV-03 proveniência em
toda linha · OBS-01 log estruturado por execução · OBS-02 `MetricasBloco` devolvida pelo matcher ·
OBS-03 códigos de saída por classe · CTL-02 (duplica REG-03) parâmetros efetivos gravados por
execução · CTL-03 `desfazer_duplicata` · LIN-02 eixos separados · LIN-03 escala fixada em 0-100
crescente · LIN-04 `regra_normalizacao()` explícita e versionada · MEC-01 versão de ofxtools fixada
· MEC-02 perfil tolera coluna extra e falha com mensagem nomeando a coluna ausente · MEC-03 esquema
versionado com migração.

**Sugestões (15).** Aceitas para tratamento junto do módulo correspondente, exceto SEC-06
(criptografia em repouso) e SUS-03 (cache do dataset de 50k), que ficam registradas como dívida
consciente — ver decisões da Fase 3.

## Premissas de V(2)

A1 (FITID estável) **deixa de ser premissa**: o design agora funciona com ela falsa, porque L0 é
chaveado por evento e L1 é apenas uma camada de evidência entre outras. A4 (bloco pequeno) deixa de
ser premissa: o teto de bloco a torna uma propriedade garantida. A7 (estorno) permanece **aberta** —
a chave de bloco por `abs(valor)` ainda agrupa estorno com a transação original; V(2) mitiga
incluindo o sinal no perfil de comparação, mas não há evidência de que isso baste. A2, A3, A5 e A6
seguem válidas e declaradas.

---

# V(3) — resposta unificada à Iteração 2 da crítica

O padrão dominante da Iteração 2 não foi "premissa oculta" (o da Iteração 1) e sim **correção que
desloca o problema**. Três causas-raiz, mais uma remoção.

- **R4 — a identidade da observação ficou forte demais.** `(fonte, arquivo_hash, indice_linha)`
  identifica o ARQUIVO, não a OBSERVAÇÃO: reimportar uma janela sobreposta gera arquivo diferente,
  logo identidade nova, logo o UNIQUE não impede nada (ASM-09) — a saída da contradição I6↔I8 tinha
  custado a idempotência do UC-2. Substituída por **chave natural com ordinal**:
  `(fonte, conta, FITID)` quando há FITID; senão
  `(fonte, conta, data, valor, descricao_bruta, ordinal)`, onde `ordinal` é a posição da linha
  dentro do grupo de linhas idênticas do mesmo dia. O ordinal distingue as duas transações
  legitimamente iguais (preserva I6) e é reproduzido igual numa reimportação sobreposta (restaura
  I8 no caso real). Limitação declarada: se o banco alterar `descricao_bruta` entre exports, a chave
  muda — o caso cai no dedup, que é o comportamento correto, não uma falha silenciosa.
- **R5 — critérios de aceitação em conflito, sem árbitro.** Declarada a precedência: **corretude
  (VAL-1, VAL-2) vence desempenho (VAL-4)**. Consequência: quando um bloco excede o teto, o
  excedente NÃO é separado silenciosamente por refino de chave — vira **pendência**. Um par nunca é
  declarado distinto sem que a evidência tenha sido avaliada ou um humano tenha olhado. E VAL-3 volta
  a ser verificável como escrito na Fase 0 por uma **projeção declarada**:
  `estado_val3 = pendente-de-revisao se Situacao == pendente, senão Resultado` — os dois eixos
  permanecem, e o critério de aceitação da Fase 0 passa a ser uma vista derivada deles.
- **R6 — o audit-log entrou sem contrato de falha.** Passa a receber a **unidade de trabalho** do
  `store` e grava na MESMA transação, em lote por importação e não uma escrita por decisão. Resolve
  a divergência estado↔trilha e tira 50.000 appends do caminho crítico dos 60 s, sem fundir os dois
  módulos (o que reconcentraria responsabilidades em `store`, que foi o problema da Iteração 1).
- **REMOÇÃO (a simplificação principal desta rodada).** SCI-06 mostrou que estimar os pesos m/u
  contra um ground truth sintético que o próprio projeto desenhou é validação circular. A resposta
  não é calibrar melhor: é **remover a estimação probabilística**. O score passa a ser uma **rubrica
  determinística de pontos por campo**, declarada em `specs/technical` com a justificativa de cada
  peso. Sob exigência de zero falso positivo e com a faixa intermediária indo para revisão humana,
  uma rubrica transparente entrega mais que um modelo probabilístico não calibrável — e é auditável,
  que é o que VAL-2 exige. Fellegi-Sunter permanece em `specs/references` como fundamentação do
  desenho, não como algoritmo implementado.

**Balanço: 12 → 12 módulos.** Nenhum acrescentado; um aparato algorítmico removido.

## V(3) — Módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | domain-model | Entidades e value objects. `ChaveEvento` é DERIVADA sob demanda, nunca armazenada — mudar a regra de normalização deixa de invalidar histórico. Igualdade de `Dinheiro` é pelo valor numérico, não pela representação. Eixos `Resultado` × `Situacao{automatica, pendente, resolvida}` com a projeção `estado_val3` declarada | `Dinheiro`, `Transacao`, `Lancamento`, `ChaveNatural(fonte, conta, fitid \| (data, valor, descricao_bruta, ordinal))`, `chave_evento(item, regra) -> ChaveEvento`, `Casamento`, `PendenciaDedup`, `PendenciaConciliacao`, `Resolucao`, `Resultado`, `Situacao`, `estado_val3(item) -> Estado5` | — |
| M-02 | ofx-adapter | Adapta OFX à porta FonteDeExtrato. Recusa payload OFXv2 contendo `<!DOCTYPE`/`<!ENTITY` e aplica teto de tamanho — entidades EXTERNAS já são recusadas pela plataforma (verificado), a expansão de entidades INTERNAS não era e é tratada aqui. Versão de ofxtools fixada. Linha inválida aborta o lote nomeando arquivo e linha | `ler(caminho, fonte) -> Iterable[RegistroBruto]` | domain-model |
| M-03 | csv-adapter | Perfil declarativo com gramática especificada. `sinal` é enum fechado, e `colunas_debito_credito` declara o comportamento nos dois casos degenerados: ambas preenchidas → erro nomeando a linha; ambas vazias → linha inválida | `carregar_perfil(nome) -> PerfilCSV`; `validar_perfil(p) -> [Erro]`; `ler(caminho, perfil) -> Iterable[RegistroBruto]` | domain-model |
| M-04 | store | Só persistência. UNIQUE sobre `ChaveNatural`. Expõe a unidade de trabalho para quem precisa gravar na mesma transação. `migrar()` faz cópia de segurança da base antes de aplicar e recusa abrir base de esquema mais novo que o binário. Índice composto declarado sobre as colunas de bloco. SQL sempre parametrizado | `unidade_de_trabalho() -> UoW`; `versao_esquema() -> int`; `migrar() -> Backup`; `gravar_lote(uow, itens) -> ResultadoImport{novas, ja_presentes_por_chave, ja_presentes_por_dedup, rejeitadas}`; `carregar_bloco(chave) -> [Item]` | domain-model |
| M-05 | audit-log | Trilha append-only gravada na unidade de trabalho DO STORE, em lote por importação. Registra decisão com camada e evidência, resolução com autor e instante, parâmetros efetivos e hash dos arquivos de entrada. Retenção declarada, com anonimização de contraparte após o prazo contábil para não colidir com o direito de eliminação | `registrar_execucao(uow, parametros, hashes) -> ExecucaoId`; `registrar_lote(uow, execucao, [decisao])`; `historico(chave_natural) -> [Evento]` | domain-model, store |
| M-06 | matcher | Candidatos por blocking com teto; **excedente do teto vira pendência, nunca é separado por refino silencioso** (precedência VAL-1 > VAL-4). Score por RUBRICA determinística de pontos por campo, escala 0-100 crescente, com dois perfis nomeados e versionados: `dedup` e `conciliacao`. Devolve métricas de bloco que o cli persiste | `candidatos(itens, chave, teto) -> (Iterable[Par], [Excedente], MetricasBloco)`; `score(par, perfil) -> Score{0..100}`; `versao_perfil(nome) -> str` | domain-model |
| M-07 | dedup-engine | Cadeia L0→L5 em lote. L0 resolvido por `ChaveNatural` do par. `desfazer_duplicata` devolve o item como `pendente` — nunca como não classificado (que permitiria refusão) nem como resolvido (que contradiria o desfazer) | `classificar_lote(uow, novas, escopo) -> [DecisaoDedup]`; `desfazer_duplicata(uow, id, motivo, autor)` | domain-model, matcher, store, audit-log |
| M-08 | reconcile-engine | Casamento 1:1 guloso estável por score decrescente; desempate por menor distância de data e, em último caso, por `ChaveNatural` — **nunca por id gerado em execução**, o que restaura o determinismo de VAL-5. Detecta 1:N antes de escolher e encaminha como pendência | `conciliar(uow, transacoes, lancamentos, config) -> ResultadoConciliacao` | domain-model, matcher, store, audit-log |
| M-09 | review-queue | Duas famílias de pendência com ações próprias. Ordenação por impacto financeiro e agrupamento. **Resolução em lote exige confirmação explícita do tamanho do grupo** e grava cada item individualmente na trilha. `desfazer` registra autor e motivo; quando o autor do desfazer é o mesmo da resolução original, a trilha marca a ausência de segunda instância | `listar(familia, ordem, agrupamento) -> [Pendencia]`; `resolver(uow, id, acao, autor) -> Resolucao`; `resolver_lote(uow, ids, acao, autor, confirmacao)`; `desfazer(uow, resolucao_id, motivo, autor)` | domain-model, store, audit-log |
| M-10 | reporter | Recebe dados. Contagem pela projeção `estado_val3` (soma = total, VAL-3 verificável como escrito). Sub-rotulação de órfão por janela POR INSTRUMENTO, com os valores e fontes depositados em specs/technical. Saneia prefixo de fórmula na exportação CSV. Cabeçalho com versão, parâmetros e versão dos perfis | `resumo(dados) -> Relatorio`; `render(relatorio, formato: {texto, csv, json}) -> str` | domain-model |
| M-11 | cli | Casos de uso nomeados com contrato (`importar`, `conciliar`, `revisar`, `relatar`). Abre a unidade de trabalho e a repassa. Persiste as métricas de bloco devolvidas pelo matcher. Código de saída por classe de falha; caminhos validados; base criada com permissão restrita | `main(argv) -> CodigoSaida`; um caso de uso por comando | todos |
| M-12 | fixture-generator | Gerador determinístico. Consome o MESMO arquivo de perfil que o `csv-adapter` lê (sem depender do módulo, mas sem reimplementar a semântica — a especificação do perfil é a fonte única). Planta duplicatas de reimportação com janelas sobrepostas, duplicatas cross-source, colisões legítimas e arquivos não conformes. Emite ground truth rotulado | `gerar(seed, n, destino, perfil) -> GroundTruth` | domain-model |

## Achados da Iteração 2 — resolução por id

**Críticos.** ASM-09 e IMP-09 e LIN-07: causa-raiz R4 — `ChaveNatural` com ordinal, e
`ResultadoImport` passa a distinguir `ja_presentes_por_chave` de `ja_presentes_por_dedup`. ASM-10 e
IMP-06: `ChaveEvento` deixa de ser armazenada e passa a ser derivada sob demanda — mudar a regra de
normalização não invalida mais o histórico, e L0 passa a ser chaveado por `ChaveNatural`, que não
depende da descrição normalizada. IMP-10: verificado empiricamente — entidades externas já são
recusadas pela plataforma; a expansão de entidades internas não era e ganha mecanismo próprio
(recusa de `<!DOCTYPE`/`<!ENTITY` e teto de tamanho). SCI-06: estimação de m/u REMOVIDA, substituída
por rubrica determinística declarada. PRF-06 e PRC-06: causa-raiz R5 — precedência corretude sobre
desempenho, excedente de bloco vira pendência, e `estado_val3` restaura a verificabilidade de VAL-3.
RES-06: causa-raiz R6 — unidade de trabalho compartilhada. MIG-01: `migrar()` faz cópia de segurança
antes de aplicar e a leitura recusa esquema mais novo.

**Importantes.** ASM-11 igualdade de `Dinheiro` por valor numérico · ASM-12 e SCI-07 rubrica e
janelas por instrumento a depositar em specs/technical com fonte ANTES da Fase 5 · ARC-07 o
blocking sai do contrato de persistência (`carregar_bloco` recebe a chave já calculada pelo matcher)
· ARC-08 gerador e parser passam a ler o MESMO arquivo de perfil, eliminando a deriva sem
reintroduzir a dependência · IMP-07 refino de chave substituído por pendência do excedente, o que
torna a especificação desnecessária · IMP-08 `historico` recebe `ChaveNatural` · SEC-07, REG-04 e
SUS-04 retenção declarada com anonimização de contraparte após o prazo contábil · SEC-08 origem dos
scripts de migração confinada · PRF-07 gravação em lote · RES-07 migração com cópia de segurança ·
UX-06 resolução em lote exige confirmação explícita do tamanho do grupo · UX-07 permanece como
efeito das dívidas aceitas pelo operador, agora registrado explicitamente · MIG-02 anonimização é
append (registro novo), não edição · MIG-03 recusa de esquema mais novo · PRC-07 `desfazer_duplicata`
devolve como `pendente` · GOV-05 a trilha marca ausência de segunda instância · GOV-06 hash dos
arquivos de entrada registrado · OBS-05 o cli persiste as métricas de bloco · CTL-04 sem refino no
limite, não há reclassificação por histerese · LIN-06 `Situacao{automatica, pendente, resolvida}`
com `automatica` significando origem da decisão, declarado · LIN-08 casos degenerados de
`colunas_debito_credito` especificados · MEC-05 perfis de comparação versionados, com a versão no
relatório e na trilha.

**Sugestões.** SEC-08 e GOV-06 resolvidos acima.

## Premissas de V(3)

A1 e A4 seguem neutralizadas. **A2 e A3 mantidas.** A5 mantida. **A6 (descrição comparável entre
fontes) deixa de ser premissa crítica**: com rubrica determinística, a descrição é um campo entre
outros com peso declarado, e sua ausência ou divergência reduz o score em vez de corromper um
modelo. **A7 (estorno confundido com duplicata pelo bloco em `abs(valor)`) PERMANECE ABERTA** — a
mitigação é o sinal entrar na rubrica com peso alto, mas não há evidência de que baste. Registrada
como limitação conhecida a verificar na Fase 6 contra o dataset.
