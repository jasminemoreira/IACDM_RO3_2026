# Lições do projeto T29 — ciclo v1.0

Lições sobre **este projeto** (domínio, stack, premissas erradas), não sobre a metodologia.
Escritas para que um v2 ou um post-mortem leia o que este ciclo aprendeu.

---

## L1 — A razão de compressão do Gorilla é propriedade do DATASET, não do algoritmo

**O que se descobriu:** os 1,37 byte/ponto publicados em R1 são a média do ODS do Facebook —
dado de monitoração dominado por gauges inteiros estáveis. Medindo o **mesmo algoritmo** em
perfis diferentes, com o codec implementado neste projeto:

| Perfil | B/ponto | Razão |
|---|---|---|
| gauge inteiro estável | 0,33 | 48,5× |
| pontos faltando | 0,40 | 40,1× |
| jitter de timestamp | 0,64 | 24,9× |
| contador monotônico | 2,67 | 6,0× |
| temperatura, 1 decimal | 6,41 | 2,5× |
| float de alta precisão | 6,63 | 2,4× |

**Variação de 20× entre o melhor e o pior caso.** No pior perfil, 6,63 B/ponto — 4,8× pior que
o número publicado.

**Consequência prática:** qualquer promessa de razão de compressão para um TSDB é inverificável
sem fixar o dataset. Quem for avaliar este tipo de ferramenta deve medir no **próprio** perfil,
nunca aceitar o número do paper. Foi por isso que o critério de aceitação deste projeto virou
"medir e reportar", não "atingir X×".

**Onde isso foi medido antes de existir código:** `specs/datasets/perfis-de-serie.md`. A
implementação depois reproduziu os quatro números com desvio de 0,0–0,1%, o que serve como
teste de fidelidade ao paper.

## L2 — O gargalo do Gorilla não é o valor, é a REGULARIDADE do timestamp

**Medido:** timestamps regulares custam **1,00 bit/ponto** (96% caem no caso `D = 0`). Com
jitter de ±1 s, o custo vai a **6,84 bits/ponto** — **6,8× pior**, e isso acontece *sem que
nenhum valor mude*.

**Insight de domínio:** todo o ganho da compressão de timestamp está concentrado num único
caso do algoritmo. Uma fonte de dados que adicione jitter (retry de rede, agendador
impreciso, timestamp de recebimento em vez de de coleta) destrói metade do benefício da
compressão sem que nada pareça errado. **Vale mais alinhar a coleta que otimizar o codec.**

## L3 — Duas fontes autoritativas do mesmo domínio podem se contradizer

R6 (Whisper) fixa **um** valor de 8 bytes por slot. R9 (Thanos) preserva **quatro** agregados
(min/max/sum/count) por ponto derivado. Isso não é detalhe: significa que **o formato Whisper
não pode representar um tier agregado no modelo do Thanos**, e o projeto tinha adotado os dois.

**Como se resolveu, e é a parte que importa:** a contradição desaparece ao notar *por que* R9
guarda quatro agregados — para poder **re-agregar sem erro**. E aí a aritmética resolve: dos
cinco métodos de R6, **`min`, `max`, `sum` e `last` são associativos** sob re-agregação
(mínimo de mínimos é o mínimo, soma de somas é a soma), e **só `average` não é**. Logo:
cascata é legítima com quatro dos cinco métodos, e `average` só pode ser derivado do tier cru.

**Regra que fica para o v2:** ao compor dois sistemas de referência, procure a *razão* de cada
escolha antes de adotar as duas — a incompatibilidade costuma estar num caso particular, não
no todo.

## L4 — Papers e docs deixam a CODIFICAÇÃO DE CAMPO implícita, e é sempre lá que o port quebra

Três lacunas na mesma classe, todas descobertas por execução e nenhuma delas resolvida pelo
texto da fonte:

| Lacuna | Por que quebra |
|---|---|
| Faixas assimétricas `[-63, 64]` em 7 bits | 7 bits em complemento de dois dão `[-64, 63]`. `D = 64` **precisa** caber e `D = -64` **não**. Solução: gravar `D - lo` |
| Comprimento significativo pode ser **64**, e o campo tem 6 bits | Ocorre em `-inf ⊕ 5e-324` (bit 63 e bit 0 setados). Gravar 64 em 6 bits trunca para 0. Solução: gravar `significant - 1` |
| `prev_delta` inicial não declarado | Muda o custo do 2º ponto do bloco, e uma afirmação errada sobre isso entrou nas nossas specs |

