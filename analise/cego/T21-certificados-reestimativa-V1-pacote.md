# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Monitor de validade de certificados com renovação antecipada e registro de quem aprovou cada emissão

## A arquitetura

## V(1) — Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | certificado | Modelo da observação de um certificado X.509 e cálculos derivados de validade. Domínio puro. | `deDer(der) -> Observacao{fingerprint256,issuer,serial,notBefore,notAfter,san[]}` · `vidaTotalDias(o) -> number` · `restanteDias(o, agora) -> number` · `semExpiracao(o) -> boolean` | — |
| M-02 | politica-limiar | Limiares configuráveis e classificação do estado de um alvo. Guarda o invariante `limiar < vidaTotal`. Domínio puro. | `validarLimiares(l, vidaTotalDias) -> Ok \| ErroConfig` · `classificar(o, l, agora) -> 'ok'\|'aviso'\|'atencao'\|'critico'\|'expirado'\|'sem-expiracao'` | certificado |
| M-03 | pedido | Entidade Pedido e sua máquina de estados `pendente -> aprovado -> fechado`. Transição inválida é impossível por construção. | `abrir(alvoId, solicitanteId, agora) -> Pedido` · `aprovar(p, aprovador, agora) -> Ok(Pedido) \| ErroTransicao` · `fechar(p, evidencia, agora) -> Ok(Pedido) \| ErroTransicao` | autorizacao |
| M-04 | reconciliacao | Compara a observação nova com a anterior e com os pedidos abertos, e decide o que aconteceu: emissão aprovada, troca não autorizada, ou escalação por inação. Domínio puro. | `reconciliar(anterior, atual, pedidoAberto, estado) -> Decisao[]` onde `Decisao = {tipo:'fechar-pedido',pedidoId,evidencia} \| {tipo:'troca-nao-autorizada',alvoId,evidencia} \| {tipo:'escalar',alvoId} \| {tipo:'nenhuma'}` | certificado, politica-limiar, pedido |
| M-05 | trilha | Trilha append-only encadeada por hash e sua verificação. Domínio puro. | `anexar(hashAnterior, evento) -> Entrada{i,evento,hashAnterior,hash}` · `verificar(entradas[]) -> {valida, quebraNoIndice?}` | — |
| M-06 | autorizacao | Atores, papéis (`solicitante`/`aprovador`/`auditor`) e verificação de credencial. | `criarAtor(nome, senha, papel) -> Ator` (scrypt) · `autenticar(ator, senha) -> boolean` (timingSafeEqual) · `podeAprovar(ator) -> boolean` | — |
| M-07 | relogio | Porta de tempo. Fonte única do "agora" em UTC — nenhum outro módulo chama `new Date()`. | `agora() -> Date` | — |
| M-08 | sonda-tls | Adaptador de saída: handshake TLS contra `host:porta` e devolução do certificado servido em DER. Inspeciona certificado inválido (`rejectUnauthorized: false`). | `sondar(host, porta, timeoutMs) -> Promise<Ok(der) \| ErroSonda{tipo:'timeout'\|'recusado'\|'dns'\|'tls'}>` | — |
| M-09 | repositorio | Porta de persistência (Repository) + Data Mapper sobre `node:sqlite`. Única fronteira com o banco. | `salvarAlvo(a)` · `listarAlvos()` · `ultimaObservacao(alvoId)` · `salvarObservacao(alvoId, o)` · `pedidoAbertoDe(alvoId)` · `salvarPedido(p)` · `anexarTrilha(entrada)` · `pontaTrilha()` · `listarTrilha(filtro)` · `buscarAtor(nome)` | certificado, pedido, trilha, autorizacao |
| M-10 | casos-de-uso | Camada de aplicação: orquestra domínio e portas. Único lugar onde a sequência de uma operação vive. | `varrer() -> RelatorioVarredura` · `abrirPedido(alvoId, solicitante)` · `aprovarPedido(pedidoId, aprovador)` · `auditar(filtro) -> Entrada[]` · `verificarIntegridade() -> {valida, quebraNoIndice?}` | todos os anteriores |
| M-11 | web-ui | Adaptador de entrada: servidor `node:http`, 5 telas em HTML renderizado e sessão. Nenhuma regra de domínio. | `GET /login \|/painel \|/alvo/:id \|/trilha` · `POST /login \|/alvos \|/varrer \|/pedidos \|/pedidos/:id/aprovar` | casos-de-uso |

Grafo de dependências é acíclico e aponta sempre para dentro: `web-ui -> casos-de-uso
-> {domínio puro, portas}`. Os módulos M-01, M-02, M-04, M-05 não importam nada de
infraestrutura — é o que permite testar CA-1, CA-3, CA-5 e CA-6 sem rede e sem banco.

## As 4 respostas obrigatórias

**1. Decomposição.** 11 módulos em três anéis: domínio puro (certificado,
politica-limiar, pedido, reconciliacao, trilha, autorizacao), portas e adaptadores
(relogio, sonda-tls, repositorio), aplicação e entrada (casos-de-uso, web-ui). A
fronteira que mais importa: **nenhuma regra de negócio em web-ui, nenhuma I/O no
domínio**.

**2. Interfaces.** Contratos na tabela acima. Convenções: erros de domínio são
**valores de retorno** (`Ok | Erro`), não exceções — a exceção fica para falha
programática. Todo tempo entra por `relogio.agora()`. Nenhum módulo além de
`repositorio` conhece SQL; nenhum além de `sonda-tls` conhece rede.

