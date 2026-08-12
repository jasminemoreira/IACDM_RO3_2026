#!/usr/bin/env node
/**
 * M-02 cli — superfície do OPERADOR.
 *
 * É esta superfície que torna a supressão auditável: sem ela, "foi suprimida" é
 * caixa-preta (UC-8). `explain` responde tanto por notificação quanto por PESSOA
 * e período — que é a pergunta que o operador realmente faz (achado UX-01).
 *
 * `purge` é DRY-RUN por padrão e exige `--yes` para apagar (achado UX-06):
 * comando destrutivo sem desfazer não pode ser o caminho fácil.
 *
 * Depende de outbox e preferences — não fala com `store` diretamente para dados
 * de domínio (achado ARC-03), exceto no cadastro operacional de chaves, que é
 * gestão do próprio adaptador de persistência.
 */
import { parseArgs } from 'node:util';
import { createApp } from '../app.ts';
import { createApi } from '../http-api/index.ts';
import { deriveStatus } from '../outbox/index.ts';
import { hashApiKey } from '../http-api/auth.ts';
import { startDevbox } from './devbox.ts';

const { values, positionals } = parseArgs({
  allowPositionals: true,
  strict: false,
  options: {
    db: { type: 'string', default: process.env.T30_DB ?? 't30.db' },
    port: { type: 'string', default: '3000' },
    'smtp-host': { type: 'string', default: '127.0.0.1' },
    'smtp-port': { type: 'string', default: '2525' },
    'hook-port': { type: 'string', default: '4000' },
    'base-url': { type: 'string' },
    recipient: { type: 'string' },
    since: { type: 'string', default: '1440' },
    id: { type: 'string' },
    tz: { type: 'string' },
    email: { type: 'string' },
    'webhook-url': { type: 'string' },
    'webhook-secret': { type: 'string' },
    'quiet-start': { type: 'string' },
    'quiet-end': { type: 'string' },
    name: { type: 'string' },
    'default-enabled': { type: 'boolean', default: true },
    transactional: { type: 'boolean', default: false },
    key: { type: 'string' },
    issuer: { type: 'string' },
    categories: { type: 'string', default: '*' },
    'allow-transactional': { type: 'boolean', default: false },
    'allow-private-webhooks': { type: 'boolean', default: false },
    yes: { type: 'boolean', default: false },
    help: { type: 'boolean', default: false },
  },
});

const command = positionals[0];
const arg = positionals[1];
const out = (o: unknown) => console.log(typeof o === 'string' ? o : JSON.stringify(o, null, 2));

const USAGE = `t30 — serviço de notificação

  serve                          sobe a API e o worker
  devbox                         sobe os provedores locais (SMTP + receptor de webhook)
  explain <notificationId>       estado, motivo da supressão e histórico de tentativas
  explain --recipient <id> [--since <min>]
  pending                        entregas pendentes
  retry <deliveryId>             reabre uma entrega terminal (dead_letter/suppressed)
  purge [--yes]                  poda por retenção (dry-run por padrão)
  stats                          profundidade da fila, idade da mais velha, dead-letters
  recipient add --id --tz [--email --webhook-url --webhook-secret --quiet-start --quiet-end]
  category set --name [--default-enabled] [--transactional]
  key add --key --issuer [--categories a,b] [--allow-transactional]

Opções globais: --db <arquivo>`;

if (values.help || !command) {
  out(USAGE);
  process.exit(0);
}

const app = createApp({
  dbPath: String(values.db),
  smtpHost: String(values['smtp-host']),
  smtpPort: Number(values['smtp-port']),
  baseUrl: values['base-url'] ? String(values['base-url']) : `http://localhost:${values.port}`,
  allowPrivateWebhooks: Boolean(values['allow-private-webhooks']),
  log: (line) => console.error(`[worker] ${line}`),
});

