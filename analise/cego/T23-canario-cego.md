# Reagrupamento cego de achados — T23-canario

Você recebe 72 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
módulo onde ocorre, a severidade e uma descrição de uma linha.

**Sua tarefa:** agrupar os achados que apontam o MESMO DEFEITO.

Atenção a defeitos **replicados**: quando dois módulos são implementações irmãs do
mesmo contrato, o mesmo defeito pode aparecer em ambos. Se uma única correção na
abstração compartilhada resolveria os dois, é o mesmo defeito.

**Critério, e é o único que vale:**

> Dois achados são o mesmo defeito quando apontam o mesmo problema no mesmo local,
> com a mesma causa raiz. Regra operacional: **se corrigir um resolveria
> automaticamente o outro, é o mesmo defeito.** Se cada um exige uma correção
> própria, são defeitos distintos — mesmo que estejam no mesmo módulo e sejam
> parecidos.

**Viés conservador, obrigatório:** na dúvida, **NÃO** agrupe. Agrupar a mais é o erro
mais caro aqui.

Não explique, não comente, não reordene. Responda **só** com este JSON:

```json
{"grupos": [["F-03", "F-07"], ["F-11", "F-02", "F-19"]]}
```

Cada lista interna é um grupo de achados que são o mesmo defeito. Achados que não
são duplicata de nenhum outro **não aparecem** — grupos de um só elemento são
implícitos. Se nenhum achado for duplicata de outro, responda `{"grupos": []}`.

## A arquitetura

Os módulos do sistema, para você saber o que cada nome significa e quais são irmãos
entre si:

