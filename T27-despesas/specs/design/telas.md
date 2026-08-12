# Telas — especificação de `ui-web` (V(2))

Escrito na Fase 3 em resposta aos achados IMP-03, UX-01, UX-02, UX-03, UX-04 e UX-05.
Não é funcionalidade nova: é a especificação de um módulo que já estava no escopo da Fase 1
e cuja ausência de detalhe era o achado. Nenhuma tela acrescenta capacidade ao sistema.

Regra global (UX-05): **todas** as telas exibem, fixo no topo,
`Você é: <nome> (<papel>, alçada R$ X)` com link para trocar. Sem isso, o usuário age como
outra pessoa sem notar — agravado por não haver autenticação (A5).

Regra global (T5 de V(4)): a renderização é a função única `render(template, dados)`, que
escapa **todo** valor de `dados` exceto os do tipo marcado `Html` (produzidos por `render`
aninhado). Não existe caminho de interpolação crua exposto, portanto não há `${}` a esquecer.

Regra global (T3/T4 de V(4)): o cookie carrega **apenas** o nonce anti-CSRF; a identidade
viaja em campo/parâmetro `u` a cada requisição.

---

## T1 — Seleção de usuário
```
Quem é você?
( ) Ana Silva      — Coordenadora  (aprova até R$ 5.000)
( ) Bruno Costa    — Coordenador   (aprova até R$ 5.000)
( ) Carla Dias     — Gerente       (aprova até R$ 50.000)
...
[Entrar]
```
A identidade escolhida é enviada como campo explícito em cada formulário seguinte — não há
cookie de sessão (é o que elimina o vetor CSRF por construção, achado SEC-03).

## T2 — Nova despesa
```
Valor  [ R$ ____________ ]     Descrição [ ____________________ ]
[Enviar para aprovação]
```
Erros possíveis, com a mensagem que o usuário vê (achado UX-02 — dizer o que fazer, não só
o que foi bloqueado):
- acima do teto (INV-10): *"R$ 2.000.000,00 excede o maior limite da empresa (R$ 500.000,00,
  Diretor). Nenhuma cadeia de aprovação pode autorizar este valor — divida em despesas
  menores ou trate fora do sistema."*
- solicitante no topo (INV-13): *"Você é Diretor e não há papel acima do seu para aprovar.
  Esta despesa precisa ser autorizada fora do sistema."*
- nenhum nível da cadeia tem decisor (INV-17/INV-18, texto de V(4) — substitui a mensagem de
  INV-15, revogada, que mandava pedir ao Admin algo que o Admin não pode fazer, achado UX-07):
  *"Esta despesa não tem nenhum aprovador possível na configuração atual da empresa e por isso
  não pode ser registrada. Trate-a fora do sistema."*

Nota (V(4), regra do pulo): um nível **intermediário** sem decisor não gera erro — é pulado e
o pulo aparece na trilha como `NIVEL_PULADO` com o motivo. A recusa acima só ocorre quando
**nenhum** nível da cadeia tem decisor.

## T3 — Bandeja (FIFO, mais antiga no topo)
```
Suas pendências                                    ordenadas: mais antiga primeiro

 12/08 10:04  R$ 80.000,00  Servidor de backup      [PRÓPRIA]        [Abrir]
 12/08 09:12  R$ 42.500,00  Consultoria jurídica    [EM NOME DE ANA] [Abrir]
```
A marcação de origem é obrigatória em cada linha. Se a lista estiver vazia:
*"Nenhuma pendência sua no momento."*

