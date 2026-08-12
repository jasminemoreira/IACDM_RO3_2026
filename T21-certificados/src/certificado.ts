/**
 * M-01 certificado — dominio puro, sem I/O.
 *
 * Modelo da observacao a partir da CADEIA INTEIRA servida e calculos de validade.
 * Referencias: RFC 5280 §4.1.2.5 (Validity, UTCTime/GeneralizedTime, sentinela
 * 99991231235959Z). Ver specs/references/normative-references.md.
 *
 * V(3), ASS-10: a classificacao usa `notAfterFolha`. `notAfterEfetivo` (menor
 * notAfter da cadeia) e SINALIZACAO SEPARADA — servidores servem cross-signed e
 * raizes extras, e usa-lo como driver do estado geraria alarme permanente que
 * renovacao nenhuma resolve.
 */

import { X509Certificate } from 'node:crypto';
import { ok, erro, type Resultado } from './tipos.ts';

/** RFC 5280 §4.1.2.5: certificado sem data de expiracao conhecida. Nao e o ano 9999. */
export const SENTINELA_SEM_EXPIRACAO = Date.UTC(9999, 11, 31, 23, 59, 59);

export type Observacao = {
  readonly fingerprint256: string;
  readonly issuer: string;
  readonly subject: string;
  readonly serial: string;
  readonly san: readonly string[];
  readonly notBefore: Date;
  /** notAfter do certificado folha — dirige a classificacao. */
  readonly notAfterFolha: Date;
  /** menor notAfter de toda a cadeia servida — sinalizacao, nao classificacao. */
  readonly notAfterEfetivo: Date;
  readonly profundidade: number;
};

export type ErroParsing =
  | { tipo: 'cadeia-vazia' }
  | { tipo: 'der-ilegivel'; indice: number; detalhe: string };

const MS_POR_DIA = 86_400_000;

/** Pre-condicao: `ders` nao vazio; o primeiro elemento e o certificado folha.
 *  MEC-02: SAN ausente vira [], subject vazio e aceito — variacao normal do mundo real. */
export function deCadeia(ders: readonly Buffer[]): Resultado<Observacao, ErroParsing> {
  if (ders.length === 0) return erro({ tipo: 'cadeia-vazia' });

  const certs: X509Certificate[] = [];
  for (const [i, der] of ders.entries()) {
    try {
      certs.push(new X509Certificate(der));
    } catch (e) {
      return erro({ tipo: 'der-ilegivel', indice: i, detalhe: (e as Error).message });
    }
  }

  const folha = certs[0]!;
  const notAfterEfetivo = certs.reduce(
    (menor, c) => (c.validToDate < menor ? c.validToDate : menor),
    folha.validToDate,
  );

  return ok({
    fingerprint256: folha.fingerprint256,
    issuer: folha.issuer.replace(/\n/g, ', '),
    subject: folha.subject.replace(/\n/g, ', '),
    serial: folha.serialNumber,
    san: parseSan(folha.subjectAltName),
    notBefore: folha.validFromDate,
    notAfterFolha: folha.validToDate,
    notAfterEfetivo,
    profundidade: certs.length,
  });
}

function parseSan(san: string | undefined): readonly string[] {
  if (!san) return [];
  return san
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

/** notAfterFolha - notBefore, em dias. Distinta de "restante". */
export function vidaTotalDias(o: Observacao): number {
  return (o.notAfterFolha.getTime() - o.notBefore.getTime()) / MS_POR_DIA;
}

/**
 * notAfterFolha - agora, truncado para baixo (specs/technical/parameters.md).
 * O truncamento e a regra declarada que resolve MEC-03/CTL-03: 29,9 dias e 29,
 * sem ambiguidade de fronteira e sem oscilar entre varreduras.
 */
export function restanteDias(o: Observacao, agora: Date): number {
  return Math.floor((o.notAfterFolha.getTime() - agora.getTime()) / MS_POR_DIA);
}

/** RFC 5280 §4.1.2.5 — trata a sentinela como "nao expira", nao como data real. */
export function semExpiracao(o: Observacao): boolean {
  return o.notAfterFolha.getTime() >= SENTINELA_SEM_EXPIRACAO;
}

/** ASS-10: a cadeia expira antes da folha? Sinalizacao, nao estado. */
export function cadeiaExpiraAntes(o: Observacao): boolean {
  return o.notAfterEfetivo.getTime() < o.notAfterFolha.getTime();
}
