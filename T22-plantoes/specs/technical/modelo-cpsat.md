# Modelo CP-SAT — formulação técnica

> Fase 1, Passo 0. Depositado ANTES de definir módulos. Toda restrição aqui
> rastreia a `specs/references/nrp-inrc2.md` (H/S) ou
> `specs/references/clt-jornada.md` (L). Nenhum parâmetro inventado.

## 1. A decisão técnica central: catálogo de restrições com DUPLA INTERPRETAÇÃO

O sistema precisa avaliar as mesmas restrições em **dois momentos com naturezas
diferentes**:

| Momento | Contexto | O que precisa da restrição |
|---|---|---|
| **UC-1 gerar** | as alocações são *incógnitas* | expressá-la como **restrição CP-SAT** sobre variáveis booleanas |
| **UC-4 responder troca** e **UC-5 relatório** | as alocações são *fatos* | **verificá-la** sobre uma escala concreta e apontar quem violou |

Escrever a mesma regra duas vezes — uma como modelo, outra como verificador — é o
defeito mais provável deste projeto: as duas cópias divergem, e o sintoma é
*"o gerador produz escala que o relatório acusa de ilegal"*. Uma restrição
implementada duas vezes é duas restrições.

**Decisão:** cada restrição é declarada UMA vez, num catálogo, expondo dois
métodos sobre a mesma definição:

```
Restricao:
    id            # 'L1', 'H3', 'S4', 'INT-01'
    origem        # legal | modelo | interna
    natureza      # rigida | flexivel   ← depende do REGIME DO CONTRATO
    peso          # None se rígida
    fonte         # 'CLT art. 66' | 'INRC-II S4' | id da regra interna

    aplicar(modelo, vars, contexto)   -> None     # modo geração (CP-SAT)
    verificar(escala, contexto)       -> [Violacao]  # modo verificação
```

Consequência de arquitetura: **catálogo de restrições é um módulo**, e os dois
motores (gerador e verificador) são clientes dele — nenhum dos dois é dono das
regras.

## 2. Variáveis de decisão

Instância de plantão: `(data, tipo_de_turno, habilitacao)` com demanda mínima e
ótima. Variável booleana:

```
x[pessoa, plantao] ∈ {0,1}   — 1 sse a pessoa está alocada àquele plantão
```

**Poda por habilitação (H4):** a variável **não é criada** quando a pessoa não
tem a habilitação exigida. H4 deixa de ser restrição e vira ausência de
variável — menos variáveis, e H4 torna-se impossível de violar por construção.
No modo *verificar*, porém, H4 **precisa existir** (uma troca pode alocar alguém
sem a habilitação). Exemplo direto da dupla interpretação da seção 1: a mesma
restrição é estrutural na geração e ativa na verificação.

## 3. Restrições rígidas — codificação

| id | Fonte | Codificação CP-SAT |
|----|-------|--------------------|
| H1 | INRC-II | `AddAtMostOne(x[p, plantao] for plantao in plantoes_do_dia(d))` para cada pessoa e dia |
| H2 | INRC-II | `Add(sum(x[p, plantao] for p in habilitados) >= plantao.demanda_minima)` |
| H3 | INRC-II | para cada par proibido `(t1, t2)`: `Add(x[p, plantao_t1_d] + x[p, plantao_t2_d1] <= 1)` |
| H4 | INRC-II | variável não criada (ver §2) |
| L1 | CLT art. 66 | **compilada em H3** — ver §4 |
| L2 | CLT art. 67 | janela deslizante de 7 dias: `Add(sum(x[p, plantao] for plantao in janela) <= dias_da_janela - 1)` — garante ≥1 dia inteiro livre, que para turnos ≤ 12h contém 24h consecutivas |
| L4 | CLT art. 59 | **não é restrição de alocação — é validação de entrada.** Ver §5 |

### Contadores de fronteira
Restrições que atravessam a borda do horizonte (H3, L1, S2, S3) recebem o estado
derivado do mês anterior como **constante**, não como variável: o último turno
trabalhado e as sequências em curso entram no modelo como se fossem dias -1, -2…
já decididos.

## 4. L1 (interjornada) compila para sucessões proibidas

Como todo tipo de turno tem hora de início e fim fixas, o intervalo entre um
turno no dia `d` e outro no dia `d+1` é **conhecido em tempo de construção do
modelo**:

```
intervalo(t1, t2) = inicio(t2) + 24h − fim(t1)
par (t1, t2) é proibido  ⟺  intervalo(t1, t2) < 11h
```

Exemplo: noturno 19:00–07:00 seguido de diurno 07:00–19:00 → intervalo = 0h →
**proibido** (art. 66). Noturno seguido de noturno → 12h → permitido.

