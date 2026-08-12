# `ui-editor-regras` — especificação da tela

Escrita na Fase 3, iteração 2, em resposta a **IMP-04 🟡** ("é o módulo com menos
especificação escrita e o de maior custo real"). O achado era a ausência de
spec; a correção é a spec, não um redesenho.

Responde também a **UX-01 🔴** (o produto precisa não ser pior que editar
células) e **UX-02 🟡** (correção no local, sem voltar à planilha).

## Objetivo da tela

O analista mantém o **rascunho** de regras com custo de edição comparável ao de
uma planilha, vê os erros do validador **na própria linha** e publica.

## Grade

Colunas, na ordem:

| # | coluna | tipo | edição | observação |
|---|---|---|---|---|
| 1 | escopo | `SKU` ou `*` | texto com autocompletar de SKU | `*` = qualquer produto |
| 2 | qtd. de | inteiro ≥ 1 | numérico | |
| 3 | qtd. até | inteiro ou vazio | numérico | vazio = aberto à direita (∞) |
| 4 | tipo | `preço` / `desconto %` | seleção | Strategy do efeito |
| 5 | valor | monetário ou percentual | texto, formatado ao sair do campo | validado por M-01 `dinheiro` |
| 6 | prioridade | inteiro | numérico | maior vence |
| 7 | vigência de | data | data | |
| 8 | vigência até | data ou vazio | data | vazio = indefinido |
| 9 | *status* | — | somente leitura | 🔴 erro / 🟡 aviso / vazio |

Linhas com erro do validador ficam marcadas na coluna 9, com o motivo em
*tooltip* e no rodapé. **O erro é corrigido na própria célula** — não há retorno
à planilha (UX-02).

## Colagem vinda da planilha (o requisito que ataca UX-01)

- Colar (`Ctrl+V`) com o cursor numa célula preenche a partir dali.
- O conteúdo do *clipboard* é lido como **TSV** (é o que Excel, LibreOffice e
  Google Sheets colocam na área de transferência ao copiar um bloco de células).
- Linhas e colunas em excesso são ignoradas com aviso; faltantes ficam com o
  valor atual.
- Cada célula colada passa pela **mesma validação** da digitação — colar não é
  caminho privilegiado.
- Colar abaixo da última linha **cria linhas novas**, até o limite de 2.000.

## Operações

| ação | efeito |
|---|---|
| adicionar linha | linha vazia ao fim |
| excluir linhas selecionadas | remove do rascunho |
| desfazer / refazer | pilha local da sessão de edição |
| salvar rascunho | persiste via `salvar_rascunho` |
| validar | roda `validar_rascunho` e pinta a coluna 9 |
| publicar | exige nome do **autor**; bloqueia se houver 🔴; se houver 🟡, exige reconhecimento explícito (PRO-04) |

## Regras de estado

- Sair da tela com alterações não salvas pede confirmação.
- Publicar substitui o rascunho pela cópia da versão publicada (PRO-01).
- `republicar(n)` **não** é operação desta tela — e não afeta o rascunho (PRO-05).

## Modo degradado — declarado, **e não acionável pela IA**

> **Arbitragem do operador (Fase 3, iteração 3, em resposta a PRO-06 🟡):** o
> plano de degradação fica escrito, mas **a Fase 5 não pode acioná-lo sozinha**.
> Se a grade estourar o orçamento, a implementação **para e pergunta**. Escopo é
> do operador; uma pré-autorização escrita pela IA continua sendo a IA decidindo
> entregar menos.

Se a grade não couber no orçamento da sessão de implementação, a degradação
**aceitável — mediante autorização explícita do operador no momento** é:

1. formulário de uma regra por vez, **mais**
2. uma área de texto que aceita colar um bloco TSV/CSV e o converte em linhas.

O item 2 é **obrigatório mesmo no modo degradado** — é ele que responde a UX-01.
Um formulário puro por regra reprova o critério, porque devolve ao analista
exatamente o custo de edição que o fez preferir a planilha.

## Acessibilidade (UX-04)

Rótulos associados a cada campo, navegação completa por teclado (`Tab` entre
células, `Enter` desce, `Esc` cancela a edição da célula), foco visível, e
mensagens de erro associadas ao campo por `aria-describedby`.

## Fronteira visual (ARQ-06)

A base de template e o CSS pertencem a `ui-web`; `ui-editor-regras` os importa.
Direção única, sem ciclo.
