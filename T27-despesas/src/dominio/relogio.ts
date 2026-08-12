/**
 * M-07 relogio — porta de produção só de leitura + adaptador controlável de teste.
 *
 * V(3)/S3: `agora() = relógio real + T27_RELOGIO_OFFSET_MS`, lido UMA vez na
 * inicialização. O relógio ANDA (achado CTRL-03: fixar o instante tornava `agora()`
 * constante — todos os `criada_em` iguais, FIFO indefinido, nenhuma vigência expirando).
 * V(3)/ARQ-04: a porta de produção não expõe mutação de tempo; `avancar`/`fixarEm`
 * vivem só em `relogioControlavel`, que não é a porta de produção.
 */
import type { Instante } from "./resultado.js";

export interface Clock {
  agora(): Instante;
}

/** Achado RES-04: offset ausente = 0; offset mal formado impede a subida do processo. */
export function lerOffsetDoAmbiente(bruto: string | undefined): number {
  if (bruto === undefined || bruto.trim() === "") return 0;
  const n = Number(bruto);
  if (!Number.isFinite(n) || !Number.isInteger(n)) {
    throw new Error(
      `T27_RELOGIO_OFFSET_MS inválido: ${JSON.stringify(bruto)}. ` +
        `Use um inteiro de milissegundos (ex.: 259200000 para 3 dias) ou deixe a variável ausente.`,
    );
  }
  return n;
}

export function relogioReal(offsetMs: number): Clock {
  return { agora: () => new Date(Date.now() + offsetMs).toISOString() };
}

/** Só teste. Deliberadamente NÃO é a porta de produção (achado ARQ-04). */
export function relogioControlavel(inicial: Instante) {
  let t = Date.parse(inicial);
  return {
    agora: (): Instante => new Date(t).toISOString(),
    avancar(ms: number) {
      t += ms;
    },
    fixarEm(i: Instante) {
      t = Date.parse(i);
    },
  };
}

/** Normalização de fuso exigida por INV-16 (achado A-07: T5 envia data sem hora). */
export function diaParaInstante(dia: string): Instante {
  return `${dia}T00:00:00.000Z`;
}
