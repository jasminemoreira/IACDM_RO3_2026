/**
 * M-06 trilha — registro append-only pela aplicação.
 * Guarda INV-7 (ator / em-nome-de / limite exercido) e INV-8 (append-only).
 *
 * V(3)/R6: a promessa é a que o código sustenta — append-only PELA APLICAÇÃO. `TrilhaRepo`
 * não expõe caminho de UPDATE nem DELETE. NÃO há proteção contra adulteração do arquivo
 * SQLite por fora (achado REG-01, aceito com justificativa registrada).
 * V(4)/T5: `registrar` devolve `Resultado` como todo o núcleo (achado LING-05) e é chamado
 * DENTRO da transação — seu erro aborta tudo, então não existe decisão gravada sem trilha
 * (achado RES-05).
 */
import { type ErroDominio, type Instante, type Resultado, erro, falha, ok } from "./resultado.js";
import type { TrilhaRepo } from "./portas.js";

export type TipoEvento = "CRIADA" | "APROVADA_NIVEL" | "NIVEL_PULADO" | "REJEITADA";

export type Evento = {
  readonly despesaId: string;
  readonly tipo: TipoEvento;
  readonly estadoAnterior: string | null;
  readonly estadoNovo: string;
  /** Nível (da matriz) a que o evento se refere; null em CRIADA. */
  readonly nivel: number | null;
  /** Quem agiu. null em NIVEL_PULADO — não há ator, é consequência de regra. */
  readonly atorId: string | null;
  /** INV-7: em nome de quem, quando houve delegação. */
  readonly emNomeDeId: string | null;
  /** Achado GOV-01: a delegação exercida é gravada, não inferida cruzando vigências. */
  readonly delegacaoId: string | null;
  /** INV-7: a autoridade exercida no instante do ato, COPIADA (INV-6 sobrevive a mudanças). */
  readonly limiteExercidoCentavos: number | null;
  /** INV-9 em REJEITADA; motivo do pulo em NIVEL_PULADO. */
  readonly motivo: string | null;
  readonly ocorridoEm: Instante;
};

export function registrar(repo: TrilhaRepo, evento: Evento): Resultado<true, ErroDominio> {
  if (evento.tipo === "REJEITADA" && (evento.motivo ?? "").trim() === "") {
    return falha(erro("MOTIVO_AUSENTE", "Rejeição sem motivo não pode ser registrada na trilha."));
  }
  if (evento.tipo === "NIVEL_PULADO" && (evento.motivo ?? "").trim() === "") {
    return falha(erro("PULO_SEM_MOTIVO", "Um nível pulado precisa registrar por que foi pulado."));
  }
  try {
    repo.anexar(evento);
    return ok(true);
  } catch (e) {
    return falha(erro("TRILHA_FALHOU", `Não foi possível registrar na trilha: ${String(e)}`));
  }
}

export function de(repo: TrilhaRepo, despesaId: string): readonly Evento[] {
  return repo.porDespesa(despesaId);
}

/** Decisões humanas: o que INV-4 consulta (pulo não é decisão de ninguém). */
export function decisoes(eventos: readonly Evento[]): readonly Evento[] {
  return eventos.filter((e) => e.tipo === "APROVADA_NIVEL" || e.tipo === "REJEITADA");
}

/** INV-18: uma despesa só chega a APROVADA com ao menos uma aprovação humana registrada. */
export function temAprovacaoHumana(eventos: readonly Evento[]): boolean {
  return eventos.some((e) => e.tipo === "APROVADA_NIVEL");
}
