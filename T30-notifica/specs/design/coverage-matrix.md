# Matriz de cobertura — crítica adversarial

Uma linha por achado. Ids únicos no projeto, prefixo estável por lente.
Nomes de módulo são os da tabela de `specs/technical/architecture.md`.

## Iteração 1 — V(1)

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| ASS-01 | delivery-worker | Assumptions | 🔴 | PRE-6 assume "worker único" mas nada o IMPÕE: subir `serve` duas vezes faz `claimDue` reivindicar a mesma entrega nos dois processos → entrega duplicada. A premissa é assumida, não garantida. |
| ASS-02 | ingestion | Assumptions | 🟡 | Assume que o conjunto de canais habilitados é conhecido no POST (entregas materializadas na transação). Se a pessoa habilitar webhook depois, a notificação já aceita nunca ganha essa entrega — comportamento não declarado. |
| ASS-03 | quiet-hours | Assumptions | 🟡 | Assume que todo dia local tem 1440 minutos. Em dias de transição de horário de verão o minuto de abertura (480) pode não existir ou existir duas vezes. |
| ASS-04 | rate-limiter | Assumptions | 🟡 | Assume leitura-e-escrita atômica do bucket. Vale com M-12 + worker único, mas o contrato `tryConsume` não declara a exigência — trocar o repositório quebraria silenciosamente. |
| ASS-05 | preferences | Assumptions | 🟡 | Invariante 3 ("ausência ≠ opt-out, resolve pelo padrão da categoria") assume um catálogo de categorias com padrão declarado. Nenhum módulo é dono desse catálogo; a tabela `preferences` não o modela. |
| ASS-06 | channel-webhook | Assumptions | 🟢 | Assume `webhook_secret` presente sempre que há `webhook_url`; o modelo permite URL sem segredo (colunas nullable independentes). |
| ARC-01 | suppression | Architectural | 🔴 | M-04 recebe `stage` e ramifica entre regras de ingest e de deliver: duas razões para mudar (SRP), e M-03/M-09 dependem de um módulo do qual usam metades disjuntas. Testar a cadeia de entrega exige montar o contexto de ingresso. |
| ARC-02 | delivery-worker | Architectural | 🟡 | M-09 acumula laço + política de backoff + política de dead-letter. Não há costura para testar a política de retry sem rodar o laço. |
| ARC-03 | cli | Architectural | 🟡 | M-02 depende de `store` diretamente — fura o hexágono, porque `explain` precisa do histórico de `attempts`, que nenhum repositório de domínio expõe. |
| ARC-04 | http-api | Architectural | 🟢 | As rotas de preferências são CRUD puro e não passam por script de domínio: validação de invariante tende a ficar no adaptador. |
| ARC-05 | store | Architectural | 🟡 | M-12 implementa TODOS os repositórios (6 clientes) sem fronteira interna — candidato natural ao "arquivo de 800 linhas" na Fase 5. |
| IMP-01 | store | Implementability | 🟡 | 9 tabelas + schema + migração + transação + 6 repositórios num módulo: é o único que provavelmente NÃO cabe em uma interação (viola E = I₀/C). |
| IMP-02 | http-api | Implementability | 🟡 | 5 rotas + API key + token assinado de unsubscribe + tradução erro→status. A estimativa de "~40 LOC" para auth foi feita na Fase 1 e não verificada. |
| IMP-03 | quiet-hours | Implementability | 🟢 | `opensAt` exige aritmética de calendário no fuso da pessoa e é sensível a DST; a assinatura não declara se `opensAt` é epoch ou hora local. |
| IMP-04 | channel-email | Implementability | 🟢 | O link de unsubscribe exige URL base configurável que não aparece em nenhum contrato nem no modelo de dados. |
| SCI-01 | rate-limiter | Scientific | 🟡 | PAR-12 (10/h) marcado POLÍTICA, sem fonte — honesto, mas alimenta um algoritmo cuja fonte (R-07) parametriza capacidade e refil, e não se declara se a janela é contínua ou hora fechada. |
| SCI-02 | quiet-hours | Scientific | 🟡 | PAR-14 (22:00–08:00) é POLÍTICA; R-09 só afirma "modele no fuso da pessoa" e não fixa janela. |
| SCI-03 | channel-webhook | Scientific | 🟢 | PAR-10 (timeout 10 s) é POLÍTICA e interage com PAR-01 sem análise: 5 tentativas × 10 s = 50 s de bloqueio do worker único. |
| SCI-04 | delivery-worker | Scientific | 🟢 | PAR-04 (5 tentativas) é desvio documentado de R-01 (~9 em 75 h), mas muda o resultado observável: destino fora do ar por 12 h que R-01 recuperaria vira dead-letter aqui. |
| SEC-01 | http-api | Security | 🔴 | PRE-8: qualquer emissor autenticado notifica QUALQUER pessoa em QUALQUER categoria, inclusive com `transactional: true`. Uma chave vazada é canal de spam com bypass de todas as supressões. |
| SEC-02 | http-api | Security | 🟡 | Token de unsubscribe declarado "de uso único", mas nem o modelo nem o contrato dizem onde o consumo é registrado — sem armazenamento, "uso único" é só assinatura, portanto reutilizável. |
| SEC-03 | channel-webhook | Security | 🟡 | SSRF: a URL é fornecida pelo destinatário e o worker faz POST nela. Nada restringe destino a IPs públicos (169.254.169.254, localhost, rede interna). |
| SEC-04 | store | Security | 🟡 | `webhook_secret` armazenado em claro; `api_keys` guarda hash, o segredo HMAC não. |
| SEC-05 | cli | Security | 🟢 | `explain` expõe o payload da notificação e não há noção de autorização — quem tem o arquivo SQLite lê tudo. |
| SEC-06 | ingestion | Security | 🟢 | `payload_json` sem limite de tamanho declarado: emissor autenticado pode inflar o banco. |
| PERF-01 | delivery-worker | Performance | 🔴 | Head-of-line blocking: worker único + timeout de 10 s por tentativa ⇒ drenagem O(N × 10 s). Notificação urgente de uma pessoa espera atrás de destinos lentos de outras. Nada na arquitetura mitiga. |
| PERF-02 | outbox | Performance | 🟡 | Entregas `delivered`/`dead_letter` permanecem na tabela para sempre (sem retenção), degradando `idx_due` indefinidamente. |
| PERF-03 | suppression | Performance | 🟢 | A regra `duplicate` consulta `notifications` por (recipient_id, dedup_key, created_at) a cada ingestão, sobre histórico que só cresce. |
| PERF-04 | rate-limiter | Performance | 🟢 | `tryConsume` é O(1), mas roda dentro do laço serial e é uma escrita no SQLite por entrega — amplia o custo por entrega. |
| REG-01 | channel-email | Regulatory | 🟡 | R-02 (RFC 8058) exige assinatura DKIM cobrindo `List-Unsubscribe` e `List-Unsubscribe-Post`. Nenhum módulo é dono de DKIM e o provider local não assina: requisito normativo sem rastreabilidade para módulo. |
| REG-02 | preferences | Regulatory | 🟡 | PAR-16 exige efetivar opt-out em 48 h, mas o opt-out só é avaliado no estágio ingest: entregas já materializadas e adiadas pela madrugada são enviadas depois do descadastro. |
| REG-03 | store | Regulatory | 🟢 | Dados pessoais (e-mail, fuso, histórico) sem política de retenção nem mecanismo de apagamento — nenhum módulo é dono de "esquecer uma pessoa". |
| RES-01 | delivery-worker | Resilience | 🔴 | Não há lease nem timeout de reivindicação: se `send` lançar exceção ou o processo morrer entre `claimDue` e `recordResult`, a entrega fica presa em estado reivindicado para sempre. É exatamente o cenário que AC-4 (matar o processo) exercita. |
| RES-02 | channel-email | Resilience | 🟡 | Falha de e-mail é assíncrona (bounce chega depois, por outro canal), mas `{ok, permanent}` só modela o resultado síncrono da submissão: um e-mail marcado `delivered` pode ter bouncado. |
| RES-03 | channel-webhook | Resilience | 🟡 | Sem circuit breaker por destino: um destino que devolve 500 para todos consome tentativas de todas as notificações dele, e o worker único paga o custo. |
| RES-04 | store | Resilience | 🟡 | `SQLITE_BUSY` entre a thread da API e o laço do worker no mesmo processo não é tratado em nenhum contrato. |
| UX-01 | cli | UI/UX | 🟡 | `explain <id>` responde por notificação, mas a pergunta real do operador é "por que ESTA PESSOA não recebeu nada hoje?" — não há consulta por destinatário nem por período. |
| UX-02 | cli | UI/UX | 🟢 | Não está declarado se `retry` ignora supressões; se não ignorar, o operador re-suprime e não entende por quê. |
| UX-03 | http-api | UI/UX | 🟡 | O POST devolve sucesso tanto para "aceitei e vou entregar" quanto para "aceitei e descartei por opt_out" — a distinção depende de o emissor ler um campo com atenção. |
| UX-04 | preferences | UI/UX | 🟢 | O one-click unsubscribe (POST sem página) não dá retorno visual: a pessoa não sabe se funcionou. |
| SUS-01 | store | Sustainability / Proportionality | 🟡 | Retenção infinita em `notifications`, `deliveries`, `attempts` e `idempotency_keys`. Nenhum módulo é dono da poda; em 10× de escala o gargalo é o banco, não a CPU. |
| SUS-02 | delivery-worker | Sustainability / Proportionality | 🟢 | Destino permanentemente morto consome 5 tentativas com backoff até 24 h POR NOTIFICAÇÃO — custo cresce com o volume, não com o número de destinos mortos. |
| ETH-01 | suppression | Ethical / Human Impact | 🔴 | Uma notificação não-transacional que importa (ex.: aviso de vencimento) pode ser suprimida por `rate_limited` e desaparecer: sem recurso, sem aviso à pessoa, sem mecanismo de correção. Decisão automática de não informar alguém, sem reparação. |
| ETH-02 | suppression | Ethical / Human Impact | 🟡 | duplica: GAM-01 — quem sofre a consequência de classificar mal `transactional` é a pessoa, não o emissor que classificou. |
| PRO-01 | ingestion | Process / Workflow | 🔴 | O estado `deferred` da notificação não tem transição de saída com dono: a entrega volta a ser devida por `next_attempt_at`, mas nenhum módulo é declarado responsável por agregar o estado da notificação a partir das entregas. A coluna existe, o dono não. |
| PRO-02 | delivery-worker | Process / Workflow | 🟡 | `suppressed` e `dead_letter` são terminais, mas `retry <id>` promete reprocessar: não há transição declarada de terminal de volta para `pending`. |
| PRO-03 | suppression | Process / Workflow | 🟡 | `defer` é produzido por quiet_hours no estágio deliver, mas o contrato admite `defer` também no ingest e a arquitetura não diz o que M-03 faz com ele. |
| PRO-04 | preferences | Process / Workflow | 🟢 | O glossário diz que opt-out vale "até reativação explícita", mas a interface tem `optOut` e não tem o caminho de volta. |
| GOV-01 | ingestion | Governance / Accountability | 🟡 | Nenhuma coluna registra QUAL emissor criou a notificação. Com PRE-8, um post-mortem não consegue responder "quem mandou isto". |
| GOV-02 | suppression | Governance / Accountability | 🟡 | Registra-se o motivo da supressão, não a regra/valor vigente (teto era 10? janela era 22–08?). Mudou a política, o histórico fica ininterpretável. |
| GOV-03 | preferences | Governance / Accountability | 🟢 | A mesma tabela é escrita por três caminhos (pessoa via unsubscribe, operador, emissor via API) e nada registra a autoria da alteração. |
| OBS-01 | delivery-worker | Observability / Operability | 🟡 | Nenhum contrato expõe métricas do laço (profundidade da fila, idade da entrega mais velha, taxa de dead-letter); `tick()` devolve contadores por chamada que ninguém agrega. |
| OBS-02 | http-api | Observability / Operability | 🟢 | Sem endpoint de saúde/prontidão: saber se o worker está vivo exige inspecionar o banco. |
| OBS-03 | store | Observability / Operability | 🟢 | Sem id de correlação entre a requisição de ingestão e as tentativas de entrega — o log de um erro não aponta para o POST que o originou. |
| CTL-01 | delivery-worker | Control Engineering | 🟡 | O laço não gera sinal de erro nem realimenta: se a taxa de chegada exceder a de entrega (worker único), a fila cresce monotonamente sem que nada perceba ou reaja — sem throttle de ingestão, sem alarme. |
| CTL-02 | rate-limiter | Control Engineering | 🟢 | A recarga usa `now - last_refill_at`; se o relógio retroceder (PRE-4 assume que não), `elapsed` negativo REDUZ tokens — a fórmula não satura em zero. |
| CTL-03 | quiet-hours | Control Engineering | 🟢 | Todas as entregas adiadas de um mesmo fuso acordam no mesmo minuto (08:00): pico sincronizado, efeito manada. O retry tem jitter; a reprogramação por janela não tem. |
| GAM-01 | ingestion | Game Theory | 🔴 | `transactional` é auto-declarado pelo emissor e ignora opt-out, janela e teto. O incentivo de todo emissor é marcar tudo como transacional, e nada no design cria custo para isso: funciona apenas sob cooperação. |
| GAM-02 | rate-limiter | Game Theory | 🟡 | Teto global por pessoa compartilhado entre TODOS os emissores: um emissor barulhento consome a cota e cala os outros. Quem é prejudicado não é quem causou. |
| GAM-03 | ingestion | Game Theory | 🟢 | A chave de dedup é escolhida pelo emissor (PRE-3): quem quiser burlar a dedup basta variá-la. A regra depende de cooperação. |
| LIN-01 | channel-email | Linguistics / Grammar | 🟡 | duplica: RES-02 — `{ok, permanent}` não define se `ok` é "submetido" ou "entregue"; duas implementações corretas do ChannelPort produzem semânticas incompatíveis de `delivered`. |
| LIN-02 | suppression | Linguistics / Grammar | 🟡 | `defer` devolve `until` sem definir se significa "não avaliar antes de" ou "entregar exatamente em" — implementações divergem na abertura da janela. |
| LIN-03 | outbox | Linguistics / Grammar | 🟡 | `recordResult(id, outcome, nextAt?)` não define quem calcula `nextAt` (worker ou outbox). Se ambos assumirem que é o outro, entregas ficam sem reprogramação. |
| LIN-04 | http-api | Linguistics / Grammar | 🟢 | `status` reusa os nomes do estado de domínio; `accepted` no HTTP (202) e `accepted` no domínio (persistida) não coincidem necessariamente. |
| LIN-05 | channel-webhook | Linguistics / Grammar | 🟢 | PAR-08 exige `webhook-timestamp` em SEGUNDOS; o modelo de dados guarda tempo em epoch MILISSEGUNDOS, e `send(msg)` não declara a unidade. É o erro de fator 1000 que a tolerância de 300 s (PAR-06) transforma em rejeição de 100% das entregas. |
| MEC-01 | store | Mechanical Engineering | 🟡 | RSK-01: a arquitetura confia que trocar `node:sqlite` por `better-sqlite3` é "troca de adaptador", mas as APIs diferem e não existe teste de contrato de repositório que garanta a equivalência. |
| MEC-02 | channel-email | Mechanical Engineering | 🟢 | Nenhuma tolerância declarada a variação de servidor SMTP (auth, STARTTLS, limite de tamanho): funciona com o provider local, não necessariamente com um real. |
| MEC-03 | delivery-worker | Mechanical Engineering | 🟢 | O intervalo do laço `tick` não está especificado em nenhum PAR-xx: a precisão temporal de todo o sistema depende de um valor que não existe na spec. |

