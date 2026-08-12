# Modelo de domínio — T32-triagem

Domain Model (Fowler) com DDD tático. Entidades com comportamento e
invariantes; objetos de valor sem identidade.

## Objetos de valor

| Tipo | Valores | Invariante |
|---|---|---|
| `Papel` | SOLICITANTE · AGENTE · GESTOR | imutável |
| `Impacto` | ALTO · MEDIO · BAIXO | atribuído pelo agente |
| `Urgencia` | ALTA · MEDIA · BAIXA | declarada pelo solicitante |
| `Prioridade` | P1..P5 | **sem construtor público** — só existe como retorno de `prioridade.derivar` |
| `Categoria` | HARDWARE · SOFTWARE · REDE · ACESSO · OUTRO | rótulo; não roteia, não afeta prioridade |
| `Prazos` | `{reconhecimento: Instante, resolucao: Instante}` | ambos derivados de `abertoEm` |
| `Instante` | ponto no tempo | só obtido via `relogio.agora()` |

## Entidades

### Chamado

```
id · solicitanteId · titulo · descricao
categoria?          (nulo até a triagem)
urgencia            (na abertura, pelo solicitante)
impacto?            (nulo até a triagem)
prioridade?         (nulo até a triagem — derivada, nunca atribuída)
estado              NAO_TRIADO | TRIADO | RECONHECIDO | ENCERRADO
abertoEm · triadoEm? · reconhecidoEm? · encerradoEm?
prazos?             (nulo até a triagem)
```

**Máquina de estados:**

```
NAO_TRIADO ──triar──▶ TRIADO ──reconhecer──▶ RECONHECIDO ──encerrar──▶ ENCERRADO
                        │                          │
                        └────────encerrar──────────┘
                        ▲
             reclassificar (não muda estado)
```

**Invariantes:**
- `prioridade` é nula ⟺ `estado = NAO_TRIADO`.
- `prioridade = matriz(impacto, urgencia)` sempre que não nula. Não há caminho
  de código que atribua prioridade por outra via.
- `prazos = sla.prazos(prioridade, abertoEm)` — sempre a partir de `abertoEm`.
- Toda mudança de `impacto`, `urgencia` ou `categoria` gera evento de trilha,
  **mesmo quando a prioridade resultante não muda** (VAL-4 / B-9).

### Recurso

```
id · chamadoId · autorId
eixosContestados    subconjunto não vazio de {URGENCIA, IMPACTO}
justificativa       obrigatória, não vazia
abertoEm
estado              ABERTO | PROVIDO | PARCIALMENTE_PROVIDO | IMPROVIDO
julgadorId? · julgadoEm? · fundamentacao?
```

Ciclo de vida, guardas de admissibilidade e efeitos: ver
`specs/technical/rito-recurso.md`. Máximo um Recurso por Chamado.

### EventoTrilha (somente-inserção)

```
id · chamadoId · tipo · atorId · instante
antes (json) · depois (json) · motivo · origem
```

`tipo` ∈ {ABERTURA, TRIAGEM, RECLASSIFICACAO, RECURSO_ABERTO,
RECURSO_JULGADO, RECONHECIMENTO, ENCERRAMENTO}.
`origem` ∈ {SOLICITANTE, AGENTE, RECURSO} — distingue uma mudança de eixo
feita pelo agente de uma decorrente de provimento de recurso.

**Nunca atualizada, nunca apagada.** CA-3 depende disso: a soma dos eventos de
mudança de classificação de um chamado deve bater com o número de mudanças
efetivas de prioridade que ele sofreu.

### Usuario

```
id · nome · papel
```

Sem credencial (A8 — identidade declarada, não provada).

## Relacionamentos

```
Usuario 1 ──< Chamado          (solicitante)
Chamado 1 ──0..1 Recurso
Chamado 1 ──< EventoTrilha
Usuario 1 ──< EventoTrilha     (ator)
Usuario 1 ──0..1 Recurso       (autor, sempre = solicitante do chamado)
Usuario 1 ──< Recurso          (julgador, sempre papel GESTOR)
```

## Matriz de autorização (M-08)

| Ação | SOLICITANTE | AGENTE | GESTOR |
|---|---|---|---|
| Abrir chamado | ✅ | ✅ | ✅ |
| Declarar urgência na abertura | ✅ | ✅ | ✅ |
| Triar (categoria + impacto) | ❌ | ✅ | ✅ |
| Reclassificar | ❌ | ✅ | ✅ |
| Reconhecer / encerrar | ❌ | ✅ | ✅ |
| Abrir recurso | ✅ **só do próprio chamado** | ❌ | ❌ |
| Julgar recurso | ❌ | ❌ | ✅ |
| Ver fila | ❌ | ✅ | ✅ |
| Ver o próprio chamado + trilha | ✅ | ✅ | ✅ |

A linha "abrir recurso" é a única com condição sobre o **alvo**, não só sobre
o papel — daí `autorizacao.pode(usuario, acao, alvo)` receber o alvo.
