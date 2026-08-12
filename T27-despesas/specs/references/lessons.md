# Lições do projeto T27 — fila de aprovação de despesas

Lições sobre **este projeto** (domínio, stack, padrões, premissas que se revelaram erradas),
não sobre a metodologia. Escritas na Fase 7 para alimentar um eventual ciclo v2.0 ou um
post-mortem. Cada uma cita o achado ou a decisão que a produziu.

---

## L1 — "A cadeia começa acima do solicitante" é a âncora do domínio, e errá-la esvazia a cadeia

A regra da matriz DoA parece ser "sobe até o papel cujo limite cobre o valor". Não é. A
âncora correta tem **duas** condições simultâneas: o papel precisa estar **acima do
solicitante** *e* cobrir o valor. V(2) ancorou só na segunda e produziu **cadeia vazia** no
caso mais comum do domínio — um Coordenador (limite R$5.000) pedindo R$100 não teria
aprovador nenhum (achado 🔴 IMP-06).

O erro é sedutor porque a fórmula errada acerta em todos os exemplos de valor alto, que são
os que a gente escreve primeiro ao pensar em alçadas. **O caso pequeno é o caso limite.**

> Para o v2: qualquer mudança em `matriz-doa.cadeiaPara` deve ser testada primeiro com o
> menor valor possível vindo do menor papel possível.

## L2 — Delegação de autoridade tem três semânticas distintas, e o domínio precisa das três

O enunciado diz "delegação temporária" como se fosse uma coisa. São três, e cada uma nasceu
de um defeito diferente:

1. **Transferência de posse** (CA-3) — com delegação ativa, o item sai da bandeja do
   delegante. Faltou na primeira implementação: a delegação *acrescentava* o delegado sem
   *remover* o delegante (diagnóstico `8e068d32`).
2. **Caminho adicional** (CA-3b) — quando o delegado é inelegível para *aquele item* por
   SoD, a delegação é inócua ali e o item **permanece** com o delegante. Sem isso, o
   Diretor que delega à única Gerente cria uma despesa **órfã permanente**: ela decide o
   nível 2 e é barrada por INV-4 no nível 3 (achado 🔴 PROC-06).
3. **Autoridade no instante do ato** (INV-6) — o que foi decidido dentro da vigência vale
   para sempre; a expiração não retroage.

As três convivem em uma única função (`autoridade.resolver`) e é ali que qualquer mudança
futura vai doer.

## L3 — Controle que **bloqueia** não é o mesmo que controle que **escala**, e o domínio real escala

A resposta intuitiva a "e se não houver nenhum Gerente?" é recusar a despesa. Foi o que
INV-15 fazia, e estava errado: nenhuma prática de DoA das fontes levantadas bloqueia gasto
por assento vago — a convenção é **pular o nível vazio e escalar** (achado 🟡 REG-04). Pior,
a mensagem de erro mandava o usuário "pedir ao Admin para cadastrar um titular", e o Admin
não pode fazer isso: edição da matriz está fora de escopo (achado 🔴 UX-07).

INV-15 foi revogada. O que sobrou é mais simples e mais fiel: pula-se o nível, **registra-se
o pulo na trilha**, e a recusa só existe quando *nenhum* nível tem decisor (INV-17), com
INV-18 garantindo pelo menos uma aprovação humana.

> Lição transferível: quando um controle novo produz uma mensagem que instrui uma ação
> impossível, o defeito não é a mensagem — é o controle.

## L4 — Em TypeScript, `as T` sobre linha de banco é um bug esperando data marcada

O único defeito que atravessou desenho, tipos e revisão estática e só caiu no primeiro teste
por HTTP foi este (diagnóstico `126d233a`):

```ts
porId: (id) => st.usuarioPorId.get(id) as Usuario | undefined,   // papel_id ≠ papelId
```

`tsc --noEmit` passa. O objeto tem `papel_id`, o tipo declara `papelId`, e `papelId` vira
`undefined` **em silêncio**. Todos os outros agregados tinham mapeamento explícito; só este
tinha cast. O `as` desliga exatamente a verificação que justificava escolher TypeScript.

> Para o v2: proibir `as` em fronteira de persistência. Mapeamento explícito campo a campo,
> ou uma função de mapeamento por tabela — nunca um cast.

