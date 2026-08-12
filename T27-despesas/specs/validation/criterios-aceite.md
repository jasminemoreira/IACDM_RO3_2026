# Critérios de aceite (CA) — T27

Escritos na Fase 0, **antes de qualquer código** (exigência do `ENUNCIADO.md` §2: o
critério de acerto objetivo é o que torna o retrabalho mensurável). CA-1 a CA-10 são
verificáveis por teste automatizado; CA-11 exige execução humana (Fase 6, gate
`manual_testing` / `ui_runnable`).

| id | Critério verificável | Invariante(s) | Tipo |
|---|---|---|---|
| CA-1 | **(reescrito na Fase 3, iteração 3, com aprovação do operador)** Despesa percorre **exatamente os níveis da cadeia que têm decisor**, e cada nível pulado por falta de decisor aparece na trilha como `NIVEL_PULADO` com o motivo. Verificado para cadeia de 1, 2 e 3 níveis, todos com decisor. *Texto anterior ("exatamente N aprovações") tornou-se inverificável quando V(3) introduziu a regra do pulo — achado IMP-08* | INV-1 | automatizado |
| CA-1b | Cadeia com um nível intermediário **sem decisor**: a despesa é aprovada com uma aprovação a menos, e a trilha contém o `NIVEL_PULADO` correspondente com o motivo | INV-1, INV-18 | automatizado |
| CA-1c | Cadeia em que **nenhum** nível tem decisor: a criação é recusada. Nenhuma despesa chega a APROVADA sem pelo menos uma aprovação humana registrada | INV-17, INV-18 | automatizado |
| CA-2 | Valor **exatamente igual** ao limite do papel encerra naquele papel (fronteira inclusiva) | INV-1 | automatizado |
| CA-3 | Com delegação ativa A→B, o item aparece na bandeja de **B** e **não** na de A. **Exceção (aprovada pelo operador na Fase 3, iteração 2):** quando B é inelegível para um item específico por INV-2 (é o solicitante) ou INV-4 (já decidiu outro nível da mesma cadeia), aquele item **permanece com A** — a delegação é caminho adicional, não transferência de posse. Sem a exceção, o item ficaria órfão (achado PROC-06) | INV-2, INV-4 | automatizado |
| CA-3b | A exceção de CA-3 é verificada por teste próprio: delegação ativa A→B + B inelegível para o item ⇒ o item está na bandeja de A e não na de B | INV-2, INV-4 | automatizado |
| CA-4 | Decisão de B registra ator efetivo=B, em nome de=A e **o limite de A** como autoridade exercida | INV-7 | automatizado |
| CA-5 | Ao expirar **ou** ser revogada a delegação, o item pendente retorna à bandeja de A; decisões tomadas dentro da vigência permanecem válidas | INV-6 | automatizado |
| CA-6 | Cada uma das 4 invariantes SoD bloqueia a ação com **mensagem específica** (auto-aprovação, redelegação, duplo voto na cadeia, vigências sobrepostas) | INV-2, INV-3, INV-4, INV-5 | automatizado |
| CA-7 | Despesa acima do maior limite da hierarquia é recusada **na criação** | INV-10 | automatizado |
| CA-8 | Rejeição sem motivo é recusada; rejeição com motivo encerra a despesa como REJEITADA e ela não retorna à fila | INV-9, INV-11 | automatizado |
| CA-9 | A trilha de auditoria de uma despesa recupera a sequência **completa** de transições, e nenhum registro anterior é alterado | INV-8 | automatizado |
| CA-10 | Estado sobrevive ao restart do processo (mesma bandeja, mesma trilha) | — | automatizado |
| CA-11 👤 | Um humano executa os casos de uso principais de ponta a ponta na UI e confirma que funcionam | todas | **manual** |

## Regras de contagem de teste (Fase 6)

