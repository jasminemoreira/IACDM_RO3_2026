# Classificação forma-vs-qualidade das instruções da Fase 2

Registro estável, decidido **antes** — para que a próxima lacuna seja uma consulta a esta
tabela, não um sétimo descarte. Vale para todos os builds.

## A regra de viés (o que autoriza uma trava)

Uma instrução da guidance só vira **gate** quando as duas condições valem:

1. **É propriedade de forma** — existência, valor num conjunto fechado, ou referência
   estrutural. Não qualidade ("é um bom achado?", "está bem descrito?"): isso é o oráculo
   (Rice/Tarski), indecidível mecanicamente.
2. **Tem falha observada no corpus, e a observação foi confirmada como falha** — não uma
   variação legítima lida como falha.

Sem (1), declara-se limitação. Sem (2), não se gateia por hipótese — declara-se e observa-se.
O resto é limitação declarada.

> **Por que a 2ª parte da condição 2.** O gate cruzado de módulos da v0.13.0 tinha observação
> (11 achados) mas diagnóstico falso: eram módulos removidos entre versões, não deriva. O gate
> saiu bom (união de versões tolera), mas foi pedido com argumento errado. Observar não basta;
> classificar a observação certo, sim. Gate preventivo também cobra.

## A tabela (matriz de cobertura / ciclo de achado)

| Instrução | Natureza | Falha no corpus? | Decisão | Onde |
|---|---|---|---|---|
| Coluna `módulo` = módulo real da arquitetura | forma (ref. estrutural) | **sim** — T14/T02, 11 achados em módulos inexistentes | **gate** (união de versões) | v0.13.0 |
| Coluna `lente` = nome canônico / NENHUMA | forma (enum) | **sim** — T21, `Sustainability` truncado | **gate** | v0.14.0 |
| Coluna `lente` declarada para a iteração do achado | forma (ref. por iteração) | **sim** — família do T14 (MEC entrou na it. 2) | **gate** (por iteração, degrada p/ união) | v0.14.0 |
| Declaração de lentes existe e cobre as 12 | forma (registro estruturado) | **sim** — três descartes por instrução sem trava | **gate** (`record_activated_lenses`) | v0.14.0 |
| Coluna `severidade` ∈ {🔴,🟡,🟢} | forma (enum) | **sim, por padrão** — 853 achados usam só os 3 glifos; um 4º valor seria não-contável | **gate** | v0.14.2 |
| Matriz é tabela de achados, não grid | forma (estrutural) | **sim** — histórico de grids | **gate** (`artifactRows`) | ≤v0.12 |
| `duplica:` descreve o defeito por si (§3) | **qualidade** | — (oráculo) | **declarar** | limitação L-x |
| `duplica:` aponta id existente (não pendurada) | forma (ref.) | **não** — 0 penduradas em 853 | **declarar** | — |
| `duplica:` tem descrição além do marcador | forma | **não** — 0 ponteiro-só em 853 | **declarar** | — |
| IDs de achado únicos no projeto | forma | **não** — 0 colisões em 853 | **declarar** | — |
| Cabeçalho `## Iteração N` presente quando multi-iteração | forma | **não** — toda matriz multi-it. tem; e o gate de lente já degrada com segurança se faltar | **declarar** | — |
| Prefixo consistente por lente | forma | **não** — consistente na amostra; e a análise agrupa pela coluna `lente`, não pelo prefixo → cosmético | **declarar** | — |
| Análise de concentração (por módulo, por lente) | **qualidade** (raciocínio, não estrutura) | — | **declarar** | — |
| Achado = evidência concreta, não opinião | **qualidade** | — (oráculo) | **declarar** | — |

**Resultado:** as três travas de coluna que existem (módulo, lente, severidade) — mais o
registro de lentes e a forma de tabela — são exatamente as com falha observada. Todo o restante
da família forma tem **zero ocorrências** no corpus → nenhuma vira gate. A família está fechada
pela regra, não por gosto. O próximo item que aparecer consulta esta tabela: se é qualidade,
limitação; se é forma sem falha observada, observa-se antes de travar.

## Segundo eixo: a trava tem que FALAR quando dispara

Um gate tem dois caminhos — o que passa e o que barra. Testar só "barrou?" (`ok === false`)
deixa passar um caminho de erro quebrado (no Python, exceção definida depois do uso → NameError
em vez da mensagem; em TS, interpolar `undefined` ou apontar a linha errada). **Todo teste de
bloqueio afirma a MENSAGEM** — que ela nomeia a linha/coluna/motivo — não só o booleano.
Auditado no build Claude: 5 testes eram só-booleano, corrigidos (commit `be245a4`); 85 no total,
todos exercendo o texto do bloqueio. Replicar a checagem nos outros builds.

## Limitação declarada L-x (para o protocolo/paper)

> A descrição de achado duplicado (§3) não é verificada. É propriedade de qualidade —
> indecidível mecanicamente — e os proxies de forma (ponteiro-só, referência pendurada)
> ocorrem zero vezes no corpus, então nenhuma trava foi adicionada. O instrumento garante
> lente e severidade canônicas e presentes; se o achado é real e se um duplicado está bem
> descrito permanece julgamento do revisor. Um duplicado mal descrito passa o gate e só é
> pego na análise/revisão humana — não é causa de descarte automático.
