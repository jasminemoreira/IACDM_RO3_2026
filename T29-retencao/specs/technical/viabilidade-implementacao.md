# Viabilidade de implementação — Tier 1/2/3 por componente (S6)

Fase 0. Regra do método: **Tier 1** = existe biblioteca madura → usar; **Tier 2** = algoritmo
documentado com implementação de referência → portar literalmente; **Tier 3** = nenhum dos
dois → se o domínio for complexo, **PoC obrigatório antes da Fase 1**.

As áreas abaixo são estimativa de porte, não a decomposição — decompor é trabalho da Fase 1.

---

| # | Área de responsabilidade | Tier | Fonte / justificativa |
|---|---|---|---|
| 1 | Escritor/leitor de bitstream | **3 (trivial)** | `int` de precisão arbitrária + deslocamento da stdlib. `bitarray`/`bitstring` ausentes e desnecessários. Domínio **não** complexo ⇒ sem PoC. Armadilha P1 (não truncar em 64 bits) já registrada |
| 2 | Codec de timestamp (delta-of-delta) | **2** | R1 §4.1.1 — 5 buckets literais; impl. de referência: Prometheus `chunkenc`. Portar literalmente |
| 3 | Codec de valor (XOR) | **2** | R1 §4.1.2 — control bits, 5+6 bits, estado `prev_leading`/`prev_trailing` |
| 4 | Bloco (janela de 2 h, header) | **2** | R1 §4.1.1 (header alinhado a 2 h, primeiro delta em 14 bits) + R8 (120 amostras/chunk) |
| 5 | Formato F1 (slot fixo) | **2** | R6 — layout com bytes exatos: Metadata 16 B, ArchiveInfo 12 B, Point 12 B |
| 6 | Formato F2 (bitstream em blocos) | **2** | R1 + R8 |
| 7 | Validação de config de retenção | **2** | R6 — regra de divisibilidade é literal e testável; R9 — armadilha da perda silenciosa (I7) |
| 8 | Downsampler (agregados + `xff`) | **2** | R9 (min/max/sum/count) + R6/R7 (`xFilesFactor` = 0.5) |
| 9 | Migrador F1 ↔ F2 | **3** | ⚠️ **Nenhuma implementação de referência existe** — é a lacuna competitiva (ver `competitors/analise.md`). Ver análise de risco abaixo |
| 10 | Gerador de dataset determinístico | **1** | `random` com seed (stdlib) e `numpy` 2.1.3 presente |
| 11 | CLI | **1** | `argparse` (stdlib) |
| 12 | Relatório de razão de compressão | **3 (trivial)** | contabilização aritmética; já prototipada na sondagem da Fase 0 |

**Contagem:** 7 componentes Tier 2 (o núcleo é port literal de fonte peer-reviewed), 2 Tier 1,
3 Tier 3 — dos quais 2 são triviais.

---

## Análise do único Tier 3 não-trivial: o migrador (#9)

**Precisa de PoC antes da Fase 1?** **Não** — e a razão importa:

- O algoritmo do migrador é composição de coisas já Tier 2: *ler tudo de F1* (#5) e *escrever
  tudo em F2* (#6). Não há algoritmo desconhecido no meio.
- Os dois pontos de extremidade estão **completamente especificados** (bytes exatos em `formatos-armazenamento.md`).
- O risco não é de viabilidade, é de **semântica** — e semântica se resolve com decisão de
  projeto na Fase 1, não com PoC.

### O risco de semântica (achado da Fase 0 a levar para a Fase 1)

F1 e F2 não são apenas contratos de **acesso** diferentes — têm **domínios de dado**
diferentes:

| | F1 (slot fixo) | F2 (bitstream) |
|---|---|---|
| Timestamp | 4 B, **quantizado** no slot de `secondsPerPoint` | delta-of-delta, **arbitrário** |
| Alcance temporal | até **2106** (Unix 32 bits) | 64 bits |
| Dois pontos no mesmo intervalo | **colidem** — o slot é único, um sobrescreve o outro | ambos coexistem |
| Ponto ausente | slot vazio é representável | ausência = simplesmente não gravado |

**Consequência direta:** a migração **não é simétrica**.

- **F1 → F2:** total, sem perda. Todo ponto de F1 tem representação em F2.
- **F2 → F1:** **potencialmente com perda** — quantização de timestamp para o slot, colisão de
  dois pontos no mesmo slot, e timestamps acima de 2106 não representáveis.

Por isso o critério **CA-2 foi escrito como F1 → F2 → F1** (a direção segura) e não como
"migração é reversível". Se a Fase 1 quiser afirmar reversibilidade nas duas direções, tem de
(a) restringir F2 ao domínio de F1 na escrita, ou (b) declarar a perda e rejeitar a migração
quando ela ocorreria. **Escolher em silêncio seria perda silenciosa de dado — a mesma classe
de falha que I7.**

→ Insumo direto para a Fase 2: lentes **Migration/Coexistence** (existe caminho de volta?) e
**Linguistics/Grammar** (duas implementações corretas do mesmo contrato produzindo
comportamentos incompatíveis).
