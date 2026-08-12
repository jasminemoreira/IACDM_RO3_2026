# Telas — módulo M-12 `ui-web`

**7 telas** (V(3)), renderizadas no servidor. Sem cadeia de build, sem SPA.
Em V(3) `ui-web` é camada **pura de renderização**: recebe dados e devolve
HTML, sem rota própria e sem dependência de módulo algum. Quem roteia é
`api-http`, a porta única.

Motor de template com **escape automático** por padrão (SEG-02) — o texto
livre de justificativa e fundamentação aparece em quatro das sete telas.

## T-0 — Entrada / seleção de usuário (V(3), UX-06)

```
┌────────────────────────────────────────────┐
│ Entrar                                     │
├────────────────────────────────────────────┤
│ Usuário  ( ) Ana    solicitante            │
│          ( ) Bruno  solicitante            │
│          ( ) Carla  agente                 │
│          ( ) Diego  agente                 │
│          ( ) Elena  gestora                │
│                                 [ Entrar ] │
└────────────────────────────────────────────┘
```

Estabelece o cookie de sessão assinado que carrega o papel (mitigação de
SEG-01). **Não há senha** — a identidade é declarada, não provada (A8), e o
risco está aceito e registrado. O que o cookie assinado elimina é a forja
trivial do papel a cada requisição, não a ausência de autenticação.

O papel vigente aparece na barra de toda tela, não só num seletor de canto
(UX-04).

## T-1 — Abrir chamado (UC-1) · papel SOLICITANTE

```
┌────────────────────────────────────────────┐
│ Novo chamado                    [Ana ▾]    │
├────────────────────────────────────────────┤
│ Título      [________________________]     │
│ Descrição   [                        ]     │
│             [                        ]     │
│ Urgência    ( ) Alta  (•) Média  ( ) Baixa │
│             ↳ texto da definição do nível  │
│                                            │
│                          [ Abrir chamado ] │
└────────────────────────────────────────────┘
```

Não há campo de impacto, categoria nem prioridade — o solicitante não os
declara. As definições dos três níveis de urgência (de `specs/technical`)
aparecem junto às opções: o solicitante só declara bem se souber o que os
níveis significam.

## T-2 — Fila (UC-5) · papéis AGENTE, GESTOR

```
┌──────────────────────────────────────────────────────────┐
│ Fila                        Categoria: [Todas ▾] [Carla ▾]│
├────┬──────────────────────┬─────┬────────────┬───────────┤
│ P  │ Chamado              │ Cat │ Resolver até│ Situação │
├────┼──────────────────────┼─────┼────────────┼───────────┤
│ P1 │ ERP fora do ar       │ SW  │ há 2 h     │ ⚠ VIOLADO │
│ P2 │ VPN instável         │ REDE│ em 5 h     │ ok        │
│ —  │ Teclado quebrado     │ —   │ —          │ não triado│
└────┴──────────────────────┴─────┴────────────┴───────────┘
```

**Ordenação em V(3) (MOV-10) — duas seções, nunca uma coluna só.**
Triados: violado primeiro, depois prioridade, depois prazo de resolução.
Não triados: por prazo de triagem crescente. As duas seções **não competem
entre si** — misturar prazo de triagem com prazo de resolução na mesma
ordenação faria um não triado de 8 h passar na frente de um P1 de 4 h
(PER-04). Não triado fora do prazo de triagem é sinalizado como violado, igual
aos demais (PRO-05).

O filtro de categoria é o único uso funcional da categoria (A10).

## T-3 — Triar (UC-2) · papel AGENTE

```
┌────────────────────────────────────────────┐
│ Triar #123 — "Impressora não imprime"      │
│ Urgência declarada: MÉDIA (pelo solicitante)│
├────────────────────────────────────────────┤
│ Categoria [Hardware ▾]                     │
│ Impacto   ( ) Alto  ( ) Médio  (•) Baixo   │
│           ↳ texto da definição do nível    │
│                                            │
│ Prioridade resultante:  P4                 │
│ Prazo de resolução:     abertura + 120 h   │
│                                  [ Triar ] │
└────────────────────────────────────────────┘
```

A prioridade aparece como **resultado calculado**, em texto — nunca como campo
editável. É a tradução visual do CA-negativo.

## T-4 — Chamado + trilha (UC-6) · TODOS os papéis

