/**
 * M-10 casos-de-uso — orquestra UC-1..UC-7 dentro de uma transação.
 *
 * V(4)/T1: NÃO decide elegibilidade — pergunta a `autoridade.algumDecisor`. A invariante SoD
 * mora no domínio (achado ARQ-08: V(3) a havia empurrado para cá, violando o Domain Model).
 * V(4)/T2: a regra do pulo é uma só, aplicada em qualquer momento e por qualquer causa, e
 * cada pulo grava `NIVEL_PULADO` na trilha (achados PROC-08, GOV-06).
 * V(4)/T5: `registrar` roda dentro da transação e seu erro aborta tudo (achado RES-05).
 */
import type { Clock } from "../dominio/relogio.js";
import type { Repositorios, Usuario } from "../dominio/portas.js";
import type { Despesa } from "../dominio/despesa.js";
import type { MatrizValida, Papel } from "../dominio/matriz-doa.js";
import type { Evento } from "../dominio/trilha.js";
import type { ItemBandeja } from "../dominio/bandeja.js";
import { type ErroDominio, type Resultado, erro, falha, ok } from "../dominio/resultado.js";
import * as despesaDom from "../dominio/despesa.js";
import * as delegacaoDom from "../dominio/delegacao.js";
import * as matriz from "../dominio/matriz-doa.js";
import * as autoridade from "../dominio/autoridade.js";
import * as trilha from "../dominio/trilha.js";
import * as bandeja from "../dominio/bandeja.js";

export type Ambiente = {
  readonly repos: Repositorios;
  readonly matriz: MatrizValida;
  readonly relogio: Clock;
  readonly novoId: () => string;
};

const naoEncontrado = (o: string) => erro("NAO_ENCONTRADO", `${o} não encontrado(a).`);

function contexto(amb: Ambiente, despesa: Despesa, cadeia: readonly Papel[], indice: number, instante: string) {
  return {
    despesa,
    indice,
    cadeia,
    usuarios: amb.repos.usuarios.todos(),
    decisoes: trilha.decisoes(amb.repos.trilha.porDespesa(despesa.id)),
    delegacoes: amb.repos.delegacoes.todas(),
    instante,
  };
}

function cadeiaDe(amb: Ambiente, despesa: Despesa): Resultado<readonly Papel[], ErroDominio> {
  const solicitante = amb.repos.usuarios.porId(despesa.solicitanteId);
  if (!solicitante) return falha(naoEncontrado("Solicitante"));
  return matriz.cadeiaPara(amb.matriz, despesa.valorCentavos, solicitante.papelId);
}

/**
 * Avança do índice `de` até o primeiro nível COM decisor, registrando `NIVEL_PULADO` para
 * cada nível pulado. Devolve o índice parado (pode ser === cadeia.length: acabou a cadeia).
 */
function pularAteDecisor(
  amb: Ambiente,
  despesa: Despesa,
  cadeia: readonly Papel[],
  de: number,
  instante: string,
): Resultado<number, ErroDominio> {
  let i = de;
  while (i < cadeia.length) {
    const ctx = contexto(amb, despesa, cadeia, i, instante);
    if (autoridade.algumDecisor(ctx)) return ok(i);
    const r = trilha.registrar(amb.repos.trilha, {
      despesaId: despesa.id,
      tipo: "NIVEL_PULADO",
      estadoAnterior: "PENDENTE",
      estadoNovo: "PENDENTE",
      nivel: cadeia[i]!.nivel,
      atorId: null,
      emNomeDeId: null,
      delegacaoId: null,
      limiteExercidoCentavos: null,
      motivo: autoridade.motivoDoPulo(ctx),
      ocorridoEm: instante,
    });
    if (!r.ok) return falha(r.erro);
    i++;
  }
  return ok(i);
}