- Cada caso de uso da Fase 0 → **pelo menos 1 positivo + 1 negativo**.
- Razão mínima: 1 teste negativo para cada 2 positivos.
- Um teste só cobre um CA se verificar o **critério exato**. Exemplos de falsa cobertura
  neste projeto:
  - CA-2 verificado com valor abaixo do limite → **não** cobre a fronteira.
  - CA-5 verificado só com revogação → **não** cobre expiração por tempo (precisa avançar
    o relógio injetável).
  - CA-6 verificado com "lançou erro" genérico → **não** cobre "mensagem específica"; são
    4 mensagens distintas.
  - CA-9 verificado só lendo a trilha → **não** cobre imutabilidade; precisa tentar alterar.

## Aritmética monetária

Todo valor é **inteiro de centavos** (BRL). Nenhuma comparação de alçada usa ponto
flutuante (INV-12). Testes de fronteira (CA-2) usam o limite exato em centavos.

---

## Resultados obtidos (Fase 7)

Suíte: Vitest 3, 4 arquivos, **43 testes, 43 passando**, 100 asserções, ~500 ms.
`tsc --noEmit` limpo. `npm audit`: 0 vulnerabilidades.

| Critério | Esperado | Obtido | |
|---|---|---|---|
| CA-1 | cadeia percorrida só nos níveis com decisor | cadeias de 1, 2 e 3 níveis; níveis [2,3] na trilha para R$80k | ✅ |
| CA-1b | nível sem decisor pulado + `NIVEL_PULADO` na trilha | pulo do nível 2 registrado com motivo "nenhum titular do papel Gerente" | ✅ |
| CA-1c | criação recusada se nenhum nível tem decisor | `SEM_DECISOR`, transação revertida, zero despesas | ✅ |
| CA-2 | `valor ≤ limite` encerra no papel | R$50.000,00 exatos encerram no Gerente; 5.000.001 escala | ✅ |
| CA-3 | item vai para B e sai de A | confirmado; o outro Gerente que não delegou continua vendo | ✅ |
| CA-3b | delegado inelegível mantém item com A | confirmado — fecha PROC-06 | ✅ |
| CA-4 | ator, em-nome-de, limite e delegação | ator=bruno, emNomeDe=carla, limite=5.000.000, `delegacaoId` gravado | ✅ |
| CA-5 | expiração/revogação devolvem; decisão permanece | após +30 dias a decisão de bruno segue válida na trilha | ✅ |
| CA-6 | 4 invariantes, 4 mensagens distintas | `AUTO_APROVACAO`, `DUPLO_VOTO`, `REDELEGACAO`, `VIGENCIAS_SOBREPOSTAS` — Set exato | ✅ |
| CA-7 | recusa na criação | teto e topo, ambos com zero despesas criadas | ✅ |
| CA-8 | motivo obrigatório, rejeição terminal | ausente das 6 bandejas; reabertura recusada com `CONFLITO` | ✅ |
| CA-9 | trilha completa e imutável | ordem correta; evento anterior byte-a-byte inalterado; repo sem UPDATE/DELETE | ✅ |
| CA-10 | sobrevive ao restart | banco em arquivo, fechar/reabrir, mesma bandeja e trilha | ✅ |
| CA-11 👤 | humano executa na UI | operador executou UC-1→UC-2 até APROVADA e, no exploratório, reportou "me parece tudo ok" | ✅ |

**Anti-vacuidade (contra AP1):** duas mutações deliberadas foram injetadas e **detectadas** —
inverter a fronteira de INV-1 quebrou CA-2/D-3; desligar INV-4 quebrou D-13 e o teste das
quatro mensagens. Restaurado o código, 43/43 voltaram ao verde. A suíte não é verde por vazio.

**Não coberto, declarado:** layout visual e legibilidade das mensagens (é o que o gate humano
cobre); RES-01 (banco corrompido, sem permissão, disco cheio) — exigiria simular falha de
sistema de arquivos. Concorrência verificada em sequência, não em paralelo: com
`better-sqlite3` síncrono em processo único (premissa A4), o caso paralelo é inatingível.

**Ressalva sobre o gate manual:** a confirmação do operador nesta rodada foi **global** sobre
os sete cenários, não item a item. O que está registrado é "não encontrou nada errado no
conjunto", não "cada borda foi validada individualmente".
