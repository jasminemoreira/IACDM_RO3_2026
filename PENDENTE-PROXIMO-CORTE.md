# Acumulado para o próximo corte

**Regra, fixada em 2026-08-17.** Cortar release a cada correção fragmenta o histórico. As
correções da leitura fina se acumulam aqui e saem num snapshot só.

Este arquivo existe para que as notas da release e a entrada do *Data availability* sejam
escritas do registro, não reconstruídas do `git log` na pressa. **Toda correção acrescenta
uma linha aqui, no mesmo commit.** O nome é durável de propósito — não precisa ser renomeado
a cada corte.

---

## Janela aberta

**Nenhuma que afete o manuscrito.** A v1.6 fechou a que existia: denominadores, ressalva dos
quatro `b = 0` estruturais e `analise/divergencias.py` estão publicados, e o *Data
availability* foi fechado contra o DOI dela.

O que está pendente é só o **regresso conhecido** — o DOI de uma versão é emitido depois de
o conteúdo dela estar fechado, então nenhuma versão pode listar o próprio. O registro do DOI
da v1.6 entra na próxima. Isso **não** é número citável sem lastro: a v1.6 existe e resolve;
só o registro dela dentro do pacote é que espera.

> **Quando entrar aqui algo que não seja o regresso, esta seção volta a valer.** Enquanto
> houver linha de conteúdo em "Acumulado", há número citável no manuscrito que nenhum DOI
> reproduz — e o *Data availability* não deve ser fechado sem conferir esta lista.

## Acumulado desde a v1.6

| commit | o que entrou | afeta citação? |
|---|---|---|
| `25649f4` | DOI da v1.6 no README e no `CITATION.cff`; terceira linha de "a partir de qual versão citar", agora incluindo as taxas de divergência | não — regresso conhecido |
| `d49e81b` | título dos painéis κ alinhado à esquerda da figura; o do (b) estava cortado na borda direita. Só recorte — nenhum valor muda | não — defeito visual |
| `e57a4d0` | largura do painel (b) derivada da fração de `\textwidth` do `.tex`; as duas escalas não batiam e os rótulos (a)/(b) saíam ~6 pt desalinhados | não — defeito visual |

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
