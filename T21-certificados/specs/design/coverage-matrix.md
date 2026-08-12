# Matriz de cobertura — crítica adversarial

Uma linha por achado. Ids únicos no projeto, prefixo consistente por lente.
Prefixo `M-` é reservado a módulos e não aparece aqui.

## Iteração 1 — V(1)

| id | module | lens | severity | description |
|------|--------|----------|----------|-------------|
| ASS-01 | certificado | Assumptions | 🟡 | assume que "o certificado do host" é um só. `getPeerX509Certificate()` devolve o leaf; a cadeia servida pode ter intermediário que expira ANTES dele. Intermediário vencido derruba o serviço com o leaf válido — a falha que o produto existe para prevenir, invisível ao design. Premissa não declarada em A1-A8 |
| ASS-02 | sonda-tls | Assumptions | 🟡 | assume TLS direto no `connect`. Serviços com STARTTLS (SMTP 587, IMAP 143, PostgreSQL 5432) negociam depois do protocolo em claro: a sonda falha e o certificado fica invisível, contradizendo A1 ("todo certificado de interesse exposto em TLS alcançável") |
| ASS-03 | reconciliacao | Assumptions | 🟡 | assume que existe observação anterior. Na PRIMEIRA varredura de um alvo `anterior = null` e o contrato não define o resultado — risco de classificar cadastro novo como troca não autorizada |
| ASS-04 | politica-limiar | Assumptions | 🟡 | assume `notBefore <= agora`. Certificado emitido com validade futura não tem estado no enum (`ok`..`expirado` não cobre "ainda não válido") — cai em `ok` e some do radar |
| ASS-05 | trilha | Assumptions | 🟡 | assume serialização determinística do evento para o hash. Se o evento for serializado com `JSON.stringify`, ordem de chaves e formato de `Date` variam entre implementações/versões: a cadeia acusa adulteração onde não houve, tornando CA-4 falso-positivo |
| ASS-06 | autorizacao | Assumptions | 🟡 | assume que existe pelo menos um Aprovador cadastrado. Nada no design diz quem cria o primeiro ator; sem ele nenhum pedido pode ser aprovado e o sistema nasce travado |
| ASS-07 | repositorio | Assumptions | 🟢 | A6 declara "uma varredura por vez", mas nada impede duas instâncias do processo abrirem o mesmo arquivo SQLite — a premissa é sobre disciplina do operador, não sobre o sistema |
| ASS-08 | relogio | Assumptions | 🟡 | a porta devolve o tempo do SO sem verificação de sanidade nem monotonia. A2 está declarada, porém NENHUM módulo consegue detectá-la falsa: relógio adiantado marca tudo expirado, atrasado esconde vencimento — e a trilha carimba com o mesmo relógio |
| ARC-01 | casos-de-uso | Architectural | 🟡 | depende dos 10 demais módulos e concentra 5 operações heterogêneas (varrer, abrirPedido, aprovarPedido, auditar, verificarIntegridade). Testá-lo isolado exige 10 dublês; é o ponto onde o grafo colapsa |
| ARC-02 | pedido | Architectural | 🟡 | entidade de domínio depende de `autorizacao` só para consultar `podeAprovar`. Bastaria receber o papel como valor — acoplamento evitável entre agregado e identidade |
| ARC-03 | repositorio | Architectural | 🟡 | um único Repository para 4 agregados (certificado, pedido, trilha, autorizacao). Trocar a persistência de um força mexer no módulo inteiro; a fronteira não é substituível por partes |
| ARC-04 | reconciliacao | Architectural | 🟢 | recebe `estado` já classificado E declara dependência de `politica-limiar` — ou classifica, ou recebe classificado. Dependência declarada sem uso claro |
| ARC-05 | web-ui | Architectural | 🟡 | acumula roteamento, render das 5 telas e gestão de sessão. Sessão é preocupação de segurança, não de apresentação: não dá para substituir o render sem tocar na autenticação |
| IMP-01 | web-ui | Implementability | 🔴 | o contrato lista rotas mas não define o HTML das telas, os campos de cada formulário, nem o mecanismo de sessão (cookie? assinado? expira quando?). Uma sessão dedicada de implementação teria de inventar tudo isso — exatamente o que AP7 proíbe |
| IMP-02 | repositorio | Implementability | 🔴 | nenhum esquema de banco definido: sem tabelas, colunas, tipos, chaves ou índices. 10 operações declaradas e zero DDL — o módulo não é implementável a partir do documento |
| IMP-03 | politica-limiar | Implementability | 🟡 | `validarLimiares(l, vidaTotalDias)` compara limiar global com vida POR certificado, mas não diz QUANDO validar: no cadastro do alvo (quando ainda não há certificado) ou a cada varredura? CA-5 depende dessa resposta |
| IMP-04 | autorizacao | Implementability | 🟡 | `criarAtor` não define os parâmetros do scrypt (N, r, p, keylen, tamanho e origem do salt) nem o formato de armazenamento do hash |
| IMP-05 | trilha | Implementability | 🟢 | `anexar` não define o formato canônico do evento nem o encoding do hash (hex ou base64) — duas implementações produzem cadeias incompatíveis |
| SCI-01 | autorizacao | Scientific | 🟡 | duplica: IMP-04 — os parâmetros do scrypt não têm fonte citada. RFC 7914 e as recomendações OWASP dão valores concretos; nenhum aparece em specs/technical, violando a regra "nenhum parâmetro numérico sem referência" |
| SCI-02 | sonda-tls | Scientific | 🟡 | `timeoutMs` aparece na assinatura sem valor nem fonte. Timeout de handshake é parâmetro operacional com prática documentada; será inventado na Fase 5 se não for depositado antes |
| SCI-03 | politica-limiar | Scientific | 🟢 | o estado `sem-expiracao` tem base normativa para o VALOR (sentinela 99991231235959Z, RFC 5280 §4.1.2.5) mas nenhuma fonte para a CONDUTA de um monitor diante dele |
| SCI-04 | trilha | Scientific | 🟢 | SHA-256 escolhido sem referência de adequação para encadeamento de auditoria; a escolha é razoável mas não citada |
| SEC-01 | web-ui | Security | 🔴 | formulários POST com sessão por cookie e nenhuma proteção CSRF declarada. Uma página maliciosa aberta no mesmo browser submete `POST /pedidos/:id/aprovar` e forja a aprovação — destrói exatamente a garantia que o produto vende |
| SEC-02 | web-ui | Security | 🔴 | subject, issuer e SAN vêm de terceiro NÃO CONFIÁVEL (o host varrido) e são renderizados em HTML sem escape declarado. Quem controla um host varrido injeta script na tela do aprovador — XSS armazenado por certificado |
| SEC-03 | web-ui | Security | 🟡 | nenhum endereço de bind declarado. Se o servidor escutar em 0.0.0.0, a aplicação "local" fica exposta à rede inteira, com login sem TLS |
| SEC-04 | autorizacao | Security | 🟡 | sem limite de tentativas nem atraso progressivo no login — força bruta contra a senha do Aprovador sem custo |
| SEC-05 | web-ui | Security | 🟡 | sessão sem expiração declarada e sem flags de cookie (HttpOnly, SameSite, Secure). Sessão esquecida aberta = aprovação disponível a quem sentar na máquina |
| SEC-06 | sonda-tls | Security | 🟡 | `rejectUnauthorized:false` é necessário e correto aqui, mas não há limite declarado de tamanho de cadeia nem de tempo total: host malicioso responde com cadeia enorme e consome memória do monitor |
| SEC-07 | repositorio | Security | 🟢 | nenhuma declaração de uso de statements parametrizados; com Data Mapper escrito à mão, concatenação de SQL é o caminho de menor esforço |
| SEC-08 | trilha | Security | 🟡 | cadeia com hash simples, sem chave (não é HMAC). Quem escreve no banco recria a cadeia inteira e ela verifica como válida — A5 declara o limite, mas o sistema não distingue "íntegra" de "reescrita coerentemente" |
| PER-01 | casos-de-uso | Performance | 🟡 | `varrer()` é sequencial com timeout por alvo: N alvos inalcançáveis × timeout. 50 alvos × 10 s = 8 min de espera, com a decisão de concorrência (single-threaded sequencial) tornando isso estrutural |
| PER-02 | web-ui | Performance | 🟡 | `POST /varrer` executa a varredura inteira dentro da requisição, sem progresso — o browser expira antes do fim em inventários grandes |
| PER-03 | repositorio | Performance | 🟡 | `verificarIntegridade()` lê a cadeia inteira e `listarTrilha` percorre estrutura que só cresce: custo O(n) crescente a cada varredura, sem índice nem paginação declarados |
| PER-04 | casos-de-uso | Performance | 🟢 | grava uma observação por alvo a cada varredura mesmo quando nada mudou — crescimento linear de dados sem informação nova |
| REG-01 | casos-de-uso | Regulatory | 🟡 | NIST SP 1800-16 exige escalação automática ao responsável central por inação. O design produz o estado `escalar`, mas nenhum módulo tem destinatário ou responsável — a escalação morre no painel. Desvio consciente (decisão de P0), porém a rastreabilidade normativa fica incompleta |
| REG-02 | certificado | Regulatory | 🟡 | RFC 5280 §4.1.2.5 exige suportar UTCTime E GeneralizedTime; `deDer` não declara tratamento de `notAfter` a partir de 2050, faixa em que UTCTime deixa de valer |
| REG-03 | politica-limiar | Regulatory | 🟢 | CA/B SC-081v3 muda a validade máxima ao longo do tempo (200 d hoje, 100 d em 2027, 47 d em 2029). Nenhum módulo registra sob qual regime a classificação foi feita — auditoria futura não sabe qual regra valia |
| REG-04 | trilha | Regulatory | 🟡 | auditoria exige carimbo temporal confiável; a trilha carimba com `relogio.agora()` da própria máquina, sem detecção de retrocesso do relógio — entradas podem ficar fora de ordem cronológica sem quebrar a cadeia de hash |
| RES-01 | sonda-tls | Resilience | 🔴 | os 4 tipos de erro estão declarados, mas o design NÃO diz o que a varredura faz com eles. Se o alvo mantém o estado anterior, o painel exibe dado velho como atual — o monitor falha silenciosamente exatamente quando o host está com problema |
| RES-02 | casos-de-uso | Resilience | 🟡 | não declara se uma falha no meio da varredura aborta o restante ou continua. Um alvo com timeout pode impedir a varredura dos demais |
| RES-03 | repositorio | Resilience | 🟡 | sem transação declarada envolvendo salvar observação + anexar trilha + fechar pedido. Falha entre as três deixa estado e trilha divergentes — e a trilha é a prova do produto |
| RES-04 | sonda-tls | Resilience | 🟡 | sem retry nem backoff: host lento intermitente vira falso "inalcançável", e o operador aprende a ignorar |
| RES-05 | repositorio | Resilience | 🟢 | arquivo de banco ausente ou corrompido não tem caminho de recuperação nem de diagnóstico declarado |
| UX-01 | web-ui | UI/UX | 🔴 | há `POST /alvos` mas nenhuma das 5 telas declaradas é o cadastro de alvo. UC-1 (colocar um host sob monitoramento) não pode ser executado pela interface — o caso de uso de entrada do produto não tem porta |
| UX-02 | web-ui | UI/UX | 🟡 | `troca-nao-autorizada` e `escalado` não têm representação declarada no painel. São as duas informações mais importantes do produto e não há onde exibi-las |
| UX-03 | web-ui | UI/UX | 🟡 | duplica: PER-02 — sem qualquer feedback durante a varredura, o operador não distingue "processando" de "travado" e dispara de novo |
| UX-04 | web-ui | UI/UX | 🟡 | a tela de trilha não declara como comunicar tamper-evident × tamper-proof. Sem isso o operador lê "válida" como "impossível de forjar" e confia além do que o sistema garante |
| UX-05 | web-ui | UI/UX | 🟢 | mensagens de erro não especificadas para senha incorreta, papel insuficiente e limiar inválido |
| SUS-01 | repositorio | Sustainability / Proportionality | 🟡 | trilha e observações crescem indefinidamente, sem política de retenção nem arquivamento. O custo cresce com o uso e nada no design o limita |
| SUS-02 | casos-de-uso | Sustainability / Proportionality | 🟢 | duplica: PER-04 — persistir observação idêntica a cada varredura gasta armazenamento sem entregar informação |
| ETH-01 | reconciliacao | Ethical / Human Impact | 🔴 | `troca-nao-autorizada` é uma acusação automatizada sobre conduta humana. Uma troca legítima de emergência é registrada como não autorizada, e a trilha é append-only: não existe caminho de contestação, correção ou contexto. Decisão automatizada sobre pessoas sem recurso |
| ETH-02 | trilha | Ethical / Human Impact | 🟡 | a trilha nomeia pessoas e é imutável por construção. Um registro errado (ator errado, sessão compartilhada) não pode ser retificado, apenas anexado — e nenhum procedimento de retificação está declarado |
| ETH-03 | autorizacao | Ethical / Human Impact | 🟢 | não há desativação de ator: quem sai da equipe permanece Aprovador válido indefinidamente |
| PRO-01 | pedido | Process / Workflow | 🔴 | a máquina de estados não tem caminho de rejeição nem de cancelamento. Pedido aberto por engano, ou recusado pelo Aprovador, fica `pendente` para sempre — estado órfão, e "recusar" é uma decisão de governança tão legítima quanto aprovar |
| PRO-02 | pedido | Process / Workflow | 🟡 | não há transição definida para o pedido cujo alvo atinge `expirado` antes da emissão — o pedido continua aberto sobre um certificado já morto |
| PRO-03 | reconciliacao | Process / Workflow | 🟡 | aprovação não expira: um pedido `aprovado` cujo host só troca o certificado meses depois fecha com uma autorização velha, dissociada do contexto em que foi dada |
| PRO-04 | casos-de-uso | Process / Workflow | 🟡 | o papel Auditor não participa de nenhuma transição — existe como permissão de leitura, sem responsabilidade no processo. Ator declarado sem fluxo |
| PRO-05 | pedido | Process / Workflow | 🟢 | o mesmo ator pode abrir e aprovar (segregação está fora de escopo por decisão), mas a trilha não MARCA a auto-aprovação como tal — o auditor não consegue filtrá-la |
| GOV-01 | casos-de-uso | Governance / Accountability | 🔴 | cadastrar/remover alvo e alterar limiares não passam pela trilha. Afrouxar o limiar de 30 para 5 dias, ou remover um alvo do inventário, é mais poderoso que aprovar um pedido — e é o único ato do sistema sem autor atribuível |
| GOV-02 | repositorio | Governance / Accountability | 🟡 | nenhuma entidade declara dono. "Quem responde por este certificado?" não tem resposta no modelo, embora seja a primeira pergunta de qualquer auditoria |
| GOV-03 | autorizacao | Governance / Accountability | 🟡 | a criação de atores não é atribuível — quem criou o Aprovador não fica registrado, e é o ato que confere todo o poder do sistema |
| GOV-04 | trilha | Governance / Accountability | 🟢 | não há exportação da trilha; um auditor externo depende do próprio sistema auditado para ler o que ele registrou sobre si |
| OBS-01 | casos-de-uso | Observability / Operability | 🟡 | não existe registro persistente das varreduras (quando rodou, quantos alvos, quantas falhas). O operador não consegue responder "a última varredura foi quando?" sem inspecionar o banco |
| OBS-02 | web-ui | Observability / Operability | 🟡 | o painel não exibe a idade do dado. Um inventário varrido há um mês é visualmente idêntico a um varrido agora — a UI apresenta como fato presente o que é registro histórico |
| OBS-03 | sonda-tls | Observability / Operability | 🟢 | o tipo de erro é classificado em 4 categorias mas o motivo original (mensagem do handshake) é descartado — diagnosticar por que um host falha exige alterar o código |
| CTL-01 | reconciliacao | Control Engineering | 🟡 | o laço observar→comparar→corrigir não tem watchdog de si mesmo: se a varredura deixa de ser disparada, nada gera sinal de erro. O sistema não regula o próprio ciclo, só reage quando invocado |
| CTL-02 | politica-limiar | Control Engineering | 🟡 | limiar é configuração de runtime que reclassifica o inventário inteiro no instante em que muda. Um alvo pode oscilar entre `critico` e `ok` conforme alguém ajusta a configuração, sem que o estado anterior fique registrado |
| CTL-03 | pedido | Control Engineering | 🟢 | sem histerese nas fronteiras: com arredondamento de dias, um alvo em 30,0 dias pode alternar de estado entre varreduras consecutivas sem que nada real tenha mudado |
| GAM-01 | casos-de-uso | Game Theory | 🔴 | o caminho de menor esforço para o operador é trocar o certificado direto no host e ignorar o sistema. O produto não tem poder algum sobre o host — só registra. Se a consequência de burlar é um destaque no painel que o próprio burlador administra, o equilíbrio racional é burlar |
| GAM-02 | autorizacao | Game Theory | 🟡 | duplica: PRO-05 — solicitante e aprovador podendo ser a mesma pessoa reduz a zero o custo de "cumprir o processo", e a aprovação vira formalidade autoassinada |
| GAM-03 | web-ui | Game Theory | 🟢 | nada captura o que foi exibido ao Aprovador no momento da decisão; aprovar em lote sem examinar é indistinguível de aprovar com análise |
| LIN-01 | reconciliacao | Linguistics / Grammar | 🔴 | contrato ambíguo em dois pontos: (a) `pedidoAberto` inclui estado `aprovado` ou apenas `pendente`? (b) recebe `estado` já classificado mas declara dependência de `politica-limiar` — duas implementações corretas do contrato divergem sobre quem classifica. Como a Fase 5 implementa módulos em sessões separadas, a ambiguidade vira incompatibilidade real |
| LIN-02 | pedido | Linguistics / Grammar | 🟡 | a convenção `Ok \| Erro` não tem forma canônica declarada (`{ok:true,valor}` vs `{tipo:'ok'}` vs tupla). 11 módulos a implementarão independentemente e não vão compor |
| LIN-03 | politica-limiar | Linguistics / Grammar | 🟡 | o enum mistura duas dimensões: `ok/aviso/atencao/critico/expirado` são níveis de urgência, `sem-expiracao` é propriedade do certificado. Forçar as duas num tipo só produz decisões arbitrárias (certificado sem expiração é `ok`?) |
| LIN-04 | sonda-tls | Linguistics / Grammar | 🟢 | `ErroSonda.tipo='tls'` é vago: cobre certificado ilegível, versão de protocolo incompatível e cadeia inválida sem distingui-los |
| MEC-01 | repositorio | Mechanical Engineering | 🟡 | nenhuma faixa de versão de Node declarada, embora o módulo dependa de API experimental (`node:sqlite`) e o projeto inteiro dependa de type-stripping nativo. O sistema só tolera a especificação exata da máquina onde foi escrito |
| MEC-02 | certificado | Mechanical Engineering | 🟡 | o contrato assume campos presentes. Certificado sem SAN, com subject vazio ou algoritmo incomum é variação normal do mundo real e não tem comportamento definido |
| MEC-03 | politica-limiar | Mechanical Engineering | 🟢 | tolerância de fronteira indefinida: 29,9 dias é `critico` ou `atencao`? A regra de arredondamento não está declarada e muda o resultado de CA-1 |
| MEC-04 | relogio | Mechanical Engineering | 🟢 | não declara que a implementação deve devolver UTC. Uma implementação que devolva hora local passa nos testes na máquina de origem e erra por horas em outro fuso |

