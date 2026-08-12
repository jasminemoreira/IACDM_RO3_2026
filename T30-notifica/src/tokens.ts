/**
 * Token assinado de descadastro — utilitário compartilhado por M-01 e M-10.
 *
 * O RFC 8058 (R-02) exige que o POST de one-click funcione SEM sessão: quem
 * clica no rodapé do e-mail não está autenticado. Sem token, o endpoint vira um
 * botão de descadastrar terceiros (achado SEC-02, primeira metade).
 *
 * O requisito de "uso único" foi ABANDONADO em vez de implementado (V(3)):
 * descadastrar é idempotente, então reapresentar o token só reexecuta o mesmo
 * opt-out. O que o token precisa é de ESCOPO (pessoa + categoria) e de VALIDADE.
 */
import { createHmac, timingSafeEqual } from 'node:crypto';

/** PAR-21 — validade do token de descadastro. */
export const PAR_21_UNSUBSCRIBE_TTL_MS = 30 * 86_400_000;

export interface UnsubscribeClaims {
  recipientId: string;
  category: string;
  expiresAt: number;
}

function sign(payload: string, secret: string): string {
  return createHmac('sha256', secret).update(payload).digest('base64url');
}

export function signUnsubscribeToken(claims: UnsubscribeClaims, secret: string): string {
  const payload = Buffer.from(JSON.stringify(claims), 'utf8').toString('base64url');
  return `${payload}.${sign(payload, secret)}`;
}

export function verifyUnsubscribeToken(token: string, secret: string, now: number): UnsubscribeClaims | null {
  const [payload, signature] = token.split('.');
  if (!payload || !signature) return null;

  const expected = Buffer.from(sign(payload, secret));
  const given = Buffer.from(signature);
  if (expected.length !== given.length || !timingSafeEqual(expected, given)) return null;

  try {
    const claims = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8')) as UnsubscribeClaims;
    if (typeof claims.expiresAt !== 'number' || claims.expiresAt < now) return null;
    return claims;
  } catch {
    return null;
  }
}
