# Acumulado para o próximo corte

**A série fechou na v1.8, em 2026-08-18.** Este arquivo continua aqui porque a regra que ele
carrega vale para qualquer correção posterior à submissão, não porque haja algo pendente.

**Regra.** Cortar release a cada correção fragmenta o histórico; as correções se acumulam
aqui e saem num snapshot só. **Toda correção acrescenta uma linha, no mesmo commit** — e
essa regra já falhou uma vez, um commit depois de escrita, o que é ele próprio um dado sobre
instrução sem trava.

---

## Janela aberta

**Nenhuma.** A v1.8 publicou a tabela número→comando, as quatro correções que a auditoria
dela encontrou e a nota sobre as figuras, e o DOI dela — `10.5281/zenodo.21994736` — já está
registrado aqui. O manuscrito foi re-congelado contra esse snapshot, valor a valor.

Sobra só o **regresso conhecido**: este registro em si vive num commit posterior à v1.8. Se
nada mais mudar, ele não precisa de snapshot próprio — a v1.8 continua reproduzindo todo
valor citado, que é a única propriedade que importa.

> **Quando entrar aqui algo que não seja o regresso, esta seção volta a valer.** Enquanto
> houver linha de conteúdo em "Acumulado", há número citável no manuscrito que nenhum DOI
> reproduz — e o *Data availability* não deve ser fechado sem conferir esta lista.

## Acumulado desde a v1.8

| commit | o que entrou | afeta citação? |
|---|---|---|
| `3022a7d` | DOI da v1.8 registrado; v1.8 marcada como versão de referência | não — regresso conhecido |
| `3022a7d` | `TABELA-NUMEROS.md` passa a trazer `ARQ × PRE` em três casas (0,005), com os 196 clusters e o Jaccard de módulos 0,36, que o manuscrito re-congelado cita | **não** — ver abaixo |

> **Por que a segunda linha não abre janela.** Os três valores **já são reproduzidos pela
> v1.8**: o Passo 4 do `ro3_analise.py` imprime `ARQ × PRE | 0.36 | 1 | 0.005` naquele
> snapshot. O que estava incompleto era o índice, que arredondava para `0.01` e não listava
> os outros dois. A propriedade que precisa valer — todo valor citado tem snapshot publicado
> que o reproduz — vale na v1.8. Um corte novo melhoraria o índice, não a reprodutibilidade.

## Antes de cortar

- [ ] `python3 analise/figuras.py --conferir` sai 0
- [ ] `python3 analise/divergencias.py` não falha na verificação contra a figura
- [ ] `python3 analise/redeclaracao.py` reproduz 36 comparações, 0 idênticas
- [ ] `python3 tools/tabela_numeros.py --auditar <tex>` — as divergências restantes são
      conhecidas e justificadas, não lacunas
- [ ] `python3 analise/test_formato.py` — 18 casos
- [ ] `python3 tools/checar_dependencias.py` — stdlib puro
- [ ] `.zenodo.json` e `CITATION.cff` na versão nova, com os DOIs anteriores já listados

## O enquadramento das notas

Estabelecido na v1.4 e herdado desde então: dizer **o que corrige** e **a partir de qual
versão citar**. A tabela de versões do README trata como opcional tudo o que se apresenta
como acréscimo, e uma release que corrige número não é acréscimo. A v1.7 exigiu o inverso —
dizer explicitamente que **não** era de número, para que o aviso das outras não se esvaziasse.