**Ganho:** L1 não precisa de aritmética temporal dentro do solver. Vira uma
tabela de pares proibidos calculada uma vez, e usa exatamente o mesmo mecanismo
de H3. Menos código e um espaço de busca menor.

**Ressalva (AP4):** vale porque os turnos têm horários fixos. Se um dia existir
plantão com horário variável, esta compilação deixa de ser válida e L1 volta a
exigir modelagem temporal. Registrado como premissa da arquitetura.

## 5. L4 é validação de entrada, não restrição de alocação

O art. 59 limita a jornada diária a 8h + 2h extras = **10h**, salvo o regime
12×36 do art. 59-A (exceção expressa ao art. 59).

Logo, um plantão de 12h atribuído a alguém com contrato de **regime comum** é
ilegal *independentemente de qualquer alocação* — a ilegalidade está na
configuração, não na escala. Restringir isso dentro do solver produz
`INFEASIBLE` sem explicação útil.

**Decisão:** o carregador de entrada rejeita a combinação (contrato de regime
comum × tipo de turno com duração > 10h) com mensagem citando o art. 59, antes
de o modelo ser construído. Falha cedo e no lugar certo.

## 6. Natureza das restrições depende do REGIME DO CONTRATO

Sob `regime = 12x36` (art. 59-A):

| Regra | Regime comum | Regime 12×36 |
|---|---|---|
| L1 interjornada 11h | ativa | **satisfeita por construção** (36h de descanso) |
| L2 repouso semanal 24h | ativa | **absorvida** (art. 59-A, § único) |
| L4 limite de 2h extras | ativa (via §5) | **inaplicável** (exceção expressa) |
| L6/L7 noturno | ativa | **compensada** (art. 59-A, § único) |

Isso é o que impede a assinatura `aplicar(modelo, vars)` de ser suficiente: ela
precisa de `contexto`, e o contexto inclui o contrato de cada pessoa. **Uma
restrição legal não tem natureza global — tem natureza por pessoa.**

## 7. Restrições flexíveis — codificação e pesos

Pesos de `specs/references/nrp-inrc2.md` (INRC-II), não arbitrados aqui.

| id | Peso | Codificação |
|----|------|-------------|
| S1 | 30 | var de folga `AddMaxEquality(falta, [otimo − sum(x), 0])`; termo `30 · falta` |
| S2 | 15/30 | var indicadora por janela de consecutividade; 15 por tipo de turno, 30 por dias trabalhados |
| S3 | 30 | idem, sobre sequências de folga |
| S4 | 10 | `10 · x[p, plantao]` para cada plantão marcado como indesejado pela pessoa |
| S5 | 30 | `AddBoolXOr`-equivalente entre sábado e domingo quando o contrato exige fim de semana completo |
| S6 | 20 | desvio absoluto do total de plantões em relação aos limites do contrato, no fim do horizonte |
| S7 | 30 | excedente de fins de semana trabalhados, no fim do horizonte |

```
Objetivo:  Minimize( Σ peso_i · violacoes_i )
```

**Indisponibilidade ≠ preferência.** Preferência é S4 (peso 10, violável).
Indisponibilidade declarada é **rígida** — a variável não é criada, como em H4.
São dois campos distintos na entrada, não um com intensidade.

## 8. Contrato determinístico do solver

```python
solver.parameters.random_seed = 0
solver.parameters.num_search_workers = 1        # multi-thread quebra determinismo
solver.parameters.max_time_in_seconds = <config, default 60>
```

Status devolvidos e o que cada um significa para o produto:

| Status CP-SAT | Significado | Ação |
|---|---|---|
| `OPTIMAL` | ótimo comprovado | grava rascunho |
| `FEASIBLE` | viável, otimalidade não provada (estourou o tempo) | grava rascunho **e avisa** (SC-5) |
| `INFEASIBLE` | não existe escala válida | **não grava**; aciona o diagnóstico (§9) |
| `MODEL_INVALID` / `UNKNOWN` | erro interno | falha com o status bruto |

Empates: com semente fixa e 1 worker, a mesma entrada produz a mesma saída. A
ordem de iteração sobre pessoas e plantões deve ser **explicitamente ordenada**
(por id), nunca dependente de ordem de dicionário — senão o determinismo depende
da ordem de leitura do arquivo.

## 9. Diagnóstico de inviabilidade (Tier 3 — maior risco técnico)

CP-SAT devolve `INFEASIBLE` sem apontar a causa. Duas abordagens, em ordem de
custo:

