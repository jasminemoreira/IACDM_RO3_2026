# RETRABALHO — T22-plantoes

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-10** |

UC-1 a UC-5 e SC-1 a SC-15, congelados na Fase 0 antes de codar, verificados na Fase 6:
**44 testes, 44 verdes** (39 originais mais 5 de regressão). Porte de referência medido —
150 alocações para 150 vagas ótimas, custo 0, 0 violações rígidas, **0,3 s contra o limite
de 60 s**. Veredito da Fase 7: o operador confirmou que atende.

As limitações (autenticação, notificação, papel de gestor, folha de pagamento, equidade
como critério) foram **decididas explicitamente ao longo das fases, com o raciocínio
registrado** — o registro é enfático em que não são esquecimento. Dívida declarada não é
retrabalho.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### O número que importa: 4 defeitos que os 39 testes verdes não pegaram

O teste exploratório da Fase 6 encontrou **4 defeitos com a suíte inteira verde**. Dois
merecem registro pelo que revelam:

**D-01 — a metade descoberta de um achado já resolvido.** `repositorio_json` tratava JSON
corrompido **na instância de entrada**, porque era isso que RES-03 apontava. Não tratava
os arquivos que o **próprio sistema grava**. O achado da Fase 2 estava certo e a correção
da Fase 3 cobriu metade do que ele implicava — e a suíte, escrita contra o achado, herdou
o mesmo recorte.

**B-01 — `--force` sobrescrevia.** A V(3) especificava imutabilidade para resolver GOV-0x,
e a implementação de `--force` a violava. Corrigido para versionar (`meu` → `meu-r1` →
`meu-r2`), preservando a anterior intacta com seus eventos.

Ambos são a mesma classe: **o teste automatizado verifica o que alguém pensou em
verificar**, e quem escreveu o teste foi quem leu o achado. É o terceiro projeto do ciclo
2 em que o exploratório rende o que a suíte não rende.

### Duas divergências de literatura, declaradas e corrigidas com número publicado

O S7 da Fase 5 encontrou as duas, e nenhuma foi desviada em silêncio.

**Assimetria do INRC-II.** O benchmark penaliza em S1 apenas a cobertura **abaixo** do
ótimo, porque suas instâncias são de demanda exata. No porte de referência (90 plantões,
150 vagas ótimas) o solver entregou **183 alocações**: com custo zero alcançável e nada
penalizando o excesso, superlotar plantão é gratuito — *"num hospital, escalar gente que
não era necessária"*. Corrigido penalizando o excesso simetricamente, **reutilizando o
peso publicado de S1 (30)**. O registro é explícito: *"nenhum número novo inventado"*.

**Contadores atravessando horizonte.** `derivar_fronteira` acumulava `total_plantoes` e
`fins_de_semana_trabalhados` sobre todas as escalas anteriores, e o acumulado entrava na
avaliação de S6/S7 do mês seguinte — mas o contrato declara `horizonte_meses=1`. Sintoma:
outubro com `--anterior` setembro dava custo 1830 e estourava os 60 s, porque cada pessoa
já *começava* o mês penalizada. No INRC-II os contadores acumulam **dentro** do horizonte
e são avaliados no fim dele.

Vale para o corpus porque é a lente CIE fazendo o que ela existe para fazer: as duas
divergências são contra uma fonte publicada, foram nomeadas contra a fonte, e a correção
usou parâmetro da própria fonte em vez de um número escolhido para funcionar.

### Poder de detecção medido, não presumido

A suíte foi validada por **5 mutações deliberadas, todas detectadas**. É o único projeto
do ciclo 2 até aqui que mede o poder de detecção da própria suíte em vez de reportar
"verde". Uma suíte verde e uma suíte capaz de reprovar não são a mesma coisa, e o registro
distingue as duas.

### Procedência do teste manual — o gate NÃO foi marcado por conta própria

O exploratório foi executado **pela IA a pedido do operador**, e o registro traz a
ressalva do AP5 explicitamente: *"não substitui o julgamento humano sobre adequação
semântica, e o gate `manual_testing` NÃO foi marcado por conta própria"*.

É a conduta mais correta dos três projetos nesse ponto. No T21 o agente executou e as
perguntas de julgamento ficaram declaradamente em aberto; no T24 o operador executou e
julgou. Aqui o agente executou, recusou-se a carimbar o gate, e esperou. **Os três
projetos têm procedências diferentes de human-AV, e isso precisa constar de qualquer
comparação entre eles.**
