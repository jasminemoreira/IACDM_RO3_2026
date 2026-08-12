# Lições do ciclo v1.0 — T26

Lições sobre **este projeto**: domínio, stack, padrões e premissas erradas. Alimentam o próximo
ciclo. Não são lições sobre a metodologia.

---

## 1. Identidade da OBSERVAÇÃO não é identidade do EVENTO

O erro mais caro do ciclo, e estava no **desenho**, não no código.

V(1) usava o hash canônico `(conta, data, valor, descrição normalizada)` para duas perguntas
diferentes: "esta linha já foi importada?" e "este é o mesmo evento financeiro?". A consequência foi
uma **contradição entre invariantes gravada no esquema do banco**: o `UNIQUE` que garantia a
idempotência (I8) proibia a preservação de colisão legítima (I6), porque duas transações realmente
distintas de R$ 12,00 no mesmo dia produzem o mesmo hash de uma duplicata.

A correção não foi uma regra a mais — foi **separar os dois conceitos**. E a primeira tentativa de
separá-los falhou de um jeito instrutivo: `(fonte, arquivo_hash, índice de linha)` identifica o
ARQUIVO, não a observação, então reimportar uma janela sobreposta (arquivo diferente) gerava
identidade nova e o `UNIQUE` deixava de impedir qualquer coisa. O caso de uso real quebrou em
silêncio e só a segunda rodada de crítica percebeu.

**O que funciona:** `ChaveNatural` = `(fonte, conta, FITID)` quando há identificador nativo; senão
`(fonte, conta, data, valor, descrição bruta, ordinal)`, onde o **ordinal** é a posição da linha
dentro do grupo de linhas idênticas. O ordinal distingue as duas transações legitimamente iguais e
se reproduz igual na reimportação, resolvendo I6 e I8 ao mesmo tempo.

**Armadilha associada:** o ordinal precisa ser CALCULADO por alguém. Ele existiu como campo no tipo
por um bom tempo sem que nenhum componente o atribuísse, e o sintoma apareceu longe da causa — a
contagem de VAL-3 não fechava num teste de conciliação.

## 2. Critério de zero-defeito só é verificável se o dataset puder produzir o defeito

"Zero falso positivo" (VAL-2) foi uma frase sem teste capaz de falhar até o gerador **plantar**
colisões legítimas no dataset. O mesmo para estornos (premissa A7) e para duplicatas cross-source
com descrição divergente (premissa A6).

O `fixture-generator` não é infraestrutura de teste: é o que transforma o critério de aceitação em
algo mensurável, e por isso justificou um módulo inteiro do orçamento de 8-12. Um dataset que só
contém casos fáceis produz uma suíte verde que não prova nada.

## 3. Calibrar contra o próprio dataset sintético é validação circular

O desenho previa estimar os pesos `m` e `u` de Fellegi-Sunter contra o ground truth do gerador. Mas
a distribuição desse ground truth foi escolhida por este projeto: os pesos ficariam ótimos para o
mundo que inventamos, sem garantia transferível para extratos reais.

A resposta certa não foi calibrar melhor — foi **remover** o aparato probabilístico e substituí-lo
por uma **rubrica determinística de pontos por campo**, declarada em `specs/technical` com
justificativa por peso. Sob exigência de zero falso positivo, com a faixa intermediária indo para
revisão humana de qualquer forma, uma rubrica transparente entrega mais que um modelo não
calibrável — e é auditável, que é o que o domínio contábil pede.

Fellegi-Sunter permanece em `specs/references` como **fundamentação do desenho** (a intuição de que
campos raros discriminam mais), não como algoritmo implementado.

## 4. Peculiaridades da stack

**`ofxtools` valida contra a especificação e RECUSA arquivos não conformes.** Ele rejeitou o nosso
próprio fixture de teste por faltar `SIGNONMSGSRSV1`. Isso é feature, não obstáculo — é exatamente o
comportamento que motivou fixar a versão. Consequências práticas: o gerador precisa emitir OFX
conforme (com bloco de signon completo), e precisa emitir os **não-conformes separadamente e de
propósito**, para exercitar o caminho de erro.

