# Reagrupamento cego de achados — T25-orcamento

Você recebe 68 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
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
| M-01 | gateway-http | recebe a requisição, orquestra reserva → envio → reconciliação, repassa resposta e streaming ao cliente | `POST /v1/messages`; `GET /*` serve a SPA | identidade, escrow, upstream, precificador |
| M-02 | identidade | resolve chave virtual → entidade; emite e revoga chaves; autentica o operador do painel | `resolver(chave) -> Entidade \| None`; `emitir(entidade) -> chave`; `autenticar_operador(segredo) -> bool` | persistencia |
| M-03 | escrow | seção crítica: decide permitir/negar contra os dois tetos e reserva o pior caso; depois reconcilia com o custo real | `reservar(entidade, valor, instante) -> Decisao{permitido, id_reserva, motivo}`; `reconciliar(id_reserva, custo_real)`; `liberar(id_reserva)` | persistencia, janela |
| M-04 | precificador | custo real a partir do `usage`; estimativa de pior caso antes da chamada | `custo(usage, modelo, instante) -> Decimal`; `pior_caso(modelo, tokens_entrada, max_tokens, instante) -> Decimal` | rate-card |
| M-05 | rate-card | carrega e valida a tabela de preços com vigência; nega modelo desconhecido | `preco(modelo, categoria_token, instante) -> Decimal` — levanta `ModeloSemPreco` se ausente | — |
| M-06 | janela | calcula a janela mensal vigente em UTC e o instante do próximo reset | `janela_de(instante) -> Janela{inicio, fim}`; `proximo_reset(instante) -> datetime` | — |
| M-07 | upstream | Strategy: cliente real (SDK `anthropic`) ou simulado; Adapter traduz `usage` da API para o modelo interno | `enviar(requisicao) -> Resposta{usage, conteudo, stop_reason}`; variante de streaming | — |
| M-08 | persistencia | conexão, schema, migração e transação; repositórios de contadores Escrow e de eventos de uso | `transacao()` (context manager); `contadores.ler/aplicar`; `eventos.registrar/consultar` | — |
| M-09 | painel-api | endpoints de leitura de consumo/saldo/tetos e de configuração de tetos, protegidos por senha de operador | `GET /api/consumo`; `GET /api/tetos`; `PUT /api/tetos/{entidade}`; `POST /api/login` | persistencia, janela, identidade |
| M-10 | painel-web | SPA servida pelo gateway: consumo por entidade, saldo, teto, estado de corte e próximo reset em UTC | página HTML/CSS/JS que consome painel-api | painel-api |
| M-01 | gateway-http | **apenas proxy**: recebe a requisição, orquestra reserva → envio → reconciliação, repassa streaming e emite log estruturado de toda decisão. Não serve mais a SPA | `POST /v1/messages` | identidade, escrow, upstream, precificador |
| M-02 | identidade | **apenas** chave virtual → entidade; emissão e revogação. Autenticação de operador saiu daqui | `resolver(chave) -> Entidade \| None`; `emitir(entidade) -> chave` | persistencia |
| M-03 | escrow | seção crítica **intencionalmente bloqueante e curta**: expira reservas vencidas, aplica teto de `max_tokens` da entidade, decide contra os dois tetos, reserva; reconcilia. Devolve motivo como **código enumerado** | `reservar(entidade, valor, instante) -> Decisao{permitido, id_reserva, codigo_motivo, escopo_estourado, reset_em}`; `reconciliar(id_reserva, custo_real)` | persistencia, janela |
| M-04 | precificador | custo real a partir do `usage`; pior caso = `max_tokens × preço_saída`. **Não chama `count_tokens`** | `custo(usage, modelo, instante)`; `pior_caso(modelo, max_tokens, instante)` | rate-card |
| M-05 | rate-card | preços com `vigente_desde` **e `vigente_ate`**; valida na inicialização e recusa modelo sem preço vigente | `preco(modelo, categoria, instante)` — levanta `ModeloSemPreco`; `validar_na_inicializacao()` | — |
| M-06 | janela | **função pura**, sem estado e sem evento de virada | `janela_de(instante) -> Janela`; `proximo_reset(instante) -> datetime` | — |
| M-07 | upstream | Strategy (real/simulado) + Adapter; **verifica que as categorias conhecidas de token cobrem o total reportado** e falha alto se não cobrirem | `enviar(requisicao) -> Resposta{usage, conteudo, stop_reason}` | — |
| M-08 | persistencia | conexão, schema, transação; contadores com criação preguiçosa; eventos com retenção configurável; consulta de verificação do invariante I2 | `transacao()`; `contadores`; `eventos`; `verificar_invariantes()` | — |
| M-09 | painel-api | leitura de consumo/saldo/tetos, configuração de tetos **com trilha de auditoria**, **autenticação de operador**, **serviço da SPA por mapa de rotas explícito**, endpoint de saúde | `GET /api/consumo`; `PUT /api/tetos/{id}`; `POST /api/login`; `GET /health`; rotas estáticas nomeadas | persistencia, janela, identidade |
| M-10 | painel-web | SPA: consumo por entidade, saldo, teto, **qual teto estourou**, **instante do próximo reset em UTC** | página servida por painel-api | painel-api |
| M-01 | gateway-http | proxy; **dono do ciclo de vida da reserva**: garante reconciliação ou liberação em `finally` por todos os caminhos de saída; log estruturado sem jamais registrar a chave virtual (só o id da entidade e uma impressão digital) | `POST /v1/messages` | identidade, escrow, upstream, precificador |
| M-02 | identidade | chave virtual → entidade; emissão e revogação | `resolver`, `emitir`, `revogar` | persistencia |
| M-03 | escrow | **enxuto**: decide contra os dois tetos, aplica teto de `max_tokens` e limite de reservas simultâneas por entidade, reserva, reconcilia, libera. Sem expiração, sem relógio, sem TTL | `reservar(...) -> Decisao`; `reconciliar(id, custo_real)`; `liberar(id)` | persistencia, janela |
| M-04 | precificador | custo real; pior caso = `bytes_do_corpo × preço_entrada + max_tokens × preço_saída` | `custo(...)`; `pior_caso(modelo, bytes_corpo, max_tokens, instante)` | rate-card |
| M-05 | rate-card | preços com vigência; **recusa apenas os modelos vencidos**, não a inicialização inteira; expõe o estado em `/health` | `preco(...)`; `modelos_vencidos()` | — |
| M-06 | janela | função pura; o instante é capturado **uma vez** na admissão e propagado | `janela_de(instante)`; `proximo_reset(instante)` | — |
| M-07 | upstream | Strategy + Adapter; verifica cobertura das categorias de token | `enviar(...)` | — |
| M-08 | persistencia | conexão, schema, transação; contadores preguiçosos; **recuperação de crash no arranque** (libera reservas `'aberta'`); **retenção aplicada no arranque**, nunca durante o tráfego; verificação de invariantes | `transacao()`; `contadores`; `eventos`; `recuperar_no_arranque()`; `verificar_invariantes()` | — |
| M-09 | painel-api | leitura, configuração de tetos com auditoria, autenticação de operador, rotas estáticas nomeadas, `/health` | `GET /api/consumo`; `PUT /api/tetos/{id}`; `POST /api/login`; `GET /health` | persistencia, janela, identidade |
| M-10 | painel-web | SPA: consumo, saldo, teto, qual teto estourou, próximo reset em UTC, **distingue "sem dados" de "consumo zero"** | página servida por painel-api | painel-api |

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | painel-api | 🟢 | A fronteira entre painel-api e painel-web é fina; poderiam ser um módulo só, liberando orçamento do porte congelado |
| F-02 | escrow | 🟡 | As expirações não são observáveis. Um sistema que libera silenciosamente reservas de requisições vivas precisa emitir sinal ao fazê-lo; sem isso, RES-04 e RES-05 são indiagnosticáveis em produção |
| F-03 | gateway-http | 🟡 | O log estruturado de toda decisão registra a entidade; se registrar também a chave virtual — ainda não especificado — o arquivo de log vira arquivo de credenciais |
| F-04 | painel-api | 🟡 | alteração de teto não é atribuível a nenhum ator |
| F-05 | persistencia | 🟡 | `evento_uso` cresce sem política de retenção: o banco cresce proporcionalmente ao uso, indefinidamente, no mesmo arquivo de que depende a seção crítica |
| F-06 | identidade | 🟡 | Duas responsabilidades com atores e ciclos de vida distintos no mesmo módulo: identidade de entidade consumidora (chave virtual) e autenticação do operador (senha) |
| F-07 | rate-card | 🟡 | O preço promocional do Sonnet 5 expira em 2026-08-31 — 21 dias após hoje. A partir daí o sistema subcontabiliza silenciosamente. Tolerância zero à passagem do tempo, sem sinal de alerta |
| F-08 | janela | 🟡 | Premissa A4 (relógio confiável) não verificada. Um ajuste de NTP para trás faz a janela "des-virar": ocorre um segundo reset dentro do mesmo mês civil e o teto efetivo dobra |
| F-09 | painel-web | 🟡 | `specs/design/` não contém mockup nem referência visual: o implementador não tem contrato de UI, só a lista de campos |
| F-10 | escrow | 🔴 | A arquitetura exige seção crítica "sem await" E adota asyncio com banco. As duas opções falham de formas opostas: driver assíncrono torna cada operação de banco um ponto de preempção DENTRO da seção crítica (lost update); `sqlite3` síncrono protege a seção mas bloqueia o event loop inteiro. A premissa "o event loop protege a seção crítica" só vale na segunda, cujo custo não foi declarado |
| F-11 | escrow | 🔴 | O TTL de 15 min pode expirar a reserva de uma requisição **viva**. A documentação registra que requisições de alto esforço levam "muitos minutos"; uma geração longa em streaming ultrapassa 15 min. A reserva é liberada, o saldo volta, outra requisição passa — e quando a original reconcilia, o custo entra por cima do teto. A simplificação 2 criou um caminho de estouro que V(1) não tinha |
| F-12 | painel-web | 🟡 | Com a virada preguiçosa, uma janela sem nenhuma requisição não tem linha de contador. O painel precisa distinguir "consumo zero" de "sem dados", sob pena de exibir zero para uma entidade cujo estado é desconhecido |
| F-13 | janela | 🟡 | `janela` virou função pura de um instante, mas nada define QUEM fornece o instante nem que seja o mesmo ao longo da requisição. Reserva e reconciliação com instantes distintos podem cair em janelas diferentes |
| F-14 | escrow | 🔴 | Reserva aberta na janela N e reconciliada na janela N+1 debita a janela errada. A transição de janela não define o que ocorre com reservas que a atravessam |
| F-15 | escrow | 🟡 | O teto de `max_tokens` limita UMA requisição, não o agregado. N requisições simultâneas logo abaixo do teto reservam N × teto e seguem negando as demais entidades. A defesa encarece o ataque, não o elimina |
| F-16 | persistencia | 🟢 | A retenção configurável introduzida em V(2) resolve o crescimento indefinido; nenhum achado novo |
| F-17 | escrow | 🔴 | `reservado_nano` acumula sem sinal de erro nem mecanismo de correção: laço de controle sem realimentação, com desvio monotônico |
| F-18 | painel-api | 🟡 | Absorveu autenticação e serviço da SPA: agora acumula leitura, configuração, autenticação e estático. O problema de ARQ-01 foi **movido**, não eliminado |
| F-19 | escrow | 🟡 | O corte não tem mecanismo de exceção nem aviso ao afetado: o trabalho de uma pessoa é interrompido sem recurso, até o operador agir ou a janela virar |
| F-20 | gateway-http | 🟡 | Repasse de streaming somado à reconciliação após o fim do stream é o trecho mais complexo do sistema, e está no módulo com mais dependências. Risco de não caber em uma única interação |
| F-21 | painel-web | 🟡 | O estado "cortado" não informa QUAL teto estourou (global ou da entidade) nem quando volta; sem isso o operador não sabe qual teto elevar |
| F-22 | painel-web | 🟢 | Se entidade corresponder a pessoa, o painel é monitoramento individual de produtividade visível a qualquer operador, sem transparência para o monitorado |
| F-23 | painel-web | 🟡 | O saldo exibido inclui reservas em voo e oscila com o tráfego. O operador pode reagir a uma oscilação transitória elevando o teto — oscilação induzida pelo observador |
| F-24 | escrow | 🟡 | O teto global compartilhado cria corrida: consumir cedo no mês domina consumir tarde. O desenho premia o comportamento que ele existe para conter |
| F-25 | persistencia | 🟢 | Com entidade redefinida como identidade técnica, nenhum requisito normativo aplicável foi identificado. Ausência de achado é resultado válido |
| F-26 | escrow | 🟡 | A máquina de estados da reserva ganhou de fato o estado `'expirada'`, que não está declarado — V(1) previa `aberta` \ | `reconciliada` \ | `liberada`. Sem o estado explícito, expiração e liberação por erro ficam indistinguíveis na auditoria |
| F-27 | escrow | 🔴 | A reconciliação de uma reserva já expirada é silenciosamente descartada: a guarda de idempotência retorna sem fazer nada quando o estado não é `'aberta'`. O custo REAL da requisição longa nunca é contabilizado — perda de contabilidade, não apenas de saldo |
| F-28 | precificador | 🟡 | Premissa A6 (`count_tokens` não é cobrado) sem fonte: o custo do próprio mecanismo de medição é desconhecido |
| F-29 | escrow | 🟡 | A expiração de reserva é uma ação do sistema que altera saldo, sem ator atribuível e sem registro. É a única mutação de contador sem autoria |
| F-30 | escrow | 🟡 | A justificativa formal para instância única (não-I-confluência do invariante de limite, Bailis et al. 2014) está marcada em specs como NÃO verificada. Decisão estrutural apoiada em afirmação não confirmada |
| F-31 | gateway-http | 🟡 | A resposta de negação ao app consumidor não tem código HTTP nem corpo especificados. O app não consegue distinguir "teto esgotado" de "429 do provedor" e retenta — exatamente o retry storm que a Fase 0 identificou ao separar limite de taxa de teto de orçamento |
| F-32 | painel-api | 🟡 | `PUT /api/tetos` altera o teto sem trilha de auditoria — a operação que desliga o corte é a menos rastreável do sistema |
| F-33 | escrow | 🟡 | O contador global é ponto único de serialização: toda requisição de toda entidade atravessa a mesma seção crítica. O teto de vazão do gateway é 1/duração da seção crítica |
| F-34 | upstream | 🟡 | Acoplado à forma exata do objeto `usage`. Uma categoria nova de token entraria como não contabilizada, e nada verifica que as categorias conhecidas cobrem o total reportado |
| F-35 | escrow | 🟡 | O TTL de 15 min tem fonte para o número de referência (timeout padrão de 10 min do SDK) mas não para a regra de derivação — por que 1,5×? Parâmetro semi-fundamentado |
| F-36 | janela | 🔴 | Nenhum módulo é dono da VIRADA da janela. `janela` apenas calcula limites; ninguém cria a linha de contador da nova janela nem executa o reset. UC-4 (reset reverte o corte) ficou sem módulo responsável |
| F-37 | persistencia | 🟡 | O invariante I2 (soma das reservas abertas = `reservado_nano`) não é verificável em execução; uma corrupção do contador seria silenciosa |
| F-38 | gateway-http | 🟡 | cliente que desconecta durante o streaming faz o `usage` nunca chegar |
| F-39 | gateway-http | 🟡 | Resposta 429 ou 5xx do provedor: nada no desenho especifica que a reserva é liberada nesse caminho |
| F-40 | identidade | 🟡 | Revogar uma chave virtual com reservas abertas não tem comportamento definido: as reservas ficam presas sem dono |
| F-41 | upstream | 🔴 | Falha, timeout ou desconexão após a reserva deixa a reserva ÓRFÃ, e a expiração automática está declarada fora de escopo. `reservado_nano` cresce monotonicamente até a entidade ser cortada com consumo real baixo. Degradação garantida pelo desenho, não hipotética |
| F-42 | rate-card | 🟡 | Preços vêm de snapshot datado de 2026-06-24 sem processo declarado de revalidação contra a fonte canônica |
| F-43 | identidade | 🟡 | Chave virtual sem expiração e sem escopo: um vazamento concede acesso até revogação manual, e nada limita quais modelos ou volumes ela pode acionar |
| F-44 | gateway-http | 🟢 | HTTP 402 com corpo próprio é contrato novo que nenhum SDK conhece; exige documentação para o cliente tratá-lo. Não é ambíguo, mas é não-padrão |
| F-45 | upstream | 🟡 | Assume que ausência de resposta significa ausência de gasto. Falso: timeout do lado do gateway após o provedor ter processado gera custo real que nunca entra no contador — subcontabilização silenciosa |
| F-46 | gateway-http | 🔴 | Nenhum módulo tem responsabilidade de log ou métrica. "Por que minha requisição foi negada?" não é diagnosticável em produção sem alterar código — e negar é a função central do sistema |
| F-47 | persistencia | 🟡 | Se entidade consumidora corresponder a uma pessoa, `evento_uso` é dado pessoal de produtividade. Nenhum requisito normativo (retenção, eliminação, base legal) foi identificado na Fase 0 nem rastreado a módulo algum |
| F-48 | precificador | 🟢 | Assume `max_tokens` presente na requisição do cliente; nenhum comportamento definido se ausente, e é dele que a reserva de pior caso depende |
| F-49 | precificador | 🟡 | `count_tokens` antes de cada requisição acrescenta uma ida-e-volta de rede por requisição apenas para tornar a reserva mais justa. Custo desproporcional ao ganho, e possivelmente cobrado (A6) |
| F-50 | painel-api | 🟢 | `GET /api/consumo` sem paginação nem agregação pré-computada; varre eventos a cada carregamento do painel |
| F-51 | gateway-http | 🟡 | Acumula orquestração, roteamento, serviço da SPA e repasse de streaming, e depende de 4 módulos. Testá-lo isoladamente exige quatro dublês simultâneos |
| F-52 | escrow | 🔴 | Ataque de negação por reserva: um app declara `max_tokens` enorme, a reserva de pior caso consome o teto global e todas as demais entidades são negadas — sem gastar um único token. Custo do ataque: uma requisição |
| F-53 | painel-api | 🟡 | O limite de tentativas de login roda no mesmo event loop de thread única do proxy. Uma rajada de tentativas de senha consome o loop e degrada TODAS as requisições ao LLM: autenticação e caminho crítico disputam o mesmo recurso escasso |
| F-54 | escrow | 🟡 | Concentra expiração, teto de `max_tokens`, decisão sobre dois escopos, reserva e reconciliação, tudo numa seção crítica sem `await`. É o módulo mais denso do sistema e o mais difícil de sustentar numa única interação |
| F-55 | persistencia | 🟢 | retenção infinita de eventos de uso |
| F-56 | gateway-http | 🔴 | Rota curinga `GET /*` servindo a SPA é superfície de travessia de caminho, num processo que detém a chave real do provedor e o arquivo do banco |
| F-57 | persistencia | 🟡 | `sqlite3` síncrono bloqueia o event loop durante a transação, transformando latência de disco em latência de todas as requisições em voo |
| F-58 | persistencia | 🟡 | A limpeza por retenção e a verificação de invariante rodam na mesma conexão síncrona bloqueante. Um `DELETE` grande bloqueia o event loop e, com ele, todo o tráfego ao LLM |
| F-59 | identidade | 🔴 | Senha única de operador sem limite de tentativas nem comparação em tempo constante: força bruta e ataque de temporização. Quem obtém a senha eleva tetos — ou seja, desliga o corte |
| F-60 | precificador | 🔴 | Remover `count_tokens` deixou o custo de **entrada** fora da reserva. Um prompt próximo da janela de 1M tokens custa US$ 5,00 de entrada no Opus 5, nada disso reservado; o teto de `max_tokens` limita a saída, não a entrada. Uma única requisição de prompt grande pode violar o invariante que é o critério de acerto do projeto |
| F-61 | gateway-http | 🟡 | "Compatível com a API da Anthropic" não está especificado: quais rotas, quais cabeçalhos são repassados, o que ocorre com parâmetros desconhecidos. Duas implementações do mesmo contrato divergiriam |
| F-62 | rate-card | 🟡 | Nenhum dono declarado para manter a tabela de preços. Como modelo sem preço é negado por decisão, a omissão de manutenção converte-se diretamente em indisponibilidade de serviço |
| F-63 | escrow | 🟡 | `Decisao.motivo` é texto livre; o cliente não pode programar contra ele. Falta um código enumerado de motivo de negação |
| F-64 | escrow | 🟡 | O TTL é parâmetro de laço de controle ajustado sem medição: 15 min veio de um timeout de SDK, não da distribuição real de duração das requisições deste sistema. Curto demais causa RES-04; longo demais devolve o desvio monotônico de RES-01 |
| F-65 | painel-web | 🟢 | Nenhum requisito de acessibilidade definido (contraste, navegação por teclado, leitor de tela) |
| F-66 | escrow | 🟢 | Com entidade = identidade técnica, o impacto humano direto foi mitigado na raiz; permanece apenas o efeito indireto já registrado em ETI-01 |
| F-67 | rate-card | 🟡 | "Recusar iniciar com tabela vencida" converte problema de contabilidade em **queda total programada**: em 2026-08-31 o gateway deixa de subir. Trocou-se falha silenciosa por falha ruidosa e catastrófica, sem o meio-termo de recusar apenas os modelos vencidos |
| F-68 | upstream | 🟡 | O contrato do upstream simulado não está especificado — como forjar `refusal`, timeout, stream parcial e `usage` arbitrário. É módulo do sistema (decisão f21733c9), não utilitário de teste |