switch (command) {
  case 'serve': {
    const server = createApi({
      store: app.store,
      preferences: app.preferences,
      ingestion: app.ingestion,
      outbox: app.outbox,
      tokenSecret: app.tokenSecret,
      workerRunning: () => app.worker.running(),
    });
    app.worker.start();
    server.listen(Number(values.port), () => {
      console.error(`t30 ouvindo em http://localhost:${values.port} — worker ativo, db=${values.db}`);
    });
    const shutdown = () => {
      app.worker.stop();
      server.close(() => {
        app.store.close();
        process.exit(0);
      });
    };
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
    break;
  }

  case 'devbox': {
    const box = await startDevbox({ smtpPort: Number(values['smtp-port']), hookPort: Number(values['hook-port']) });
    console.error(`devbox: SMTP em ${box.smtpPort}, receptor de webhook em ${box.hookPort}`);
    setInterval(() => {
      if (box.mailbox.length) console.error(`caixa: ${box.mailbox.length} mensagens`);
      if (box.received.length) console.error(`webhooks recebidos: ${box.received.length}`);
    }, 5000);
    break;
  }

  case 'explain': {
    const now = app.store.now();
    if (values.recipient) {
      const since = now - Number(values.since) * 60_000;
      const rows = app.outbox.byRecipient(String(values.recipient), since);
      out(
        rows.map(({ notificationId, deliveries }) => {
          const n = app.store.notifications.get(notificationId)!;
          return {
            id: n.id,
            category: n.category,
            issuer: n.issuer,
            createdAt: new Date(n.createdAt).toISOString(),
            status: deriveStatus(n, deliveries, now),
            suppressedReason: n.suppressedReason,
            deliveries: deliveries.map((d) => `${d.channel}: ${d.status}${d.suppressedReason ? ` (${d.suppressedReason} ${d.suppressedDetail ?? ''})` : ''}`),
          };
        }),
      );
      break;
    }
    if (!arg) {
      out('uso: t30 explain <notificationId> | t30 explain --recipient <id>');
      process.exitCode = 1;
      break;
    }
    const n = app.store.notifications.get(arg);
    if (!n) {
      out(`notificação ${arg} não encontrada`);
      process.exitCode = 1;
      break;
    }
    const deliveries = app.outbox.history(n.id);
    out({
      id: n.id,
      recipientId: n.recipientId,
      category: n.category,
      transactional: n.transactional,
      issuer: n.issuer,
      status: deriveStatus(n, deliveries, now),
      suppressedReason: n.suppressedReason,
      deliveries: deliveries.map((d) => ({
        id: d.id,
        channel: d.channel,
        status: d.status,
        attempts: d.attempts,
        nextAttemptAt: new Date(d.nextAttemptAt).toISOString(),
        suppressedReason: d.suppressedReason,
        suppressedDetail: d.suppressedDetail,
        attemptLog: d.attemptLog,
      })),
    });
    break;
  }

  case 'pending': {
    const now = app.store.now();
    out(
      app.outbox.pending(now).map((d) => ({
        id: d.id,
        channel: d.channel,
        attempts: d.attempts,
        due: new Date(d.nextAttemptAt).toISOString(),
        overdueMs: Math.max(0, now - d.nextAttemptAt),
      })),
    );
    break;
  }

  case 'retry': {
    if (!arg) {
      out('uso: t30 retry <deliveryId>');
      process.exitCode = 1;
      break;
    }
    // UX-02: `retry` reabre a entrega e ela volta a passar pela política. Se a
    // supressão ainda se aplicar, ela será suprimida de novo — e o motivo
    // aparecerá no explain. Reabrir não é "forçar entrega".
    const ok = app.outbox.reopen(arg, app.store.now());
    out(ok ? `entrega ${arg} reaberta (volta a ser avaliada pela política)` : `entrega ${arg} não está em estado terminal`);
    if (!ok) process.exitCode = 1;
    break;
  }

  case 'purge': {
    const dryRun = !values.yes;
    const result = app.store.purge(app.store.now(), dryRun);
    out({
      modo: dryRun ? 'dry-run (nada foi apagado — use --yes)' : 'executado',
      notificacoes: result.notifications,
      entregas: result.deliveries,
    });
    break;
  }

  case 'stats': {
    out(app.outbox.stats(app.store.now()));
    break;
  }

  case 'recipient': {
    if (arg !== 'add') {
      out('uso: t30 recipient add --id <id> --tz <IANA> [...]');
      process.exitCode = 1;
      break;
    }
    const r = app.preferences.putRecipient({
      id: String(values.id),
      timezone: String(values.tz),
      email: values.email ? String(values.email) : null,
      webhookUrl: values['webhook-url'] ? String(values['webhook-url']) : null,
      webhookSecret: values['webhook-secret'] ? String(values['webhook-secret']) : null,
      quietStart: values['quiet-start'] !== undefined ? Number(values['quiet-start']) : undefined,
      quietEnd: values['quiet-end'] !== undefined ? Number(values['quiet-end']) : undefined,
    });
    out({ ...r, webhookSecret: r.webhookSecret ? '<cifrado em repouso>' : null });
    break;
  }

  case 'category': {
    if (arg !== 'set') {
      out('uso: t30 category set --name <nome> [--default-enabled] [--transactional]');
      process.exitCode = 1;
      break;
    }
    const c = app.preferences.setCategory(
      {
        name: String(values.name),
        defaultEnabled: Boolean(values['default-enabled']),
        transactional: Boolean(values.transactional),
      },
      `cli:${process.env.USER ?? 'operador'}`,
    );
    if (c.transactional) {
      console.error(
        `ATENÇÃO: categoria "${c.name}" é transacional — ignora opt-out, janela de silêncio e teto de frequência de TODAS as pessoas.`,
      );
    }
    out(c);
    break;
  }

  case 'key': {
    if (arg !== 'add') {
      out('uso: t30 key add --key <segredo> --issuer <nome> [--categories a,b] [--allow-transactional]');
      process.exitCode = 1;
      break;
    }
    app.store.apiKeys.put(
      hashApiKey(String(values.key)),
      {
        issuer: String(values.issuer),
        categories: String(values.categories).split(',').map((s) => s.trim()),
        allowTransactional: Boolean(values['allow-transactional']),
      },
      app.store.now(),
    );
    out(`chave registrada para emissor "${values.issuer}" (guardada como hash)`);
    break;
  }

  default:
    out(`comando desconhecido: ${command}\n\n${USAGE}`);
    process.exitCode = 1;
}

if (command !== 'serve' && command !== 'devbox') {
  app.close();
}
