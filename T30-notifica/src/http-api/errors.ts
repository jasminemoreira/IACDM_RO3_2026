/**
 * M-01 http-api — tradução erro de domínio -> status HTTP.
 *
 * LIN-04: `accepted` no HTTP (202) e `accepted` no domínio (persistida) não são
 * a mesma coisa. A tradução mora aqui, explícita, em vez de o domínio conhecer
 * códigos HTTP.
 */
import { IngestError } from '../ingestion/index.ts';
import { ValidationError } from '../preferences/index.ts';

export interface HttpError {
  status: number;
  body: { error: string; code: string; field?: string };
}

export function translate(err: unknown): HttpError {
  if (err instanceof IngestError) {
    const status = {
      unknown_recipient: 404,
      unknown_category: 422,
      payload_too_large: 413,
      idempotency_conflict: 422,
      no_channel: 422,
    }[err.code];
    return { status, body: { error: err.message, code: err.code } };
  }
  if (err instanceof ValidationError) {
    return { status: 422, body: { error: err.message, code: 'validation_error', field: err.field } };
  }
  return { status: 500, body: { error: (err as Error)?.message ?? 'erro interno', code: 'internal' } };
}
