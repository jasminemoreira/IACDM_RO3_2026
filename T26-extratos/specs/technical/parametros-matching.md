# Parâmetros numéricos de matching — com fonte

Antídoto ao **AP7** (codar sem referência). Toda constante usada por dedup ou conciliação
aparece aqui com origem. Constante sem linha nesta tabela **não entra no código**.
Fontes completas em `specs/references/fontes-externas.md`.

## Tabela de parâmetros

| # | Parâmetro | Valor default | Origem | Status |
|---|---|---|---|---|
| P1 | Janela de data para casar transação × lançamento | ± 3 dias corridos | Regra ilustrativa da literatura de conciliação ("valor dentro de US$ 0,50 e data dentro de 3 dias") — [Entries](https://www.tryentries.com/blog/bank-reconciliation-exceptions-framework) | **Configurável**. Default documentado, não constante mágica. |
| P2 | Tolerância de valor para "casado-com-divergência" | `Decimal("0.00")` (exato) por default; tolerância opcional configurável | Extrapolação do exemplo de US$ 0,50; **não há padrão peer-reviewed**. Casar valores diferentes por default esconde erro contábil. | **Default = exato.** Divergência de valor só com opção explícita. |
| P3 | Limiar de auto-conciliação (alta confiança) | score ≥ 95 | Faixa de prática de mercado: 95-100 auto-concilia sem revisão — [Optimus](https://optimus.tech/blog/fuzzy-matching-algorithms-in-bank-reconciliation-when-exact-match-fails) | Prática de fornecedor, não peer-reviewed. Configurável. |
| P4 | Limiar inferior de revisão humana | 70 ≤ score < 95 → fila de pendências | Mesmas faixas: 85-94 auto com amostragem, 70-84 revisor humano | Neste projeto as faixas 85-94 e 70-84 são **fundidas em revisão humana** — decisão conservadora coerente com o invariante I5/I6 (0 falso-positivo exigido). |
| P5 | Corte de não-candidato | score < 70 → não casa, vira órfão | [Optimus](https://optimus.tech/blog/fuzzy-matching-algorithms-in-bank-reconciliation-when-exact-match-fails) | Configurável. |
| P6 | Algoritmo de similaridade de descrição | Jaro-Winkler (nomes curtos de contraparte) ou Levenshtein normalizado | Algoritmos nomeados na literatura de conciliação | Escolha final e biblioteca a decidir na Fase 1. |
| P7 | Chave de blocking (obrigatória antes de comparação par-a-par) | disjunção de: (a) `(abs(valor) exato, bucket de data ±P1)`; (b) `(valor arredondado, contraparte normalizada)` | Blocking descarta pares que não concordam na chave — [arXiv:1603.07816](https://arxiv.org/abs/1603.07816); prática de conciliação recomenda blocking por faixa de valor/janela de data antes do difuso caro | Necessário para o requisito de desempenho (ver §Orçamento). |
| P8 | Escala decimal monetária | `Decimal`, 2 casas, `ROUND_HALF_UP` | Invariante I1 do glossário; `ofxtools` já entrega `Decimal` | Vinculante. |
| P9 | Proporção esperada de não-casados que são diferença de tempo | 40-60% | [Entries](https://www.tryentries.com/blog/bank-reconciliation-exceptions-framework) | Não é parâmetro de execução: é **expectativa de calibração** do relatório e do dataset de teste. |

## Orçamento de desempenho (requisito: 50.000 transações em < 60s)

Comparação de todos os pares é `O(n²)`:

```
50.000² / 2 ≈ 1,25 × 10⁹ pares
```

Inviável em Python em 60s. Com blocking (P7), o custo cai para
`O(n · b)` onde `b` é o tamanho médio do bloco. Alvo de projeto: **b ≤ 50**, ou seja
`50.000 × 50 = 2,5 × 10⁶` comparações — ordem de grandeza tratável.

**Consequência vinculante:** blocking não é otimização; é requisito de corretude do orçamento.
A Fase 1 deve alocar isso a um módulo nomeado, e a Fase 2 (lente Performance) deve verificar o
caso patológico: **um bloco degenerado** (ex.: milhares de transações de mesmo valor redondo,
como tarifas de R$ 30,00) reintroduz o `O(n²)` dentro do bloco.

## Precedência de identidade no dedup (camadas)

Ordem de decisão, da evidência mais forte para a mais fraca:

**Revisada em V(3) e realinhada à implementação na Fase 5.** As camadas L1 e L2 da formulação
original — `(instituição, conta, FITID)` e hash canônico — **colapsaram numa só**, porque a
`ChaveNatural` introduzida por R4 já é o identificador nativo quando ele existe e a chave natural
com ordinal quando não existe. Manter duas camadas para o que virou um teste único seria a spec
descrevendo um sistema que não é o construído.

| Camada | Evidência | Decisão | Justificativa |
|---|---|---|---|
| L0 | Resolução humana gravada para o par | vincula, sem reavaliar | Invariante I7 |
| L1 | `ChaveNatural` idêntica — FITID quando existe, senão `(data, valor, descrição bruta, ordinal)` | duplicata determinística | Garantida pelo UNIQUE do `store`, não por código. Cobre reimportação do mesmo arquivo e do mesmo período |
| L2 | Mesma origem `(fonte, conta, arquivo)` com chaves distintas | **distintas — veto** | I6: se a instituição imprimiu duas linhas, houve dois eventos. É o que preserva a colisão legítima, e nenhuma rubrica sobre atributos consegue fazê-lo |
| L3 | Score ≥ P3 (95) | duplicata | Rubrica determinística de `rubrica-score.md` |
| L4 | P5 ≤ score < P3, **ou excedente de bloco** | **pendência** (não decide) | I5 e VAL-2. O excedente entra aqui por PRF-06: nunca é declarado distinto sem revisão |
| L5 | score < P5 (70) | transações distintas | — |

**A armadilha original deixou de existir.** A formulação anterior assumia FITID estável entre
downloads — premissa A1, com contra-evidência documentada. Em V(3) o FITID é apenas *uma das formas*
da `ChaveNatural`: se a instituição o alterar, o caso desce para L3/L4 e é avaliado ou revisado, em
vez de escapar. O piso de evidência forte garante que valor e data coincidentes nunca caiam em L5.

---

## Decisões finais e o que foi descartado — Fase 7

| Decisão | Resultado | Por quê |
|---|---|---|
| Estimação de m/u (Fellegi-Sunter) | **DESCARTADA** | Calibrar contra ground truth sintético desenhado pelo próprio projeto é validação circular (SCI-06). Substituída por rubrica determinística e auditável. A formulação matemática segue em `references/` como fundamentação do desenho |
| Casamento ótimo global (húngaro) | **DESCARTADO** | O(n³) inviabiliza VAL-4 mesmo com blocking (PRF-04). Guloso estável com desempate declarado é reproduzível e explicável ao analista, que é o que a auditoria contábil pede |
| Refino de chave para caber no teto de bloco | **DESCARTADO** | Trocaria falso negativo por desempenho. O excedente vira pendência (PRF-06) — corretude vence desempenho, precedência declarada em V(3) |
| Detecção automática de layout CSV | **DESCARTADA** já na Fase 0 | Heurística para problema com solução determinística conhecida (perfil declarado) — sinal de alarme do S6 |
| Hash canônico como identidade da observação | **DESCARTADO** em V(3) | Confundia identidade da linha com identidade do evento; gerava a contradição I6↔I8. Substituído por `ChaveNatural` com ordinal |
| Chave de bloco única | **DESCARTADA** na Fase 5 | Impedia estruturalmente o cross-source entre contas. Substituída por indexação por disjunção, que a pesquisa da Fase 0 já documentava |

### Valores efetivos ao fim do ciclo

`TETO_BLOCO=50` · `CORTE_FUSAO=95` · `CORTE_REVISAO=70` · `SIM_ALTA=90` · `SIM_MEDIA=70` ·
`PISO_EVIDENCIA_FORTE=70` · janelas `pix=0, ted=1, boleto=1, cartao=32, desconhecido=3` ·
`Escopo.janela_dias=90` · tolerância de valor default `Decimal("0")`.

Todos gravados pelo `audit-log` em cada execução e impressos no cabeçalho do relatório, de modo que
alterar um limiar não reclassifique o histórico em silêncio (CTL-02, REG-03).
