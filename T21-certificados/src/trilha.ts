/**
 * M-05 trilha — dominio puro. Cadeia append-only encadeada por hash.
 *
 * Garantia real: TAMPER-EVIDENT verificavel, nao tamper-proof. Quem controla a
 * maquina reescreve a cadeia inteira (premissa A5). O que o sistema garante e
 * que uma alteracao PONTUAL e detectavel — e so isso e o que a UI pode dizer.
 *
 * ASS-05/IMP-05: serializacao canonica (chaves ordenadas, datas ISO UTC) e hash
 * em hex minusculo. Sem canonicalizacao a cadeia acusaria adulteracao inexistente
 * e CA-4 viraria falso-positivo.
 */

import { createHash } from 'node:crypto';

export const GENESIS = 'GENESIS';

/** Enumeracao fechada — specs/models/schema.md. */
export type TipoEvento =
  | 'ator-criado'
  | 'alvo-cadastrado'
  | 'alvo-removido'
  | 'limiar-alterado'
  | 'varredura-iniciada'
  | 'varredura-concluida'
  | 'varredura-interrompida'
  | 'pedido-aberto'
  | 'pedido-aprovado'
  | 'pedido-rejeitado'
  | 'pedido-cancelado'
  | 'pedido-fechado'
  | 'pedido-expirado-sem-emissao'
  | 'troca-nao-autorizada'
  | 'troca-justificada'
  | 'rollback-detectado'
  | 'relogio-retrocedeu';

export type Evento = {
  readonly tipo: TipoEvento;
  readonly atorId: string | null;
  readonly alvoId: string | null;
  readonly pedidoId: string | null;
  /** ASS-12: indice da entrada a que este evento se refere (justificativa -> troca). */
  readonly refIndice: number | null;
  readonly dados: Readonly<Record<string, unknown>>;
};

export type Entrada = Evento & {
  readonly i: number;
  readonly registradoEm: Date;
  readonly hashAnterior: string;
  readonly hash: string;
};

/**
 * Serializacao canonica: chaves ordenadas recursivamente, Date como ISO UTC.
 * Duas implementacoes deste contrato precisam produzir byte a byte o mesmo texto.
 */
export function canonicalizar(valor: unknown): string {
  if (valor === null || valor === undefined) return 'null';
  if (valor instanceof Date) return JSON.stringify(valor.toISOString());
  if (Array.isArray(valor)) return `[${valor.map(canonicalizar).join(',')}]`;
  if (typeof valor === 'object') {
    const entradas = Object.entries(valor as Record<string, unknown>)
      .filter(([, v]) => v !== undefined)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .map(([k, v]) => `${JSON.stringify(k)}:${canonicalizar(v)}`);
    return `{${entradas.join(',')}}`;
  }
  return JSON.stringify(valor);
}

export function payloadDe(evento: Evento, registradoEm: Date): string {
  return canonicalizar({
    tipo: evento.tipo,
    atorId: evento.atorId,
    alvoId: evento.alvoId,
    pedidoId: evento.pedidoId,
    refIndice: evento.refIndice,
    dados: evento.dados,
    registradoEm,
  });
}

export function hashDe(hashAnterior: string, payload: string): string {
  return createHash('sha256').update(hashAnterior).update(payload).digest('hex');
}

/** Monta a proxima entrada. Nao persiste — quem persiste e o repositorio. */
export function anexar(hashAnterior: string, evento: Evento, agora: Date, i: number): Entrada {
  const payload = payloadDe(evento, agora);
  return { ...evento, i, registradoEm: agora, hashAnterior, hash: hashDe(hashAnterior, payload) };
}

export type ResultadoVerificacao = { valida: boolean; quebraNoIndice?: number };

/** CA-4: VALIDA na cadeia intacta, INVALIDA apos adulteracao de 1 registro. */
export function verificar(entradas: readonly Entrada[]): ResultadoVerificacao {
  let anterior = GENESIS;
  for (const e of entradas) {
    const esperado = hashDe(anterior, payloadDe(e, e.registradoEm));
    if (e.hashAnterior !== anterior || e.hash !== esperado) {
      return { valida: false, quebraNoIndice: e.i };
    }
    anterior = e.hash;
  }
  return { valida: true };
}
