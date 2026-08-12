# Matriz de cobertura — crítica adversarial

Um achado por linha. Lentes: 7 universais + 11 condicionais declaradas via
`record_activated_lenses`. Não ativada: Migration / Coexistence (projeto greenfield).

---

## Iteração 1 — V(1)

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| A-01 | escrow | Assumptions | 🔴 | A arquitetura exige seção crítica "sem await" E adota asyncio com banco. As duas opções falham de formas opostas: driver assíncrono torna cada operação de banco um ponto de preempção DENTRO da seção crítica (lost update); `sqlite3` síncrono protege a seção mas bloqueia o event loop inteiro. A premissa "o event loop protege a seção crítica" só vale na segunda, cujo custo não foi declarado |
| A-02 | janela | Assumptions | 🟡 | Premissa A4 (relógio confiável) não verificada. Um ajuste de NTP para trás faz a janela "des-virar": ocorre um segundo reset dentro do mesmo mês civil e o teto efetivo dobra |
| A-03 | upstream | Assumptions | 🟡 | Assume que ausência de resposta significa ausência de gasto. Falso: timeout do lado do gateway após o provedor ter processado gera custo real que nunca entra no contador — subcontabilização silenciosa |
| A-04 | precificador | Assumptions | 🟢 | Assume `max_tokens` presente na requisição do cliente; nenhum comportamento definido se ausente, e é dele que a reserva de pior caso depende |
| ARQ-01 | gateway-http | Architectural | 🟡 | Acumula orquestração, roteamento, serviço da SPA e repasse de streaming, e depende de 4 módulos. Testá-lo isoladamente exige quatro dublês simultâneos |
| ARQ-02 | identidade | Architectural | 🟡 | Duas responsabilidades com atores e ciclos de vida distintos no mesmo módulo: identidade de entidade consumidora (chave virtual) e autenticação do operador (senha) |
| ARQ-03 | janela | Architectural | 🔴 | Nenhum módulo é dono da VIRADA da janela. `janela` apenas calcula limites; ninguém cria a linha de contador da nova janela nem executa o reset. UC-4 (reset reverte o corte) ficou sem módulo responsável |
| ARQ-04 | painel-api | Architectural | 🟢 | A fronteira entre painel-api e painel-web é fina; poderiam ser um módulo só, liberando orçamento do porte congelado |
| IMP-01 | gateway-http | Implementability | 🟡 | Repasse de streaming somado à reconciliação após o fim do stream é o trecho mais complexo do sistema, e está no módulo com mais dependências. Risco de não caber em uma única interação |
| IMP-02 | painel-web | Implementability | 🟡 | `specs/design/` não contém mockup nem referência visual: o implementador não tem contrato de UI, só a lista de campos |
| IMP-03 | upstream | Implementability | 🟡 | O contrato do upstream simulado não está especificado — como forjar `refusal`, timeout, stream parcial e `usage` arbitrário. É módulo do sistema (decisão f21733c9), não utilitário de teste |
| CIE-01 | rate-card | Scientific | 🟡 | Preços vêm de snapshot datado de 2026-06-24 sem processo declarado de revalidação contra a fonte canônica |
| CIE-02 | escrow | Scientific | 🟡 | A justificativa formal para instância única (não-I-confluência do invariante de limite, Bailis et al. 2014) está marcada em specs como NÃO verificada. Decisão estrutural apoiada em afirmação não confirmada |
| CIE-03 | precificador | Scientific | 🟡 | Premissa A6 (`count_tokens` não é cobrado) sem fonte: o custo do próprio mecanismo de medição é desconhecido |
| SEG-01 | identidade | Security | 🔴 | Senha única de operador sem limite de tentativas nem comparação em tempo constante: força bruta e ataque de temporização. Quem obtém a senha eleva tetos — ou seja, desliga o corte |
| SEG-02 | gateway-http | Security | 🔴 | Rota curinga `GET /*` servindo a SPA é superfície de travessia de caminho, num processo que detém a chave real do provedor e o arquivo do banco |
| SEG-03 | identidade | Security | 🟡 | Chave virtual sem expiração e sem escopo: um vazamento concede acesso até revogação manual, e nada limita quais modelos ou volumes ela pode acionar |
| SEG-04 | painel-api | Security | 🟡 | `PUT /api/tetos` altera o teto sem trilha de auditoria — a operação que desliga o corte é a menos rastreável do sistema |
| PERF-01 | escrow | Performance | 🟡 | O contador global é ponto único de serialização: toda requisição de toda entidade atravessa a mesma seção crítica. O teto de vazão do gateway é 1/duração da seção crítica |
| PERF-02 | persistencia | Performance | 🟡 | duplica: A-01 — `sqlite3` síncrono bloqueia o event loop durante a transação, transformando latência de disco em latência de todas as requisições em voo |
| PERF-03 | persistencia | Performance | 🟡 | `evento_uso` cresce sem política de retenção: o banco cresce proporcionalmente ao uso, indefinidamente, no mesmo arquivo de que depende a seção crítica |
| PERF-04 | painel-api | Performance | 🟢 | `GET /api/consumo` sem paginação nem agregação pré-computada; varre eventos a cada carregamento do painel |
| REG-01 | persistencia | Regulatory | 🟡 | Se entidade consumidora corresponder a uma pessoa, `evento_uso` é dado pessoal de produtividade. Nenhum requisito normativo (retenção, eliminação, base legal) foi identificado na Fase 0 nem rastreado a módulo algum |
| RES-01 | upstream | Resilience | 🔴 | Falha, timeout ou desconexão após a reserva deixa a reserva ÓRFÃ, e a expiração automática está declarada fora de escopo. `reservado_nano` cresce monotonicamente até a entidade ser cortada com consumo real baixo. Degradação garantida pelo desenho, não hipotética |
| RES-02 | gateway-http | Resilience | 🟡 | Resposta 429 ou 5xx do provedor: nada no desenho especifica que a reserva é liberada nesse caminho |
| RES-03 | gateway-http | Resilience | 🟡 | duplica: RES-01 — cliente que desconecta durante o streaming faz o `usage` nunca chegar |
| UX-01 | painel-web | UI/UX | 🟡 | O estado "cortado" não informa QUAL teto estourou (global ou da entidade) nem quando volta; sem isso o operador não sabe qual teto elevar |
| UX-02 | gateway-http | UI/UX | 🟡 | A resposta de negação ao app consumidor não tem código HTTP nem corpo especificados. O app não consegue distinguir "teto esgotado" de "429 do provedor" e retenta — exatamente o retry storm que a Fase 0 identificou ao separar limite de taxa de teto de orçamento |
| UX-03 | painel-web | UI/UX | 🟢 | Nenhum requisito de acessibilidade definido (contraste, navegação por teclado, leitor de tela) |
| SUS-01 | precificador | Sustainability / Proportionality | 🟡 | `count_tokens` antes de cada requisição acrescenta uma ida-e-volta de rede por requisição apenas para tornar a reserva mais justa. Custo desproporcional ao ganho, e possivelmente cobrado (A6) |
| SUS-02 | persistencia | Sustainability / Proportionality | 🟢 | duplica: PERF-03 — retenção infinita de eventos de uso |
| ETI-01 | escrow | Ethical / Human Impact | 🟡 | O corte não tem mecanismo de exceção nem aviso ao afetado: o trabalho de uma pessoa é interrompido sem recurso, até o operador agir ou a janela virar |
| ETI-02 | painel-web | Ethical / Human Impact | 🟢 | Se entidade corresponder a pessoa, o painel é monitoramento individual de produtividade visível a qualquer operador, sem transparência para o monitorado |
| PRO-01 | escrow | Process / Workflow | 🔴 | Reserva aberta na janela N e reconciliada na janela N+1 debita a janela errada. A transição de janela não define o que ocorre com reservas que a atravessam |
| PRO-02 | identidade | Process / Workflow | 🟡 | Revogar uma chave virtual com reservas abertas não tem comportamento definido: as reservas ficam presas sem dono |
| GOV-01 | painel-api | Governance / Accountability | 🟡 | duplica: SEG-04 — alteração de teto não é atribuível a nenhum ator |
| GOV-02 | rate-card | Governance / Accountability | 🟡 | Nenhum dono declarado para manter a tabela de preços. Como modelo sem preço é negado por decisão, a omissão de manutenção converte-se diretamente em indisponibilidade de serviço |
| OBS-01 | gateway-http | Observability / Operability | 🔴 | Nenhum módulo tem responsabilidade de log ou métrica. "Por que minha requisição foi negada?" não é diagnosticável em produção sem alterar código — e negar é a função central do sistema |
| OBS-02 | persistencia | Observability / Operability | 🟡 | O invariante I2 (soma das reservas abertas = `reservado_nano`) não é verificável em execução; uma corrupção do contador seria silenciosa |
| CTL-01 | escrow | Control Engineering | 🔴 | duplica: RES-01 — `reservado_nano` acumula sem sinal de erro nem mecanismo de correção: laço de controle sem realimentação, com desvio monotônico |
| CTL-02 | painel-web | Control Engineering | 🟡 | O saldo exibido inclui reservas em voo e oscila com o tráfego. O operador pode reagir a uma oscilação transitória elevando o teto — oscilação induzida pelo observador |
| GAM-01 | escrow | Game Theory | 🔴 | Ataque de negação por reserva: um app declara `max_tokens` enorme, a reserva de pior caso consome o teto global e todas as demais entidades são negadas — sem gastar um único token. Custo do ataque: uma requisição |
| GAM-02 | escrow | Game Theory | 🟡 | O teto global compartilhado cria corrida: consumir cedo no mês domina consumir tarde. O desenho premia o comportamento que ele existe para conter |
| LIN-01 | gateway-http | Linguistics / Grammar | 🟡 | "Compatível com a API da Anthropic" não está especificado: quais rotas, quais cabeçalhos são repassados, o que ocorre com parâmetros desconhecidos. Duas implementações do mesmo contrato divergiriam |
| LIN-02 | escrow | Linguistics / Grammar | 🟡 | `Decisao.motivo` é texto livre; o cliente não pode programar contra ele. Falta um código enumerado de motivo de negação |
| MEC-01 | rate-card | Mechanical Engineering | 🟡 | O preço promocional do Sonnet 5 expira em 2026-08-31 — 21 dias após hoje. A partir daí o sistema subcontabiliza silenciosamente. Tolerância zero à passagem do tempo, sem sinal de alerta |
| MEC-02 | upstream | Mechanical Engineering | 🟡 | Acoplado à forma exata do objeto `usage`. Uma categoria nova de token entraria como não contabilizada, e nada verifica que as categorias conhecidas cobrem o total reportado |

