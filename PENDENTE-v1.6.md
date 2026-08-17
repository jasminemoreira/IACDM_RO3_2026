# Acumulado para a v1.6 — corte único, ao fim da leitura fina

**Decisão de 2026-08-17.** Cortar release a cada correção fragmenta o histórico. A leitura
fina do manuscrito continua produzindo correções; elas se acumulam aqui e saem num snapshot
só, **antes do congelamento**.

Este arquivo existe para que as notas da v1.6 e a entrada do *Data availability* sejam
escritas do registro, não reconstruídas do `git log` na pressa do congelamento. **Toda
correção que entrar depois da v1.5 acrescenta uma linha aqui, no mesmo commit.**

---

## ⚠ A janela aberta, e o que ela quebra

Entre a v1.5 e a v1.6 há números **citados no paper que nenhum DOI publicado reproduz**.

| o que o paper pode citar | está na v1.5? |
|---|---|
| denominadores das divergências (SUS 11/25, ETI 5/13, …) | **não** |
| a ressalva de que quatro `b = 0` são estruturais | **não** |
| `analise/divergencias.py` | **não** |
| DOIs da v1.4 e v1.5 no README e no `CITATION.cff` | **não** |

**Consequência para o chat do artigo:** não finalize o *Data availability* nem cite
denominadores contra o DOI da v1.5. Espere a v1.6, que é o primeiro snapshot que os contém.

O resto do §5.1 e o §1.4 **estão** na v1.5 e podem ser citados agora.

---

## Acumulado desde a v1.5

| commit | o que entrou |
|---|---|
| `57006a8` | DOIs da v1.4 e da v1.5 registrados no README e no `CITATION.cff`; a tabela de versões passa a distinguir **correção** de acréscimo |
| `c16816c` | `analise/divergencias.py`; §2.4 com denominadores por direção; a ressalva estrutural dos quatro `b = 0`; a nota do "35 unidirecional" reescrita |

## Rascunho das notas da v1.6

Montar destas linhas no corte. O enquadramento que importa, e que já foi usado na v1.4 e na
v1.5: dizer **o que corrige** e **a partir de qual versão citar**, porque a tabela de
versões trata como opcional tudo o que se apresenta como acréscimo.

## Antes de cortar

- [ ] `python3 analise/figuras.py --conferir` sai 0
- [ ] `python3 analise/divergencias.py` não falha na verificação contra a figura
- [ ] `python3 analise/redeclaracao.py` reproduz 36 comparações, 0 idênticas
- [ ] `python3 analise/test_formato.py` — 18 casos
- [ ] `python3 tools/checar_dependencias.py` — stdlib puro
- [ ] `.zenodo.json` e `CITATION.cff` em 1.6.0, com os DOIs da v1.4 e v1.5 já listados
- [ ] tabela número→comando, se o manuscrito tiver congelado
