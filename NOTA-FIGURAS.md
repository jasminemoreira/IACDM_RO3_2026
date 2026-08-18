# Nota — o manuscrito tabula; as figuras seguem no depósito

**2026-08-18, no fecho da série.** O manuscrito congelado **não inclui mais as figuras**: o
painel κ virou tabela, com os valores exportados em duas casas, e a figura de divergências
foi superada pela tabela de denominadores, que diz mais no mesmo espaço.

**As figuras permanecem válidas e continuam no pacote.** Esta nota existe para que ninguém
leia a ausência delas no paper como abandono — que é exatamente o tipo de leitura que este
projeto já cometeu uma vez, quando a ausência de um par numa lista truncada foi lida como
ausência de sobreposição.

---

## O que mudou, e o que não

| | |
|---|---|
| **muda** | o paper apresenta os valores como tabela em vez de gráfico |
| **não muda** | de onde os valores vêm, como são computados, e o que os verifica |

Os CSVs em `analise/saidas/figuras/` são a **fonte comum**. O manuscrito tabula deles; o
`make_figures.R` plota deles. Não há dois caminhos: há um cálculo e duas apresentações.

```bash
python3 analise/figuras.py --conferir              # computa os CSV e confere com a fonte única
Rscript --vanilla analise/figuras/make_figures.R   # renderiza (opcional — só o PDF depende de R)
```

**A verificação não se perde com as figuras.** O `--conferir` recomputa as tabelas do
resultado a partir do corpus e as compara célula a célula com o `RESULTADO-RO3.md`, saindo
com código 1 se divergirem. Ele guardava os valores plotados e continua guardando os valores
tabulados, porque são os mesmos valores.

## Por que as figuras ficam

Três razões, e nenhuma é sentimental:

1. **São o artefato de um cálculo que o paper cita.** Um revisor que queira ver a
   distribuição de contribuição exclusiva sob as quatro clusterizações lê melhor 19 lentes ×
   4 séries num gráfico do que numa tabela de 76 células.
2. **A figura de robustez nunca esteve no recorte.** O que saiu do paper foi o painel κ e a
   de divergências; `fig-robustness.pdf` e `fig-divergences.pdf` continuam sendo a leitura
   mais rápida dos §1.4 e §2.4 do resultado.
3. **Reexecutar o pipeline as reproduz.** Removê-las do pacote tornaria uma saída do
   pipeline órfã — o script continuaria gerando arquivos que o depósito não guarda.

## Precisão

A tabela do manuscrito traz **duas casas decimais**; os CSVs trazem precisão plena. Para o
`esperado ao acaso`, isso importa: `fig-kappa-chance.csv` guarda dez casas justamente porque
dividir pelos valores arredondados erra a razão em até meia unidade. **Quem recomputar deve
partir do CSV, não da tabela impressa.**
