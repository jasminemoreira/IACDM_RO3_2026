# IACDM — RO3: as 19 lentes de crítica são ortogonais?

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21908907.svg)](https://doi.org/10.5281/zenodo.21908907)
[![Licença: CC BY 4.0](https://img.shields.io/badge/licen%C3%A7a-CC%20BY%204.0-blue.svg)](LICENSE)

Corpus e análise do experimento que testa a **RO3** da metodologia IACDM: *cada uma das 19
lentes de crítica detecta uma classe de falha que nenhuma outra detecta?*

**Doze projetos de software construídos do zero**, cada um em sessão única de 2 a 4 horas,
todos sob o mesmo instrumento, com a crítica arquitetural registrada em matriz de cobertura
auditável.

> **Resultado:** nenhuma das 19 lentes apresentou contribuição exclusiva zero — em nenhum
> projeto, em nenhum agregado, e sob quatro clusterizações independentes do que conta como
> "mesmo defeito".

Leia **[`RESULTADO-RO3.md`](RESULTADO-RO3.md)** — é a fonte única dos números.

<details>
<summary><b>Summary in English</b></summary>

Corpus and analysis of an experiment testing **RQ3** of the IACDM methodology: *does each of
19 architectural-critique lenses detect a failure class no other lens detects?*

Twelve software projects were built from scratch, each in a single 2–4 hour session, all
under the same instrument (`versus-claude 0.14.2`, homogeneity verified by hash), producing
**1,100 critique findings** and 1,029 distinct defects across 130 modules.

**No lens showed zero exclusive contribution** — in no project, and under four independent
clusterings of what counts as "the same defect", including the union of all four, which
collapses 1,029 defects into 668. Mean overlap 11%.

Two unplanned findings: the **activation criterion** is the fragile part, not the taxonomy;
and the method produces commitments — architectural premises, resolutions of critical
findings — that **no mechanism ever re-confronts** with the built artifact.

Everything needed to recompute the paper's numbers is archived here and runs **offline, with
no API keys and no third-party Python packages**. See *Reproduzir* below; the documents are
in Portuguese.
</details>

---

## O que há aqui

| caminho | conteúdo |
|---|---|
| **[`RESULTADO-RO3.md`](RESULTADO-RO3.md)** | **o resultado completo** — três achados, limitações medidas, sete correções de percurso |
| [`ERRATA-CRITERIO-DUPLICA.md`](ERRATA-CRITERIO-DUPLICA.md) | esclarecimento sobre a cláusula de viés do §3 do protocolo — o protocolo não é alterado |
| [`ADJUDICACAO-ETI.md`](ADJUDICACAO-ETI.md) | a adjudicação da lente Ética: critério datado, cegamento, dois juízes — e por que a fronteira não reproduz |
| [`INSTRUCOES-REDACAO.md`](INSTRUCOES-REDACAO.md) | como usar os achados no artigo, e o que **não** afirmar |
| [`LOG-OPERACAO.md`](LOG-OPERACAO.md) | os 12 projetos, os **7 descartes** e as violações de protocolo |
| [`PROJETOS.md`](PROJETOS.md) | o desenho da amostra — que lentes cada projeto deveria exercitar |
| [`ACHADOS-TAXONOMIA.md`](ACHADOS-TAXONOMIA.md) | achados sobre os critérios das lentes |
| [`ACHADOS-METODO.md`](ACHADOS-METODO.md) | M1–M8, sobre gates, hooks e safeguards |
| [`CLASSIFICACAO-FORMA-VS-QUALIDADE-FASE2.md`](CLASSIFICACAO-FORMA-VS-QUALIDADE-FASE2.md) | a regra que autoriza uma trava — **normativo** |
| [`patches/`](patches/) | especificação corretiva pós-lote, com evidência por item |
| [`FORMATOS.md`](FORMATOS.md) | schema dos JSONs, colunas da matriz, convenção de nomes |
| [`analise/`](analise/) | o pipeline: parser, Passos 1–5, remarcação cega, estimativa de lentes, figuras |
| [`instrumento/`](instrumento/) | o bundle `versus-claude 0.14.2` que rodou os doze |
| `T21…T32/` | os doze projetos |

## Um projeto, por dentro

```
T29-retencao/
├── ENUNCIADO.md                       o problema, congelado antes de começar
├── RETRABALHO.md                      defeitos pós-entrega (zero) e achados pré-entrega
├── specs/
│   ├── technical/architecture.md      arquitetura, V(1) … V(N), uma por iteração
│   ├── design/coverage-matrix.md      A MATRIZ — id | módulo | lente | severidade | descrição
│   ├── validation/  datasets/  references/  …
└── .versus/state.json                 decisões, critérios de saída, lentes por iteração
```

A **matriz de cobertura** é o dado primário. O `state.json` traz o registro estruturado das
lentes declaradas ativas em cada iteração do laço crítica↔revisão, mais as decisões
narrativas — que é de onde vieram todos os achados de método.

## Reproduzir

**Requisitos: Python 3.10 ou superior. Nada além disso.** O pipeline é stdlib puro — sem
pacotes de terceiros, inclusive nas chamadas HTTP. Verificável:

```bash
python3 tools/checar_dependencias.py
```

### Caminho A — recomputar os números do paper *(offline, sem chave nenhuma)*

**É este que reproduz tudo o que o artigo afirma.** Roda a partir das saídas já arquivadas;
não faz chamada de rede.

```bash
python3 analise/test_formato.py                    # 18 casos adversariais de formato
python3 analise/ro3_analise.py T21-certificados T24-catalogo T22-plantoes T23-canario \
    T25-orcamento T26-extratos T27-despesas T28-agenda T29-retencao T30-notifica \
    T31-precos T32-triagem                          # Passos 1–5 sobre os doze
python3 analise/cegar_duplicatas.py comparar T22-plantoes \
    analise/cego/T22-plantoes-resposta.json         # κ, a partir da resposta arquivada
python3 analise/sonda_eti_refutada.py               # a sonda retratada e sua refutação
```

O agregado dos doze está em [`analise/saidas/AGREGADO-12.md`](analise/saidas/AGREGADO-12.md).

**O `versus-claude 0.14.2` não é necessário.** Ele gerou o corpus, que está arquivado; a
cópia do bundle usada está em [`instrumento/`](instrumento/) e o pipeline lê os nomes
canônicos das lentes de lá. Um `$VERSUS_BUNDLE` pode apontar para outro, se quiser.

### Caminho B — reexecutar a coleta *(exige chaves e ferramentas externas)*

Só para quem quiser **refazer** as avaliações em vez de recomputar a partir delas. Nada do
que o paper afirma depende disto.

```bash
OPENAI_API_KEY=… python3 analise/cegar_duplicatas.py julgar T22-plantoes gpt-5.4-2026-03-05
QWEN_API_KEY=…   python3 analise/reestimar_lentes.py T22-plantoes --versao 1 --n 3 --modelo qwen3.6-27b
                 python3 analise/reestimar_lentes.py T22-plantoes --versao 1 --n 3 --modelo kimicode
```

Ferramentas: `ollama` para o juiz local, o CLI `kimi` com sessão OAuth, e chaves da OpenAI
e do DashScope. Ausentes, os scripts **falham com mensagem explícita** — nunca com
resultado silenciosamente diferente. Reexecução não reproduz os JSONs byte a byte: os
modelos são estocásticos e alguns não expõem `seed`.

### As figuras do paper

```bash
python3 analise/figuras.py --conferir            # recomputa os dados e confere
Rscript --vanilla analise/figuras/make_figures.R # renderiza (R 4.5 + ggplot2)
```

Nenhum número é digitado no script de plotagem: os quatro conjuntos são recomputados do
corpus e escritos em `analise/saidas/figuras/*.csv`. O **`--conferir`** compara as tabelas
recomputadas do §1.4 e do §5.1, célula a célula, com o que está escrito no
`RESULTADO-RO3.md`, e sai com código 1 se divergirem.

Só a renderização precisa de R. Quem quiser apenas conferir o que está plotado roda o
primeiro comando, que é stdlib como o resto do pipeline.

### Formatos

Schema dos JSONs, colunas da matriz e a convenção `T21–T32`: **[`FORMATOS.md`](FORMATOS.md)**.

## Números

```
corpus            12 projetos · 1.100 achados · 1.029 defeitos distintos · 130 módulos · 37 h
descartes         7, todos documentados
instrumento       versus-claude 0.14.2 — server.js md5 9dfee8be… idêntico nos doze
agente gerador    claude-opus-5 — uniforme nos doze, verificado nos transcripts
ortogonalidade    0 lentes com contribuição exclusiva zero, em 4 clusterizações
sobreposição      média 11% · mínimo 2% (ARQ) · máximo 33% (SUS)
pares de lentes   41 de 171 (24%) compartilham algum defeito · maior Jaccard 0,10 (DES×SUS)
ARQ × PRE         Jaccard 0,00 — a suspeita a priori do protocolo não se confirma
robustez          união de 4 avaliadores: 1.029 → 668 clusters, nenhuma lente em zero
```

## O que este corpus não é

Não é amostra aleatória de software real. São doze projetos de porte comparável — 8 a 12
módulos, sessão única —, com domínios **escolhidos** para exercitar as lentes condicionais,
todos gerados pelo mesmo agente.

O resultado diz que **nenhuma lente é redundante** no corpus medido, sob um critério
pré-registrado. Não diz que a taxonomia é completa nem ótima.

## Notas de honestidade

**A taxonomia medida não é a publicada.** Os gatilhos de SUS, UX e GOV foram reescritos
durante o experimento, porque GOV e SUS ficaram em **0 ativações de 7 projetos** e nenhuma
reescrita de enunciado resolvia. Detalhe em `RESULTADO-RO3.md` §5.6.

**Sete leituras intermediárias foram contrariadas por dado posterior**, cinco delas por
projeto subsequente. Estão tabuladas em `RESULTADO-RO3.md` §6, com o que se afirmou e o que
o dado mostrou. A entrada sobre estimadores foi reescrita quatro vezes.

**O gate de testes travou em 4 de 12 projetos** e foi contornado nos quatro, sempre com a
saída real e sempre declarado pelo agente. Nenhuma falsificação ocorreu; o achado é que o
mecanismo não a impediria.

**Uma cláusula do protocolo é ambígua, e a errata diz qual é a leitura correta.** O §3
descreve a direção do viés da marcação de duplicatas usando "conservador" em dois sentidos
incompatíveis. O protocolo fica como está — é o pré-registro —, e
[`ERRATA-CRITERIO-DUPLICA.md`](ERRATA-CRITERIO-DUPLICA.md) registra a leitura correta: a
regra enviesa **a favor** da hipótese, e a união das quatro clusterizações é o corretivo
desenhado para isso.

**A cadeia de correção está no repositório, incluindo o que não deu certo.** A sonda lexical
que sustentaria a adjudicação de ETI foi **retratada** — media densidade de prosa sobre humanos
e homônimos, não dano — e está preservada em
[`analise/sonda_eti_refutada.py`](analise/sonda_eti_refutada.py), com a refutação no mesmo
comando. O que a substituiu está em [`ADJUDICACAO-ETI.md`](ADJUDICACAO-ETI.md).

**Há cinco chaves privadas sintéticas** em `T21-certificados/specs/datasets/`, geradas com
`openssl` para a suíte de testes daquele projeto. Ver a
[nota no diretório](T21-certificados/specs/datasets/NOTA-CHAVES-DE-TESTE.md) — a verificação
leva segundos e não depende de confiar em quem publicou.

---

## Licença e citação

Corpus e documentos sob **CC-BY-4.0**; o pipeline em `analise/` é adicionalmente MIT. Ver
[`LICENSE`](LICENSE).

Para citar, use [`CITATION.cff`](CITATION.cff) — o GitHub monta a citação formatada no
botão *Cite this repository*, na barra lateral.

**No artigo, cite o DOI de conceito:** [`10.5281/zenodo.21908907`](https://doi.org/10.5281/zenodo.21908907).
Ele resolve sempre para a versão mais recente, então uma correção futura no corpus não
invalida a citação. O DOI desta versão especificamente é
[`10.5281/zenodo.21908908`](https://doi.org/10.5281/zenodo.21908908) (v1.0).

### As versões arquivadas

| versão | DOI | o que acrescenta |
|---|---|---|
| **v1.0** | [`10.5281/zenodo.21908908`](https://doi.org/10.5281/zenodo.21908908) | **o corpus da RO3 tal como medido** — taxonomia X, congelada |
| v1.1 | [`10.5281/zenodo.21925568`](https://doi.org/10.5281/zenodo.21925568) | experimento dos gatilhos reescritos · adjudicação de ETI · sonda refutada |
| v1.2 | [`10.5281/zenodo.21926465`](https://doi.org/10.5281/zenodo.21926465) | executabilidade, formatos, identificador do modelo gerador |
| v1.3 | [`10.5281/zenodo.21939285`](https://doi.org/10.5281/zenodo.21939285) | errata sobre a cláusula de viés do critério de duplicatas |
| v1.4 | [`10.5281/zenodo.21952689`](https://doi.org/10.5281/zenodo.21952689) | figuras recomputáveis do corpus · **correção do painel κ do §5.1** |
| v1.5 | [`10.5281/zenodo.21967113`](https://doi.org/10.5281/zenodo.21967113) | **correção da faixa de similaridade** da redeclaração, agora Jaccard nomeado |
| v1.6 | [`10.5281/zenodo.21984162`](https://doi.org/10.5281/zenodo.21984162) | denominadores das divergências · **quatro `b = 0` que eram estruturais** |
| v1.7 | *(DOI ao indexar)* | legibilidade da figura κ — recorte, alinhamento e rótulos de eixo · nenhum valor muda |

**A distinção importa para quem cita.** A **v1.0** é o corpus da RO3 como medido. Quem cite
resultados da RO3 pode usar o DOI de conceito; quem cite os números da **adjudicação de ETI**
ou do **experimento dos gatilhos** precisa da **v1.1 ou posterior**, porque eles não existem
na v1.0.

**Três versões corrigem números ou enquadramento, não só acrescentam.** Quem cite o
**painel κ do §5.1** precisa da **v1.4 ou posterior** — as anteriores comparam arestas
declaradas contra fechos transitivos. Quem cite a **similaridade das justificativas de
redeclaração** precisa da **v1.5 ou posterior** — as anteriores trazem uma faixa cujo piso é
artefato de heurística de biblioteca. Quem cite as **taxas de divergência de ativação**, ou
a afirmação de que elas correm numa direção só, precisa da **v1.6 ou posterior** — nas
anteriores os denominadores não existem e quatro dos cinco zeros aparecem sem a ressalva de
que eram estruturais. Nenhuma conclusão muda em nenhum dos três casos.

> **Nota sobre esta tabela.** Cada versão só pode listar os DOIs das **anteriores** — o DOI
> de uma versão é emitido no momento em que ela é arquivada, depois de o conteúdo estar
> fechado. A tabela acima, portanto, sempre estará uma linha atrás de si mesma. O DOI de
> conceito não tem esse problema e é o que resolve sempre para a mais recente.

INDT · Jasmine Moreira ([0000-0002-3744-9528](https://orcid.org/0000-0002-3744-9528)) · 2026
