# Critérios de aceitação e sucesso — T22 distribuidor de plantões

> Fase 0, Nível 5. Escritos ANTES de qualquer código (exigência do ENUNCIADO §2:
> "critério de acerto objetivo, escrito antes de codar"). Cada critério é
> verificável por execução, não por opinião. Alimentam o Mapa de Testes da Fase 6.

## Porte de referência (define "funciona" em números)

| Grandeza | Valor |
|---|---|
| Profissionais | ~30 |
| Plantões por dia | ~3 (turnos × habilitações) |
| Horizonte | 30 dias (mensal) |
| Ordem de grandeza do modelo | ~2.700 variáveis binárias de alocação |

## Critérios de sucesso (SC)

| id | Critério | Como medir | Limiar |
|----|----------|-----------|--------|
| SC-1 | Gera escala viável no porte de referência | executar UC-1 sobre instância de 30×3×30 e validar com UC-5 | **0 violações rígidas** e escala completa |
| SC-2 | Tempo de geração | cronometrar UC-1 no porte de referência | **≤ 60 s** (limite configurável; default 60 s) |
| SC-3 | Determinismo | executar UC-1 3× com a mesma entrada e mesma semente | **saída idêntica** nas 3 execuções |
| SC-4 | Instância inviável falha com diagnóstico | instância fabricada sem cobertura possível | **não grava escala**; código de saída ≠ 0; mensagem nomeia ≥1 restrição e o ponto do conflito (dia/turno/habilitação) |
| SC-5 | Solução sub-ótima é declarada | instância que estoure o limite de tempo | devolve a melhor viável **e informa que não é comprovadamente ótima** |
| SC-6 | Troca válida se efetiva | UC-3 seguido de UC-4 (aceite) sobre par compatível | as duas alocações permutam; UC-5 continua com **0 violações rígidas** |
| SC-7 | Troca ilegal é rejeitada | UC-4 sobre troca que quebraria a interjornada de 11h (L1) | **rejeitada**, escala **inalterada**, mensagem cita a regra violada (artigo da CLT ou id da regra interna) |
| SC-8 | Corrida entre trocas | duas trocas pendentes sobre o mesmo plantão; aceitar a primeira, depois a segunda | a segunda **falha na revalidação** com motivo; escala permanece consistente |
| SC-9 | Emenda entre meses | gerar mês 1, depois mês 2 na sequência | nenhuma violação de L1/L2 **na virada**; contadores de fronteira derivados da escala do mês 1 |
| SC-10 | Rastreabilidade normativa | inspecionar o relatório do UC-5 | **toda** violação exibe a origem (artigo da CLT, id INRC-II ou id de regra interna) e o custo soft total é apresentado |
| SC-11 | Fronteira legal × interna preservada | inspecionar cadastro de restrições | cada restrição carrega `origem ∈ {legal, interna}` e `natureza ∈ {rígida, flexível}` |

## Critérios de aceitação (o que precisa ser verdade para o operador aceitar)

1. Os **5 casos de uso** (UC-1 gerar, UC-2 consultar, UC-3 solicitar troca, UC-4 responder troca, UC-5 relatório de conformidade) executam ponta a ponta pela CLI, sobre dados gerados pelo gerador sintético do próprio projeto.
2. Nenhum parâmetro numérico no código sem fonte citada — cada um rastreia a `specs/references/clt-jornada.md` (L1-L8) ou `specs/references/nrp-inrc2.md` (H1-H4, S1-S7).
3. O operador executa manualmente ao menos um caso de uso completo e confirma o comportamento (Fase 6, gate humano — não substituível por teste automatizado).
4. A suíte automatizada roda verde, com ao menos 1 teste negativo para cada 2 positivos.

## Fora de escopo (YAGNI) — item | razão

| Item | Razão |
|---|---|
| Autenticação, senhas, permissões | Ator único (plantonista) e CLI local; identidade entra por parâmetro. Custo alto, valor nulo no contexto. |
| Interface gráfica, web ou API HTTP | Plataforma decidida como CLI + biblioteca. Somar UI estouraria o orçamento de 8-12 módulos e a sessão. |
| Notificações (e-mail, push) | ⚠️ **Limitação consciente, não esquecimento.** Nos concorrentes (QGenda) a notificação é o que faz o fluxo de troca andar; sem ela, uma troca PENDENTE pode ficar parada indefinidamente. O par precisa consultar ativamente. Registrado como risco aceito. |
| Folha de pagamento / cálculo de remuneração | O adicional noturno (20%) e a hora extra (50%) servem para **classificar e restringir**, nunca para apurar valores. O sistema não é sistema de RH. |
| Papel de gestor / homologação em duplo estágio | Decisão do Nível 3: ator único; aprovação = consentimento do par + revalidação automática. |
| Calendário de feriados dedicado | Feriado é um dia com demanda de cobertura diferente — já expressável na demanda por dia. Módulo próprio seria redundância. |
| Equidade como critério de aceitação | Fairness permanece como termo **soft** com peso publicado (S5/S7 do INRC-II), mas não foi eleita motivação do produto; logo não é critério de aceite. |

## Critérios adicionais (iteração 1 — fechamento das ambiguidades)

