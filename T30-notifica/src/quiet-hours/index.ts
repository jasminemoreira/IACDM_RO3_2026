/**
 * M-06 quiet-hours — FUNÇÃO PURA. Sem I/O, sem estado, sem relógio próprio.
 *
 * Portado de specs/examples/reference-implementations.md §4 (Tier 2).
 * PAR-14: janela padrão 22:00–08:00 no fuso da PESSOA (invariante 4 do glossário).
 *
 * EDGE-1 / RSK-03 — o erro clássico é escrever `start <= m && m < end`, que é
 * SEMPRE falso quando a janela cruza a meia-noite (1320 -> 480).
 *
 * ASS-03 / ASS-08 (DST): em dias de transição o dia local não tem 1440 minutos.
 * Hora inexistente -> abre no próximo instante válido. Hora repetida -> a
 * PRIMEIRA ocorrência. Ambos caem naturalmente da busca por avanço abaixo.
 */

export interface QuietWindow {
  /** Minutos desde 00:00 local. */
  start: number;
  end: number;
}

export interface QuietCheck {
  inWindow: boolean;
  /** Epoch ms do próximo instante fora da janela. Ausente quando já está fora. */
  opensAt?: number;
}

const MINUTE = 60_000;

/** Minuto do dia (0..1439) no fuso informado. Usa ICU, sem lib de datas. */
export function localMinuteOfDay(tz: string, at: number): number {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: tz,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(new Date(at));
  const hour = Number(parts.find((p) => p.type === 'hour')!.value);
  const minute = Number(parts.find((p) => p.type === 'minute')!.value);
  // ICU pode devolver 24 para meia-noite em alguns locales/horários.
  return (hour % 24) * 60 + minute;
}

export function isInWindow(window: QuietWindow, tz: string, at: number): boolean {
  if (window.start === window.end) return false; // janela vazia = silêncio desligado
  const m = localMinuteOfDay(tz, at);
  return window.start <= window.end
    ? m >= window.start && m < window.end // janela normal
    : m >= window.start || m < window.end; // cruza a meia-noite (EDGE-1)
}

export function check(window: QuietWindow, tz: string, at: number): QuietCheck {
  if (!isInWindow(window, tz, at)) return { inWindow: false };

  // Estimativa direta pelo delta de minutos locais...
  const m = localMinuteOfDay(tz, at);
  const deltaMinutes = (window.end - m + 1440) % 1440;
  let candidate = at + deltaMinutes * MINUTE;

  // ...corrigida por avanço quando o dia local não tem 1440 minutos (DST).
  // O limite de 180 passos cobre saltos de até 3 h, muito além de qualquer
  // transição real, e garante terminação.
  for (let i = 0; i < 180 && isInWindow(window, tz, candidate); i++) {
    candidate += MINUTE;
  }
  return { inWindow: true, opensAt: candidate };
}