## T4 — Detalhe da despesa + decisão  ⟵ tela do achado 🔴 UX-01
```
Despesa #4711 — R$ 42.500,00 — "Consultoria jurídica"
Solicitante: Bruno Costa (Coordenador)     Criada: 12/08 09:12
Cadeia: Gerente → Diretor        Aguardando: Gerente (nível 2)

┌────────────────────────────────────────────────────────────┐
│ ⚠ Você está decidindo EM NOME DE Ana Silva (Gerente),      │
│   exercendo a alçada dela: R$ 50.000,00.                   │
│   Delegação nº 88, vigente de 10/08 a 20/08.               │
└────────────────────────────────────────────────────────────┘

[Aprovar]   [Rejeitar]  ← exige motivo

Trilha
  12/08 09:12  CRIADA            Bruno Costa
  12/08 09:40  APROVADA nível 1  Bruno? não — Ana Silva, alçada R$ 5.000  …
```
O bloco de autoridade é **obrigatório e visível antes do clique**. Quando não há delegação,
o bloco diz: *"Você está decidindo por autoridade própria, alçada R$ 50.000,00."*

Rejeição (achado UX-04, INV-11 é terminal e irreversível):
```
Rejeitar #4711 — esta ação ENCERRA a despesa e não pode ser desfeita.
Motivo (obrigatório) [ ___________________________ ]
[Confirmar rejeição]  [Cancelar]
```
Sem motivo: *"Informe o motivo — ele fica registrado na trilha e é o que o solicitante lê."*

## T5 — Delegações
```
Minhas delegações
  nº 88  para Bruno Costa   10/08 → 20/08   ATIVA (termina em 8 dias)   [Revogar]
  nº 71  para Duda Reis     01/07 → 15/07   encerrada

Delegar minha autoridade
  Para [ v ]   De [ __/__ ]  Até [ __/__ ]   [Delegar]
```
"termina em N dias" (achado UX-03) é cálculo sobre dado já existente exibido na tela — **não**
é notificação, que está fora de escopo. Erros de SoD, com texto acionável:
- sobreposta (INV-5): *"Você já delegou a Bruno de 10/08 a 20/08. Revogue aquela delegação
  antes de criar outra que se sobreponha."*
- transitiva (INV-3): *"Você está exercendo a autoridade de Ana e não pode repassá-la.
  Só Ana pode delegar a autoridade dela."*
- antedatada (INV-16): *"A data de início não pode ser no passado."*

## T6 — Auditoria (Admin)
Lista de despesas com filtro por estado; abre em T4. Delegações de todos os usuários, com
ação de revogar (o Admin é a válvula de escape quando o delegante está indisponível).
Erro de auto-aprovação (INV-2) e de duplo voto (INV-4), quando ocorrerem em T4:
- *"Você é o solicitante desta despesa e não pode aprová-la, nem em nome de outra pessoa."*
- *"Você já decidiu o nível 1 desta despesa. Um mesmo aprovador não pode decidir dois níveis
  da mesma cadeia — ela precisa de outra pessoa."*

---

## Procedimento de demonstração da expiração (CA-5) — resolve IMP-09

O relógio é o relógio real deslocado por `T27_RELOGIO_OFFSET_MS`, lido na inicialização.
Para demonstrar manualmente que uma delegação expira com item na bandeja:

1. Suba normalmente (`T27_RELOGIO_OFFSET_MS` ausente = 0).
2. Crie uma delegação de A para B com vigência começando hoje e terminando em 2 dias.
3. Crie uma despesa que caia na cadeia de A e confirme que ela aparece na bandeja de **B**.
4. **Encerre o processo** e suba de novo com `T27_RELOGIO_OFFSET_MS=259200000` (3 dias).
5. Abra a bandeja de A: o item está lá. Abra a de B: não está. A aprovação que B tenha dado
   no passo 3 continua na trilha, válida (INV-6).

O estado vive em SQLite, então o reinício não perde nada. Voltar o offset para um valor
menor faz o tempo andar para trás — é ação deliberada do operador (achado CTRL-04, aceito).

## Duas identidades ao mesmo tempo (CA-3, CA-3b, CA-11) — resolve UX-08

A identidade viaja em cada requisição (parâmetro `u`), não em cookie. Para operar delegante
e delegado lado a lado, basta **duas abas comuns** do mesmo navegador. O cookie carrega
apenas o nonce anti-CSRF, que é o mesmo para as duas abas e não amarra identidade.