**Totais da Iteração 1:** 68 achados — 🔴 8 · 🟡 35 · 🟢 25.
**Duplicatas marcadas:** ETH-02 → GAM-01; LIN-01 → RES-02.

## Iteração 2 — V(2)

Crítica do desenho revisado. Módulos `suppression` (removido) e os nomes de V(1)
permanecem registrados acima — esta seção usa os nomes de V(2).

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| RES-05 | outbox | Resilience | 🔴 | O lease dura PAR-20 = 60 s, mas nada garante que o envio termine dentro dele: um SMTP lento com PAR-10 = 10 s de timeout, mais fila interna de 8 em voo, pode ultrapassar 60 s. O lease expira, outro ciclo reivindica a MESMA entrega e o primeiro envio ainda está em voo → **entrega duplicada**. O lease curou a perda e criou a duplicação. |
| RES-06 | outbox | Resilience | 🔴 | **Poison message:** se o processamento lançar exceção ANTES de `recordResult`, o lease expira e a entrega volta a ser devida com `attempts` **inalterado** — ela nunca chega a PAR-04 e reprocessa para sempre. O caminho de dead-letter só é alcançado por falha reportada, não por falha não capturada. |
| ARC-06 | delivery-policy | Architectural | 🟡 | O módulo é descrito como "funções puras sobre estado", mas depende de `preferences` para reavaliar opt-out. Ou faz I/O (e não é puro), ou recebe o contexto montado — e aí não está declarado quem o monta. A contradição está no próprio contrato. |
| ARC-07 | preferences | Architectural | 🟡 | M-05 passou a ter duas razões para mudar: preferências da PESSOA (dado do usuário) e catálogo de categorias (política do OPERADOR). É exatamente a violação de SRP que ARC-01 apontou em `suppression` — a correção reproduziu o padrão em outro módulo. |
| ARC-08 | store | Architectural | 🟡 | Retenção é declarada em dois lugares: PAR-18 global (90 dias) e `categories.retention_days` por categoria. Nenhuma regra de precedência foi definida. |
| SEC-07 | http-api | Security | 🟡 | O escopo da API key é por categoria, mas não distingue "pode emitir nesta categoria" de "pode emitir como transacional". Um emissor autorizado numa categoria transacional herda o bypass de supressão. |
| SEC-08 | ingestion | Security | 🟡 | A chave de idempotência é global, não escopada por emissor: dois emissores usando a mesma `Idempotency-Key` colidem, e um recebe a resposta referente à notificação do outro. |
| SEC-09 | store | Security | 🟡 | A cifra AES-GCM não tem versionamento nem rotação de chave: trocar a chave de ambiente torna todos os `webhook_secret` ilegíveis, sem caminho de migração. |
| SEC-10 | channel-webhook | Security | 🟡 | A guarda anti-SSRF valida a URL no cadastro e antes do envio, mas o DNS pode reresolver entre a validação e a conexão — DNS rebinding contorna a guarda. |
| SEC-11 | channel-webhook | Security | 🟡 | Não está declarado se o adaptador segue redirecionamentos. Se seguir, um destino público responde 302 para `169.254.169.254` e o anti-SSRF de SEC-10 é contornado por desenho. |
| SEC-12 | http-api | Security | 🟢 | `GET /health` expõe profundidade de fila e idade da entrega mais velha sem autenticação declarada. |
| ETH-03 | preferences | Ethical / Human Impact | 🟡 | O catálogo tirou do emissor o poder de anular o consentimento da pessoa — e o entregou ao OPERADOR, sem trava. Marcar `marketing` como transacional faz o opt-out de todas as pessoas deixar de valer, silenciosamente. O poder foi movido, não removido. |
| REG-04 | preferences | Regulatory | 🟡 | duplica: ETH-03 — uma categoria marcada transacional que ignora opt-out conflita com a obrigação de honrar o descadastro (R-02, PAR-16). |
| GAM-04 | rate-limiter | Game Theory | 🟢 | duplica: ETH-03 — o incentivo de classificar como transacional para escapar do teto migrou do emissor para o operador. |
| PRO-05 | delivery-policy | Process / Workflow | 🟡 | `defer(until)` e `nextAttempt()` escrevem o mesmo campo `next_attempt_at`. Para uma entrega que já falhou E entrou em janela de silêncio, qual valor prevalece não está declarado. |
| PRO-07 | channel-email | Process / Workflow | 🟡 | Os estados terminais passaram a diferir por canal (`sent` para e-mail submetido, `delivered` para webhook com 2xx), mas `specs/validation/acceptance-criteria.md` ainda descreve o comportamento de V(1): UC-1 fala em "2 entregas" sem distinguir. O artefato de aceitação ficou desatualizado em relação ao desenho. |
| LIN-06 | delivery-policy | Linguistics / Grammar | 🟡 | Não está definido se, após um envio falho, o worker chama `nextAttempt()` ou se `decide()` já devolve o próximo instante. Duas implementações corretas do contrato reprogramam de formas diferentes. |
| PERF-05 | delivery-worker | Performance | 🟡 | A relação entre o tamanho do lote de `claim(now, n, lease)` e PAR-19 = 8 em voo não está declarada. Se `n` > 8, as entregas excedentes esperam sua vez **com o lease correndo** — e podem perdê-lo antes de sequer serem tentadas (agrava RES-05). |
| ASS-07 | outbox | Assumptions | 🟡 | O lease torna o multiprocesso seguro e, com isso, passa a assumir relógios sincronizados entre processos — premissa nova que PRE-4 (relógio não retrocede) não cobre. |
| ASS-08 | quiet-hours | Assumptions | 🟢 | O comportamento em DST foi declarado para a hora inexistente (abre no próximo instante válido), mas não para a hora REPETIDA no fim do horário de verão: a janela abre duas vezes? |
| IMP-05 | http-api | Implementability | 🟡 | IMP-02 já duvidava dos "~40 LOC" de auth; V(2) acrescentou escopo por categoria, `/health`, métricas e token com validade. M-01 é agora o maior módulo da borda e continua sem decomposição interna declarada. |
| SCI-05 | delivery-policy | Scientific | 🟢 | PAR-25 (dispersão de 0–5 min na reabertura) é POLÍTICA e interage com a janela: numa janela curta, o jitter pode empurrar a entrega para fora dela. |
| GOV-04 | preferences | Governance / Accountability | 🟡 | `preferences.changed_by` registra o ator da alteração de preferência, mas o catálogo de categorias — que agora decide o que ignora consentimento — não registra quem o alterou. A lacuna corrigida em GOV-03 reabriu ao lado. |
| OBS-04 | outbox | Observability / Operability | 🟢 | O alarme de PAR-23 (idade da fila) não tem dono declarado: `outbox.stats()` produz o número, e não está dito se quem compara com o limiar é o worker, a API ou a CLI. |
| CTL-05 | delivery-policy | Control Engineering | 🟡 | V(2) ganhou sensor (stats + alarme) mas não ganhou atuador: detectada a fila crescente, nada no desenho reage — sem throttle de ingestão, sem priorização, sem degradação controlada. A malha continua aberta, agora instrumentada. |
| UX-06 | cli | UI/UX | 🟡 | `purge` é comando destrutivo e foi acrescentado sem `--dry-run` nem confirmação declarada: o operador apaga histórico por engano e não há desfazer. |
| SUS-03 | store | Sustainability / Proportionality | 🟢 | `attempts_json` embutido na entrega retém o detalhe de erro de cada tentativa por PAR-18 = 90 dias: o volume por entrega cresce com o número de tentativas, não só com o número de entregas. |
| MEC-04 | store | Mechanical Engineering | 🟢 | PAR-22 (WAL) pressupõe sistema de arquivos com locking adequado. O ambiente medido é WSL2 — em caminho montado do host ou em rede, WAL degrada ou falha. Tolerância não declarada. |

**Totais da Iteração 2:** 28 achados — 🔴 2 · 🟡 19 · 🟢 7.
**Duplicatas marcadas:** REG-04 → ETH-03; GAM-04 → ETH-03.
