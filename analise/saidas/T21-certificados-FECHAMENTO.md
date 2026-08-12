# Fechamento — T21-certificados

Primeiro projeto válido do ciclo 2. Concluído 2026-08-09, 4,1 h, 8 fases, instrumento
**versus-claude 0.14.2** (única versão instalada).

110 achados · 12 módulos · 2 iterações do laço 2↔3 · 105 defeitos distintos ·
severidades: 13 crítico, 70 importante, 27 sugestão.

Passos 1–5 completos em `T21-certificados-passos.md`. Aqui só o que precisa de leitura.

---

## 1. Formato: limpo

Validação sem nenhuma recusa. Todas as 110 lentes canônicas e dentro do conjunto
declarado **para a iteração de cada achado**; `stateVersion=1` com `activatedLenses`
estruturado em duas entradas (`it1` contra V(1), `it2` contra V(3)), cada uma com os 12
condicionais contabilizados.

É o primeiro projeto em que o bloco 1 + bloco 2 do `PEDIDO-v0.14.0` operam juntos, e o
defeito que custou o T21-quotas (lente por nome não canônico) não teria passado.

## 2. Ativação: 11 de 12 condicionais

Ativaram nas duas iterações, sem mudança entre elas: RES · UX · SUS · ETI · PRO · GOV ·
OBS · CTR · JOG · LIN · MEC. Só MIG ficou de fora, com justificativa.

Já registrado como achado aberto em `ACHADOS-TAXONOMIA.md` — a distinção
condicional/universal pode ser empiricamente frágil sob os gatilhos da v0.12.9. Decisão
tomada: **não corrigir durante o lote**, reavaliar com quatro projetos. O T24 é o primeiro
teste fora do slot T21.

Nota lateral que contraria a hipótese de M3 do taxonomia: **MEC ativou já na iteração 1**,
contra a V(1). É a primeira observação nesse sentido — as três anteriores apontavam para
maturação. Uma observação não derruba três, mas registra-se.

## 3. Estimativa cega sobre a V(1) — e os dois estimadores não concordam entre si

Dois estimadores, 3 rodadas cada, sobre a arquitetura V(1) (não sobre o enunciado), com o
**mesmo pacote** — o texto é gerado uma vez e gravado em
`cego/T21-certificados-reestimativa-V1-pacote.md`.

| lente | `qwen3.6:27b` | `kimicode` | Fase 2 |
|---|---|---|---|
| RES · UX · PRO · GOV · OBS · CTR | sim | sim | SIM |
| MIG | não | não | não |
| **LIN** | **não** | sim | SIM |
| **SUS** | 2/3 | sim | SIM |
| **MEC** | 2/3 | sim | SIM |
| ETI | **não** | 1/3 | SIM |
| JOG | **não** | 1/3 | SIM |

| | qwen3.6:27b | kimicode |
|---|---|---|
| coincidem | 7 | **10** |
| divergem | 3 (ETI, JOG, LIN) | **0** |
| oscilaram | 2 (SUS, MEC) | 2 (ETI, JOG) |

**O resultado central deste passo não é a divergência com a Fase 2 — é que os dois
estimadores lêem partes diferentes da definição da lente.** E a divergência **não é
incapacidade do modelo local**: nas três lentes em que o Qwen diverge, ele repete
justificativa quase idêntica nas 3 rodadas, e a leitura dele é a **mais fiel ao texto do
gatilho**.

| lente | gatilho canônico | justificativa do Qwen (estável em 3/3) |
|---|---|---|
| JOG | *"Multiple independent actors, **public API, external integrations, marketplace or platform design**"* | *"sem mercado aberto, API pública ou incentivos econômicos entre entidades independentes"* |
| ETI | *"Automated decisions **about people** (scoring, classification, moderation)"* | *"classifica certificados X.509, não pessoas"* |
| LIN | *"…interface contracts **between independent teams**"* | *"contratos internos em TypeScript no mesmo repositório, não protocolos entre equipes independentes"* |