/** UC-1 — Solicitar despesa. */
export function solicitar(
  amb: Ambiente,
  entrada: { solicitanteId: string; valorCentavos: number; descricao: string },
): Resultado<Despesa, ErroDominio> {
  const solicitante = amb.repos.usuarios.porId(entrada.solicitanteId);
  if (!solicitante) return falha(naoEncontrado("Usuário"));

  const agora = amb.relogio.agora();
  const cadeia = matriz.cadeiaPara(amb.matriz, entrada.valorCentavos, solicitante.papelId);
  if (!cadeia.ok) return falha(cadeia.erro);

  const criada = despesaDom.criar({
    id: amb.novoId(),
    solicitanteId: solicitante.id,
    valorCentavos: entrada.valorCentavos,
    descricao: entrada.descricao,
    criadaEm: agora,
  });
  if (!criada.ok) return falha(criada.erro);

  try {
    return amb.repos.emTransacao(() => {
      // A despesa é gravada ANTES de qualquer evento: `evento_trilha.despesa_id` tem chave
      // estrangeira para `despesa(id)` e as PRAGMA foreign_keys estão ligadas — registrar o
      // pulo antes de existir a despesa violaria a FK. Se a criação for recusada logo abaixo,
      // a transação inteira reverte e nada disto persiste.
      amb.repos.despesas.salvar(criada.valor);

      const ev = trilha.registrar(amb.repos.trilha, {
        despesaId: criada.valor.id,
        tipo: "CRIADA",
        estadoAnterior: null,
        estadoNovo: "PENDENTE",
        nivel: cadeia.valor[0]!.nivel,
        atorId: solicitante.id,
        emNomeDeId: null,
        delegacaoId: null,
        limiteExercidoCentavos: null,
        motivo: null,
        ocorridoEm: agora,
      });
      if (!ev.ok) throw new ErroTransacional(ev.erro);

      const inicio = pularAteDecisor(amb, criada.valor, cadeia.valor, 0, agora);
      if (!inicio.ok) throw new ErroTransacional(inicio.erro);

      // INV-17 + INV-18: nenhum nível da cadeia tem decisor — a despesa não pode ser
      // registrada, porque nenhuma aprovação humana seria possível.
      if (inicio.valor >= cadeia.valor.length) {
        throw new ErroTransacional(
          erro(
            "SEM_DECISOR",
            "Esta despesa não tem nenhum aprovador possível na configuração atual da empresa " +
              "e por isso não pode ser registrada. Trate-a fora do sistema.",
          ),
        );
      }

      const despesa = { ...criada.valor, indiceCadeia: inicio.valor };
      amb.repos.despesas.salvar(despesa);
      return ok(despesa);
    });
  } catch (e) {
    if (e instanceof ErroTransacional) return falha(e.erroDominio);
    throw e;
  }
}

/** UC-2 / UC-5 — Aprovar (por autoridade própria ou por delegação). */
export function aprovar(
  amb: Ambiente,
  entrada: { despesaId: string; atuanteId: string },
): Resultado<Despesa, ErroDominio> {
  return decidir(amb, entrada.despesaId, entrada.atuanteId, { tipo: "aprovar" });
}

/** UC-3 — Rejeitar com motivo obrigatório (INV-9), terminal (INV-11). */
export function rejeitar(
  amb: Ambiente,
  entrada: { despesaId: string; atuanteId: string; motivo: string },
): Resultado<Despesa, ErroDominio> {
  return decidir(amb, entrada.despesaId, entrada.atuanteId, { tipo: "rejeitar", motivo: entrada.motivo });
}

class ErroTransacional extends Error {
  constructor(readonly erroDominio: ErroDominio) {
    super(erroDominio.mensagem);
  }
}

