/**
 * M-02 politica-limiar — dominio puro.
 *
 * Limiares por alvo, classificacao de urgencia e decisao de escalacao.
 * Valores 90/60/30 dias: NIST SP 1800-16 (specs/technical/parameters.md).
 *
 * V(3), ASS-11/CTL-04: o estado do alvo e SEMPRE DERIVADO na leitura, a partir da
 * observacao e do limiar vigente — nunca persistido. Mudar a politica reclassifica
 * tudo por construcao, sem painel e historico dessincronizados.
 */

import {
  restanteDias,
  semExpiracao as certSemExpiracao,
  vidaTotalDias,
  type Observacao,
} from './certificado.ts';
import { ok, erro, type Resultado } from './tipos.ts';

export type Limiares = { readonly aviso: number; readonly atencao: number; readonly critico: number };

/** NIST SP 1800-16: notificar 90, 60 e 30 dias antes do vencimento. */
export const LIMIARES_PADRAO: Limiares = { aviso: 90, atencao: 60, critico: 30 };

export type Urgencia = 'ok' | 'aviso' | 'atencao' | 'critico' | 'expirado' | 'ainda-nao-valido';

/** LIN-03: urgencia e semExpiracao sao DIMENSOES SEPARADAS. Um certificado sem
 *  expiracao nao e "ok" por urgencia — ele esta fora da escala. */
export type Classificacao = { readonly urgencia: Urgencia; readonly semExpiracao: boolean };

export type ErroConfig =
  | { tipo: 'limiar-nao-positivo'; qual: keyof Limiares; valor: number }
  | { tipo: 'limiares-fora-de-ordem' }
  | { tipo: 'limiar-maior-que-vida'; qual: keyof Limiares; valor: number; vidaTotalDias: number };

/**
 * CA-5 — o invariante `limiar < (notAfter - notBefore)`.
 *
 * Sob CA/B SC-081v3 a vida maxima caiu para 200 dias (hoje) e cai para 47 em 2029:
 * um limiar de 90 dias contra um certificado de 45 geraria alerta permanente desde a
 * emissao, que e o ruido que treina o operador a ignorar o alerta — exatamente a
 * falha que a NIST SP 1800-16 quer evitar. Ver specs/technical/renewal-thresholds.md.
 */
export function validarLimiares(l: Limiares, vidaDias: number): Resultado<void, ErroConfig> {
  for (const qual of ['aviso', 'atencao', 'critico'] as const) {
    if (!Number.isFinite(l[qual]) || l[qual] <= 0) {
      return erro({ tipo: 'limiar-nao-positivo', qual, valor: l[qual] });
    }
  }
  if (!(l.critico < l.atencao && l.atencao < l.aviso)) {
    return erro({ tipo: 'limiares-fora-de-ordem' });
  }
  for (const qual of ['aviso', 'atencao', 'critico'] as const) {
    if (l[qual] >= vidaDias) {
      return erro({ tipo: 'limiar-maior-que-vida', qual, valor: l[qual], vidaTotalDias: vidaDias });
    }
  }
  return ok(undefined);
}

export function validarContraObservacao(l: Limiares, o: Observacao): Resultado<void, ErroConfig> {
  return validarLimiares(l, vidaTotalDias(o));
}

/** CA-1 — classificacao nos estados a partir da observacao e do limiar vigente. */
export function classificar(o: Observacao, l: Limiares, agora: Date): Classificacao {
  const sem = certSemExpiracao(o);
  if (agora.getTime() < o.notBefore.getTime()) {
    return { urgencia: 'ainda-nao-valido', semExpiracao: sem };
  }
  if (sem) return { urgencia: 'ok', semExpiracao: true };

  const restante = restanteDias(o, agora);
  if (restante < 0) return { urgencia: 'expirado', semExpiracao: false };
  if (restante <= l.critico) return { urgencia: 'critico', semExpiracao: false };
  if (restante <= l.atencao) return { urgencia: 'atencao', semExpiracao: false };
  if (restante <= l.aviso) return { urgencia: 'aviso', semExpiracao: false };
  return { urgencia: 'ok', semExpiracao: false };
}

/**
 * NIST SP 1800-16 exige escalacao automatica por inacao. Aqui a escalacao e ESTADO
 * VISIVEL, nao notificacao de saida — o produto nao tem canal externo por decisao
 * da Fase 0, e isso esta registrado como desvio normativo consciente.
 */
export function deveEscalar(urgencia: Urgencia, temPedidoAberto: boolean): boolean {
  return (urgencia === 'critico' || urgencia === 'expirado') && !temPedidoAberto;
}