1. **Verificação estrutural pré-solve (barata, cobre a maioria dos casos reais):**
   para cada plantão, contar quantas pessoas são elegíveis (têm a habilitação,
   não estão indisponíveis, o contrato permite). Se `elegíveis < demanda_mínima`,
   a instância é inviável e a causa é local e nomeável:
   `"dia 14, noturno, cardiologia: exige 2, apenas 1 elegível"`.
2. **Relaxação por camadas (fallback):** re-resolver removendo grupos de
   restrições em ordem de "afrouxabilidade" (primeiro as internas, depois S,
   nunca as legais); o grupo cuja remoção torna o modelo viável é o conflito.
   Custa N solves adicionais.

**Decisão:** implementar (1); (2) só se (1) não explicar o caso. A verificação
estrutural também serve como validação de entrada útil por si só.

## 10. Porte e desempenho esperado

30 pessoas × ~3 plantões/dia × 30 dias ⇒ ~2.700 variáveis booleanas, antes da
poda por habilitação. Está uma ordem de grandeza abaixo das instâncias do
INRC-II (que a literatura resolve em segundos a minutos). **PR-2** (≤60 s)
segue aberta até haver medição — a estimativa é favorável, não é prova.

## 11. Pseudocódigo de S2/S3 — consecutividade com fronteira

> Depositado na Fase 3, iteração 2. Paga a dívida IMP-02, levantada na crítica
> de V(1) e reincidente como IMP-05 na crítica de V(2): a parte mais intrincada
> do modelo tinha apenas o idioma nomeado, o que é convite ao AP7 (implementar
> por intuição).

S2 penaliza sequências de trabalho fora de `[min_dias_consecutivos,
max_dias_consecutivos]`; S3 faz o mesmo para sequências de folga. A dificuldade
não é a janela — é que a sequência **já pode estar em curso** quando o horizonte
começa.

### 11.1 Variável auxiliar por pessoa e dia

```
trabalha[p, d] = OR sobre todos os plantões do dia d
                 → m.AddMaxEquality(trabalha[p,d], [x[p,pl] for pl in plantoes_do_dia(d)])
```

### 11.2 Máximo de dias consecutivos (limite rígido do contrato)

Toda janela de `max+1` dias consecutivos precisa conter ao menos uma folga:

```
para cada pessoa p, para cada d em 0 .. D-(max+1):
    m.Add(sum(trabalha[p, d+i] for i in 0..max) <= max)
```

### 11.3 Fronteira: a sequência herdada entra como dias negativos já decididos

`fronteira[p].dias_trabalhados_consecutivos = k` significa que os dias
`-1, -2, … -k` foram trabalhados. Em vez de criar variáveis para o passado,
encurta-se a primeira janela:

```
k = fronteira[p].dias_trabalhados_consecutivos
se k > 0:
    restante = max - k                      # quantos dias ainda podem ser trabalhados
    se restante <= 0:
        m.Add(trabalha[p, 0] == 0)          # a sequência já esgotou: dia 0 é folga forçada
    senão:
        m.Add(sum(trabalha[p, i] for i in 0..restante) <= restante)
```

O mesmo raciocínio, com o sinal invertido, vale para `folgas_consecutivas` e S3.

### 11.4 Mínimo de dias consecutivos (penalidade flexível)

Uma sequência mais curta que `min` é violação de S2. Detecta-se pelo padrão
folga-trabalho-folga mais curto que o mínimo:

```
para cada janela de tamanho L em 1 .. min-1:
    para cada d:
        # início de sequência: d-1 folga (ou fronteira), d..d+L-1 trabalho, d+L folga
        viol = m.NewBoolVar(f'S2min_{p}_{d}_{L}')
        m.AddBoolAnd([trabalha[p,i] for i in d..d+L-1]
                     + [trabalha[p,d-1].Not(), trabalha[p,d+L].Not()]
                    ).OnlyEnforceIf(viol)
        termos_objetivo.append(15 * viol)      # peso S2 por tipo de turno; 30 por dias trabalhados
```

Nas bordas (`d = 0` e `d+L = D`) o vizinho ausente vem da fronteira, à esquerda,
e é tratado como "sem restrição" à direita — a sequência que continua além do
horizonte será avaliada no mês seguinte, com este mesmo mecanismo.

### 11.5 Por que não usar `AddAutomaton`

CP-SAT tem `AddAutomaton`, que expressa padrões de sequência com um autômato
finito e é a codificação canônica para consecutividade. Foi considerada e
**descartada por KISS**: exige construir a tabela de transições e mapear o
estado inicial a partir da fronteira, o que troca aritmética simples e legível
por uma estrutura que ninguém revisa com confiança numa sessão. Se S2/S3 vierem
a ser gargalo medido na Fase 6, `AddAutomaton` é o próximo passo documentado —
não antes.