function decidir(
  amb: Ambiente,
  despesaId: string,
  atuanteId: string,
  acao: { tipo: "aprovar" } | { tipo: "rejeitar"; motivo: string },
): Resultado<Despesa, ErroDominio> {
  const atuante = amb.repos.usuarios.porId(atuanteId);
  if (!atuante) return falha(naoEncontrado("Usuário"));
  const agora = amb.relogio.agora();

  try {
    return amb.repos.emTransacao(() => {
      // Leitura DENTRO da transação: ler antes e decidir depois reabriria a janela de corrida
      // que a transação existe para fechar (specs/examples).
      const despesa = amb.repos.despesas.porId(despesaId);
      if (!despesa) throw new ErroTransacional(naoEncontrado("Despesa"));
      if (despesa.estado !== "PENDENTE" || despesa.indiceCadeia === null) {
        throw new ErroTransacional(
          erro("CONFLITO", `Esta despesa já está ${despesa.estado.toLowerCase()} — outra pessoa decidiu antes.`),
        );
      }

      const cadeia = cadeiaDe(amb, despesa);
      if (!cadeia.ok) throw new ErroTransacional(cadeia.erro);

      const indice = despesa.indiceCadeia;
      const ctx = contexto(amb, despesa, cadeia.valor, indice, agora);
      const autorizacao = autoridade.resolver(ctx, atuante);
      if (!autorizacao.ok) throw new ErroTransacional(autorizacao.erro);

      const papel = cadeia.valor[indice]!;

      if (acao.tipo === "rejeitar") {
        const rejeitada = despesaDom.rejeitar(despesa, acao.motivo);
        if (!rejeitada.ok) throw new ErroTransacional(rejeitada.erro);
        amb.repos.despesas.salvar(rejeitada.valor);
        registrarOuAbortar(amb, {
          despesaId: despesa.id,
          tipo: "REJEITADA",
          estadoAnterior: "PENDENTE",
          estadoNovo: "REJEITADA",
          nivel: papel.nivel,
          atorId: atuante.id,
          emNomeDeId: autorizacao.valor.emNomeDe?.id ?? null,
          delegacaoId: autorizacao.valor.delegacaoId,
          limiteExercidoCentavos: autorizacao.valor.limiteExercidoCentavos,
          motivo: acao.motivo.trim(),
          ocorridoEm: agora,
        });
        return ok(rejeitada.valor);
      }

      registrarOuAbortar(amb, {
        despesaId: despesa.id,
        tipo: "APROVADA_NIVEL",
        estadoAnterior: "PENDENTE",
        estadoNovo: "PENDENTE",
        nivel: papel.nivel,
        atorId: atuante.id,
        emNomeDeId: autorizacao.valor.emNomeDe?.id ?? null,
        delegacaoId: autorizacao.valor.delegacaoId,
        limiteExercidoCentavos: autorizacao.valor.limiteExercidoCentavos,
        motivo: null,
        ocorridoEm: agora,
      });

      const proximo = pularAteDecisor(amb, despesa, cadeia.valor, indice + 1, agora);
      if (!proximo.ok) throw new ErroTransacional(proximo.erro);

      const atualizada = despesaDom.avancar(despesa, proximo.valor, cadeia.valor.length);

      // INV-18: nunca APROVADA sem ao menos uma aprovação humana registrada.
      if (atualizada.estado === "APROVADA" && !trilha.temAprovacaoHumana(amb.repos.trilha.porDespesa(despesa.id))) {
        throw new ErroTransacional(
          erro("SEM_APROVACAO_HUMANA", "Nenhuma aprovação humana foi registrada para esta despesa."),
        );
      }

      amb.repos.despesas.salvar(atualizada);
      return ok(atualizada);
    });
  } catch (e) {
    if (e instanceof ErroTransacional) return falha(e.erroDominio);
    throw e;
  }
}

function registrarOuAbortar(amb: Ambiente, evento: Evento): void {
  const r = trilha.registrar(amb.repos.trilha, evento);
  if (!r.ok) throw new ErroTransacional(r.erro);
}

