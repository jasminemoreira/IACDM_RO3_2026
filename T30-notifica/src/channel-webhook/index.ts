/**
 * M-11 channel-webhook — adaptador HTTP da ChannelPort.
 *
 * Assinatura portada literalmente de specs/examples §2 (Tier 2, fonte R-01):
 *   headers: webhook-id, webhook-timestamp (SEGUNDOS), webhook-signature
 *   assinado: `${id}.${timestamp}.${payload}`, HMAC-SHA256, base64, prefixo v1,
 *   sucesso = 2xx (PAR-09).
 *
 * LIN-05: o sistema inteiro trabalha em epoch MILISSEGUNDOS; `webhook-timestamp`
 * é em SEGUNDOS. É o erro de fator 1000 que a tolerância de 300 s (PAR-06)
 * transformaria em rejeição de 100% das entregas — por isso a conversão é
 * explícita e tem teste.
 *
 * SEC-10 (DNS rebinding): resolve o nome UMA vez, valida o IP resolvido e
 * conecta NAQUELE IP, preservando o header Host. Validar a URL e depois deixar o
 * agente resolver de novo é a janela clássica de TOCTOU.
 * SEC-11 (redirect): `node:http` não segue redirecionamento por padrão, e 3xx é
 * tratado como falha PERMANENTE — seguir um 302 para 169.254.169.254 furaria o
 * anti-SSRF por desenho.
 */
import { createHmac, randomUUID } from 'node:crypto';
import { lookup as dnsLookup } from 'node:dns/promises';
import { request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
import { isIP } from 'node:net';
import type { ChannelPort, OutboundMessage, SendResult } from '../types.ts';

/** PAR-10 — timeout de requisição. */
export const PAR_10_REQUEST_TIMEOUT_MS = 10_000;

/** Faixas que um destino de webhook nunca deve alcançar (achado SEC-03). */
export function isPrivateAddress(ip: string): boolean {
  if (isIP(ip) === 6) {
    const v6 = ip.toLowerCase();
    if (v6 === '::1' || v6 === '::') return true;
    if (v6.startsWith('fe80') || v6.startsWith('fc') || v6.startsWith('fd')) return true;
    // IPv4 mapeado em IPv6.
    const mapped = v6.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/);
    if (mapped) return isPrivateAddress(mapped[1]);
    return false;
  }
  const [a, b] = ip.split('.').map(Number);
  if (a === 10 || a === 127 || a === 0) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 169 && b === 254) return true; // metadados de nuvem
  if (a === 100 && b >= 64 && b <= 127) return true; // CGNAT
  return false;
}

export interface UrlCheck {
  ok: boolean;
  address?: string;
  family?: number;
  reason?: string;
}

/** Validação usada no cadastro do destinatário E antes de cada envio. */
export async function resolveAndValidate(rawUrl: string): Promise<UrlCheck> {
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    return { ok: false, reason: 'URL inválida' };
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    return { ok: false, reason: `esquema não permitido: ${url.protocol}` };
  }
  try {
    const { address, family } = await dnsLookup(url.hostname);
    if (isPrivateAddress(address)) {
      return { ok: false, address, family, reason: `destino resolve para endereço privado: ${address}` };
    }
    return { ok: true, address, family };
  } catch (err) {
    return { ok: false, reason: `falha ao resolver DNS: ${(err as Error).message}` };
  }
}

export function signPayload(id: string, timestampSeconds: number, payload: string, secret: string): string {
  const signed = `${id}.${timestampSeconds}.${payload}`; // ordem literal de R-01
  return `v1,${createHmac('sha256', secret).update(signed).digest('base64')}`;
}

export interface WebhookOptions {
  /** Permite apontar para o receptor local nos testes sem furar o anti-SSRF. */
  allowPrivateAddresses?: boolean;
}

