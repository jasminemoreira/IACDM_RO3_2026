/**
 * M-02 matriz-doa — papéis, níveis, limites e a cadeia de aprovação.
 * Guarda INV-1 (fronteira inclusiva), INV-10 (acima do teto), INV-13 (solicitante no topo),
 * INV-14 (matriz válida na carga).
 *
 * V(3)/S1.3: a assinatura NÃO recebe `titulares` — este módulo é domínio puro e não sabe
 * de pessoas (achado ARQ-06). Quem sabe de gente é `autoridade` (M-04).
 * INV-15 está REVOGADA: a regra de pular nível sem decisor vive em `casos-de-uso` + M-04.
 */
import { type ErroDominio, type Resultado, erro, falha, ok } from "./resultado.js";

export type Papel = {
  readonly id: string;
  readonly nome: string;
  readonly nivel: number;
  readonly limiteCentavos: number;
};

/** Marca de tipo: só sai de `validar`, portanto ninguém usa uma matriz não verificada. */
export type MatrizValida = { readonly papeis: readonly Papel[] };

/**
 * INV-14 — verificada UMA vez na carga; o processo não sobe se falhar (achado A-01: um seed
 * com níveis 1 e 3, ou dois papéis no mesmo nível, produzia cadeia errada em silêncio).
 * V(4)/T5: cobre também o seed de usuários (achado A-10).
 */
export function validar(
  papeis: readonly Papel[],
  usuarios: readonly { id: string; papelId: string }[],
): Resultado<MatrizValida, ErroDominio> {
  if (papeis.length === 0) return falha(erro("MATRIZ_VAZIA", "A matriz DoA não tem nenhum papel."));

  const ordenados = [...papeis].sort((a, b) => a.nivel - b.nivel);

  for (let i = 0; i < ordenados.length; i++) {
    const p = ordenados[i]!;
    if (p.nivel !== i + 1) {
      return falha(
        erro(
          "NIVEIS_NAO_CONTIGUOS",
          `Os níveis da matriz devem ser contíguos a partir de 1; encontrei ${p.nivel} na posição ${i + 1}.`,
        ),
      );
    }
    if (!Number.isInteger(p.limiteCentavos) || p.limiteCentavos <= 0) {
      return falha(erro("LIMITE_INVALIDO", `O limite de ${p.nome} precisa ser um inteiro positivo de centavos.`));
    }
    const anterior = ordenados[i - 1];
    if (anterior && p.limiteCentavos <= anterior.limiteCentavos) {
      return falha(
        erro(
          "LIMITES_NAO_CRESCENTES",
          `O limite de ${p.nome} (nível ${p.nivel}) não é maior que o de ${anterior.nome} (nível ${anterior.nivel}).`,
        ),
      );
    }
  }

  for (const u of usuarios) {
    if (!ordenados.some((p) => p.id === u.papelId)) {
      return falha(
        erro("USUARIO_SEM_PAPEL", `O usuário ${u.id} aponta para o papel inexistente ${u.papelId}.`),
      );
    }
  }

  return ok({ papeis: ordenados });
}

export function porId(matriz: MatrizValida, papelId: string): Papel | undefined {
  return matriz.papeis.find((p) => p.id === papelId);
}

export function limiteDe(matriz: MatrizValida, papelId: string): number | undefined {
  return porId(matriz, papelId)?.limiteCentavos;
}

/**
 * A cadeia de aprovação — V(3)/S1.1, depois do achado 🔴 IMP-06.
 *
 * cadeia(valor, papelSolicitante) = papéis de nível ESTRITAMENTE ACIMA do solicitante,
 * em ordem crescente, até e incluindo o primeiro cujo limite cobre o valor (INV-1, `<=`).
 *
 * A âncora "acima do solicitante" é o que V(2) errava: com `p*` ancorado no menor papel da
 * matriz que cobre o valor, uma despesa de R$100 pedida por um Coordenador (limite R$5.000)
 * produzia cadeia VAZIA — despesa sem nenhum aprovador. A cadeia aqui nunca é vazia: ou tem
 * ao menos um papel, ou o retorno é erro.
 */
export function cadeiaPara(
  matriz: MatrizValida,
  valorCentavos: number,
  papelSolicitanteId: string,
): Resultado<readonly Papel[], ErroDominio> {
  const solicitante = porId(matriz, papelSolicitanteId);
  if (!solicitante) {
    return falha(erro("PAPEL_DESCONHECIDO", `Papel ${papelSolicitanteId} não existe na matriz.`));
  }

  const acima = matriz.papeis.filter((p) => p.nivel > solicitante.nivel);

  // INV-13: quem ocupa o topo não tem autoridade acima de si.
  if (acima.length === 0) {
    const topo = matriz.papeis[matriz.papeis.length - 1]!;
    return falha(
      erro(
        "SEM_AUTORIDADE_ACIMA",
        `Você é ${topo.nome} e não há papel acima do seu para aprovar. ` +
          `Esta despesa precisa ser autorizada fora do sistema.`,
      ),
    );
  }

  const indiceCobre = acima.findIndex((p) => valorCentavos <= p.limiteCentavos);

  // INV-10: nenhum papel acima cobre o valor — não existe cadeia possível.
  if (indiceCobre === -1) {
    const maior = acima[acima.length - 1]!;
    return falha(
      erro(
        "ACIMA_DO_TETO",
        `${formatarBRL(valorCentavos)} excede o maior limite disponível acima de você ` +
          `(${formatarBRL(maior.limiteCentavos)}, ${maior.nome}). Nenhuma cadeia de aprovação pode ` +
          `autorizar este valor — divida em despesas menores ou trate fora do sistema.`,
      ),
    );
  }

  return ok(acima.slice(0, indiceCobre + 1));
}

export function formatarBRL(centavos: number): string {
  const sinal = centavos < 0 ? "-" : "";
  const abs = Math.abs(centavos);
  const reais = Math.floor(abs / 100).toString();
  const cents = (abs % 100).toString().padStart(2, "0");
  const comMilhar = reais.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${sinal}R$ ${comMilhar},${cents}`;
}

/**
 * Conversão de reais para centavos por parsing de string (achado do módulo M-11 em
 * specs/examples): `parseFloat(x) * 100` erra em valores como 19,99.
 */
export function reaisParaCentavos(bruto: string): Resultado<number, ErroDominio> {
  const limpo = bruto.trim().replace(/^R\$\s*/i, "").replace(/\s/g, "");
  if (!/^\d{1,3}(\.\d{3})*(,\d{1,2})?$|^\d+(,\d{1,2})?$|^\d+(\.\d{1,2})?$/.test(limpo)) {
    return falha(erro("VALOR_MAL_FORMADO", `Não entendi o valor "${bruto}". Use por exemplo 50.000,00 ou 1234,56.`));
  }
  let inteiro: string;
  let decimal = "00";
  if (limpo.includes(",")) {
    const [i, d] = limpo.split(",") as [string, string];
    inteiro = i.replace(/\./g, "");
    decimal = d.padEnd(2, "0");
  } else if (/^\d+\.\d{1,2}$/.test(limpo)) {
    const [i, d] = limpo.split(".") as [string, string];
    inteiro = i;
    decimal = d.padEnd(2, "0");
  } else {
    inteiro = limpo.replace(/\./g, "");
  }
  return ok(Number(inteiro) * 100 + Number(decimal));
}
