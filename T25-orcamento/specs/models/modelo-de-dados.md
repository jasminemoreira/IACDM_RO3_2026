# Modelo de dados — T25

Deriva de `../technical/architecture.md` V(1). Nomes de tabela e coluna seguem o
glossário (`../domain/glossario.md`); sinônimos proibidos ali também são proibidos aqui.

---

## 1. Representação de dinheiro — decisão derivada, com aritmética

**Nunca ponto flutuante.** Precedente: a própria API da Anthropic exige valores
monetários como **string inteira em unidades menores** justamente "para que nenhum
arredondamento de ponto flutuante seja aplicado" (`../technical/rate-card-llm.md` §4).

Mas **centavos são grosseiros demais para este domínio.** Verificação:

| Modelo | Preço de entrada | Por token | 1.000 tokens |
|---|---|---|---|
| Opus 5 | US$ 5,00 / 1M | US$ 0,000005 | US$ 0,005 = **meio centavo** |
| Haiku 4.5 | US$ 1,00 / 1M | US$ 0,000001 | US$ 0,001 = **um décimo de centavo** |

Guardar em centavos truncaria requisições inteiras para **zero** — o consumo real
desapareceria da contabilidade e o teto nunca seria atingido. Este é o modo de falha
silencioso mais perigoso do sistema.

**Unidade adotada: NANO-unidade monetária (10⁻⁹), inteiro de 64 bits.**

Verificação de exatidão — todo preço e todo multiplicador vigente resulta em inteiro:

| Caso | Cálculo | Nano por token | Inteiro? |
|---|---|---|---|
| Opus 5, entrada não-cacheada | 5 / 1e6 × 1e9 | 5.000 | ✅ |
| Opus 5, leitura de cache (×0,1) | 5.000 × 0,1 | 500 | ✅ |
| Opus 5, escrita de cache 5min (×1,25) | 5.000 × 1,25 | 6.250 | ✅ |
| Opus 5, escrita de cache 1h (×2) | 5.000 × 2 | 10.000 | ✅ |
| Sonnet 5 promocional, leitura de cache | 2.000 × 0,1 | 200 | ✅ |
| Haiku 4.5, leitura de cache | 1.000 × 0,1 | 100 | ✅ |
| Batch (×0,5) sobre qualquer um acima | — | inteiro | ✅ |

Nenhum caso da rate card vigente produz fração. Um inteiro de 64 bits com sinal
comporta ~9,2 × 10¹⁸ nano = **~9,2 bilhões de unidades monetárias** — folga absurda.

**Regra:** toda aritmética de custo é inteira, em nano. A conversão para moeda com
duas casas acontece **apenas na apresentação** (M-10 painel-web). Espelha o precedente
da Anthropic, que reporta arredondado ao centavo mas compara valores exatos.

---

## 2. Tabelas

### `entidade`
| coluna | tipo | notas |
|---|---|---|
| `id` | TEXT PK | identificador legível, ex. `equipe-busca` |
| `nome` | TEXT | rótulo para o painel |
| `criada_em` | TEXT | ISO 8601 UTC |

### `chave_virtual`
| coluna | tipo | notas |
|---|---|---|
| `hash` | TEXT PK | **hash** da chave, nunca a chave em claro |
| `entidade_id` | TEXT FK | |
| `revogada_em` | TEXT NULL | revogação é marcação, não exclusão (trilha de auditoria) |

### `teto`
| coluna | tipo | notas |
|---|---|---|
| `escopo` | TEXT PK parte 1 | `'global'` ou `'entidade'` |
| `entidade_id` | TEXT PK parte 2 | `''` quando escopo é global |
| `valor_nano` | INTEGER | o teto, em nano-unidades |
| `atualizado_em` | TEXT | |

### `contador` — o par Escrow (O'Neil, 1986)
| coluna | tipo | notas |
|---|---|---|
| `escopo` | TEXT PK parte 1 | `'global'` \| `'entidade'` |
| `entidade_id` | TEXT PK parte 2 | |
| `janela_inicio` | TEXT PK parte 3 | ISO 8601 UTC — **a chave inclui a janela**, então a virada não apaga histórico: cria uma linha nova |
| `confirmado_nano` | INTEGER | custo real já reconciliado |
| `reservado_nano` | INTEGER | reservas em voo, ainda não reconciliadas |

> **A decisão de admissão lê `confirmado_nano + reservado_nano` contra `teto.valor_nano`.**
> Ler apenas `confirmado_nano` é o bug que faz N requisições concorrentes passarem juntas.

### `reserva`
| coluna | tipo | notas |
|---|---|---|
| `id` | TEXT PK | id_reserva; torna `reconciliar` idempotente |
| `entidade_id` | TEXT | |
| `janela_inicio` | TEXT | |
| `valor_nano` | INTEGER | o pior caso reservado |
| `estado` | TEXT | `'aberta'` \| `'reconciliada'` \| `'liberada'` |
| `criada_em` | TEXT | permite detectar **reserva órfã** por idade (política ainda indefinida — vai à Fase 2) |

### `evento_uso`
| coluna | tipo | notas |
|---|---|---|
| `id` | TEXT PK | |
| `entidade_id`, `modelo` | TEXT | |
| `tokens_entrada`, `tokens_cache_leitura`, `tokens_cache_escrita`, `tokens_saida` | INTEGER | **as quatro categorias separadas** — agregá-las perderia a informação de preço |
| `custo_nano` | INTEGER | |
| `stop_reason` | TEXT | política de cobrança depende dele (`refusal` antes da saída não é cobrada) |
| `ocorrido_em` | TEXT | ISO 8601 UTC |

### `rate_card`
| coluna | tipo | notas |
|---|---|---|
| `modelo` | TEXT PK parte 1 | |
| `categoria` | TEXT PK parte 2 | `entrada` \| `cache_leitura` \| `cache_escrita_5m` \| `cache_escrita_1h` \| `saida` |
| `vigente_desde` | TEXT PK parte 3 | ISO 8601 — vigência é chave, não atributo |
| `nano_por_token` | INTEGER | |
| `fonte` | TEXT | **obrigatório** — URL ou referência. Preço sem fonte não entra |

---

## 3. Invariantes de dados (a Fase 2 vai atacá-los)

| # | Invariante |
|---|---|
| I1 | `confirmado_nano ≥ 0` e `reservado_nano ≥ 0` — sempre |
| I2 | Soma dos `valor_nano` das reservas `'aberta'` de um escopo = `reservado_nano` daquele escopo |
| I3 | Reconciliar uma reserva move valor de `reservado` para `confirmado` e o custo real é **≤** o valor reservado |
| I4 | Para toda linha de contador: `confirmado_nano ≤ teto.valor_nano` — **o invariante do critério de acerto** |
| I5 | Toda linha de `rate_card` tem `fonte` não vazia |

I4 é o que o teste de concorrência mede. I2 é o que detecta reserva órfã ou vazamento.