**A pior das três** é a do comprimento 64: um codec com esse bug **passa em todos os perfis de
série realistas** e só quebra em dado patológico. Sem o caso-limite `-inf` seguido de
subnormal na bateria de testes, o defeito ia para produção.

**Regra que fica:** ao portar um algoritmo bit a bit, escreva primeiro os testes dos
**extremos de cada campo** — não das entradas típicas.

## L5 — Quando a fonte dá a FÓRMULA e o RESULTADO, a fórmula é a autoridade

Duas vezes no mesmo ciclo, um número transcrito de resumo estava errado enquanto a fórmula na
mesma fonte estava certa:

1. **Fase 0:** um resumo muito citado do paper do Gorilla lista faixas de bucket diferentes das
   do paper. Pego porque li o PDF original.
2. **Fase 6:** as specs deste projeto diziam que o Metadata do Whisper tem **20 bytes**.
   `struct.calcsize('!2LfL')` = **16**, e os quatro campos listados na mesma linha somam 16. O
   número veio de um resumo; a fórmula estava ali do lado. Propagou para 6 arquivos, incluindo
   o README.

O segundo caso é a lição amarga: **eu já tinha pego essa exata classe de erro e não
generalizei a regra.** O código nunca esteve errado (usa `calcsize`); a documentação esteve.

## L6 — Premissa refutada: `write()` não era streaming, apesar do padrão Iterator

A arquitetura declarava (P-A8) que o fluxo era ponto a ponto via `Iterator`, e o padrão
Iterator/generator foi escolhido na Fase 1 exatamente para isso. A implementação de
`store_f2.write()` agrupava **toda** a entrada num dicionário antes de escrever o primeiro
chunk:

| Entrada | Pico de memória (antes) | Depois |
|---|---|---|
| 10.000 pontos | 1,9 MB (151 B/ponto) | 1,5 MB |
| 100.000 pontos | 15,4 MB (154 B/ponto) | 1,5 MB |
| 500.000 pontos | 74,7 MB (149 B/ponto) | 1,5 MB |
| 2.000.000 pontos | **330 MB de RSS** | plano |

**Como foi descoberto:** por acidente, testando atomicidade. Ao matar o `ingest` com `SIGKILL`
aos 0,5 s, **nada havia sido escrito** — não era lentidão, era a entrada inteira sendo
bufferizada.

**Insight que vale para qualquer projeto:** escolher o *padrão* Iterator não garante
comportamento de streaming; garante só a *assinatura*. A propriedade tem de ser testada, e o
teste tem de medir **consumo**, não resultado — porque o defeito não altera nenhuma saída.
O teste que ficou compara o pico entre 2 e 20 chunks **cheios** (a primeira versão do teste
comparava chunk cheio com chunk parcial e media preenchimento, não buffering).

## L7 — Os dois formatos têm domínios de DADO diferentes, não só contratos de acesso diferentes

Foi o achado central da Fase 0 e sobreviveu intacto até o produto:

| | F1 (slot fixo) | F2 (bitstream) |
|---|---|---|
| Timestamp | 4 B, alinhado ao slot, **teto em 2106** | 64 bits, arbitrário |
| Dois pontos no mesmo intervalo | **colidem** | coexistem |
| Acesso | aleatório por slot | sequencial por chunk |
| Custo medido | **360 B/ponto** (pré-alocado) | **1 B/ponto** |

**Logo a migração não é simétrica:** F1 → F2 é sempre total; F2 → F1 pode perder. E a
diferença de custo medida é de **~360×** no mesmo dado — F1 pré-aloca o arquivo inteiro na
criação, o que é o preço do tamanho previsível.

**Decisão que se provou certa:** o contrato da porta expõe **só iteração sequencial** (o mínimo
comum) e declara as diferenças em `capabilities()` em vez de escondê-las. E o `precheck` da
migração compara capacidades **contra os dados**, não contra uma flag — sem isso, toda migração
F2 → F1 abortaria por causa dos 32 bits de timestamp, inclusive quando os dados cabem.

## L8 — Validade-por-timestamp: o round-robin do Whisper já É a expiração