**`xml.etree` recusa entidades EXTERNAS mas expande as INTERNAS.** Verificado empiricamente: um
`SYSTEM "file:///etc/passwd"` resulta em `ParseError: undefined entity`, então a metade XXE do risco
de OFXv2 já vem fechada pela plataforma. Mas a expansão exponencial de entidades internas é real e
precisou de mecanismo próprio (recusa de `<!DOCTYPE`/`<!ENTITY` mais teto de tamanho). A mitigação
inicial estava escrita para o vetor errado, e só foi descoberta porque foi **testada** em vez de
assumida.

**Codecs de byte único não sinalizam encoding errado.** `cp1252` e `latin-1` aceitam quase qualquer
sequência, então ler um arquivo UTF-8 declarando `cp1252` TEM SUCESSO e produz mojibake silencioso —
a descrição muda, o hash muda, a dedup falha sem sinal. Confiar em `UnicodeDecodeError` cobre só a
direção rara. O teste determinístico que funciona: se o perfil declara codec de byte único e os
bytes são UTF-8 válido com sequências multibyte, recusar.

**Serializar coleções de chaves com delimitador é armadilha** quando o delimitador aparece no
conteúdo — e aqui aparece por construção, porque `ChaveNatural.texto()` usa `|` internamente. JSON
resolve; concatenação não.

## 5. Corrigir a classe de defeito no desenho não imuniza a implementação

A lente Performance encontrou o `O(n²)` e o padrão `N+1` na arquitetura V(1), e a implementação os
**reintroduziu três vezes**: um `any()` dentro de um laço sobre a outra coleção; uma consulta SQL por
bloco no composition root; e um `set()` reconstruído dentro de uma compreensão de lista.

Duas dessas correções foram feitas por dedução, estavam corretas — e **não eram o gargalo**. Só a
medição por estágio (parse 1,3 s, construção 0,1 s, candidatos 0,0 s, gravação 0,2 s, classificação
0,1 s) localizou a linha culpada, ao mostrar que o custo estava fora de tudo que havia sido medido.

O mesmo padrão apareceu em `CTL-01`: o laço de realimentação da resolução humana foi **projetado
corretamente** em V(3) e **implementado errado** (o dicionário era indexado por `pendencia_id`
enquanto a consulta usava a chave do par), de modo que a camada L0 nunca disparava e a mesma
pendência voltaria à fila todo mês. Um teste escrito a partir do código jamais pegaria isso; o teste
derivado da spec pegou.

---

## Premissas: o que se confirmou e o que segue aberto

| id | Premissa | Desfecho |
|---|---|---|
| A1 | FITID estável entre downloads | **Neutralizada por desenho.** O sistema funciona com ela falsa: FITID virou apenas uma das formas da `ChaveNatural`, e se a instituição o alterar o caso desce para avaliação ou revisão em vez de escapar |
| A4 | Blocking mantém blocos pequenos | **Virou propriedade garantida** pelo teto de bloco, com o excedente escalado para revisão |
| A6 | Descrição da contraparte comparável entre fontes | **Confirmada como problema real.** A conciliação automática exige similaridade ≥ 70, logo pares com valor e data exatos mas contrapartes nomeadas de formas diferentes vão para revisão humana. Comportamento conservador MANTIDO por decisão do operador |
| A7 | `abs(valor)` não confunde estorno com duplicata | **SEGUE ABERTA.** A fusão é vetada por sinal oposto e há teste; o inchaço de bloco permanece. Há um teste que AFIRMA a limitação: se ela mudar, ele falha e obriga a revisitar |
| A2, A3, A5 | CSV sem ID nativo; layout do livro estável; todo par tem resposta certa | Mantidas, sem contra-evidência no ciclo |

## O que medir primeiro num v2.0

1. **Extratos reais**, não sintéticos. VAL-1 e VAL-2 valem para os casos plantados; a distribuição
   real dos bancos brasileiros é desconhecida por este ciclo.
2. **Desempenho com base acumulada.** VAL-4 foi medido num banco vazio; SUS-01 aponta que o custo
   cresce com a história, e a janela de 90 dias é o único freio.
3. **A7 com estornos reais** — os três casos que a mitigação não cobre: estorno parcial, estorno
   lançado como crédito de mesma natureza, e o inchaço de bloco.
4. **Volume de fila na prática.** Se a exigência de similaridade de contraparte gerar mais revisão
   do que o analista consegue absorver, a decisão conservadora precisa ser reexaminada — com dados,
   não por preferência.