O Qwen aplicou o **gatilho como escrito**; a Fase 2 ativou pela **pergunta central**. É o
defeito já documentado para GOV — pergunta mais larga que a condição de ativação —
reaparecendo em três lentes de uma vez. Registrado em `ACHADOS-TAXONOMIA.md`.

### A concordância está contaminada pela taxa-base

A Fase 2 declarou **11 de 12**. Um leitor que dissesse "sim" a tudo acertaria 11 e
erraria 1.

| estimador | ativas por rodada | acertos |
|---|---|---|
| qwen3.6:27b | 7 · 8 · 7 | 7 |
| kimicode | 11 · 9 · 9 | 10 |

**Boa parte da vantagem do Kimi é permissividade, não acurácia** — e ela só existe porque
a taxa-base está em 11/12, que é o achado da ativação quase universal (§2). Os dois
problemas se contaminam, e nenhuma contagem de concordância deste projeto deve ser lida
sem a coluna de ativações ao lado.

**Regra adotada para os doze:** os dois estimadores em todos, **n=3 em todos**, e
concordância nunca reportada sem a contagem de ativações. Um permissivo e um restritivo
cercam a resposta; qualquer um sozinho seria pior, e mudar n no meio do lote trocaria
homogeneidade por precisão que não temos como usar.

**Defeitos de capacidade observados no modelo local**, para constar: quantização Q4_K_M, e
vazamento de token chinês (`评分` no lugar de "pontuação") em 2 das 3 justificativas de
ETI. Não corrompeu nenhuma decisão — as três leituras são coerentes e citam o gatilho —
mas é o tipo de artefato que num texto pior poderia corromper.

**Ressalva de instrumento, a constar em toda comparação entre os dois:** o Ollama recebe
`temperature` e `seed` por rodada; o CLI do Kimi **não expõe nenhum dos dois**. O critério
de estabilidade (3/3 ou 0/3) continua aplicável, mas o mecanismo de variação não é o
mesmo, e "oscilou" não significa exatamente a mesma coisa nos dois.

Nota de operação: o Kimi voltou por OAuth do CLI, não pela chave de API revogada. Roda em
diretório temporário vazio — o CLI é agente, e com acesso ao repositório poderia ler os
projetos ou a matriz, o que desfaria o cegamento.

## 4. Remarcação cega: os dois juízes não concordaram em nenhum par

O resultado mais forte do projeto, e o mais desconfortável.

| | todos os pares | mesmo módulo |
|---|---|---|
| κ de Cohen | **−0,001** | **−0,009** |
| pares avaliados | 5995 | 526 |
| **ambos: duplicata** | **0** | **0** |
| só o modelo gerador | 5 | 4 |
| só o juiz cego | 6 | 6 |

Gerador marcou 5 pares. Juiz cego marcou 6. **Interseção vazia.**

**Sobre o rótulo.** O script imprime *"pior que acaso — as marcações discordam
sistematicamente"*, porque κ < 0. Isso **superinterpreta**: −0,001 é indistinguível de
zero, e com 11 marcações positivas em 5995 pares a concordância esperada por acaso é
praticamente nula de qualquer forma. A leitura correta é *nenhuma concordância além do
acaso*, não *discordância sistemática*.

O limiar `k < 0` produzindo o rótulo mais duro para um valor essencialmente nulo é defeito
do meu classificador. **Não vou corrigi-lo agora** — seria a segunda vez que suavizo um
rótulo depois de ver um resultado que não gostei (a primeira foi o `MIN_POSITIVOS`, já
declarada como A3), e duas já formam padrão. Fica como pendência declarada, a corrigir
uniformemente sobre os doze **depois** que todos rodarem, com o antes e o depois visíveis.

**As seis do juiz cego que o gerador não viu** são o dado interessante, porque são
sobreposição nos achados que o próprio gerador produziu:

