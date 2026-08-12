/**
 * M-06 autorizacao — dominio puro. Atores, papeis e credencial.
 *
 * Parametros de scrypt com FONTE (specs/technical/parameters.md):
 * OWASP Password Storage Cheat Sheet — Argon2id e a primeira escolha; scrypt e o
 * fallback recomendado quando Argon2id nao esta disponivel. Node 24 nao traz
 * Argon2 embutido e o projeto proibe dependencia de runtime, o que torna scrypt a
 * escolha justificada e nao a conveniente.
 *
 * ATENCAO (AP7): N=2^17 com r=8 exige ~134 MB. O default de `maxmem` do Node e
 * 32 MB e `scryptSync` LANCA sem o ajuste abaixo. Baixar N para caber no default
 * seria enfraquecer o parametro em silencio.
 */

import { randomBytes, randomUUID, scryptSync, timingSafeEqual } from 'node:crypto';
import type { Papel } from './pedido.ts';

export const SCRYPT = {
  N: 2 ** 17,
  r: 8,
  p: 1,
  keylen: 32,
  saltBytes: 16,
  maxmem: 192 * 1024 * 1024,
} as const;

export type Ator = {
  readonly id: string;
  readonly nome: string;
  readonly papel: Papel;
  readonly senhaHash: string;
  readonly senhaSalt: string;
  readonly ativo: boolean;
  readonly criadoEm: Date;
};

function derivar(senha: string, saltHex: string): string {
  const salt = Buffer.from(saltHex, 'hex');
  return scryptSync(senha.normalize('NFC'), salt, SCRYPT.keylen, {
    N: SCRYPT.N,
    r: SCRYPT.r,
    p: SCRYPT.p,
    maxmem: SCRYPT.maxmem,
  }).toString('hex');
}

export function criarAtor(nome: string, senha: string, papel: Papel, agora: Date): Ator {
  const senhaSalt = randomBytes(SCRYPT.saltBytes).toString('hex');
  return {
    id: randomUUID(),
    nome,
    papel,
    senhaHash: derivar(senha, senhaSalt),
    senhaSalt,
    ativo: true,
    criadoEm: agora,
  };
}

/** ETH-03: desativar preserva o historico; apagar o ator apagaria a atribuicao. */
export function desativar(a: Ator): Ator {
  return { ...a, ativo: false };
}

export function autenticar(a: Ator, senha: string): boolean {
  if (!a.ativo) return false;
  const esperado = Buffer.from(a.senhaHash, 'hex');
  const obtido = Buffer.from(derivar(senha, a.senhaSalt), 'hex');
  return esperado.length === obtido.length && timingSafeEqual(esperado, obtido);
}

export function papelDe(a: Ator): Papel {
  return a.papel;
}

export function podeAprovar(a: Ator): boolean {
  return a.ativo && a.papel === 'aprovador';
}
