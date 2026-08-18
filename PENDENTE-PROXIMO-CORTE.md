# Acumulado para o próximo corte

**Regra, fixada em 2026-08-17.** Cortar release a cada correção fragmenta o histórico. As
correções da leitura fina se acumulam aqui e saem num snapshot só.

Este arquivo existe para que as notas da release e a entrada do *Data availability* sejam
escritas do registro, não reconstruídas do `git log` na pressa. **Toda correção acrescenta
uma linha aqui, no mesmo commit.** O nome é durável de propósito — não precisa ser renomeado
a cada corte.

---

## Janela aberta

**Nenhuma que afete o manuscrito.** A **v1.7** publicou as três correções visuais da figura
κ. Pendente apenas o **regresso conhecido** — o DOI da v1.7 só pode ser registrado na
próxima versão, porque é emitido depois de o conteúdo dela estar fechado.

> **Quando entrar aqui algo que não seja o regresso, esta seção volta a valer.** Enquanto
> houver linha de conteúdo em "Acumulado", há número citável no manuscrito que nenhum DOI
> reproduz — e o *Data availability* não deve ser fechado sem conferir esta lista.

## Acumulado desde a v1.7

| commit | o que entrou | afeta citação? |
|---|---|---|

## Antes de cortar

- [ ] `python3 analise/figuras.py --conferir` sai 0
- [ ] `python3 analise/divergencias.py` não falha na verificação contra a figura
- [ ] `python3 analise/redeclaracao.py` reproduz 36 comparações, 0 idênticas
- [ ] `python3 analise/test_formato.py` — 18 casos
- [ ] `python3 tools/checar_dependencias.py` — stdlib puro
- [ ] `.zenodo.json` e `CITATION.cff` na versão nova, com os DOIs anteriores já listados
- [ ] tabela número→comando, se o manuscrito tiver congelado

## O enquadramento das notas

Estabelecido na v1.4 e herdado desde então: dizer **o que corrige** e **a partir de qual
versão citar**. A tabela de versões do README trata como opcional tudo o que se apresenta
como acréscimo, e uma release que corrige número não é acréscimo.