```
┌────────────────────────────────────────────────────────┐
│ #123 — Impressora não imprime            P4  ⚠ ok      │
│ Ana · Hardware · impacto BAIXO · urgência MÉDIA         │
│ Aberto em 10/03 09:00 · resolver até 15/03 09:00        │
├────────────────────────────────────────────────────────┤
│ Histórico de classificação                             │
│ 10/03 09:00  Ana      abertura     urgência: MÉDIA     │
│ 10/03 09:30  Carla    triagem      impacto: — → BAIXO  │
│                                    prioridade: — → P4  │
│ 10/03 11:00  Ana      recurso      contesta URGÊNCIA   │
│                       "fecho o balanço hoje"           │
│ 10/03 14:00  Elena    PROVIDO      urgência: MÉDIA→ALTA│
│                                    prioridade: P4 → P3 │
│                       "prazo contábil confirmado"      │
├────────────────────────────────────────────────────────┤
│              [ Recorrer ]   [ Reconhecer ]  [ Encerrar ]│
└────────────────────────────────────────────────────────┘
```

**Reconhecer e Encerrar (V(2), PRO-02/PRO-03)** ficam aqui, visíveis a agente
e gestor. Eram transições já modeladas na Fase 1 que as telas haviam omitido —
sem elas, a meta de reconhecimento por prioridade era inatingível. **Encerrar**
fica indisponível enquanto houver recurso ABERTO, com o motivo dito em texto
(MOV-4); passadas 24 h sem julgamento o recurso prescreve e o botão libera
(MOV-11).

Mesma trilha para os três papéis (decisão A3 da Fase 0): sem assimetria de
informação contra a parte mais fraca do rito. O botão **Recorrer** só aparece
quando as 5 guardas de admissibilidade passam; caso contrário, no lugar dele
aparece o motivo — "prazo para recorrer encerrado em 12/03 09:30", "já houve
recurso neste chamado". Um botão que falha ao ser clicado é pior que um botão
ausente com explicação.

## T-5 — Recorrer (UC-4a) · papel SOLICITANTE

```
┌────────────────────────────────────────────┐
│ Recurso do chamado #123                    │
│ Você pode recorrer até 12/03 09:30         │
├────────────────────────────────────────────┤
│ Contesto:  [x] a urgência (MÉDIA)          │
│            [ ] o impacto (BAIXO)           │
│ Por quê    [                        ]      │
│            [                        ]      │
│                                            │
│ Este é seu único recurso neste chamado.    │
│                       [ Enviar recurso ]   │
└────────────────────────────────────────────┘
```

O prazo e a unicidade são ditos **antes** do envio, não depois da recusa.

## T-6 — Julgar (UC-4b) · papel GESTOR

```
┌────────────────────────────────────────────────────┐
│ Recurso do chamado #123 — aberto há 3 h            │
│ Ana contesta a URGÊNCIA: "fecho o balanço hoje"    │
│ Classificação atual: impacto BAIXO · urgência MÉDIA │
│ 2º recurso de Ana nos últimos 30 dias              │
├────────────────────────────────────────────────────┤
│ Desfecho  ( ) Provido  ( ) Parcial  ( ) Improvido  │
│ Urgência  [ MÉDIA ▾ ]      (habilitado se provido) │
│ Fundamentação [                              ]     │
│                                                    │
│ Se provido: P3 · prazo recontado desde a abertura  │
│ ⚠ o chamado passará a constar VIOLADO              │
│                                     [ Julgar ]     │
└────────────────────────────────────────────────────┘
```

O aviso de violação iminente é obrigatório: o gestor precisa saber que o
provimento vai marcar o chamado como violado **antes** de decidir, e que isso é
o comportamento correto (GT-3), não um efeito colateral. A trilha registrará a
violação com `origem=RECURSO`, distinguindo **violamos porque triamos errado**
de **violamos porque demoramos** — sem essa distinção, prover um recurso seria
criar um número ruim contra a própria equipe do gestor (JOG-02).

**A contagem "2º recurso de Ana nos últimos 30 dias" (V(3), MOV-14)** aparece
**só aqui**, e só para o gestor. É contexto de uma decisão específica, não
relatório — a distinção importa porque relatórios estão no escopo negativo e
porque ETI-03 apontou, com razão, que contar quem exerce um direito o inibe. A
tensão entre ETI-03 e ETI-04 foi arbitrada pelo operador, não dissolvida: esta
linha existe porque a política anti-abuso da Fase 0 dependia explicitamente de
o abuso ser visível.

## T-3 — nota sobre a matriz visível

T-3 exibe a matriz 3×3 inteira como tabela estática, com a urgência declarada
destacada — sem JavaScript e sem triar às cegas (UX-01). O efeito colateral
está registrado e aceito: o agente vê o resultado de cada impacto antes de
escolher e pode mirar o resultado (UX-05). Esconder a matriz seria segurança
por obscuridade e prejudicaria o agente honesto, que precisa entender o que
está atribuindo.

## Fora de escopo visual

Sem identidade visual, sem ilustração, sem ícone além de caracteres. HTML
semântico com contraste e navegação por teclado; acessibilidade avançada e
i18n estão no escopo negativo.
