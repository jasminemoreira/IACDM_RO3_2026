# Estado da arte — infraestrutura de notificação

Levantado na Fase 0 para responder: o que estes produtos consideram *mínimo* num
serviço de notificação, e onde estão as lacunas conhecidas. Fontes: R-09, R-10
em `specs/references/notification-references.md`.

## Comparativo

| Capacidade | Knock | Novu | Courier | AWS SNS/Pinpoint | T30 (este projeto) |
|---|---|---|---|---|---|
| Preferências por pessoa (categoria × canal) | ✅ painel pronto | ✅ subscriber-first | ✅ | parcial (tópicos) | ✅ escopo |
| Janela de silêncio controlada pela pessoa | ✅ | ✅ (Schedule no Inbox) | ✅ | ❌ | ✅ escopo |
| Janela de silêncio **por canal** | ✅ (raro) | ❌ | ❌ | ❌ | estrutura suporta, padrão global |
| Exceção transacional (ignora supressão) | ✅ | ✅ | ✅ (por nó do fluxo) | — | ✅ escopo |
| Teto de frequência | ✅ | ✅ | ✅ | ❌ | ✅ escopo |
| Deduplicação / idempotência | ✅ | ✅ | ✅ | parcial | ✅ escopo |
| Fan-out multicanal | ✅ | ✅ | ✅ | ✅ | 2 canais |
| Feed in-app + componentes de UI | ✅ | ✅ | parcial | ❌ | ❌ fora de escopo |
| Editor visual de fluxo / templates | ✅ | ✅ | ✅ | ❌ | ❌ fora de escopo |

## Observações que informam a arquitetura

1. **A supressão é um pipeline, não um filtro único.** Nas três plataformas o
   caminho é o mesmo: verificar opt-out → verificar janela de silêncio (e
   *enfileirar*, não descartar) → verificar teto (e agrupar ou descartar) →
   entregar. Isso valida a decisão de ter um ponto único de avaliação de regras
   em vez de espalhar `if`s pelos canais.

2. **Enfileirar vence descartar.** Courier, Customer.io, Knock e Novu adiam a
   entrega até a janela abrir; só Braze oferece abortar como opção de primeira
   classe. Adotamos adiar (PAR-15).

3. **Exceção transacional é universal.** Toda plataforma madura tem uma via que
   ignora preferências. Confirma que `transacional` precisa ser propriedade da
   notificação, não do canal.

4. **Janela por canal é a lacuna do mercado.** Só Braze e Knock oferecem. Modelar
   a estrutura para suportar (sobrescrita por canal) custa pouco e é onde o
   estado da arte ainda é fraco.

5. **O que estes produtos fazem e nós NÃO faremos:** editor visual de fluxos,
   feed in-app com componentes de UI, catálogo de templates, analytics de
   engajamento. São produto, não o núcleo do problema do enunciado. Vão para o
   Nível 5 (YAGNI) com justificativa.
