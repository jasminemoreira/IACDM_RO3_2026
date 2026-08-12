/**
 * M-04 autoridade — "quem pode decidir este item agora e sob qual autoridade".
 * Único ponto onde alçada e delegação se cruzam.
 * Guarda INV-2 (auto-aprovação), INV-4 (duplo voto), INV-6 (autoridade no instante do ato),
 * INV-17 e INV-18 (contenção da regra do pulo).
 *
 * V(4)/T1 — DEFINIÇÃO ÚNICA: um nível é DECIDÍVEL por `u` no instante `t` se e somente se
 * `resolver` devolve sucesso para `u`. Não existe segundo conceito de elegibilidade em lugar
 * nenhum do sistema; era a falta dessa definição que gerava LING-07, A-09 e ARQ-08. Por isso
 * `algumDecisor` mora AQUI, no domínio, e não em `casos-de-uso`.
 *
 * ARQ-01: não depende de `trilha` — recebe as decisões por parâmetro, permanecendo testável
 * sem banco.
 *
 * Estrutura portada de DW-RBAC (Wainer & Kumar), construção *execution*: a autoridade efetiva
 * de um ator sobre um ato é a união da autoridade própria com a delegada VIGENTE NAQUELE
 * INSTANTE, verificada no ato e não na entrada na fila. Ver specs/technical/dw-rbac-mapeamento.md.
 */
import type { Despesa } from "./despesa.js";
import type { Delegacao } from "./delegacao.js";
import type { Papel } from "./matriz-doa.js";
import type { Usuario } from "./portas.js";
import type { Evento } from "./trilha.js";
import { type ErroDominio, type Instante, type Resultado, erro, falha, ok } from "./resultado.js";
import { vigentes } from "./delegacao.js";

export type Autoridade = {
  /** null quando o ator decide por autoridade própria. */
  readonly emNomeDe: Usuario | null;
  readonly delegacaoId: string | null;
  readonly limiteExercidoCentavos: number;
};

export type Contexto = {
  readonly despesa: Despesa;
  /** Índice explícito: `algumDecisor` precisa perguntar por níveis que não são o corrente. */
  readonly indice: number;
  readonly cadeia: readonly Papel[];
  readonly usuarios: readonly Usuario[];
  /** Decisões humanas já registradas para esta despesa (INV-4). */
  readonly decisoes: readonly Evento[];
  readonly delegacoes: readonly Delegacao[];
  readonly instante: Instante;
};

export function resolver(ctx: Contexto, atuante: Usuario): Resultado<Autoridade, ErroDominio> {
  return resolverInterno(ctx, atuante, true);
}

/**
 * `aplicarTransferencia` desliga a regra de posse ao perguntar "o delegado conseguiria
 * decidir?", o que evita recursão mútua: o delegado nunca é avaliado pelo ramo de autoridade
 * própria deste item.
 */
function resolverInterno(
  ctx: Contexto,
  atuante: Usuario,
  aplicarTransferencia: boolean,
): Resultado<Autoridade, ErroDominio> {
  const { despesa, indice, cadeia, decisoes, instante } = ctx;

  if (despesa.estado !== "PENDENTE") {
    return falha(erro("NAO_PENDENTE", `Esta despesa já está ${despesa.estado.toLowerCase()}.`));
  }
  const papelDoNivel = cadeia[indice];
  if (!papelDoNivel) {
    return falha(erro("NIVEL_INEXISTENTE", "Este nível não existe na cadeia desta despesa."));
  }

  // INV-2 — vale para o ATOR EFETIVO, inclusive quando ele ocuparia o nível por delegação.
  if (atuante.id === despesa.solicitanteId) {
    return falha(
      erro(
        "AUTO_APROVACAO",
        "Você é o solicitante desta despesa e não pode aprová-la, nem em nome de outra pessoa.",
      ),
    );
  }

  // INV-4 — princípio dos quatro olhos: sem isto, uma cadeia de dois níveis exercida pela
  // mesma pessoa via delegação seria uma aprovação única disfarçada.
  const jaDecidiu = decisoes.find((d) => d.atorId === atuante.id);
  if (jaDecidiu) {
    return falha(
      erro(
        "DUPLO_VOTO",
        `Você já decidiu o nível ${jaDecidiu.nivel} desta despesa. Um mesmo aprovador não pode ` +
          `decidir dois níveis da mesma cadeia — ela precisa de outra pessoa.`,
      ),
    );
  }

  const ativas = vigentes(ctx.delegacoes, instante);

  // Autoridade própria — com a regra de posse de CA-3.
  if (atuante.papelId === papelDoNivel.id) {
    if (aplicarTransferencia) {
      const minha = ativas.find((d) => d.deleganteId === atuante.id);
      const delegado = minha ? ctx.usuarios.find((u) => u.id === minha.delegadoId) : undefined;
      // CA-3: com delegação vigente, o item SAI da bandeja do delegante.
      // CA-3b (exceção aprovada pelo operador): se o delegado é inelegível para ESTE item
      // por INV-2 ou INV-4, a delegação é inócua aqui e o item permanece com o delegante —
      // sem isso ele ficaria órfão (achado PROC-06).
      if (minha && delegado && resolverInterno(ctx, delegado, false).ok) {
        return falha(
          erro(
            "DELEGADA",
            `Você delegou sua autoridade a ${delegado.nome} até ${minha.fim.slice(0, 10)}; ` +
              `este item está na bandeja dele(a).`,
          ),
        );
      }
    }
    return ok({ emNomeDe: null, delegacaoId: null, limiteExercidoCentavos: papelDoNivel.limiteCentavos });
  }

  // Autoridade delegada, vigente NESTE instante (INV-6). Não é transitiva (INV-3): a busca
  // olha só delegações cujo DELEGANTE ocupa o papel do nível — nunca encadeia.
  for (const d of ativas) {
    if (d.delegadoId !== atuante.id) continue;
    const delegante = ctx.usuarios.find((u) => u.id === d.deleganteId);
    if (!delegante || delegante.papelId !== papelDoNivel.id) continue;
    return ok({
      emNomeDe: delegante,
      delegacaoId: d.id,
      limiteExercidoCentavos: papelDoNivel.limiteCentavos,
    });
  }

  return falha(
    erro(
      "SEM_AUTORIDADE",
      `Esta despesa aguarda decisão de ${papelDoNivel.nome}, e você não exerce essa alçada ` +
        `nem por autoridade própria nem por delegação vigente.`,
    ),
  );
}

/**
 * V(4)/T1 — a mesma definição, aplicada ao conjunto: existe ALGUÉM que decide este nível?
 * Usada na criação (INV-17) e a cada avanço da cadeia (regra do pulo). Um nível é pulado
 * quando isto é falso, seja por papel vago, por INV-2 ou por INV-4 — uma regra só.
 */
export function algumDecisor(ctx: Contexto): boolean {
  return ctx.usuarios.some((u) => resolver(ctx, u).ok);
}

/** Por que o nível foi pulado — vai para a trilha (achado GOV-06). */
export function motivoDoPulo(ctx: Contexto): string {
  const papel = ctx.cadeia[ctx.indice];
  if (!papel) return "nível inexistente";
  const titulares = ctx.usuarios.filter((u) => u.papelId === papel.id);
  if (titulares.length === 0) return `nenhum titular do papel ${papel.nome}`;
  return `nenhum titular de ${papel.nome} é decisor elegível (solicitante ou já decidiu outro nível)`;
}
