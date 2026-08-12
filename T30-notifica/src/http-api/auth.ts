/**
 * M-01 http-api — autenticação e escopo (decomposição interna declarada, IMP-05).
 *
 * SEC-01: a chave identifica o emissor E limita as categorias em que ele pode
 * emitir. Sem isso, uma chave vazada é canal de spam para qualquer pessoa.
 * SEC-07: "pode emitir na categoria" e "pode emitir COMO TRANSACIONAL" são
 * permissões SEPARADAS — herdar o bypass de supressão só por estar autorizado
 * numa categoria transacional era escalada de privilégio.
 *
 * A chave é guardada como hash; a comparação é em tempo constante.
 */
import { createHash, timingSafeEqual } from 'node:crypto';
import type { ApiKeyRecord, Store } from '../store/index.ts';

export function hashApiKey(key: string): string {
  return createHash('sha256').update(key).digest('hex');
}

export interface AuthResult {
  ok: boolean;
  issuer?: string;
  key?: ApiKeyRecord;
  status?: number;
  message?: string;
}

export function authenticate(store: Store, header: string | undefined): AuthResult {
  if (!header) return { ok: false, status: 401, message: 'header Authorization ausente' };
  const raw = header.startsWith('Bearer ') ? header.slice(7) : header;
  const record = store.apiKeys.find(hashApiKey(raw));
  if (!record) return { ok: false, status: 401, message: 'chave inválida' };
  return { ok: true, issuer: record.issuer, key: record };
}

/** Comparação em tempo constante para segredos de tamanho igual. */
export function safeEqual(a: string, b: string): boolean {
  const ba = Buffer.from(a);
  const bb = Buffer.from(b);
  return ba.length === bb.length && timingSafeEqual(ba, bb);
}

export function authorizeCategory(
  key: ApiKeyRecord,
  category: string,
  categoryIsTransactional: boolean,
): { ok: boolean; message?: string } {
  const scoped = key.categories.includes('*') || key.categories.includes(category);
  if (!scoped) return { ok: false, message: `emissor não autorizado na categoria ${category}` };
  if (categoryIsTransactional && !key.allowTransactional) {
    return { ok: false, message: `emissor não autorizado a emitir na categoria transacional ${category}` };
  }
  return { ok: true };
}
