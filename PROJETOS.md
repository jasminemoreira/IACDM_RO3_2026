# Os 12 projetos do lote

Congelado no `BATCH-PROTOCOL.md` §2. `taskId` é o nome da pasta E o nome do
projeto no `init_project` — sem variação, ou o pareamento futuro se perde.

> As **lentes esperadas** ficam nesta tabela, fora das pastas dos projetos. É
> predição: se estivesse dentro do workspace, a sessão a leria antes da Fase 2
> declarar as lentes ativas, e a medição ia embora.

| # | taskId | o que é | lentes esperadas | piloto |
|---|---|---|---|---|
| 1 | `T21-certificados` | Monitor de validade de certificados com renovação antecipada e registro de quem aprovou cada emissão | RES · CTR · OBS · GOV | sim |
| 2 | `T22-plantoes` | Distribuidor de plantões com restrições, trocas entre pessoas e aprovação | ETI · PRO · JOG · GOV · UX |  |
| 3 | `T23-canario` | Coordenador de implantação canário com rollback automático por métrica, convivendo com a versão estável | CTR · RES · OBS · MIG · PRO |  |
| 4 | `T24-catalogo` | Catálogo de dados com donos declarados por domínio e linhagem entre eles | GOV · LIN · MEC | sim |
| 5 | `T25-orcamento` | Painel de consumo com teto de orçamento e corte automático ao atingir o limite | SUS · OBS · CTR · UX |  |
| 6 | `T26-extratos` | Importador de extratos de múltiplas fontes externas, com deduplicação e conciliação | LIN · RES · SUS · MIG |  |
| 7 | `T27-despesas` | Fila de aprovação de despesas com alçadas por valor e delegação temporária | PRO · GOV · JOG · UX |  |
| 8 | `T28-agenda` | Sincronizador entre dois calendários externos, com detecção e resolução de conflito | RES · LIN · CTR · PRO |  |
| 9 | `T29-retencao` | Compactador de séries temporais com política de retenção e troca do formato de armazenamento | SUS · MIG · MEC · LIN |  |
| 10 | `T30-notifica` | Serviço de notificação com preferências por pessoa, supressão e canais externos | RES · PRO · UX · ETI · OBS · SUS |  |
| 11 | `T31-precos` | Motor de regras de preço com faixas, histórico e explicação da decisão, substituindo uma tabela legada | ETI · GOV · MEC · LIN · MIG |  |
| 12 | `T32-triagem` | Triagem de chamados com prioridade automática, reclassificação e recurso do solicitante | ETI · CTR · PRO · UX · MEC · JOG |  |

## Descartados

| taskId | data | motivo |
|---|---|---|
| `ciclo 1 — 7 projetos` | 2026-08-08 | T01, T13, T05, T14, T15, T02, T03. Descarte integral para que os doze rodem sob instrumento único — ver _lote-1-descartado/MOTIVO.md |
| `T21-quotas` | 2026-08-09 | coluna `lente` da matriz sem validação — 4 achados com nome abreviado. Corrigido na v0.14.0; slot reaproveitado pela 2ª vez |
| `T21-cofre` | 2026-08-08 | reset do laço 2↔3 era assimétrico: os critérios da Fase 3 sobreviviam à volta, e o gate 3→4 passou com o carimbo da iteração 1. Corrigido na v0.13.1; slot reaproveitado com enunciado novo |

O piloto (§6) é T21 e T24, que exercitam grupos de lentes disjuntos. O objetivo
dele não é dado: é descobrir se o formato do achado sobrevive ao uso real.
Depois do piloto, os dez restantes em qualquer ordem.

Estado de cada projeto: `python3 analise/preparar.py estado`
