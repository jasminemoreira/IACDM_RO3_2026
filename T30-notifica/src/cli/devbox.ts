/**
 * Provedores LOCAIS — a decisão de tecnologia da Fase 0 foi "porta + adaptadores
 * com provider local": adaptadores reais em código, apontando para um servidor
 * SMTP de teste e um receptor de webhook local. Trocar por SendGrid/Twilio é
 * mudança de CONFIGURAÇÃO, não de arquitetura.
 *
 * Não é simulação: os caminhos de falha de rede (timeout, 5xx, conexão recusada)
 * são exercitados de verdade — que é onde mora o risco de um serviço de
 * notificação.
 */
import { createServer } from 'node:http';
import { SMTPServer } from 'smtp-server';

export interface Devbox {
  smtpPort: number;
  hookPort: number;
  mailbox: Array<{ to: string; raw: string; at: number }>;
  received: Array<{ headers: Record<string, string | string[] | undefined>; body: string; at: number }>;
  stop(): Promise<void>;
}

export interface DevboxOptions {
  smtpPort?: number;
  hookPort?: number;
  /** Faz o receptor responder este status — para exercitar retry e dead-letter. */
  hookStatus?: () => number;
  /** Atraso artificial no receptor, para exercitar o timeout de PAR-10. */
  hookDelayMs?: () => number;
}

export async function startDevbox(opts: DevboxOptions = {}): Promise<Devbox> {
  const mailbox: Devbox['mailbox'] = [];
  const received: Devbox['received'] = [];

  const smtp = new SMTPServer({
    authOptional: true,
    disabledCommands: ['STARTTLS', 'AUTH'],
    onData(stream, session, callback) {
      const chunks: Buffer[] = [];
      stream.on('data', (c: Buffer) => chunks.push(c));
      stream.on('end', () => {
        mailbox.push({
          to: session.envelope.rcptTo.map((r) => r.address).join(','),
          raw: Buffer.concat(chunks).toString('utf8'),
          at: Date.now(),
        });
        callback();
      });
    },
  });

  const hook = createServer((req, res) => {
    const chunks: Buffer[] = [];
    req.on('data', (c) => chunks.push(c as Buffer));
    req.on('end', () => {
      received.push({ headers: req.headers, body: Buffer.concat(chunks).toString('utf8'), at: Date.now() });
      const status = opts.hookStatus?.() ?? 200;
      const delay = opts.hookDelayMs?.() ?? 0;
      setTimeout(() => {
        res.writeHead(status, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ ok: status < 300 }));
      }, delay).unref?.();
    });
  });

  const smtpPort = await new Promise<number>((resolve, reject) => {
    smtp.on('error', reject);
    smtp.listen(opts.smtpPort ?? 0, '127.0.0.1', () => {
      resolve((smtp.server.address() as { port: number }).port);
    });
  });

  const hookPort = await new Promise<number>((resolve) => {
    hook.listen(opts.hookPort ?? 0, '127.0.0.1', () => resolve((hook.address() as { port: number }).port));
  });

  return {
    smtpPort,
    hookPort,
    mailbox,
    received,
    async stop() {
      await new Promise<void>((resolve) => smtp.close(() => resolve()));
      await new Promise<void>((resolve) => hook.close(() => resolve()));
    },
  };
}
