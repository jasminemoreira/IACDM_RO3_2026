/**
 * M-05 bandeja — a fila de um aprovador: pendências próprias + recebidas por delegação.
 * FIFO por `criadaEm` (mais antiga primeiro), valor e origem visíveis.
 *
 * V(2)/R8 + V(3): duas dependências — `autoridade` e os repositórios. A responsabilidade é
 * uma só: filtrar as pendentes por "este usuário decide este item agora?", que é exatamente
 * a definição única de decidível (V(4)/T1).
 *
 * V(3)/S2 — delegação é CAMINHO ADICIONAL, não transferência de posse: quando o delegado é
 * inelegível para um item específico (INV-2 ou INV-4), `resolver` falha para ele e o item
 * continua aparecendo para o delegante. É o que fecha PROC-06 e o que CA-3b verifica.
 */
import type { Despesa } from "./despesa.js";
import type { Delegacao } from "./delegacao.js";
import type { MatrizValida, Papel } from "./matriz-doa.js";
import type { Usuario } from "./portas.js";
import type { Evento } from "./trilha.js";
import type { Instante } from "./resultado.js";
import { cadeiaPara } from "./matriz-doa.js";
import { resolver } from "./autoridade.js";
import { decisoes as apenasDecisoes } from "./trilha.js";

export type ItemBandeja = {
  readonly despesa: Despesa;
  readonly papelDoNivel: Papel;
  readonly origem: { tipo: "propria" } | { tipo: "delegada"; emNomeDe: Usuario; delegacaoId: string };
  readonly limiteExercidoCentavos: number;
};

export type Fontes = {
  readonly matriz: MatrizValida;
  readonly pendentes: readonly Despesa[];
  readonly usuarios: readonly Usuario[];
  readonly delegacoes: readonly Delegacao[];
  readonly eventosDe: (despesaId: string) => readonly Evento[];
};

export function listar(fontes: Fontes, usuario: Usuario, instante: Instante): readonly ItemBandeja[] {
  const itens: ItemBandeja[] = [];

  for (const despesa of fontes.pendentes) {
    if (despesa.indiceCadeia === null) continue;

    const solicitante = fontes.usuarios.find((u) => u.id === despesa.solicitanteId);
    if (!solicitante) continue;

    const cadeia = cadeiaPara(fontes.matriz, despesa.valorCentavos, solicitante.papelId);
    if (!cadeia.ok) continue;

    const papelDoNivel = cadeia.valor[despesa.indiceCadeia];
    if (!papelDoNivel) continue;

    const r = resolver(
      {
        despesa,
        indice: despesa.indiceCadeia,
        cadeia: cadeia.valor,
        usuarios: fontes.usuarios,
        decisoes: apenasDecisoes(fontes.eventosDe(despesa.id)),
        delegacoes: fontes.delegacoes,
        instante,
      },
      usuario,
    );
    if (!r.ok) continue;

    itens.push({
      despesa,
      papelDoNivel,
      origem: r.valor.emNomeDe
        ? { tipo: "delegada", emNomeDe: r.valor.emNomeDe, delegacaoId: r.valor.delegacaoId! }
        : { tipo: "propria" },
      limiteExercidoCentavos: r.valor.limiteExercidoCentavos,
    });
  }

  // FIFO: mais antiga primeiro. Ordem determinística — nada envelhece esquecido no fim.
  return itens.sort((a, b) =>
    a.despesa.criadaEm === b.despesa.criadaEm
      ? a.despesa.id.localeCompare(b.despesa.id)
      : a.despesa.criadaEm.localeCompare(b.despesa.criadaEm),
  );
}
