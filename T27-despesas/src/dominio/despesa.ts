/**
 * M-01 dominio-despesa — entidade Despesa, estados e transições válidas.
 * Guarda INV-9 (rejeição exige motivo), INV-11 (rejeição é terminal),
 * INV-12 (dinheiro em inteiro de centavos).
 */
import { type ErroDominio, type Instante, type Resultado, erro, falha, ok } from "./resultado.js";

export type Estado = "PENDENTE" | "APROVADA" | "REJEITADA";

export type Despesa = {
  readonly id: string;
  readonly solicitanteId: string;
  /** INV-12: inteiro de centavos. Nunca ponto flutuante. */
  readonly valorCentavos: number;
  readonly descricao: string;
  readonly estado: Estado;
  /** Índice do nível corrente DENTRO da cadeia (0-based). null quando terminal. */
  readonly indiceCadeia: number | null;
  readonly criadaEm: Instante;
};

export function criar(entrada: {
  id: string;
  solicitanteId: string;
  valorCentavos: number;
  descricao: string;
  criadaEm: Instante;
}): Resultado<Despesa, ErroDominio> {
  if (!Number.isInteger(entrada.valorCentavos)) {
    return falha(erro("VALOR_NAO_INTEIRO", "O valor precisa estar em centavos inteiros."));
  }
  if (entrada.valorCentavos <= 0) {
    return falha(erro("VALOR_NAO_POSITIVO", "Informe um valor maior que zero."));
  }
  if (entrada.descricao.trim() === "") {
    return falha(erro("DESCRICAO_VAZIA", "Descreva a despesa — é o que o aprovador lê para decidir."));
  }
  return ok({
    id: entrada.id,
    solicitanteId: entrada.solicitanteId,
    valorCentavos: entrada.valorCentavos,
    descricao: entrada.descricao.trim(),
    estado: "PENDENTE",
    indiceCadeia: 0,
    criadaEm: entrada.criadaEm,
  });
}

/** Avança para o próximo índice da cadeia, ou encerra APROVADA quando a cadeia acabou. */
export function avancar(despesa: Despesa, proximoIndice: number, tamanhoCadeia: number): Despesa {
  if (proximoIndice >= tamanhoCadeia) {
    return { ...despesa, estado: "APROVADA", indiceCadeia: null };
  }
  return { ...despesa, indiceCadeia: proximoIndice };
}

/** INV-9 + INV-11: motivo obrigatório, estado terminal. */
export function rejeitar(despesa: Despesa, motivo: string): Resultado<Despesa, ErroDominio> {
  if (despesa.estado !== "PENDENTE") {
    return falha(erro("NAO_PENDENTE", `Esta despesa já está ${despesa.estado.toLowerCase()}.`));
  }
  if (motivo.trim() === "") {
    return falha(
      erro(
        "MOTIVO_AUSENTE",
        "Informe o motivo — ele fica registrado na trilha e é o que o solicitante lê.",
      ),
    );
  }
  return ok({ ...despesa, estado: "REJEITADA", indiceCadeia: null });
}
