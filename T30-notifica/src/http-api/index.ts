/**
 * M-01 http-api — adaptador de entrada HTTP.
 *
 * Decomposição interna declarada (achado IMP-05): rotas aqui, autenticação em
 * auth.ts, tradução de erros em errors.ts.
 *
 * Rotas:
 *   POST /notifications                     (chave + escopo de categoria)
 *   GET  /notifications/:id                 (chave)
 *   GET  /recipients/:id/preferences        (chave)
 *   PUT  /recipients/:id/preferences        (chave)
 *   POST /unsubscribe                       (token assinado — RFC 8058, sem sessão)
 *   GET  /health                            (liveness sem chave; métricas com chave)
 *
 * Cadastro de pessoas e do catálogo é superfície do OPERADOR e vive na CLI, não
 * aqui — a API serve sistemas emissores e a própria pessoa.
 */
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import type { Channel } from '../types.ts';
import type { Store } from '../store/index.ts';
import type { Preferences } from '../preferences/index.ts';
import type { Ingestion } from '../ingestion/index.ts';
import { deriveStatus, type Outbox } from '../outbox/index.ts';
import { verifyUnsubscribeToken } from '../tokens.ts';
import { authenticate, authorizeCategory } from './auth.ts';
import { translate } from './errors.ts';

export interface ApiDeps {
  store: Store;
  preferences: Preferences;
  ingestion: Ingestion;
  outbox: Outbox;
  tokenSecret: string;
  workerRunning: () => boolean;
}

const MAX_BODY_BYTES = 256 * 1024; // guarda de transporte; PAR-26 é validado no domínio

async function readBody(req: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY_BYTES) throw new Error('corpo da requisição excede o limite de transporte');
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks).toString('utf8');
}

function send(res: ServerResponse, status: number, body: unknown): void {
  const json = JSON.stringify(body);
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(json);
}

export function createApi(deps: ApiDeps): Server {
  const { store, preferences, ingestion, outbox } = deps;

  return createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');
      const path = url.pathname;
      const method = req.method ?? 'GET';

      // --- GET /health ------------------------------------------------------
      // SEC-12: sem chave devolve só liveness. Profundidade de fila e idade da
      // entrega mais velha são informação operacional e exigem chave.
      if (method === 'GET' && path === '/health') {
        const auth = authenticate(store, req.headers.authorization);
        if (!auth.ok) {
          return send(res, 200, { status: 'ok', worker: deps.workerRunning() ? 'running' : 'stopped' });
        }
        const stats = outbox.stats(store.now());
        return send(res, 200, { status: 'ok', worker: deps.workerRunning() ? 'running' : 'stopped', queue: stats });
      }

      // --- POST /unsubscribe (RFC 8058 one-click, sem sessão) ---------------
      if (method === 'POST' && path === '/unsubscribe') {
        const token = url.searchParams.get('token') ?? new URLSearchParams(await readBody(req)).get('token');
        if (!token) return send(res, 400, { error: 'token ausente', code: 'missing_token' });

        const claims = verifyUnsubscribeToken(token, deps.tokenSecret, store.now());
        if (!claims) return send(res, 403, { error: 'token inválido ou expirado', code: 'invalid_token' });

        preferences.optOut(claims.recipientId, { category: claims.category }, `unsubscribe:${claims.recipientId}`);
        // UX-04 (aceito): sem página de confirmação — a resposta é a confirmação
        // que o cliente de e-mail consegue mostrar. Página web ficou fora de escopo.
        return send(res, 200, { unsubscribed: true, category: claims.category });
      }

      // --- daqui para baixo, tudo exige chave -------------------------------
      const auth = authenticate(store, req.headers.authorization);
      if (!auth.ok) return send(res, auth.status!, { error: auth.message, code: 'unauthorized' });

      // --- POST /notifications ----------------------------------------------
      if (method === 'POST' && path === '/notifications') {
        const raw = await readBody(req);
        let cmd;
        try {
          cmd = JSON.parse(raw);
        } catch {
          return send(res, 400, { error: 'JSON inválido', code: 'bad_json' });
        }

        const category = preferences.category(cmd.category);
        if (!category) {
          return send(res, 422, { error: `categoria fora do catálogo: ${cmd.category}`, code: 'unknown_category' });
        }
        const allowed = authorizeCategory(auth.key!, category.name, category.transactional);
        if (!allowed.ok) return send(res, 403, { error: allowed.message, code: 'forbidden_category' });

        const result = ingestion.ingest(
          {
            recipientId: cmd.recipientId,
            category: cmd.category,
            dedupKey: cmd.dedupKey ?? null,
            payload: cmd.payload,
          },
          auth.issuer!,
          (req.headers['idempotency-key'] as string | undefined) ?? null,
        );
        // UX-03: 202 = vai entregar; 200 com reason = aceitei e descartei.
        return send(res, result.status === 'accepted' ? 202 : 200, result);
      }

      // --- GET /notifications/:id -------------------------------------------
      const notifMatch = path.match(/^\/notifications\/([^/]+)$/);
      if (method === 'GET' && notifMatch) {
        const notification = store.notifications.get(notifMatch[1]);
        if (!notification) return send(res, 404, { error: 'notificação não encontrada', code: 'not_found' });
        const deliveries = outbox.history(notification.id);
        const now = store.now();
        return send(res, 200, {
          id: notification.id,
          recipientId: notification.recipientId,
          category: notification.category,
          transactional: notification.transactional,
          issuer: notification.issuer,
          status: deriveStatus(notification, deliveries, now), // DERIVADO (PRO-01)
          suppressedReason: notification.suppressedReason,
          deliveries: deliveries.map((d) => ({
            channel: d.channel,
            status: d.status,
            attempts: d.attempts,
            nextAttemptAt: d.nextAttemptAt,
            suppressedReason: d.suppressedReason,
            suppressedDetail: d.suppressedDetail,
          })),
        });
      }

      // --- GET|PUT /recipients/:id/preferences ------------------------------
      const prefMatch = path.match(/^\/recipients\/([^/]+)\/preferences$/);
      if (prefMatch) {
        const recipientId = prefMatch[1];
        const recipient = preferences.recipient(recipientId);
        if (!recipient) return send(res, 404, { error: 'destinatário não encontrado', code: 'not_found' });

        if (method === 'GET') {
          return send(res, 200, {
            recipientId,
            timezone: recipient.timezone,
            quietHours: { start: recipient.quietStart, end: recipient.quietEnd },
            preferences: preferences.list(recipientId),
            categories: preferences.listCategories().map((c) => ({
              name: c.name,
              defaultEnabled: c.defaultEnabled,
              // ETH-03: transparência — a pessoa consegue ver quais categorias
              // ignoram o consentimento dela.
              ignoresOptOut: c.transactional,
            })),
          });
        }

        if (method === 'PUT') {
          const body = JSON.parse(await readBody(req)) as {
            entries: Array<{ category: string; channel: Channel | '*'; enabled: boolean }>;
          };
          for (const e of body.entries ?? []) {
            const actor = `api:${auth.issuer}`;
            if (e.enabled) preferences.optIn(recipientId, { category: e.category, channel: e.channel as Channel }, actor);
            else preferences.optOut(recipientId, { category: e.category, channel: e.channel as Channel }, actor);
          }
          return send(res, 200, { recipientId, preferences: preferences.list(recipientId) });
        }
      }

      return send(res, 404, { error: 'rota não encontrada', code: 'not_found' });
    } catch (err) {
      const { status, body } = translate(err);
      return send(res, status, body);
    }
  });
}
