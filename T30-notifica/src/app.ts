/**
 * Raiz de composição — liga os 12 módulos.
 *
 * Não é um módulo: é o fio que injeta as dependências na direção que o arranjo
 * hexagonal exige (adaptadores para dentro, núcleo sem conhecer HTTP/SQL/SMTP).
 */
import type { Channel, ChannelPort } from './types.ts';
import { openStore, type Store } from './store/index.ts';
import { createPreferences, type Preferences } from './preferences/index.ts';
import { createRateLimiter } from './rate-limiter/index.ts';
import { createDeliveryPolicy, type DeliveryPolicy } from './delivery-policy/index.ts';
import { createOutbox, type Outbox } from './outbox/index.ts';
import { createIngestion, type Ingestion } from './ingestion/index.ts';
import { createEmailChannel } from './channel-email/index.ts';
import { createWebhookChannel } from './channel-webhook/index.ts';
import { createDeliveryWorker, type DeliveryWorker } from './delivery-worker/index.ts';

export interface AppConfig {
  dbPath: string;
  smtpHost?: string;
  smtpPort?: number;
  mailFrom?: string;
  baseUrl?: string;
  tokenSecret?: string;
  secretKey?: string;
  /** Só para o provider local: permite webhook em 127.0.0.1 sem furar o anti-SSRF. */
  allowPrivateWebhooks?: boolean;
  log?: (line: string) => void;
}

export interface App {
  store: Store;
  preferences: Preferences;
  outbox: Outbox;
  ingestion: Ingestion;
  policy: DeliveryPolicy;
  worker: DeliveryWorker;
  channels: Record<Channel, ChannelPort>;
  tokenSecret: string;
  close(): void;
}

export function createApp(cfg: AppConfig): App {
  const tokenSecret = cfg.tokenSecret ?? process.env.T30_TOKEN_SECRET ?? 'segredo-de-token-t30';

  const store = openStore(cfg.dbPath, { secretKey: cfg.secretKey });
  const preferences = createPreferences(store);
  const rateLimiter = createRateLimiter(store);
  const policy = createDeliveryPolicy(rateLimiter);
  const outbox = createOutbox(store);
  const ingestion = createIngestion(store, preferences, outbox);

  const channels: Record<Channel, ChannelPort> = {
    email: createEmailChannel({
      host: cfg.smtpHost ?? '127.0.0.1',
      port: cfg.smtpPort ?? 2525,
      from: cfg.mailFrom ?? 't30@localhost',
      baseUrl: cfg.baseUrl ?? 'http://localhost:3000',
      tokenSecret,
    }),
    webhook: createWebhookChannel({ allowPrivateAddresses: cfg.allowPrivateWebhooks ?? false }),
  };

  const worker = createDeliveryWorker({ store, outbox, policy, preferences, channels, log: cfg.log });

  return {
    store,
    preferences,
    outbox,
    ingestion,
    policy,
    worker,
    channels,
    tokenSecret,
    close() {
      worker.stop();
      store.close();
    },
  };
}