Descoberto ao tentar conciliar dois mecanismos que pareciam concorrentes: um arquivo
round-robin sobrescreve o slot mais antigo ao dar a volta, **e** o projeto tinha um `expire()`
explícito.

A resposta não era escolher. No Whisper, um slot só é válido se o timestamp gravado nele for
igual ao timestamp **esperado daquela posição** — então ao dar a volta o slot antigo passa a
ter timestamp que não corresponde e **já está expirado por definição**. Um mecanismo, não dois.

**Consequência:** `expire()` em F1 é um no-op que apenas *reporta* a fronteira efetiva. E a
invariante "retenção efetiva ≥ retenção nominal" tem semântica uniforme nos dois formatos: F1
a deriva do tamanho do arquivo, F2 do `base_ts` do chunk sobrevivente mais antigo.

## L9 — Estado que pode ser DERIVADO do dado não deve ser armazenado

A versão intermediária da arquitetura resolveu "falta modelar o estado de progresso da
retenção" **armazenando** uma marca d'água. Isso criou duas escritas atômicas (o dado e o
header) sem transação entre elas — e uma falha na janela entre as duas, combinada com a regra
"timestamp duplicado é erro", travava a retenção **permanentemente**.

A versão final percebeu que **o dado derivado já contém o estado**:
`derived_through_ts(tier) = max(base_ts dos chunks) + block_seconds`. Com isso:

- não há duas escritas, logo não há janela;
- re-derivar produz o **mesmo nome de arquivo**, sobrescrito atomicamente ⇒ idempotente por construção;
- recomputar depois de corrigir a configuração é apagar o chunk (antes era impossível);
- o estado não pode divergir do disco, porque **é** o disco.

**Padrão que vale levar:** diagnóstico certo ("falta estado") com cura errada ("guardar o
estado"). Antes de dar casa a um estado novo, verifique se ele já é derivável do que existe.

## L10 — `nan != nan` e `0.0 == -0.0` invalidam silenciosamente qualquer teste de lossless

Num codec sem perda de ponto flutuante, comparar valores com `==` é errado nas duas direções:
`nan == nan` é falso (reprova um round-trip correto) e `0.0 == -0.0` é verdadeiro (aprova um
codec que perdeu o bit de sinal). Toda comparação neste projeto passa por bytes
(`struct.pack('>d', a) == struct.pack('>d', b)`), e há um teste cuja única função é
**demonstrar** que `==` daria o resultado errado.

Também: `float('nan')` genérico **não preserva o payload** do NaN — o teste tem de construir o
NaN a partir dos bits (`0x7ff8000000000001`) para verificar preservação de verdade.

---

## Números finais do ciclo

| | |
|---|---|
| Módulos | 12 (estáveis por 3 versões da arquitetura) |
| Linhas de produção | 2.349 · **zero dependência externa** |
| Testes | 141, sendo 50 negativos / 49 positivos (funções) |
| Achados da crítica adversarial | 109 em 2 rodadas · críticos **19 → 6 → 0** |
| Defeitos achados após o design convergir | **7** (3 no micro-check da implementação, 1 na migração, 3 nos casos de borda) + 1 premissa refutada |
| Erros nas próprias specs, achados pelos testes | **3** |

## O que fica em aberto para um v2

1. **Teste exploratório humano — a lacuna nomeada deste ciclo.** Ninguém além da IA executou a
   CLI. O julgamento de legibilidade de mensagem e acionabilidade de relatório não foi
   exercido. Evidência de que importa: **4 defeitos sobreviveram a um "parece tudo bem"** e só
   apareceram quando os casos foram de fato executados.
2. **Escritor único (`P-A2`) sem trava.** Dois processos no mesmo acervo o corrompem, e nada
   impede.
3. **Journal não é à prova de alteração** (sem encadeamento de hash) e **`crc32` não autentica**.
   Ambos declarados; nenhum mitigado.
4. **Entrada fora de ordem tem comportamento divergente entre F1 e F2** — F1 rejeita o ponto
   retroativo, F2 o aceita reconstruindo o chunk ordenado. Divergência real entre duas
   implementações do mesmo contrato, num canto que nenhuma das duas rodadas de crítica nomeou.
5. **Chimp e Elf ficaram de fora** sendo melhores (Elf: +51% sobre Gorilla). A comparação
   direta, medida no nosso próprio dataset, seria o experimento natural de um v2.