| par | módulo | tipo |
|---|---|---|
| `UX-01 + UX-06` | web-ui | mesma lente |
| `SEC-01 + SEC-02` | web-ui | mesma lente |
| `PRO-01 + PRO-06` | pedido | mesma lente |
| `ARC-03 + LIN-06` | repositorio | **entre lentes** |
| `ARC-04 + LIN-01` | reconciliacao | **entre lentes** |
| `GOV-01 + REG-01` | casos-de-uso | **entre lentes** |

Três das seis são **dentro da mesma lente** — exatamente o item C1 do
`CORRECOES-EXTENSAO-R2.md`, que pedia uma frase dizendo que `duplica` também vale
intra-lente. A frase entrou na guidance e o gerador continua não marcando esses casos. É
evidência de que instrução sem trava não resolveu, pela quarta vez no lote.

## 5. Quanto o Passo 2 depende de quem marca

Se a marcação do juiz cego substituísse a do gerador, a contribuição exclusiva mudaria
assim:

| lente | excl. gerador | excl. juiz | Δ |
|---|---|---|---|
| ARQ Architectural | 7 | 5 | **−2** |
| LIN Linguistics / Grammar | 6 | 4 | **−2** |
| REG Regulatory | 5 | 4 | −1 |
| GOV Governance / Accountability | 5 | 4 | −1 |
| DES Performance | 4 | 6 | +2 |
| JOG Game Theory | 2 | 4 | +2 |
| IMP · CIE · SUS | | | +1 cada |
| as outras 9 | | | sem mudança |

Sob a **união** das duas marcações (a leitura mais conservadora — todo par que qualquer
juiz agrupou conta como um só defeito), 99 clusters em vez de 105, e SEG cai de 10 para 9,
PRO de 6 para 5, UX de 6 para 5.

**A conclusão que importa: nenhuma lente chega perto de zero exclusivo sob nenhuma das
três clusterizações.** A menor é JOG, com 2 sob a marcação do gerador. O veredito do §4 —
remover a lente cujos defeitos são 100% compartilhados — não muda de sinal para lente
alguma. A instabilidade é de **magnitude**, não de **classificação**.

Isso reforça o adendo A6: a sobreposição média é 9% neste projeto, e o critério binário do
§4 exige 100%. A distância é grande o bastante para que discordância entre juízes não a
atravesse.

## 6. Método e instrumento

Extraídos das fases 5–7 para `ACHADOS-METODO.md`:

- **M1** — o gate `tests_passing` recusou avançar cinco vezes com a suíte verde. Dois
  defeitos: marcadores que não cobrem o repórter padrão do `node:test`, e — o grave —
  `unknown` não escrevendo estado, o que congela um `fail` sem caminho de recuperação.
  Verificado no bundle. Pedido em `patches/PEDIDO-M1-test-outcome.md`. **Sem descarte**: a
  matriz fecha na Fase 4, antes do gate.
- **M2** — diagnóstico de causa raiz que acertou o sintoma antes da causa; um teste que
  montava o cenário errado e teria ficado verde sem exercitar CA-5.

`RETRABALHO.md` do projeto: **zero defeitos pós-entrega**. Duas dívidas de granularidade
(ARC-06, ARC-07) foram nomeadas na entrega, não descobertas depois.

---

## Pendências que este projeto abre

1. **Os dois estimadores aplicam partes diferentes da definição da lente** — o Qwen o
   gatilho, o Kimi e a Fase 2 a pergunta central. Não é ruído: é o defeito de GOV em ETI,
   JOG e LIN. Os dois passam a ser obrigatórios nos doze, com n=3, e a concordância nunca
   vai reportada sem a contagem de ativações.
2. **Rótulo de κ para valores nulos-por-baixo.** Corrigir uniformemente após os doze.
3. **`duplica` intra-lente continua não sendo marcado** apesar da guidance. Quarto caso de
   instrução sem trava; candidato a gate, se a operadora quiser um.