/** UC-4 — Delegar temporariamente. */
export function delegar(
  amb: Ambiente,
  entrada: { deleganteId: string; delegadoId: string; inicio: string; fim: string },
): Resultado<{ id: string }, ErroDominio> {
  const delegante = amb.repos.usuarios.porId(entrada.deleganteId);
  const delegado = amb.repos.usuarios.porId(entrada.delegadoId);
  if (!delegante || !delegado) return falha(naoEncontrado("Usuário"));

  const agora = amb.relogio.agora();
  const todas = amb.repos.delegacoes.todas();

  const permitido = delegacaoDom.podeCriar({
    deleganteId: delegante.id,
    delegadoId: delegado.id,
    inicio: entrada.inicio,
    fim: entrada.fim,
    agora,
    ativasDoDelegante: amb.repos.delegacoes.porDelegante(delegante.id).filter((d) => d.estado === "ATIVA"),
    recebidasVigentesPeloDelegante: delegacaoDom
      .vigentes(todas, agora)
      .filter((d) => d.delegadoId === delegante.id),
  });
  if (!permitido.ok) return falha(permitido.erro);

  const id = amb.novoId();
  amb.repos.emTransacao(() => {
    amb.repos.delegacoes.salvar({
      id,
      deleganteId: delegante.id,
      delegadoId: delegado.id,
      inicio: entrada.inicio,
      fim: entrada.fim,
      estado: "ATIVA",
      revogadaEm: null,
      revogadaPor: null,
      criadaEm: agora,
    });
  });
  return ok({ id });
}

/** UC-6 — Revogar delegação (pelo delegante ou pelo Admin). */
export function revogar(
  amb: Ambiente,
  entrada: { delegacaoId: string; atuanteId: string; ehAdmin: boolean },
): Resultado<true, ErroDominio> {
  const d = amb.repos.delegacoes.porId(entrada.delegacaoId);
  if (!d) return falha(naoEncontrado("Delegação"));
  if (d.deleganteId !== entrada.atuanteId && !entrada.ehAdmin) {
    return falha(erro("NAO_AUTORIZADO", "Só o delegante ou o Admin podem revogar esta delegação."));
  }
  const revogada = delegacaoDom.revogar(d, entrada.atuanteId, amb.relogio.agora());
  if (!revogada.ok) return falha(revogada.erro);
  amb.repos.emTransacao(() => amb.repos.delegacoes.salvar(revogada.valor));
  return ok(true);
}

/** UC-7 — Bandeja e trilha (leitura). */
export function verBandeja(amb: Ambiente, usuarioId: string): Resultado<readonly ItemBandeja[], ErroDominio> {
  const usuario = amb.repos.usuarios.porId(usuarioId);
  if (!usuario) return falha(naoEncontrado("Usuário"));
  return ok(
    bandeja.listar(
      {
        matriz: amb.matriz,
        pendentes: amb.repos.despesas.pendentes(),
        usuarios: amb.repos.usuarios.todos(),
        delegacoes: amb.repos.delegacoes.todas(),
        eventosDe: (id) => amb.repos.trilha.porDespesa(id),
      },
      usuario,
      amb.relogio.agora(),
    ),
  );
}

export function verTrilha(
  amb: Ambiente,
  despesaId: string,
): Resultado<{ despesa: Despesa; cadeia: readonly Papel[]; eventos: readonly Evento[] }, ErroDominio> {
  const despesa = amb.repos.despesas.porId(despesaId);
  if (!despesa) return falha(naoEncontrado("Despesa"));
  const cadeia = cadeiaDe(amb, despesa);
  if (!cadeia.ok) return falha(cadeia.erro);
  return ok({ despesa, cadeia: cadeia.valor, eventos: amb.repos.trilha.porDespesa(despesaId) });
}

/** Autoridade que o usuário exerceria sobre esta despesa agora — a tela T4 exige exibi-la. */
export function autoridadeSobre(
  amb: Ambiente,
  despesaId: string,
  usuarioId: string,
): Resultado<autoridade.Autoridade, ErroDominio> {
  const despesa = amb.repos.despesas.porId(despesaId);
  const usuario = amb.repos.usuarios.porId(usuarioId);
  if (!despesa || !usuario) return falha(naoEncontrado("Despesa ou usuário"));
  if (despesa.indiceCadeia === null) return falha(erro("NAO_PENDENTE", "Esta despesa já foi encerrada."));
  const cadeia = cadeiaDe(amb, despesa);
  if (!cadeia.ok) return falha(cadeia.erro);
  return autoridade.resolver(
    contexto(amb, despesa, cadeia.valor, despesa.indiceCadeia, amb.relogio.agora()),
    usuario,
  );
}
