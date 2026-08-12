# RETRABALHO — T23-canario

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-10** |

CA-0, UC-1 a UC-4 e VAL-1 a VAL-12, congelados na Fase 0 antes de codar, verificados na
Fase 6: **62 testes verdes** (pytest), incluindo a superfície de CLI exercida por
`subprocess`. Veredito da Fase 7: *"Atende — CA-0 satisfeito"*, com o critério de acerto
objetivo **verificado por mão humana**: com a mesma configuração de limiares, UC-2 reverte
e UC-3 não reverte.

Duas limitações permanecem como dívida declarada, nunca mascarada: **VAL-6** (separar
latência p99 de sucesso da de falha) cumprida só nominalmente, porque o substrato simulado
não modela requisições individuais; e os limiares da guarda absoluta.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### O achado mais importante: teste de mutação revelou cobertura falsa

**A defesa contra REG-01 nunca discriminou nada, e 62 testes verdes não notaram.**

Com `tamanho_janela == amostra_minima == 50` e a janela implementada como
`deque(maxlen=50)`, a contagem por série é limitada superiormente a 50. Logo `pronta()` —
que exige ≥50 em canário **e** baseline — só é verdadeira quando as duas séries têm
exatamente 50 pontos, e nesse caso a razão min/max é sempre 1,0. **`volumes_comparaveis`
jamais retorna falso na configuração padrão.**

REG-01 é o achado de "canário sem tráfego promovido por vacuidade". A correção existia, o
teste existia, o teste passava — e a condição que ele deveria exercer era inalcançável.

Quem descobriu não foi a suíte: foi o **teste de mutação**. É a diferença entre uma suíte
verde e uma suíte capaz de reprovar, e aqui ela apareceu com consequência concreta.

Registrado também o poder medido: inverter a cauda do Mann-Whitney derruba **14** testes;
desligar a checagem de volumes comparáveis derruba **2**. O segundo número é justamente o
sintoma — dois testes para uma defesa central.

### Um achado da Fase 2 ressurgindo por outra porta

UC-4 revertia por falha em vez de tolerar o coletor fora. Causa: quando a coleta não
produz amostras, a janela deslizante mantém as **amostras antigas** e `pronta()` segue
verdadeira, então o coordenador rejulga exatamente os mesmos dados. O veredito se repete
idêntico, e o contador de falhas — que **pressupõe julgamentos independentes** — soma três
reprovações do mesmo julgamento e dispara rollback.

O registro nomeia o que isso é: *"o achado CTL-03 ressurgindo por outra porta"*. A crítica
da Fase 2 estava certa, a correção da Fase 3 fechou um caminho, e o mesmo defeito voltou
por outro. Mesma classe do D-01 do T22 — **correção que cobre parte do que o achado
implica**, agora em dois projetos.

### `specs/datasets` vazio, encontrado em modo generativo

A revisão adversarial de escopo da Fase 5 achou que `specs/datasets` estava vazio, embora
o Production Capacity Check da Fase 0 o listasse como ativo requerido. O operador escolheu
**fechar as lacunas** em vez de renegociar escopo ou aceitar débito. Fechado com
`gerar_datasets.py` depositando uc1..uc4 mais índice, determinísticos por semente.

### Procedência do teste manual — a mais forte dos quatro

Executado **pelo operador, não simulado pelo agente**, com resultado *"Tudo conforme o
esperado"*. E rendeu: fechou **VAL-12**, que estava marcada como 🟡 não exercida — Ctrl+C
encerrou em REVERTIDO com motivo de aborto do operador. Confirmou também que UC-4
apresenta a queda do coletor como **erro de coleta** e não como falha do canário, e que a
guarda absoluta reverteu em t=10 com zero julgamentos.

| projeto | quem executou | quem julgou | resultado |
|---|---|---|---|
| T21-certificados | agente | operador | perguntas de julgamento em aberto |
| T24-catalogo | operador | operador | human-AV pleno |
| T22-plantoes | agente | operador | agente recusou carimbar o gate |
| **T23-canario** | **operador** | **operador** | **fechou um critério que a suíte não exercia** |
