/**
 * M-07 relogio — porta de tempo.
 *
 * Fonte UNICA do "agora" em UTC: nenhum outro modulo chama `new Date()`.
 * E o que torna a classificacao de vencimento (CA-1) deterministica nos testes.
 *
 * V(2)/V(3): ganha deteccao de retrocesso (ASS-08, REG-04) — primeira mitigacao
 * real da premissa A2. Relogio consistentemente errado continua indetectavel;
 * isso esta declarado, nao prometido a mais.
 */

import { ok, erro, type Resultado } from './tipos.ts';

export type Retrocesso = { tipo: 'relogio-retrocedeu'; deltaMs: number };

export type Relogio = {
  agora(): Date;
  /** RES-07: comportamento definido — a operacao e RECUSADA quando ha retrocesso. */
  verificarMonotonia(ultimoCarimbo: Date | null): Resultado<void, Retrocesso>;
};

export function criarRelogio(fonte: () => Date = () => new Date()): Relogio {
  return {
    agora: () => fonte(),
    verificarMonotonia(ultimoCarimbo) {
      if (ultimoCarimbo === null) return ok(undefined);
      const deltaMs = ultimoCarimbo.getTime() - fonte().getTime();
      return deltaMs > 0 ? erro({ tipo: 'relogio-retrocedeu', deltaMs }) : ok(undefined);
    },
  };
}

/** Relogio fixo para teste — a injecao existe para isto. */
export function relogioFixo(instante: Date): Relogio {
  return criarRelogio(() => new Date(instante.getTime()));
}
