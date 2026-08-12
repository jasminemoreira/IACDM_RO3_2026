/**
 * Contratos compartilhados entre módulos — T30.
 *
 * Vocabulário canônico: specs/domain/glossary.md.
 * Um termo, um significado; os sinônimos proibidos estão lá.
 */

/** Meio de entrega com contrato próprio. Provedor é a implementação por trás dele. */
export type Channel = 'email' | 'webhook';

/** Enum FECHADO. Toda supressão é nomeada — silêncio sem motivo é defeito. */
export type SuppressionReason = 'opt_out' | 'quiet_hours' | 'rate_limited' | 'duplicate';

/** Estado de UMA tentativa concreta por UM canal. */
export type DeliveryStatus =
  | 'pending'
  | 'sent' // e-mail: submetido ao provedor (bounce é assíncrono, não observável aqui)
  | 'delivered' // webhook: 2xx confirmado (PAR-09)
  | 'dead_letter'
  | 'suppressed';

/** Estado da Notificação — DERIVADO das entregas, nunca armazenado (achado PRO-01). */
export type NotificationStatus =
  | 'accepted'
  | 'suppressed'
  | 'deferred'
  | 'delivered'
  | 'partially_delivered'
  | 'failed';

export interface Recipient {
  id: string;
  /** Fuso IANA. Campo OBRIGATÓRIO, validado no cadastro (PRE-2 / EDGE-2). */
  timezone: string;
  email: string | null;
  webhookUrl: string | null;
  /** Já decifrado. Em repouso fica como ciphertext versionado (SEC-04/SEC-09). */
  webhookSecret: string | null;
  /** Minutos desde 00:00 local. start > end significa janela cruzando a meia-noite. */
  quietStart: number;
  quietEnd: number;
  tokens: number;
  lastRefillAt: number;
}

/** Catálogo do OPERADOR — não do emissor (achado GAM-01). */
export interface Category {
  name: string;
  /** Invariante 3: ausência de preferência ≠ opt-out; resolve por aqui. */
  defaultEnabled: boolean;
  /** Quem decide o que é transacional é o catálogo, não quem emite. */
  transactional: boolean;
  /** Sobrepõe PAR-18 quando presente (precedência declarada, achado ARC-08). */
  retentionDays: number | null;
  changedBy: string;
  changedAt: number;
}

export interface Notification {
  id: string;
  recipientId: string;
  category: string;
  transactional: boolean;
  dedupKey: string | null;
  payload: NotificationPayload;
  issuer: string;
  suppressedReason: SuppressionReason | null;
  createdAt: number;
}

export interface NotificationPayload {
  subject: string;
  body: string;
  data?: Record<string, unknown>;
}

export interface Delivery {
  id: string;
  notificationId: string;
  channel: Channel;
  status: DeliveryStatus;
  attempts: number;
  nextAttemptAt: number;
  leaseUntil: number | null;
  /** Fencing token do lease vigente — recordResult o exige (achado RES-05). */
  leaseToken: string | null;
  suppressedReason: SuppressionReason | null;
  /** Valor do parâmetro vigente na decisão, ex. "cap=10/1h" (achado GOV-02). */
  suppressedDetail: string | null;
  attemptLog: AttemptRecord[];
}

export interface AttemptRecord {
  n: number;
  at: number;
  outcome: 'ok' | 'transient' | 'permanent';
  detail: string;
}

/**
 * Porta de saída de canal. `permanent` separa "não adianta tentar de novo"
 * (URL inválida, 4xx, endereço inexistente) de "tente depois" (timeout, 5xx).
 * Sem essa distinção, EDGE-3 vira 5 tentativas inúteis contra um host que nunca
 * existiu.
 */
export interface ChannelPort {
  readonly channel: Channel;
  /**
   * Estado terminal de sucesso DESTE canal (achados RES-02 / LIN-01):
   * `sent` para e-mail — só sabemos que o provedor aceitou a submissão, e o
   * bounce chega depois por outro caminho; `delivered` para webhook, onde o 2xx
   * é confirmação do destino. Chamar os dois de "entregue" seria mentir num
   * deles.
   */
  readonly terminalStatus: Extract<DeliveryStatus, 'sent' | 'delivered'>;
  send(msg: OutboundMessage, signal: AbortSignal): Promise<SendResult>;
}

export interface SendResult {
  accepted: boolean;
  permanent: boolean;
  detail: string;
}

export interface OutboundMessage {
  deliveryId: string;
  notificationId: string;
  recipient: Recipient;
  category: string;
  /** Vem do CATÁLOGO (achado GAM-01). O canal usa isto para escolher o template
   *  e para decidir se faz sentido oferecer descadastro. */
  transactional: boolean;
  payload: NotificationPayload;
  /** Epoch MILISSEGUNDOS em todo o sistema. O canal webhook converte para
   *  segundos ao montar `webhook-timestamp` (PAR-08 / achado LIN-05). */
  now: number;
}

/** Contexto JÁ MATERIALIZADO. delivery-policy não faz I/O (achado ARC-06). */
export interface DecisionContext {
  delivery: Delivery;
  notification: Notification;
  recipient: Recipient;
  category: Category;
  /** Resultado de preferences.resolve para (categoria, canal) — pré-carregado. */
  channelEnabled: boolean;
  now: number;
}

export type Verdict =
  | { decision: 'send' }
  | { decision: 'suppress'; reason: SuppressionReason; detail: string }
  /** `until` = "não avaliar antes de" (achado LIN-02). */
  | { decision: 'defer'; until: number; reason: 'quiet_hours' };
