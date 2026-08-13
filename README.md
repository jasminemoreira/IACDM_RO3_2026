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

---

## O que há aqui

| caminho | conteúdo |
|---|---|
| **[`RESULTADO-RO3.md`](RESULTADO-RO3.md)** | **o resultado completo** — três achados, limitações medidas, sete correções de percurso |
| [`ADJUDICACAO-ETI.md`](ADJUDICACAO-ETI.md) | a adjudicação da lente Ética: critério datado, cegamento, dois juízes — e por que a fronteira não reproduz |
| [`INSTRUCOES-REDACAO.md`](INSTRUCOES-REDACAO.md) | como usar os achados no artigo, e o que **não** afirmar |
| [`LOG-OPERACAO.md`](LOG-OPERACAO.md) | os 12 projetos, os **7 descartes** e as violações de protocolo |
| [`PROJETOS.md`](PROJETOS.md) | o desenho da amostra — que lentes cada projeto deveria exercitar |
| [`ACHADOS-TAXONOMIA.md`](ACHADOS-TAXONOMIA.md) | achados sobre os critérios das lentes |
| [`ACHADOS-METODO.md`](ACHADOS-METODO.md) | M1–M8, sobre gates, hooks e safeguards |
| [`CLASSIFICACAO-FORMA-VS-QUALIDADE-FASE2.md`](CLASSIFICACAO-FORMA-VS-QUALIDADE-FASE2.md) | a regra que autoriza uma trava — **normativo** |
| [`patches/`](patches/) | especificação corretiva pós-lote, com evidência por item |
| [`analise/`](analise/) | o pipeline: parser, Passos 1–5, remarcação cega, estimativa de lentes |
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

## Reproduzir a análise

```bash
python3 analise/test_formato.py          # 18 casos adversariais de formato
python3 analise/ro3_analise.py T21-certificados T24-catalogo … T32-triagem
```

O agregado dos doze está em [`analise/saidas/AGREGADO-12.md`](analise/saidas/AGREGADO-12.md).

A remarcação cega e a estimativa de lentes chamam modelos externos e exigem
`OPENAI_API_KEY` ou `QWEN_API_KEY` no ambiente. Sem elas, falham com mensagem explícita —
nunca com resultado silenciosamente diferente.

## Números

```
corpus            12 projetos · 1.100 achados · 1.029 defeitos distintos · 130 módulos · 37 h
descartes         7, todos documentados
instrumento       versus-claude 0.14.2 — server.js md5 9dfee8be… idêntico nos doze
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

**Duas versões, e a distinção importa para o artigo.** A **v1.0** é o corpus da RO3 tal como
medido — a taxonomia X, congelada. A **v1.1** acrescenta o que veio depois: o experimento dos
gatilhos reescritos e a adjudicação de ETI. Um artigo que cite resultados da RO3 pode citar o
DOI de conceito; um que cite os números da adjudicação **precisa** da v1.1, porque eles não
existem na v1.0.

INDT · Jasmine Moreira ([0000-0002-3744-9528](https://orcid.org/0000-0002-3744-9528)) · 2026