## Iteração 2 — V(3)

Nota de rastreabilidade: o motor do Versus numera esta rodada como V(3); a arquitetura
efetivamente criticada aqui é a seção **`# V(2)`** de `specs/technical/architecture.md`
— o mesmo artefato, contagem de versão do motor. Os 12 módulos de V(2), incluindo os
dois novos (`caso-varredura`, `caso-governanca`) e os mecanismos introduzidos na Fase 3
(CSRF, `justificarTroca`, `emTransacao`, cadeia inteira, `verificarMonotonia`).

| id | module | lens | severity | description |
|------|--------|----------|----------|-------------|
| ASS-09 | caso-varredura | Assumptions | 🟡 | assume UM pedido aprovado por alvo. `PortaPedidos.aprovadoDe` pode devolver vários (dois aprovados para o mesmo alvo), mas `reconciliar` recebe `pedidoAprovado` no singular — qual deles a emissão fecha não está definido |
| ASS-10 | certificado | Assumptions | 🟡 | `notAfterEfetivo = min(cadeia)` assume que todo certificado servido pertence à cadeia de confiança em uso. Servidores costumam servir cross-signed ou raízes extras; um certificado irrelevante com validade curta vira alarme permanente que nenhuma renovação resolve |
| ASS-11 | caso-governanca | Assumptions | 🟡 | `alterarLimiares` assume efeito só para frente. As observações já gravadas não são reclassificadas, então o painel pode exibir estado calculado sob a política antiga sem indicar isso |
| ASS-12 | trilha | Assumptions | 🟡 | `justificarTroca` assume que existe um evento `troca-nao-autorizada` ao qual se referir, mas nada no contrato liga a justificativa a um evento específico — com duas trocas não autorizadas no mesmo alvo, não se sabe qual foi justificada |
| ARC-06 | caso-governanca | Architectural | 🟡 | 10 operações num módulo: herdou parte do problema que motivou dividir `casos-de-uso`. Auditoria (leitura pura, sem transação) e governança (escrita transacional atribuível) têm naturezas e dependências distintas |
| ARC-07 | web-ui | Architectural | 🟡 | `ARC-05` foi resolvido só no papel: sessão, CSRF, roteamento e render das 6 telas continuam no mesmo módulo. Não dá para substituir o render sem tocar na autenticação |
| IMP-06 | caso-varredura | Implementability | 🟡 | a relação entre "uma transação por alvo" e o registro global `varredura-iniciada`/`varredura-concluida` não está definida: em qual transação `varredura.concluida_em` é escrita, e o que acontece com ela se o último alvo falhar? |
| IMP-07 | web-ui | Implementability | 🟡 | token CSRF é exigido mas não especificado: onde é gerado, onde é guardado, escopo por sessão ou por formulário, e qual o comportamento quando expira. Implementável de três formas incompatíveis |
| SCI-05 | web-ui | Scientific | 🟢 | expiração de sessão em 30 min entrou sem fonte citada — é o único parâmetro de V(2) que escapou de `specs/technical/parameters.md` |
| SCI-06 | sonda-tls | Scientific | 🟢 | limite de 10 certificados na cadeia é declarado como decisão de projeto sem fonte; o documento admite a ausência, o que é honesto, mas o parâmetro segue sem referência |
| SEC-09 | caso-governanca | Security | 🔴 | `justificarTroca` aceita QUALQUER ator autenticado — inclusive o que fez a troca por fora. Quem burla tem, por definição, acesso ao sistema: ele mesmo justifica a própria troca e o destaque desaparece. O mecanismo criado na Fase 3 para encarecer a burla é operável pelo burlador |
| SEC-10 | web-ui | Security | 🟡 | sessão de 30 min sem rotação do identificador após autenticação — fixação de sessão: um identificador conhecido antes do login continua válido depois dele |
| SEC-11 | repositorio | Security | 🟡 | `emTransacao` como única forma de escrita é convenção, não imposição: nada no contrato impede um módulo de obter o handle do banco e escrever fora da transação e fora da trilha |
| PER-05 | caso-varredura | Performance | 🟡 | a retentativa única introduzida contra `RES-04` dobra o pior caso da varredura sequencial: 50 alvos inalcançáveis × 2 tentativas × 10 s = 16 min |
| PER-06 | trilha | Performance | 🟢 | `PER-03` não foi resolvido, apenas indexado: `verificar` continua lendo a cadeia inteira, e a cadeia só cresce |
| REG-05 | caso-governanca | Regulatory | 🟡 | `removerAlvo` sem `ON DELETE` definido no DDL: auditoria exige que observações e pedidos históricos sobrevivam à remoção do alvo, e o esquema atual ou apaga em cascata ou falha por chave estrangeira |
| RES-06 | caso-varredura | Resilience | 🟡 | processo morto no meio da varredura deixa `varredura.concluida_em` NULL para sempre, sem caminho de reconciliação — varreduras órfãs acumulam e a contagem de falhas fica errada |
| RES-07 | relogio | Resilience | 🟡 | `verificarMonotonia` detecta o retrocesso mas o contrato não diz o que o sistema FAZ com ele: aborta a varredura, registra e continua, ou recusa gravar na trilha? |
| UX-06 | web-ui | UI/UX | 🟡 | mesmo defeito de `UX-01` em outro lugar: `autorizacao` expõe `criarAtor` e `desativar`, e nenhuma das 6 telas é gestão de atores. Criar o primeiro Aprovador (`ASS-06`) continua sem porta na UI |
| UX-07 | web-ui | UI/UX | 🟢 | existe `POST /alvo/:id/justificar` mas nenhuma tela declarada onde a justificativa é escrita |
| SUS-03 | repositorio | Sustainability / Proportionality | 🟢 | `falha_sonda` grava uma linha por alvo falho por varredura, sem deduplicação: um host permanentemente fora produz uma linha nova a cada execução |
| ETH-04 | caso-governanca | Ethical / Human Impact | 🟡 | a justificativa encerra o assunto sem revisão: nada distingue "justificada e aceita" de "justificada e contestada". Quem foi acusado escreve a própria defesa e ela vale como resolução final |
| PRO-06 | pedido | Process / Workflow | 🟡 | `expirarSemEmissao` é transição declarada que nenhum caso de uso chama — `caso-varredura` não a lista entre suas operações. Transição órfã, o inverso do estado órfão de `PRO-01` |
| PRO-07 | caso-governanca | Process / Workflow | 🟢 | `cancelarPedido` não restringe o estado de origem: cancelar um pedido já aprovado apagaria o efeito de uma aprovação registrada |
| GOV-05 | caso-governanca | Governance / Accountability | 🟡 | `dono` do alvo é texto livre, não referência a `ator(id)`. "Quem responde por este certificado" continua não sendo uma identidade do sistema — não dá para notificar, filtrar nem responsabilizar |
| OBS-04 | caso-varredura | Observability / Operability | 🟡 | `PER-02`/`UX-03` só foram parcialmente resolvidos: `RelatorioVarredura` é devolvido no fim, e o POST síncrono continua sem progresso incremental durante a execução |
| CTL-04 | caso-varredura | Control Engineering | 🟡 | "gravar observação só quando o fingerprint muda" ainda exige escrever `visto_ultima_vez` a cada varredura — a economia é menor que o previsto. Pior: mudança de política reclassifica sem nova observação, dessincronizando painel e histórico |
| GAM-04 | caso-governanca | Game Theory | 🔴 | duplica: SEC-09 — o mesmo defeito pelo lado do incentivo. Se o burlador pode encerrar a própria acusação, o payoff de burlar não mudou em relação a V(1) e o mecanismo adicionado na Fase 3 não alterou o equilíbrio |
| LIN-05 | reconciliacao | Linguistics / Grammar | 🟡 | `mudanca-sem-avanco` (fingerprint mudou, `notAfter` não avançou) é devolvido sem consumidor definido: `caso-varredura` não declara o que faz com esse valor — rollback de certificado fica sem tratamento |
| LIN-06 | repositorio | Linguistics / Grammar | 🟢 | as 4 portas nomeiam a mesma ideia de formas diferentes (`buscar` em Alvos e Atores, `abertoDe`/`aprovadoDe` em Pedidos, `ponta` em Trilha) — atrito desnecessário entre implementações feitas em sessões separadas |
| MEC-05 | repositorio | Mechanical Engineering | 🟡 | `PRAGMA journal_mode = WAL` combinado com trava exclusiva de escrita é contraditório: WAL existe para permitir leitores concorrentes com um escritor, e a trava exclusiva anula o motivo de usá-lo |