| id | Critério | Como medir | Limiar |
|----|----------|-----------|--------|
| SC-12 | Troca expira com o plantão | pendente cujo plantão mais próximo já passou | aceite **recusado**, sem parâmetro de prazo configurável envolvido |
| SC-13 | Degradação flexível é visível | aceitar troca legal que piore o custo | efetiva **e** reporta o delta (`240 → 310, +70`) com os termos que pioraram |
| SC-14 | Ciclo de vida protege as trocas | re-gerar sobre escala publicada com trocas efetivadas | recusa sem flag explícita; com a flag, **avisa quantas trocas serão descartadas** |
| SC-15 | Regime 12×36 não é rejeitado indevidamente | escala 12×36 válida submetida ao UC-5 | **0 violações rígidas** — L1, L2, L4, L6 e L7 **não** aplicadas cumulativamente sobre contrato 12×36 |

## Premissas

| id | Premissa | Estado | Como cai se for falsa |
|----|----------|--------|----------------------|
| PR-1 | Valores da CLT (L1-L8) corretos | ✅ **FECHADA** — conferidos contra `planalto.gov.br` (HTTP 200), transcrição literal em `specs/references/clt-jornada.md` | — |
| PR-2 | CP-SAT resolve 30×3×30 em ≤ 60 s | 🟡 aberta | SC-2 não fecha; relaxar limite ou reduzir porte |
| PR-3 | Sob 12×36, aplicar L1/L2/L4/L6/L7 cumulativamente rejeita escalas legais | ✅ **CONFIRMADA na fonte** (art. 59-A caput e parágrafo único) — deixou de ser premissa e virou requisito, coberto por SC-15 | o motor recusaria escalas válidas e o sintoma pareceria "falta de gente" |
| PR-4 | Fronteira derivável da escala anterior sem ambiguidade | 🟡 aberta | emenda entre meses volta a violar restrições (SC-9 falha) |

---

# Resultados medidos (Fase 7 — fechamento do ciclo v1.0)

Porte de referência: 30 pessoas, 3 plantões/dia, 30 dias (90 plantões,
150 vagas ótimas, ~2.700 variáveis binárias antes da poda).

| id | Critério | Limiar | Obtido | |
|----|----------|--------|--------|---|
| SC-1 | escala viável no porte | 0 violações rígidas | 0 | ✅ |
| SC-2 | tempo de geração | ≤ 60 s | **0,3 s** | ✅ |
| SC-3 | determinismo | saída idêntica em 3 execuções | md5 idêntico | ✅ |
| SC-4 | inviável falha com diagnóstico | nomeia ≥1 restrição e o ponto | "01/09, diurno, cardio: exige 5, apenas 4 elegíveis", exit 3 | ✅ |
| SC-5 | sub-ótimo declarado | avisa que não é comprovadamente ótimo | aviso emitido | ✅ |
| SC-6 | troca válida se efetiva | permuta + 0 rígidas | ✅ | ✅ |
| SC-7 | troca ilegal rejeitada | cita a regra violada | "o regime 12x36 exige 36h ininterruptas (CLT art. 59-A)" | ✅ |
| SC-8 | corrida entre trocas | 2ª falha na revalidação | "a escala mudou desde que esta troca foi criada" | ✅ |
| SC-9 | emenda entre meses | 0 violações na virada | nenhuma das 5 pessoas que fecharam o mês trabalha no dia 1 | ✅ |
| SC-10 | rastreabilidade normativa | toda violação com origem | ✅ | ✅ |
| SC-11 | origem × natureza | INV-2 respeitada | ✅ | ✅ |
| SC-12 | expiração com o plantão | sem parâmetro de prazo | EXPIRADA | ✅ |
| SC-13 | delta de custo visível | delta + termos piorados | "+10, S4" | ✅ |
| SC-14 | re-geração protegida | avisa e preserva | cria `<id>-r1`, anterior intacta | ✅ |
| SC-15 | 12×36 não rejeitado | 0 rígidas | 0 | ✅ |

**15/15 atendidos.** Suíte: 44 testes verdes; poder de detecção verificado por
9 mutações injetadas e 9 detectadas.

## Premissas — estado final

| id | Premissa | Fecho |
|----|----------|-------|
| PR-1 | valores da CLT corretos | ✅ conferidos contra planalto.gov.br, transcrição literal |
| PR-2 | CP-SAT resolve o porte em ≤ 60 s | ✅ **0,3 s** — folga de três ordens de grandeza |
| PR-3 | aplicar as regras cumulativamente sob 12×36 rejeita escalas legais | ⚠️ **PARCIALMENTE FALSA** — vale só para L4; L3 domina L1 e L2. Ver `specs/references/lessons.md` §L1 |
| PR-4 | fronteira derivável sem ambiguidade | ⚠️ **refinada** — a derivação é correta, mas contadores acumulados não podem atravessar horizontes contratuais distintos. Ver §L3 |

## Não verificado (declarado, não omitido)

- Legibilidade das mensagens para um plantonista não-técnico — exige julgamento
  humano; nenhum teste automatizado alcança.
- Adequação dos pesos do INRC-II ao contexto brasileiro (premissa A8) — exigiria
  estudo empírico fora do escopo deste ciclo.
