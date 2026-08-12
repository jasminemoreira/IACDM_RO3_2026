# Implementações de referência (S6 Tier 2 — portar, não inventar)

Trechos e formatos extraídos de documentação verificada. Na Fase 5 estes são para
**portar literalmente**, mantendo estrutura e nomes. Fonte de cada item em
`../references/fontes.md`.

---

## 1. Ler o consumo real da resposta (F1, F2)

O SDK Python expõe os quatro campos diretamente. **Os quatro são necessários** — usar
só `input_tokens` subestima o consumo (ver `../technical/token-accounting.md` §1).

```python
u = response.usage
u.input_tokens                  # entrada não-cacheada  (preço cheio)
u.cache_read_input_tokens       # leitura de cache      (~0,1×)
u.cache_creation_input_tokens   # escrita de cache      (1,25× ou 2×)
u.output_tokens                 # saída                 (preço de saída)

# prompt total = input + cache_creation + cache_read   (NÃO é só input_tokens)
```

## 2. Fórmula de custo (F2 — portar exatamente)

```
custo_nano = tokens_entrada        × nano(modelo, 'entrada')
           + tokens_cache_leitura  × nano(modelo, 'cache_leitura')
           + tokens_cache_escrita  × nano(modelo, 'cache_escrita_5m' | '_1h')
           + tokens_saida          × nano(modelo, 'saida')
```

Aritmética **inteira em nano** (justificativa em `../models/modelo-de-dados.md` §1).
Sem divisão intermediária: multiplicar tokens por nano-por-token e somar.

## 3. Reserva de pior caso, antes da chamada (derivado de F3 + A1)

```
pior_caso_nano = tokens_entrada_contados × nano(modelo, 'entrada')
               + max_tokens              × nano(modelo, 'saida')
```

`max_tokens` é limite **rígido** imposto pela API — é o que torna a reserva finita.
`tokens_entrada_contados` vem de `client.messages.count_tokens(model=..., messages=...)`,
que é **específico do modelo**. Se a contagem prévia for descartada por custo de
latência, usar 0 nesse termo: a reserva fica menor mas continua limitada por `max_tokens`.

⚠️ **Nunca usar `tiktoken` ou qualquer tokenizador de terceiro** — subestima tokens
Claude em 15–20% em texto comum e muito mais em código (F3, textual).

## 4. Seção crítica: reservar (padrão Escrow, O'Neil 1986 — F9)

Estrutura obrigatória. **Nenhum `await` de rede dentro do bloco.**

```python
# M-03 escrow.reservar
with persistencia.transacao() as tx:          # transação cobre AMBOS os contadores
    for escopo in (GLOBAL, entidade):
        c = tx.contadores.ler(escopo, janela)
        t = tx.tetos.ler(escopo)
        if c.confirmado_nano + c.reservado_nano + valor_nano > t.valor_nano:
            return Decisao(permitido=False, motivo=f"teto {escopo} esgotado")
    # só chega aqui se AMBOS couberem — o mais restritivo vence
    id_reserva = novo_id()
    for escopo in (GLOBAL, entidade):
        tx.contadores.somar_reservado(escopo, janela, +valor_nano)
    tx.reservas.criar(id_reserva, entidade, janela, valor_nano, estado="aberta")
    return Decisao(permitido=True, id_reserva=id_reserva)

# A chamada ao provedor acontece DEPOIS, fora desta transação. Essa é
# a motivação original do método Escrow: a transação é longa e não pode bloquear.
```

## 5. Reconciliação idempotente

```python
# M-03 escrow.reconciliar
with persistencia.transacao() as tx:
    r = tx.reservas.ler(id_reserva)
    if r is None or r.estado != "aberta":
        return                                  # idempotente: já aplicada, não debita de novo
    for escopo in (GLOBAL, r.entidade_id):
        tx.contadores.somar_reservado(escopo, r.janela_inicio, -r.valor_nano)
        tx.contadores.somar_confirmado(escopo, r.janela_inicio, +custo_real_nano)
    tx.reservas.marcar(id_reserva, "reconciliada")
```

`custo_real_nano ≤ r.valor_nano` sempre (invariante I3): a reserva é o pior caso.

## 6. Capturar `usage` em streaming (F1)

Em `stream=True`, o `usage` com `output_tokens` chega no evento **`message_delta`**, ao
final. A reserva permanece aberta durante toda a geração.

```python
with client.messages.stream(model=..., max_tokens=..., messages=...) as stream:
    for event in stream:
        ...                                  # repassa deltas ao cliente
    final = stream.get_final_message()       # usage completo aqui
```

## 7. Política de cobrança por `stop_reason` (F4)

| `stop_reason` | Ação de contabilidade |
|---|---|
| `end_turn`, `max_tokens`, `pause_turn` | cobrar normalmente pelo `usage` retornado |
| `refusal` **antes de qualquer saída** | **não cobrar** — nem entrada nem saída; liberar a reserva integralmente |
| `refusal` **no meio do stream** | cobrar o parcial já transmitido |
| erro de rede / timeout | nenhum `usage` — a reserva fica **órfã** (política indefinida, Fase 2) |

## 8. Transação em `sqlite3` (biblioteca padrão)

O módulo `sqlite3` da stdlib faz commit/rollback via context manager na conexão.
Detalhe que importa: o nível de isolamento e o modo de journal determinam se a
sequência ler-decidir-escrever está protegida contra *lost update* — premissa **A7,
explicitamente não verificada** (`../technical/architecture.md`). Validar na Fase 6
com o teste do critério de acerto, não presumir.