---

## Iteração 2 — V(2)

Lentes redeclaradas contra V(2) em 2026-08-10T21:12:49Z (11 condicionais ativadas;
Migration / Coexistence não ativada — segue greenfield). Os três críticos desta rodada
foram **criados pelas próprias simplificações de V(2)**.

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| RES-04 | escrow | Resilience | 🔴 | O TTL de 15 min pode expirar a reserva de uma requisição **viva**. A documentação registra que requisições de alto esforço levam "muitos minutos"; uma geração longa em streaming ultrapassa 15 min. A reserva é liberada, o saldo volta, outra requisição passa — e quando a original reconcilia, o custo entra por cima do teto. A simplificação 2 criou um caminho de estouro que V(1) não tinha |
| RES-05 | escrow | Resilience | 🔴 | A reconciliação de uma reserva já expirada é silenciosamente descartada: a guarda de idempotência retorna sem fazer nada quando o estado não é `'aberta'`. O custo REAL da requisição longa nunca é contabilizado — perda de contabilidade, não apenas de saldo |
| A-05 | precificador | Assumptions | 🔴 | Remover `count_tokens` deixou o custo de **entrada** fora da reserva. Um prompt próximo da janela de 1M tokens custa US$ 5,00 de entrada no Opus 5, nada disso reservado; o teto de `max_tokens` limita a saída, não a entrada. Uma única requisição de prompt grande pode violar o invariante que é o critério de acerto do projeto |
| A-06 | janela | Assumptions | 🟡 | `janela` virou função pura de um instante, mas nada define QUEM fornece o instante nem que seja o mesmo ao longo da requisição. Reserva e reconciliação com instantes distintos podem cair em janelas diferentes |
| ARQ-05 | painel-api | Architectural | 🟡 | Absorveu autenticação e serviço da SPA: agora acumula leitura, configuração, autenticação e estático. O problema de ARQ-01 foi **movido**, não eliminado |
| IMP-04 | escrow | Implementability | 🟡 | Concentra expiração, teto de `max_tokens`, decisão sobre dois escopos, reserva e reconciliação, tudo numa seção crítica sem `await`. É o módulo mais denso do sistema e o mais difícil de sustentar numa única interação |
| CIE-04 | escrow | Scientific | 🟡 | O TTL de 15 min tem fonte para o número de referência (timeout padrão de 10 min do SDK) mas não para a regra de derivação — por que 1,5×? Parâmetro semi-fundamentado |
| SEG-05 | painel-api | Security | 🟡 | O limite de tentativas de login roda no mesmo event loop de thread única do proxy. Uma rajada de tentativas de senha consome o loop e degrada TODAS as requisições ao LLM: autenticação e caminho crítico disputam o mesmo recurso escasso |
| SEG-06 | gateway-http | Security | 🟡 | O log estruturado de toda decisão registra a entidade; se registrar também a chave virtual — ainda não especificado — o arquivo de log vira arquivo de credenciais |
| PERF-05 | persistencia | Performance | 🟡 | A limpeza por retenção e a verificação de invariante rodam na mesma conexão síncrona bloqueante. Um `DELETE` grande bloqueia o event loop e, com ele, todo o tráfego ao LLM |
| REG-02 | persistencia | Regulatory | 🟢 | Com entidade redefinida como identidade técnica, nenhum requisito normativo aplicável foi identificado. Ausência de achado é resultado válido |
| UX-04 | painel-web | UI/UX | 🟡 | Com a virada preguiçosa, uma janela sem nenhuma requisição não tem linha de contador. O painel precisa distinguir "consumo zero" de "sem dados", sob pena de exibir zero para uma entidade cujo estado é desconhecido |
| SUS-03 | persistencia | Sustainability / Proportionality | 🟢 | A retenção configurável introduzida em V(2) resolve o crescimento indefinido; nenhum achado novo |
| ETI-03 | escrow | Ethical / Human Impact | 🟢 | Com entidade = identidade técnica, o impacto humano direto foi mitigado na raiz; permanece apenas o efeito indireto já registrado em ETI-01 |
| PRO-03 | escrow | Process / Workflow | 🟡 | A máquina de estados da reserva ganhou de fato o estado `'expirada'`, que não está declarado — V(1) previa `aberta` \| `reconciliada` \| `liberada`. Sem o estado explícito, expiração e liberação por erro ficam indistinguíveis na auditoria |
| GOV-03 | escrow | Governance / Accountability | 🟡 | A expiração de reserva é uma ação do sistema que altera saldo, sem ator atribuível e sem registro. É a única mutação de contador sem autoria |
| OBS-03 | escrow | Observability / Operability | 🟡 | As expirações não são observáveis. Um sistema que libera silenciosamente reservas de requisições vivas precisa emitir sinal ao fazê-lo; sem isso, RES-04 e RES-05 são indiagnosticáveis em produção |
| CTL-03 | escrow | Control Engineering | 🟡 | O TTL é parâmetro de laço de controle ajustado sem medição: 15 min veio de um timeout de SDK, não da distribuição real de duração das requisições deste sistema. Curto demais causa RES-04; longo demais devolve o desvio monotônico de RES-01 |
| GAM-03 | escrow | Game Theory | 🟡 | O teto de `max_tokens` limita UMA requisição, não o agregado. N requisições simultâneas logo abaixo do teto reservam N × teto e seguem negando as demais entidades. A defesa encarece o ataque, não o elimina |
| LIN-03 | gateway-http | Linguistics / Grammar | 🟢 | HTTP 402 com corpo próprio é contrato novo que nenhum SDK conhece; exige documentação para o cliente tratá-lo. Não é ambíguo, mas é não-padrão |
| MEC-03 | rate-card | Mechanical Engineering | 🟡 | "Recusar iniciar com tabela vencida" converte problema de contabilidade em **queda total programada**: em 2026-08-31 o gateway deixa de subir. Trocou-se falha silenciosa por falha ruidosa e catastrófica, sem o meio-termo de recusar apenas os modelos vencidos |
