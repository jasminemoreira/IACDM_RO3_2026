# Acumulado para o próximo corte

**Regra, fixada em 2026-08-17.** Cortar release a cada correção fragmenta o histórico. As
correções da leitura fina se acumulam aqui e saem num snapshot só.

Este arquivo existe para que as notas da release e a entrada do *Data availability* sejam
escritas do registro, não reconstruídas do `git log` na pressa. **Toda correção acrescenta
uma linha aqui, no mesmo commit.** O nome é durável de propósito — não precisa ser renomeado
a cada corte.

---

## Janela aberta

**Aberta.** A tabela número→comando e as quatro correções que ela encontrou não estão em
nenhum DOI publicado. A **v1.8** — o fecho da série — é o snapshot que as carrega, e o
manuscrito não deve ser submetido citando a v1.7 para esses valores.

> **Quando entrar aqui algo que não seja o regresso, esta seção volta a valer.** Enquanto
> houver linha de conteúdo em "Acumulado", há número citável no manuscrito que nenhum DOI
> reproduz — e o *Data availability* não deve ser fechado sem conferir esta lista.

## Acumulado desde a v1.7

| commit | o que entrou | afeta citação? |
|---|---|---|
| `846c364` | `tools/tabela_numeros.py` e `TABELA-NUMEROS.md`: 197 valores × comando, com auditoria de cobertura contra o `.tex` | **sim — é o artefato pedido** |
| `846c364` | quatro correções que a auditoria achou: ARQ×PRE, mediana, critérios de saída | **sim — quatro números do manuscrito** |
| `cfba04c` | DOI da v1.7 no README e no `CITATION.cff`; a nota de "a partir de qual versão citar" ganha o contraponto — a v1.7 não é versão de número | não — regresso conhecido |

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
