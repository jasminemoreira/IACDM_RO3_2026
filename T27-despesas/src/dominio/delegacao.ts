/**
 * M-03 dominio-delegacao — entidade Delegação, vigência, revogação.
 * Guarda INV-3 (não transitiva), INV-5 (sem vigências sobrepostas), INV-16 (não antedatada).
 *
 * V(3)/ARQ-05: NÃO depende de `relogio` — `Instante` é `string`, tipo primitivo; o instante
 * corrente entra por parâmetro.
 */
import { type ErroDominio, type Instante, type Resultado, erro, falha, ok } from "./resultado.js";

export type EstadoDelegacao = "ATIVA" | "REVOGADA";

export type Delegacao = {
  readonly id: string;
  readonly deleganteId: string;
  readonly delegadoId: string;
  readonly inicio: Instante;
  readonly fim: Instante;
  readonly estado: EstadoDelegacao;
  readonly revogadaEm: Instante | null;
  readonly revogadaPor: string | null;
  readonly criadaEm: Instante;
};

/**
 * `EXPIRADA` deliberadamente NÃO é um estado gravado: expiração é função do relógio, não um
 * fato persistido. Gravá-la exigiria o agendador que o escopo negativo exclui, e criaria a
 * possibilidade de o banco discordar do relógio.
 */
export function ativaEm(
  delegacoes: readonly Delegacao[],
  deleganteId: string,
  instante: Instante,
): Delegacao | null {
  return (
    delegacoes.find(
      (d) =>
        d.deleganteId === deleganteId &&
        d.estado === "ATIVA" &&
        d.inicio <= instante &&
        instante < d.fim,
    ) ?? null
  );
}

/** Todas as delegações vigentes agora, de qualquer delegante. */
export function vigentes(delegacoes: readonly Delegacao[], instante: Instante): readonly Delegacao[] {
  return delegacoes.filter((d) => d.estado === "ATIVA" && d.inicio <= instante && instante < d.fim);
}

export function podeCriar(entrada: {
  deleganteId: string;
  delegadoId: string;
  inicio: Instante;
  fim: Instante;
  agora: Instante;
  /** Delegações do delegante (para INV-5). */
  ativasDoDelegante: readonly Delegacao[];
  /** Delegações que o DELEGANTE recebeu e estão vigentes (para INV-3). */
  recebidasVigentesPeloDelegante: readonly Delegacao[];
}): Resultado<true, ErroDominio> {
  const { deleganteId, delegadoId, inicio, fim, agora } = entrada;

  if (deleganteId === delegadoId) {
    return falha(erro("DELEGADO_IGUAL_DELEGANTE", "Você não pode delegar para si mesmo."));
  }
  if (!(fim > inicio)) {
    return falha(erro("VIGENCIA_INVALIDA", "A data de fim precisa ser posterior à de início."));
  }
  // INV-16 (achado A-03): delegação antedatada é indistinguível, para a auditoria, de uma
  // delegação legítima esquecida.
  if (inicio.slice(0, 10) < agora.slice(0, 10)) {
    return falha(erro("ANTEDATADA", "A data de início não pode ser no passado."));
  }
  // INV-3 (cenário D-14): quem está exercendo a autoridade de outra pessoa não pode repassá-la.
  if (entrada.recebidasVigentesPeloDelegante.length > 0) {
    const de = entrada.recebidasVigentesPeloDelegante[0]!.deleganteId;
    return falha(
      erro(
        "REDELEGACAO",
        `Você está exercendo a autoridade de ${de} e não pode repassá-la. ` +
          `Só ${de} pode delegar a autoridade de ${de}.`,
      ),
    );
  }
  // INV-5 (cenário D-15): duas delegações ativas do mesmo delegante com vigências que se
  // cruzam tornam ambíguo qual delegado recebe o item.
  const sobreposta = entrada.ativasDoDelegante.find(
    (d) => d.estado === "ATIVA" && d.inicio < fim && inicio < d.fim,
  );
  if (sobreposta) {
    return falha(
      erro(
        "VIGENCIAS_SOBREPOSTAS",
        `Você já delegou a ${sobreposta.delegadoId} de ${sobreposta.inicio.slice(0, 10)} a ` +
          `${sobreposta.fim.slice(0, 10)}. Revogue aquela delegação antes de criar outra que se sobreponha.`,
      ),
    );
  }

  return ok(true);
}

export function revogar(
  delegacao: Delegacao,
  porUsuarioId: string,
  instante: Instante,
): Resultado<Delegacao, ErroDominio> {
  if (delegacao.estado !== "ATIVA") {
    return falha(erro("JA_REVOGADA", "Esta delegação já foi revogada."));
  }
  return ok({ ...delegacao, estado: "REVOGADA", revogadaEm: instante, revogadaPor: porUsuarioId });
}
