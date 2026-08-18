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
dela encontrou e a nota sobre as figuras. Pendente apenas o **regresso conhecido**: o DOI da
v1.8 só pode ser registrado num snapshot posterior.

> **Quando entrar aqui algo que não seja o regresso, esta seção volta a valer.** Enquanto
> houver linha de conteúdo em "Acumulado", há número citável no manuscrito que nenhum DOI
> reproduz — e o *Data availability* não deve ser fechado sem conferir esta lista.

## Acumulado desde a v1.8

*(vazio)*

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
