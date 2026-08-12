# RETRABALHO — T26-extratos

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-10** |

VAL-1 a VAL-8 e UC-1 a UC-5, congelados na Fase 0 antes de codar, **medidos contra ground
truth** e não afirmados:

| critério | medido |
|---|---|
| VAL-1 zero falso negativo | 53/53 duplicatas de reimportação · 10/10 cross-source (7 fundidas, 3 escaladas, nenhuma descartada) |
| VAL-2 zero falso positivo | 4/4 colisões legítimas preservadas |
| VAL-3 | 399/399 no dataset pequeno · 61.872/61.872 no de 50 mil |
| VAL-4 (< 60 s para 50 mil) | **4,9 s** |
| VAL-5 · VAL-6 · VAL-8 | digest idêntico · sem violação · sem float |

41 testes verdes em 7,0 s, execução real verificada (S4). Veredito da Fase 7: *"Atende —
fecho o ciclo"*.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### A Fase 5 achou dez defeitos, e o padrão é o mesmo em todos

Nenhum foi achado lendo código. Os registros dizem como cada um apareceu: *"achada pela
micro-verificação S7, não por teste"*, *"encontradas executando a rubrica do M-06 matcher,
não por teste formal"*, *"por MEDIÇÃO e não por palpite"*.

**O mais grave — a correção da Fase 3 foi desfeita pela implementação da Fase 5.** VAL-4
estourou 120 s contra limite de 60 s por **três padrões quadráticos ou N+1 reintroduzidos**
depois que a arquitetura os havia eliminado. O registro é explícito: *"é exatamente o O(n²)
acidental que PRF-01 e PRF-02 mandaram erradicar, reintroduzido na função de filtro"*. O
pior deles era `any(e.conta == n.conta for n in novas)` dentro do laço sobre `existentes` —
36 mil × 36 mil, mais de 10⁹ comparações.

Isto é uma classe nova, distinta das quatro de `ACHADOS-METODO.md`: ali o problema estava
no teste; aqui a **crítica estava certa, a correção estava completa, e a implementação a
desfez**. Registrado como §M6.

**E a causa raiz real só apareceu por profilagem.** O registro é honesto sobre as duas
tentativas anteriores: *"as duas correções anteriores eram reais mas não eram o gargalo"*.
O gargalo era `novas = [t for t in transacoes if t.chave in set(res.chaves_novas)]` —
reconstruindo o conjunto a cada iteração da compreensão, 36 mil construções de um set de
36 mil elementos.

### Dois defeitos que as lentes previram nominalmente

**LIN.** `ChaveNatural.texto()` usa `|` como separador interno, e a lista de chaves
candidatas de uma pendência foi serializada juntando-as **também com `|`**. O split parte
as chaves ao meio. O registro nomeia: *"é exatamente a classe de defeito que a lente
Linguistics / Grammar cobre — dois níveis de estrutura compartilhando o mesmo delimitador,
sem escape"*.

**MEC.** O adapter OFX recusou um fixture escrito à mão sem o bloco `SIGNONMSGSRSV1`. O
registro conclui que **o adapter está correto** e que *"o comportamento observado é
precisamente o que o achado MEC-01 previu: a biblioteca recusa arquivos não conformes"*.

São os dois casos mais limpos do lote de **achado da Fase 2 antecipando defeito concreto da
Fase 5**, com o vínculo nomeado no registro em vez de reconstruído por mim depois.

### Um falso negativo estrutural que o próprio material da Fase 0 previa

`chave_bloco()` incluía a conta, então duas observações do mesmo evento em contas distintas
caíam em blocos diferentes e o par **nunca era gerado** — o escopo do `dedup-engine`
declara `cross_source=True` e o blocking o anulava em silêncio. O registro aponta o que
faltou: *"aplicar o que a própria pesquisa já depositara: `specs/references/fontes-externas.md`
§2.2"*. A informação estava no repositório de specs e não foi consultada.

### Renovação de sessão recusada, com risco declarado

Oferecida ao operador com recomendação favorável (*"desacoplar implementador de testador,
espírito do S4; e a conversa já é longa, o que é o próprio AP3"*). O operador escolheu
continuar. O registro declara o risco aceito — **viés de confirmação, quem escreveu o
código tende a escrever testes que confirmam** — e adota mitigação: o mapa de testes
derivado das **specs**, não do código.

É a primeira vez no lote que o AP3 é acionado explicitamente e a decisão fica registrada
dos dois lados.

### Caracterização honesta do gate manual

O operador reportou *"Executei e funcionou"* e *"parece ok para mim, podemos fechar"*. O
registro se recusa a chamar isso de mais do que é: *"para não superestimar a evidência num
post-mortem: o que houve foi **VALIDAÇÃO DE ACEITAÇÃO**"*.

É o oposto de AP1, e o segundo caso no lote de agente limitando a força da própria
evidência (o primeiro foi o T22 recusando carimbar o gate).