**3. Premissas.** Ver lista abaixo — é o insumo direto da lente Assumptions na Fase 2.

**4. Escopo negativo.** O sistema deliberadamente NÃO: emite certificados (sem ACME,
sem CA, sem chave privada); importa PEM/DER nem aceita cadastro manual de metadados;
notifica por e-mail ou webhook; agenda varreduras (sem daemon, sem cron interno);
agrupa alvos que compartilham certificado; impõe segregação de funções; assina
decisões criptograficamente; ancora a trilha fora da máquina; monitora certificados
não expostos em TLS.

## Premissas assumidas (V(1))

| id | Premissa | Se for falsa |
|---|---|---|
| A1 | Todo certificado de interesse está exposto em porta TLS alcançável | certificados fora de TLS ficam invisíveis ao inventário |
| A2 | O relógio da máquina está correto | toda classificação de vencimento erra junto — **sem mitigação no V(1)** |
| A3 | Fingerprint diferente com `notAfter` avançado ⇒ houve emissão | mitigada por `reconciliacao`: sem pedido aprovado vira `troca-nao-autorizada` (CA-6) |
| A4 | Existe um humano para aprovar dentro da janela de alerta | pedidos ficam pendentes até o vencimento; `escalar` torna isso visível |
| A5 | A máquina que roda o sistema é confiável | a trilha é reescrevível por inteiro — é tamper-**evident**, não tamper-proof |
| A6 | Uma varredura por vez, disparada por pessoa | duas execuções simultâneas do processo poderiam intercalar escritas na cadeia de hash |
| A7 | O volume de alvos é pequeno (dezenas) | varredura sequencial fica lenta; sem paginação no painel |
| A8 | `node:sqlite` experimental não muda de API dentro do ciclo | upgrade de Node poderia quebrar `repositorio` — isolado atrás do Repository |

---

---

## Como funcionam as lentes

Um processo de crítica arquitetural aplica lentes: cada uma faz uma pergunta central
a cada módulo, e detecta uma classe de falha que as outras não detectam.

**Sete são universais** — rodam sempre e não estão em questão: Premissas, Arquitetura,
Implementabilidade, Rigor científico, Segurança, Desempenho, Conformidade regulatória.
**Não as inclua na resposta.**

**Doze são condicionais**, e são essas que você vai avaliar.

**A ativação é por SINAL DO PROJETO, e só.** Que outra lente pareça cobrir a mesma
classe de falha **não** é motivo para deixar uma de fora: não achar nada já é um
resultado válido, e decidir de antemão que duas lentes se sobrepõem é conclusão, não
premissa. Nunca marque `false` por redundância com outra lente — o motivo tem que ser
um sinal do projeto ("não há dependência externa", "não há superfície de usuário"),
nunca "já coberta pela lente X".


| lente | pergunta central | ativa quando |
|---|---|---|
| Resilience | What happens when an external dependency fails, responds slowly, or returns unexpected data? | External dependencies (APIs, DBs, queues, third-party services) |
| UI/UX | Can the user complete their task without frustration, confusion, or error? | Any surface a PERSON operates — including a CLI or operational tooling, not only graphical end-user interfaces |
| Migration / Coexistence | What breaks during the transition from old to new? Is there a rollback path? | Replacing or modifying existing production system |
| Sustainability / Proportionality | Is resource consumption proportionate to value delivered? Cost at 10\xD7 scale? | The system decides, allocates, or consumes a resource whose cost grows with use — e.g. (but NOT only) AI/ML, high-volume data processing, elastic infrastructure. Apply the central question, do not just match the examples |
| Ethical / Human Impact | Who is potentially harmed? Are there audit, correction, and transparency mechanisms? | Automated decisions about people (scoring, classification, moderation) |
| Process / Workflow | Are processes, state transitions, actor responsibilities, and exception paths complete? | Multi-actor flows, state machines, or business processes |
| Governance / Accountability | Is every action attributable? Does every data entity have a defined owner? | The system records or decides something someone will later need to audit, attribute, or answer for — data with distinct owners, actions that need authorship, or an obligation to account. This is a SYSTEM property: a single-operator project activates it when the system has it (not only multi-team / compliance contexts) |
| Observability / Operability | Can degradation be detected and incidents diagnosed in production without code changes? | Production systems with operational requirements |
| Control Engineering | Where does the system generate an error signal and correct it? Risk of oscillation or state drift? | State synchronization, runtime configuration affecting behavior, self-correcting or feedback-driven systems |
| Game Theory | Do system actors have aligned incentives? Where does the design assume cooperation and may encounter strategic defection? | Multiple independent actors, public API, external integrations, marketplace or platform design |
| Linguistics / Grammar | Is the interface contract unambiguous? Can two correct implementations of the same contract produce incompatible behaviors? | Inter-component communication, protocol definitions, message formats, interface contracts between independent teams |
| Mechanical Engineering | Where are the tolerances? Does the system tolerate variation or only work at exact specification? | Module maintenance, system evolution, long-lived systems with technical debt accumulation |

---

## O que responder

Para **cada uma das 12**: `ativa` (true/false) e `sinal` — uma frase curta dizendo **o
que na arquitetura** aciona, ou não aciona, a lente. Preencha o `sinal` também nas
`false`. E `modulos_estimados`: quantos módulos a arquitetura tem.

As 12 têm que aparecer, com o nome exato da tabela. Só o JSON, sem preâmbulo:

```json
{
  "projeto": "T21-certificados",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