## L5 — Premissa declarada não é premissa imposta, e a diferença aparece na lente Assumptions

Na primeira rodada de crítica, a lente `Assumptions` atingiu **6 de 12 módulos** com o mesmo
mecanismo: o desenho enumerava A1-A8 honestamente e depois **confiava** nelas. A correção
não foi remendar seis módulos; foi converter duas premissas em verificação executada
(INV-14, validada na carga, com o processo recusando subir). Na rodada seguinte, a mesma
lente caiu para 2 módulos.

Sobraram premissas legítimas — A2, A4, A5, A6, A7, A8 — e elas estão declaradas com a
consequência de cada uma ser falsa. A mais cara é **A5**: sem autenticação, toda invariante
SoD é contornável por quem chame a API direto. O sistema impõe SoD **contra engano, não
contra adversário**, e isso foi aceito explicitamente, não esquecido.

## L6 — Corrigir tem custo próprio, e neste projeto ele foi mensurado

| rodada | achados | 🔴 | 🔴 que eram regressões da rodada anterior |
|---|---|---|---|
| 1 — V(1) | 57 | 10 | — (desenho original) |
| 2 — V(2) | 21 | 6 | **5 de 6** |
| 3 — V(3) | 17 | 5 | **5 de 5** |

O volume cai, mas a proporção de críticos que são **efeito colateral das correções
anteriores** sobe até 100%. Exemplos concretos: remover a rota de relógio por segurança
congelou o relógio e quebrou o FIFO (CTRL-03); corrigir a contradição de contrato de
`matriz-doa` empurrou uma invariante SoD para fora do domínio (ARQ-08); trocar identidade
de cookie por campo tirou o CSRF e pôs a identidade na URL (SEC-06).

Nenhuma dessas rodadas foi desperdício — a rodada 2 encontrou IMP-06 e PROC-06, que teriam
ido para produção. Mas foi essa tabela, e não a regra de percentual do método, que sustentou
a decisão de parar na terceira.

## L7 — Achados de tecnologia que valem para o próximo ciclo

- **`better-sqlite3` ≤ 9 não instala em Node 24**: sem prebuild, `node-gyp` falha. A v13 tem
  prebuild. Vale fixar a versão maior desde o início em ambiente Node recente.
- **`fastify` 4 e `vitest` 1.6 entram com vulnerabilidades conhecidas** (1 crítica, 3 altas
  no `npm audit`). Fastify 5 + `@fastify/formbody` 8 + Vitest 3 zeram o audit.
- **"Escape por padrão" não existe em template de string**: `${x}` interpola cru. A única
  forma de garantir é um template marcado que escapa tudo exceto o tipo `Html`, sem
  nenhuma função pública que converta string em `Html` (achado IMP-07/LING-06).
- **Duplo envio anti-CSRF com valor público não é defesa**: o id do usuário está listado na
  tela de seleção. O cookie precisa carregar um **nonce aleatório** (achado 🔴 SEC-07).
- **Relógio deslocável, não fixável**: `agora() = real + offset` preserva cronologia, FIFO e
  expiração. Fixar o instante no boot congela tudo (achado 🔴 CTRL-03).

## L8 — O que ficou de fora, conscientemente, e é candidato natural a v2.0

| item | por que ficou fora | achado |
|---|---|---|
| Detecção de fracionamento (*splitting*) | dividir R$60k em duas de R$30k pula o nível superior; detectar exige agregação por período — capacidade nova | GT-02 |
| Restrição de para quem se pode delegar | delegado complacente e par recíproco A↔B continuam possíveis | GT-01 |
| Cancelamento pela própria pessoa que solicitou | a única saída hoje é um aprovador rejeitar | PROC-03 |
| Trilha à prova de adulteração (hash encadeado) | INV-8 é append-only *pela aplicação*; o arquivo SQLite é editável por fora | REG-01 |
| Política de retenção | retenção ilimitada; SOX pede prazo definido | REG-02 |
| Autenticação real | A5, aceita explicitamente | SEC-01 |
| Caminho de correção de dado errado no seed | com a matriz não editável, um papel errado só se corrige editando o arquivo e reiniciando | GOV-02 |
