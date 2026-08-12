# RETRABALHO — T29-retencao

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-11** |

CA-1 a CA-4, congelados na Fase 0 antes de codar, verificados na Fase 6: **141 instâncias
de teste, 0 falhas**, 50 negativos para 49 positivos (o mínimo exigido é 1:2, superado). O
codec Gorilla foi portado literalmente de R1 §4.1.1/§4.1.2 e a fidelidade **medida** — o
comando `report` reproduz os quatro perfis da sondagem da Fase 0 com desvio de 0,0–0,1%,
*"o que só acontece se todos os parâmetros do codec estiverem certos"*.

Veredito da Fase 7: atende aos requisitos da Fase 0.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### Uma premissa da arquitetura refutada por medição

Detalhado em `ACHADOS-METODO.md` §M8. A premissa **P-A8** dizia *"a migração é streaming
ponto a ponto via Iterator"*; a medição mostrou pico de memória **linear na entrada**, ~150
bytes por ponto, 330 MB de RSS para 2 milhões.

> *"A premissa está refutada pelo próprio código."*

E o modo de descoberta é o que dá o valor: apareceu num **teste de outra propriedade**. Ao
matar o ingest com SIGKILL aos 0,5 s e 1,0 s para verificar atomicidade, **zero chunks
tinham sido escritos** — não é lentidão, é a entrada inteira sendo agrupada antes de
qualquer escrita.

O registro também recusa a saída fácil de alegar fora de escopo: *"throughput/latência
estão explicitamente fora de escopo, mas 'memória proporcional à entrada' nunca foi
declarada — o OPOSTO foi declarado (P-A8)"*.

Corrigido para fluir por janela: memória plana em 1,5 MB de 10 mil a 500 mil pontos, de
151 para 3 bytes por ponto, com teste de regressão comparando o pico entre 2 e 20 chunks
cheios.

### Três das cinco falhas iniciais eram erros nas SPECS, não no código

E o registro diz por que isso era esperado: *"é o resultado esperado de testar contra as
specs em vez de contra a implementação"*.

O caso mais claro: `METADATA_SIZE` documentado como **20 bytes** quando
`struct.calcsize('>2LfL')` dá **16**. O número errado tinha se propagado para
`specs/technical/formatos-armazenamento.md`, `specs/models/tipos.md` e o README, porque foi
**transcrito de um resumo** em vez de calculado.

Isto é a mitigação do AP3 adotada no T26 — derivar o mapa de testes das specs, não do
código — dando um retorno que não estava previsto: ela **encontra erros nas specs**, não só
no código.

### Um campo de 6 bits que não comporta o valor 64

Achado pelo micro-check S7 **antes de qualquer teste formal**. O campo de comprimento
significativo de R1 §4.1.2 tem 6 bits, que representam 0..63, mas o comprimento
significativo do XOR pode ser **64** — quando o XOR tem simultaneamente o bit 63 e o bit 0
setados.

Caso concreto reproduzido: `-inf (0xFFF0000000000000) XOR 5e-324 (0x0000000000000001) =
0xFFF0000000000001`, lead=0, trail=0, significante=64.

É conformidade com especificação externa no nível em que ela realmente morde, e a mesma
classe do achado do INRC-II no T22.

### Traceback vazando para o operador em três caminhos

`cli.main()` capturava **apenas** `SeriesError`. Qualquer outra exceção subia até o `runpy`
e o operador recebia traceback de Python com exit 1, em vez de mensagem com exit 2. Três
caminhos concretos: CSV com lixo (`ValueError`), arquivo inexistente (`OSError`), duração
inválida.

### A lacuna que este projeto nomeia, e ela é a mais importante do lote

**O operador escolheu explicitamente *"Aceito o que você rodou; não executei eu mesmo"*.**

O registro não difere isso em silêncio — declara o que ficou sem cobertura: *"o julgamento
de se as mensagens de erro são compreensíveis para quem não escreveu o código, se os
relatórios são acionáveis, e se o modelo mental da CLI faz sentido"*.

E aponta a evidência que demonstra o custo, dentro do próprio projeto:

> *"4 defeitos sobreviveram ao 'parece tudo bem' e só apareceram quando alguém executou os
> casos"*

Os quatro são os três tracebacks mais o P-A8. **Foram encontrados depois de o operador
dizer que parecia tudo bem.** É a evidência mais direta do lote de que aprovação não é
verificação — e ela vem de um projeto onde o human-AV foi declinado, o que a torna
autodemonstrativa.

Sexto dos nove projetos, e o primeiro sem human-AV pleno por escolha explícita registrada.

### Dois pontos de julgamento decididos pelo operador

*"Manter os dois como estão"*: CSV vazio resulta em exit 0 com `written:0` — transformar em
erro impediria ingestão incremental legítima; e `read` com `--from >= --to` resulta em
saída vazia com exit 0, correto por definição de intervalo semiaberto. Ambos documentados
em teste.