| id | módulo | responsabilidade | interface | depende-de |
|---|---|---|---|---|
| M-01 | janela | Acumula amostras por participante×métrica; sabe se atingiu a amostra mínima (≥50, R-03/R-05) | `adicionar(participante, metrica, valor, instante)` · `series(participante, metrica) -> [float]` · `suficiente(metrica) -> bool` | — |
| M-02 | julgamento | Dono de `metrica` (nome + direção) e `veredito`. Função PURA: séries pareadas → veredito, via Mann-Whitney U a 98% de confiança | `julgar(serie_canario, serie_baseline, metrica) -> Veredito` | janela |
| M-03 | score | Função PURA: vereditos → score `(Pass/Total)×100` excluindo Nodata do denominador; aprova/reprova por limiar único | `pontuar([Veredito]) -> Score` · `aprova(score) -> bool` | julgamento |
| M-04 | guarda-absoluta | Função PURA: amostras recentes → rollback imediato, sem aguardar a amostra mínima | `dispara(series_canario) -> Motivo \| None` | janela |
| M-05 | contadores | Falha (total acumulado) vs. erro (sucessão, limite 4, reset ao recuperar) — R-06 | `registrar_falha()` · `registrar_erro()` · `registrar_ok()` · `estourou() -> bool` | — |
| M-06 | plano-de-passos | Sequência de pesos do canário; próximo passo; se é o último | `proximo(atual) -> int \| None` · `ultimo(peso) -> bool` | — |
| M-07 | coordenador | Máquina de estados (progredindo / pausado / revertido / promovido) e o laço de execução. Orquestra e emite eventos | `executar() -> Desfecho` · `assinar(observador)` · `abortar()` | janela, julgamento, score, guarda-absoluta, contadores, plano-de-passos, relogio, fonte-de-metricas, alvo-de-implantacao |
| M-08 | relogio | PORTA + adaptador virtual: avanço programático do tempo. Nenhum outro módulo lê o relógio do sistema | `agora() -> int` · `avancar(delta)` | — |
| M-09 | fonte-de-metricas | PORTA de coleta. Distingue amostra de indisponibilidade — não são o mesmo evento | `coletar(participante, metrica) -> Amostra \| Indisponivel` | — |
| M-10 | alvo-de-implantacao | PORTA + adaptador. Dono de `participante` e da distribuição de peso (soma 100). Rollback = 100% à estável | `aplicar(pesos)` · `distribuicao() -> {papel: peso}` | — |
| M-11 | simulador-de-cenario | Adaptador de fonte-de-metricas. Gera amostras por cenário (UC-1…UC-4), RNG semeável, modela idade de instância (aquecimento) | implementa `fonte-de-metricas` | fonte-de-metricas, relogio |
| M-12 | cli | Entrada do operador. OBSERVA eventos do coordenador; imprime progresso, motivo e decisão final. Único módulo que escreve no terminal | `main(argv) -> int` | coordenador, simulador-de-cenario, relogio, alvo-de-implantacao |
| M-01 | janela | Janela **DESLIZANTE** de tamanho fixo por participante×métrica. Descarta o mais antigo ao exceder. Também recusa julgamento quando os volumes de canário e baseline divergem além da razão tolerada | `adicionar(participante, metrica, valor, instante)` · `series(participante, metrica) -> [float]` · `pronta(metrica) -> bool` · `volumes_comparaveis(metrica) -> bool` | configuracao |
| M-02 | julgamento | Dono de `metrica` (nome + direção) e `veredito`. Função PURA. **Usa `alternative` unicaudal derivado da direção**; empate/indefinição → `Nodata` | `julgar(serie_canario, serie_baseline, metrica) -> Veredito` | janela, configuracao |
| M-03 | score | Função PURA: vereditos → score `(Pass/Total)×100` excluindo Nodata; **denominador zero → `Indefinido`, nem aprova nem reprova** | `pontuar([Veredito]) -> Score` · `aprova(score) -> bool` | configuracao |
| M-04 | guarda-absoluta | Função PURA: piso de segurança sem aguardar amostra. **Limiares são parâmetro OBRIGATÓRIO do operador, sem valor padrão** | `dispara(series_canario) -> Motivo \| None` | janela, configuracao |
| M-05 | contadores | Falha (total acumulado) vs. erro (sucessão) — **ambos POR MÉTRICA**, não globais. Sucesso consecutivo para sair de `pausado` | `registrar_falha(metrica)` · `registrar_erro(metrica)` · `registrar_ok(metrica)` · `estourou() -> bool` · `recuperou() -> bool` | configuracao |
| M-06 | configuracao | **NOVO.** Objeto congelado, validado na construção, dono de TODOS os parâmetros e da sequência de pesos. Folha do grafo: ninguém depende dele para comportamento, só para valores | `proximo_peso(atual) -> int \| None` · atributos somente-leitura | — |
| M-07 | coordenador | Máquina de **5 estados** (aquecendo / progredindo / pausado / revertido / promovido) com histerese. Verifica a flag de aborto a cada iteração. Respeita duração máxima. Emite eventos **tipados** | `executar() -> Desfecho` · `assinar(observador)` · `abortar()` | M-01…M-06, M-08…M-10 |
| M-08 | relogio | PORTA + adaptador virtual. **Dono único do avanço: apenas `coordenador` chama `avancar`** | `agora() -> int` · `avancar(delta)` | — |
| M-09 | fonte-de-metricas | PORTA de coleta. **Quatro desfechos**: Amostra, Indisponivel, Lenta, Invalida. **Uma chamada = uma amostra** (cardinalidade fixada) | `coletar(participante, metrica) -> Amostra \| Indisponivel \| Lenta \| Invalida` | — |
| M-10 | alvo-de-implantacao | PORTA + adaptador. Dono de `participante`, dos pesos e das duas invariantes. **Deriva os três pesos do peso do canário, espelhando baseline em canário.** Executa a troca de papéis ao promover | `aplicar(peso_canario)` · `distribuicao() -> {papel: peso}` · `promover()` · `reverter()` | configuracao |
| M-11 | simulador-de-cenario | Adaptador de fonte-de-metricas. **Contrato exige modelar idade de instância**: em t=0 a série da estável difere mensuravelmente da do baseline | implementa `fonte-de-metricas` | fonte-de-metricas, relogio, configuracao |
| M-12 | cli | Composition root: constrói `configuracao` a partir de um **perfil nomeado**, instala o tratador de sinal para o aborto, observa eventos e imprime. Único módulo que escreve no terminal | `main(argv) -> int` | coordenador, simulador-de-cenario, relogio, alvo-de-implantacao, configuracao |
| M-06 | configuracao | Objeto congelado APENAS da configuração de **DECISÃO**: limiares, tamanho de janela, histerese, tolerância, intervalo, duração máxima, sequência de pesos. **Semente e cenário saíram daqui.** Valida na construção as quatro regras enumeradas abaixo | `proximo_peso(atual) -> int \| None` · atributos somente-leitura | — |
| M-11 | simulador-de-cenario | Adaptador de fonte-de-metricas e **dono da configuração de CENÁRIO**: qual cenário, semente, magnitude e persistência do efeito de aquecimento | implementa `fonte-de-metricas` · `Cenario(nome, semente, aquecimento)` | fonte-de-metricas, relogio |
| M-02 | julgamento | Como em V(2), porém com **alfa = 0,01 unicaudal** (preserva a taxa por cauda dos 98% bicaudais de R-02) e **sem o veredito `Low`**, que o teste unicaudal nunca produz | `julgar(...) -> Veredito` onde Veredito ∈ {Pass, High, Nodata} | janela, configuracao |
| M-07 | coordenador | Como em V(2). **Expiração por duração máxima mapeia para `revertido`**, com motivo `expirou` — continuam 5 estados | `executar() -> Desfecho` · `assinar(observador)` · `abortar()` | M-01…M-06, M-08…M-10 |

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | guarda-absoluta | 🟡 | dispara(series_canario) -> Motivo\ | None não recebe limiares. De onde vêm os valores? Não há módulo de configuração na decomposição |
| F-02 | cli | 🟢 | Semente e parâmetros vêm da linha de comando sem validação declarada; pesos negativos ou acima de 100 entram direto e quebram a invariante de soma |
| F-03 | janela | 🟡 | A janela cumulativa cria inércia crescente: quanto maior a série, mais amostras ruins são necessárias para mover a estatística. O sistema fica progressivamente MAIS LENTO para reagir justamente quando o canário já recebe MAIS tráfego |
| F-04 | relogio | 🟢 | Assume intervalo constante entre julgamentos; nada no contrato impede avanços de tamanho variável, que alterariam a densidade de amostras por janela |
| F-05 | fonte-de-metricas | 🟡 | O desfecho `Lenta` foi acrescentado sem semântica: o chamador conta como erro, como amostra tardia, ou descarta? Um desfecho declarado e não interpretado é pior que ausente, porque duas implementações corretas divergem |
| F-06 | fonte-de-metricas | 🟡 | coletar(participante, metrica) não define cardinalidade: uma chamada devolve uma amostra ou um lote acumulado desde a última chamada? Duas implementações corretas do contrato produzem densidades de série incompatíveis |
| F-07 | cli | 🟢 | O nome do perfil vem de argv sem validação de existência; um nome inválido deve falhar com mensagem clara, não com exceção de acesso |
| F-08 | julgamento | 🟡 | O contrato não especifica como converter o retorno do scipy em veredito. mannwhitneyu devolve statistic e pvalue; distinguir High de Low exige comparar medianas ou usar alternative='greater'/'less'. Não especificado, a implementação vai inventar |
| F-09 | cli | 🟡 | Exigir o limiar da guarda sem valor padrão impede o operador de executar qualquer coisa antes de tomar uma decisão que ele não tem base para tomar. O problema passou de "número inventado por mim" para "número inventado por ele" — melhora a atribuição, não a qualidade |
| F-10 | cli | 🔴 | coordenador expõe abortar(), mas o laço é monothread e bloqueante e a CLI não tem canal declarado para acioná-lo. VAL-12 exige que o aborto manual funcione a qualquer momento, e o design não oferece mecanismo — A7 é falsa como está |
| F-11 | janela | 🟢 | Descartar o elemento mais antigo de uma lista Python é O(n); um deque torna a operação O(1). Irrelevante neste porte, trivial de corrigir |
| F-12 | janela | 🟡 | Assume que amostras nunca são descartadas. Sendo cumulativa, amostras do passo 1 (peso 5%) se misturam com as do passo 4 (peso 50%) e o julgamento compara regimes de carga diferentes como se fossem um só |
| F-13 | alvo-de-implantacao | 🟡 | `estavel = 100 − 2×canario` assume que o baseline existe durante toda a implantação. O contrato de `promover()` não diz o que acontece com o baseline ao promover |
| F-14 | configuracao | 🟡 | O tamanho da janela deslizante foi igualado à amostra mínima (50). R-03 fala em amostra mínima para VALIDADE ESTATÍSTICA, não em tamanho de janela de observação. Dois conceitos distintos foram fundidos por conveniência, e o número emprestado passou a governar algo que a fonte não governa |
| F-15 | cli | 🟡 | Não há como distinguir na saída "não reverteu porque estava bom" de "não reverteu porque nunca houve amostra suficiente" — dois desfechos operacionalmente opostos com a mesma aparência |
| F-16 | janela | 🔴 | A janela deslizante de 50 amostras faz julgamentos consecutivos compartilharem a maior parte das amostras quando o intervalo produz menos de 50 pontos novos. Os julgamentos deixam de ser independentes, mas `contadores` soma falhas como se fossem: uma única degradação transitória é contada N vezes enquanto permanece na janela. O `threshold` de R-07, importado para resolver MEC-01, pressupõe julgamentos independentes e não transfere |
| F-17 | coordenador | 🔴 | Nenhum módulo é dono da CONFIGURAÇÃO (limiar de score, limiares da guarda, amostra mínima, intervalo, sequência de pesos, semente). Sem um objeto de configuração, o critério de acerto CA-0 — "UC-2 e UC-3 sob a MESMA configuração" — não é sequer expressável, muito menos verificável |
| F-18 | cli | 🟡 | O design não define o que é impresso enquanto os julgamentos dão Nodata. Silêncio durante os primeiros 50 pontos é indistinguível de travamento para quem olha o terminal |
| F-19 | cli | 🟢 | main(argv) -> int não declara quais argumentos aceita; a superfície do operador está indefinida |
| F-20 | simulador-de-cenario | 🟢 | Tem duas razões para mudar: implementa a porta fonte-de-metricas E depende de relogio para gerar séries no tempo — violação branda de SRP |
| F-21 | julgamento | 🟡 | Acoplamento rígido ao comportamento exato do scipy: method='auto' alterna entre exato e assintótico conforme tamanho de amostra e presença de empates. Uma atualização de versão pode mudar vereditos de borda sem que nada no sistema perceba |
| F-22 | coordenador | 🟡 | A lista de eventos tipados não inclui a transição `aquecendo→progredindo` nem quantas amostras faltam para a janela ficar pronta. O operador continua sem saber quanto falta |
| F-23 | coordenador | 🔴 | O estado pausado não tem critério de saída definido. Quantos julgamentos bons devolvem a progredindo? Um? Todos? Sem isso a transição é indefinida e o estado vira armadilha ou porta giratória |
| F-24 | score | 🟡 | Depende de julgamento apenas para o tipo Veredito. Testar score arrasta scipy como dependência transitiva, embora score seja aritmética pura sobre um enum |
| F-25 | contadores | 🟡 | Com contadores POR MÉTRICA, não está definido o que dispara o rollback: uma métrica estourando, a maioria, ou todas. A correção de RES-02 criou uma decisão de agregação sem dono |
| F-26 | janela | 🟡 | `volumes_comparaveis()` assume que contagens divergentes significam problema de tráfego. Mas erros de coleta também reduzem a contagem de um lado, e o mecanismo anti-REG-01 dispara por falha de coletor — confundindo-se com o que `contadores` já trata |
| F-27 | score | 🟡 | O limiar único adotado não vem de R-03: 75 e 95 foram abandonados ao eliminar a faixa Marginal. O limiar efetivo passou a ser "score == 100", que não tem fonte alguma |
| F-28 | configuracao | 🟡 | 11 dos 12 módulos dependem dele. É folha do grafo, mas folha universal: trocamos um hub de comportamento (coordenador) por um hub de dados, e qualquer mudança de parâmetro toca o grafo inteiro |
| F-29 | alvo-de-implantacao | 🔴 | Com espelhamento, expor o canário a 50% exige expor o baseline a 50%, e `estavel` vai a ZERO. No último passo, 100% dos usuários estão em instâncias recém-implantadas e frias — metade num canário não aprovado, metade num baseline igualmente novo. É a negação da propriedade de segurança que uma implantação canário existe para oferecer |
| F-30 | configuracao | 🟡 | "Validado na construção" não enumera as validações: soma dos pesos, monotonicidade da sequência, teto de 50% do canário, K de histerese ≥ 1. Sem enumerá-las, a validação é promessa, não tolerância |
| F-31 | coordenador | 🔴 | sem histerese na transição progredindo↔pausado, um canário limítrofe faz o sistema oscilar a cada julgamento, alternando estado sem nunca convergir para promoção ou rollback |
| F-32 | alvo-de-implantacao | 🟡 | `reverter()` e `promover()` levam a estados terminais, mas o contrato não declara se são idempotentes nem o que ocorre se chamados fora de ordem ou duas vezes |
| F-33 | coordenador | 🔴 | Se o coletor for irregular, `aquecendo` pode nunca satisfazer janela pronta mais volumes comparáveis, e a duração máxima encerra a execução AINDA em `aquecendo` — desfecho que não é promovido nem revertido. Existe um quinto término não nomeado na máquina de estados |
| F-34 | score | 🔴 | Tolerância ZERO: aprovar exige score 100, isto é, as três métricas em Pass. Com 98% de confiança e 3 métricas por julgamento, a probabilidade de ao menos um falso positivo em n julgamentos é 1-0,98^(3n) — em 10 julgamentos, cerca de 45%. UC-1 (canário saudável) reprovaria por ruído em quase metade das execuções. É o problema de comparações múltiplas, e o design não tem nenhuma correção |
| F-35 | plano-de-passos | 🔴 | Assume que canário e baseline recebem sempre o mesmo volume de tráfego. O plano avança só o peso do canário; se o baseline ficar em 5% enquanto o canário vai a 50%, a comparação vira carga-diferente e a diferença de carga é lida como diferença de versão (viola R-03: "same type and amount of traffic") |
| F-36 | score | 🟡 | `Indefinido` foi criado para o denominador zero, mas nenhum módulo declara o que o coordenador faz com ele. Não avança nem reprova, logo o passo fica parado — e isso realimenta PRO-05 |
| F-37 | julgamento | 🟢 | R-02 documenta outlierFactor 3.0 e nanStrategy; o design não trata outliers nem valores não-numéricos em nenhum módulo |
| F-38 | coordenador | 🟡 | Não existe estado para "aguardando amostra mínima". Nos primeiros 50 pontos o sistema está nominalmente em progredindo, mas não pode progredir — a máquina de estados não representa a fase inicial da própria execução |
| F-39 | relogio | 🟡 | avancar(delta) não declara quem é o dono do avanço. Se coordenador e simulador-de-cenario ambos avançarem, o tempo corre em dobro e a temporização de R-07 deixa de valer |
| F-40 | julgamento | 🔴 | O design declara seguir os quatro sinais de ouro (R-01) mas julga apenas 3: TRÁFEGO não tem módulo nem rastreabilidade. Consequência concreta: se o canário parar de receber requisições, latência e taxa de erro melhoram e a saturação cai — o canário é PROMOVIDO justamente por estar quebrado |
| F-41 | coordenador | 🟡 | Não há limite global de duração. Se o coletor alternar ok/erro indefinidamente, o contador nunca estoura, a janela nunca enche e o laço não termina |
| F-42 | coordenador | 🟡 | A histerese é assimétrica: sair de `pausado` exige K sucessos consecutivos, mas entrar exige uma única falha. O sistema entra fácil e sai difícil, o que enviesa sistematicamente contra a promoção |
| F-43 | simulador-de-cenario | 🟡 | O contrato exige que a série da estável difira "mensuravelmente" da do baseline em t=0, mas não diz por quanto nem por quanto tempo o efeito persiste. "Mensuravelmente" não é verificável — ASM-01 virou contrato sem virar critério |
| F-44 | guarda-absoluta | 🟡 | os limiares continuam sem fonte bibliográfica; tornar o parâmetro obrigatório mudou a atribuição, não a fundamentação |
| F-45 | cli | 🟢 | Não há distinção entre saída para humano e saída para máquina; um operador que queira encadear o resultado precisa analisar texto de progresso |
| F-46 | contadores | 🟡 | Não está definido se o limite de 4 erros consecutivos é por métrica ou global. Sendo global, uma única métrica com coleta quebrada derruba a execução inteira |
| F-47 | julgamento | 🟢 | Overhead fixo de chamada ao scipy por métrica por julgamento; com 3 métricas continua trivial — sem gargalo real neste porte |
| F-48 | configuracao | 🔴 | O objeto congelado guarda ao mesmo tempo os limiares de decisão E a semente e o cenário do simulador. Como UC-2 e UC-3 são cenários diferentes, eles necessariamente recebem objetos `configuracao` diferentes — e "a MESMA configuração" do CA-0 volta a ser inverificável. IMP-03 foi resolvido na forma e não na substância: falta separar configuração de DECISÃO de configuração de CENÁRIO |
| F-49 | alvo-de-implantacao | 🟢 | aplicar(pesos) não diz se pesos é o mapa completo dos três papéis ou um delta parcial; a invariante de soma depende dessa leitura |
| F-50 | relogio | 🟢 | "Apenas o coordenador avança o relógio" é convenção documentada, não impedimento estrutural — nada no contrato impede outro módulo de chamar `avancar` |
| F-51 | plano-de-passos | 🟡 | nenhum módulo é dono da regra que relaciona o peso do baseline ao do canário; a responsabilidade é órfã na decomposição |
| F-52 | julgamento | 🟡 | Com teste unicaudal e direção menor-é-melhor, o veredito `Low` nunca é produzido — vira código morto, e o modelo de domínio continua declarando-o como valor possível |
| F-53 | fonte-de-metricas | 🟡 | O contrato prevê Amostra ou Indisponivel e nada mais. Não cobre "responde devagar" nem "devolve dado absurdo" (NaN, negativo, infinito) — dois desfechos para um mundo com pelo menos quatro |
| F-54 | alvo-de-implantacao | 🟡 | O desfecho "canário vira estável" não tem operação em nenhum módulo. aplicar(pesos) só move peso; a troca de papéis ao promover é uma transição sem dono |
| F-55 | janela | 🟢 | retenção ilimitada de amostras, consumo cresce sem teto ao longo da execução |
| F-56 | guarda-absoluta | 🟡 | Assume que "degradação grosseira" é observável nas amostras recentes, mas não define quantas amostras nem em que janela — o contrato recebe a série inteira |
| F-57 | coordenador | 🟡 | Não há caminho de rollback para o próprio coordenador. Se ele levantar exceção no meio da execução, os pesos permanecem no último estado aplicado — canário recebendo tráfego, ninguém julgando |
| F-58 | alvo-de-implantacao | 🟡 | aplicar(pesos) não valida a invariante soma==100. Um chamador defeituoso deixa o sistema com 150% ou 70% do tráfego atribuído, e nada detecta |
| F-59 | julgamento | 🟡 | Passar a `alternative='greater'` unicaudal mantendo alfa em 0,02 dobra a taxa de falso positivo na cauda testada em relação ao bicaudal. Os 98% de R-02 descrevem o teste bicaudal do Kayenta; mudamos o teste e mantivemos o número citado como fonte |
| F-60 | simulador-de-cenario | 🔴 | A2 assume que o simulador modela idade de instância, mas nenhum contrato exige isso. Se o adaptador gerar amostras idênticas para estável e baseline, os quatro UC passam e a decisão BASELINE PAREADO nunca é exercida — nada no sistema detecta a omissão |
| F-61 | alvo-de-implantacao | 🟡 | A mudança de peso é instantânea no modelo; não há noção de requisições em voo durante a transição. O rollback assume corte limpo, o que nenhum roteamento real oferece |
| F-62 | guarda-absoluta | 🔴 | Nenhum limiar da guarda tem fonte bibliográfica (A3 / VAL-9). É o único componente do sistema cujos números são invenção declarada — exatamente a classe de falha que esta lente existe para pegar |
| F-63 | julgamento | 🟡 | R-02 especifica 98% de confiança mas não diz se o teste é bicaudal ou unicaudal. Com direção menor-é-melhor, alternative='two-sided' a 98% não equivale a alternative='greater' a 98% — a escolha muda a taxa de falso positivo e não está especificada |
| F-64 | coordenador | 🟡 | A trilha de julgamentos intermediários não é retida em lugar nenhum. Depois da execução não há como auditar por que reverteu — resta apenas o que a CLI imprimiu no momento, e a decisão de não persistir é do escopo |
| F-65 | alvo-de-implantacao | 🟡 | O rollback devolve 100% à estável, mas no último passo a estável esteve a 0%. Reverter para uma estável que ficou sem tráfego é reverter para instâncias frias — o mesmo efeito de idade que motivou o baseline pareado, agora do lado do destino do rollback |
| F-66 | plano-de-passos | 🟡 | A exposição cresce sem que a confiança acumulada entre na decisão de quanto crescer: o design permite saltar de 5% para 50% com a mesma evidência que sustentou os 5% |
| F-67 | cli | 🟡 | A configuração é impressa, mas nada vincula estruturalmente o que foi impresso ao que foi usado: a impressão é uma segunda leitura do objeto, não um subproduto da execução |
| F-68 | cli | 🟢 | não há registro de qual configuração produziu qual desfecho, porque não há objeto de configuração a registrar |
| F-69 | janela | 🟡 | Os 50 pontos de R-03/R-05 referem-se a séries temporais de produção com granularidade de minutos. Aplicar o mesmo número a amostras sintéticas de RNG assume uma equivalência não demonstrada (A4) |
| F-70 | coordenador | 🟡 | Depende de 9 dos 11 demais módulos. Não é testável isoladamente sem construir 9 dublês; é o ponto de concentração declarado em A5 |
| F-71 | coordenador | 🟡 | Os eventos emitidos não estão especificados: quais eventos, com que dados, em que momento. "emite eventos" é o contrato inteiro, e a CLI é a única consumidora |
| F-72 | janela | 🟡 | Sendo cumulativa, cresce O(n) e o Mann-Whitney custa O(n log n) por julgamento: o custo total cresce de forma superlinear ao longo da execução. Com relógio virtual comprimido gerando muitos pontos, isso domina o tempo de teste |