export function createWebhookChannel(opts: WebhookOptions = {}): ChannelPort {
  return {
    channel: 'webhook',
    // 2xx é confirmação do destino, não só submissão (PAR-09).
    terminalStatus: 'delivered',

    async send(msg: OutboundMessage, signal: AbortSignal): Promise<SendResult> {
      const { recipient } = msg;
      if (!recipient.webhookUrl) {
        return { accepted: false, permanent: true, detail: 'destinatário sem webhook_url' };
      }
      if (!recipient.webhookSecret) {
        // ASS-06: URL sem segredo não é entregável — assinar é obrigatório.
        return { accepted: false, permanent: true, detail: 'destinatário sem webhook_secret' };
      }

      const check = await resolveAndValidate(recipient.webhookUrl);
      const pinned = check.address;
      if (!check.ok && !(opts.allowPrivateAddresses && pinned)) {
        return { accepted: false, permanent: true, detail: check.reason ?? 'destino rejeitado' };
      }

      const url = new URL(recipient.webhookUrl);
      const body = JSON.stringify({
        id: msg.notificationId,
        category: msg.category,
        recipientId: recipient.id,
        payload: msg.payload,
      });

      const webhookId = randomUUID();
      // A CADA tentativa o timestamp é NOVO; o id da mensagem permanece (R-01).
      const timestampSeconds = Math.floor(msg.now / 1000);

      const headers = {
        'content-type': 'application/json',
        'webhook-id': webhookId,
        'webhook-timestamp': String(timestampSeconds),
        'webhook-signature': signPayload(webhookId, timestampSeconds, body, recipient.webhookSecret),
        'content-length': String(Buffer.byteLength(body)),
      };

      const doRequest = url.protocol === 'https:' ? httpsRequest : httpRequest;

      return await new Promise<SendResult>((resolve) => {
        let settled = false;
        const finish = (r: SendResult) => {
          if (!settled) {
            settled = true;
            resolve(r);
          }
        };

        const req = doRequest(
          {
            protocol: url.protocol,
            hostname: url.hostname,
            port: url.port || (url.protocol === 'https:' ? 443 : 80),
            path: url.pathname + url.search,
            method: 'POST',
            headers,
            timeout: PAR_10_REQUEST_TIMEOUT_MS,
            // Pino do IP já validado: o resolvedor não é consultado de novo.
            lookup: pinned
              ? (_hostname, _options, cb) => cb(null, pinned as never, (check.family ?? 4) as never)
              : undefined,
          },
          (res) => {
            const status = res.statusCode ?? 0;
            res.resume(); // drena, não precisamos do corpo
            res.on('end', () => {
              if (status >= 200 && status <= 299) {
                finish({ accepted: true, permanent: false, detail: `HTTP ${status}` });
              } else if (status >= 300 && status <= 399) {
                finish({ accepted: false, permanent: true, detail: `HTTP ${status}: redirecionamento não é seguido` });
              } else if (status >= 400 && status <= 499 && status !== 408 && status !== 429) {
                finish({ accepted: false, permanent: true, detail: `HTTP ${status}` });
              } else {
                finish({ accepted: false, permanent: false, detail: `HTTP ${status}` });
              }
            });
          },
        );

        req.on('timeout', () => {
          req.destroy();
          finish({ accepted: false, permanent: false, detail: `timeout de ${PAR_10_REQUEST_TIMEOUT_MS}ms` });
        });
        req.on('error', (err) => {
          const code = (err as NodeJS.ErrnoException).code;
          // ENOTFOUND é permanente; recusa de conexão e reset são transitórios.
          const permanent = code === 'ENOTFOUND' || code === 'ERR_INVALID_URL';
          finish({ accepted: false, permanent, detail: `${code ?? 'erro'}: ${err.message}` });
        });
        signal.addEventListener('abort', () => {
          req.destroy();
          finish({ accepted: false, permanent: false, detail: 'abortado pelo worker' });
        });

        req.end(body);
      });
    },
  };
}
