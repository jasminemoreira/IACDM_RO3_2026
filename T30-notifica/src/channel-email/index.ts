/**
 * M-10 channel-email — adaptador SMTP da ChannelPort (Tier 1: nodemailer).
 *
 * PAR-17 / RFC 8058 (R-02): todo e-mail carrega
 *   List-Unsubscribe: <https://.../unsubscribe?token=...>
 *   List-Unsubscribe-Post: List-Unsubscribe=One-Click
 * O valor do segundo header é LITERAL e não admite variação.
 *
 * REG-01 (risco aceito): o RFC 8058 também exige assinatura DKIM cobrindo esses
 * headers. DKIM é responsabilidade do PROVEDOR de e-mail, não deste serviço —
 * emitimos os headers exigidos e a assinatura é configuração do provedor real.
 * Está registrado como aceito, não como esquecido.
 *
 * RES-02: o estado terminal aqui é `sent`, não `delivered`. Só sabemos que o
 * provedor aceitou a submissão; bounce é assíncrono e chega por outro caminho.
 */
import nodemailer from 'nodemailer';
import type { ChannelPort, OutboundMessage, SendResult } from '../types.ts';
import { PAR_21_UNSUBSCRIBE_TTL_MS, signUnsubscribeToken } from '../tokens.ts';

export interface EmailOptions {
  host: string;
  port: number;
  from: string;
  /** IMP-04: a URL base do link de descadastro precisa ser configurável. */
  baseUrl: string;
  /** Segredo de assinatura do token de descadastro. */
  tokenSecret: string;
}

/**
 * Dois templates, e a diferença entre eles é semântica, não estética:
 *
 * - `standard`: traz o rodapé de descadastro. É a mensagem que a pessoa pode
 *   recusar, e o RFC 8058 se aplica a ela.
 * - `transactional`: NÃO traz rodapé de descadastro. A categoria é transacional
 *   por decisão do catálogo, o opt-out não vale para ela, e oferecer um link que
 *   não desliga nada seria mentir para a pessoa. Em vez disso, diz por que ela
 *   está recebendo.
 */
export function renderEmail(
  msg: OutboundMessage,
  unsubscribeUrl: string,
  transactional: boolean,
): { subject: string; text: string } {
  const { payload, category } = msg;
  const footer = transactional
    ? [`Categoria: ${category}`, 'Esta é uma mensagem transacional e não pode ser desativada nas preferências.']
    : [`Categoria: ${category}`, `Para não receber mais mensagens desta categoria: ${unsubscribeUrl}`];
  return {
    subject: payload.subject,
    text: [payload.body, '', '---', ...footer].join('\n'),
  };
}

export function createEmailChannel(opts: EmailOptions): ChannelPort {
  const transport = nodemailer.createTransport({
    host: opts.host,
    port: opts.port,
    secure: false,
    // MEC-02: tolerância a servidor SMTP real não está declarada — o provider
    // local não exige auth nem STARTTLS. Risco aceito e registrado.
    tls: { rejectUnauthorized: false },
  });

  return {
    channel: 'email',
    terminalStatus: 'sent',

    async send(msg: OutboundMessage, signal: AbortSignal): Promise<SendResult> {
      const { recipient } = msg;
      if (!recipient.email) {
        return { accepted: false, permanent: true, detail: 'destinatário sem e-mail' };
      }

      const token = signUnsubscribeToken(
        {
          recipientId: recipient.id,
          category: msg.category,
          expiresAt: msg.now + PAR_21_UNSUBSCRIBE_TTL_MS,
        },
        opts.tokenSecret,
      );
      const unsubscribeUrl = `${opts.baseUrl.replace(/\/$/, '')}/unsubscribe?token=${token}`;
      const { subject, text } = renderEmail(msg, unsubscribeUrl, msg.transactional);

      // Os headers de descadastro só acompanham mensagem que a pessoa PODE
      // recusar. Numa transacional eles apontariam para um botão que não desliga
      // nada — pior que ausência, é promessa falsa.
      const headers: Record<string, string> = msg.transactional
        ? {}
        : {
            'List-Unsubscribe': `<${unsubscribeUrl}>`,
            // Valor literal exigido pelo RFC 8058 — não admite variação.
            'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
          };

      try {
        const sent = await Promise.race([
          transport.sendMail({
            from: opts.from,
            to: recipient.email,
            subject,
            text,
            headers,
          }),
          abortPromise(signal),
        ]);
        if (sent === ABORTED) {
          return { accepted: false, permanent: false, detail: 'abortado pelo worker' };
        }
        return { accepted: true, permanent: false, detail: 'submetido ao provedor SMTP' };
      } catch (err) {
        const code = (err as NodeJS.ErrnoException).code ?? '';
        const message = (err as Error).message;
        // 5xx de SMTP é recusa definitiva; conexão recusada é transitória.
        const permanent = /\b5\d\d\b/.test(message) || code === 'EENVELOPE';
        return { accepted: false, permanent, detail: `${code || 'erro'}: ${message}` };
      }
    },
  };
}

const ABORTED = Symbol('aborted');

function abortPromise(signal: AbortSignal): Promise<typeof ABORTED> {
  return new Promise((resolve) => {
    if (signal.aborted) return resolve(ABORTED);
    signal.addEventListener('abort', () => resolve(ABORTED), { once: true });
  });
}
