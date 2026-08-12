/** CA-3, CA-3b, CA-4, CA-5, CA-6 — delegação, posse do item e as quatro invariantes SoD. */
import { describe, it, expect } from "vitest";
import { montar, precisa, erroDe, dias, T0 } from "./ajuda.js";
import * as uc from "../src/app/casos-de-uso.js";

const HOJE = T0.slice(0, 10);
const emDias = (n: number) => new Date(Date.parse(T0) + dias(n)).toISOString().slice(0, 10) + "T00:00:00.000Z";

function comDelegacao(b: ReturnType<typeof montar>, de: string, para: string, ate = 3) {
  return precisa(
    uc.delegar(b.amb, { deleganteId: de, delegadoId: para, inicio: `${HOJE}T00:00:00.000Z`, fim: emDias(ate) }),
  );
}
const idsNaBandeja = (b: ReturnType<typeof montar>, u: string) =>
  precisa(uc.verBandeja(b.amb, u)).map((i) => i.despesa.id);

describe("CA-3 — a delegação move o item para o delegado", () => {
  it("D-7: item aparece na bandeja de B e NÃO na de A", () => {
    const b = montar();
    comDelegacao(b, "carla", "bruno");
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "Consultoria" }));

    expect(idsNaBandeja(b, "bruno")).toContain(d.id);
    expect(idsNaBandeja(b, "carla")).not.toContain(d.id);
    // O outro Gerente, que não delegou, continua vendo — ele exerce a própria alçada.
    expect(idsNaBandeja(b, "dario")).toContain(d.id);
  });

  it("CA-3b / D-8 (negativo): delegado inelegível por INV-2 mantém o item com o delegante", () => {
    const b = montar();
    comDelegacao(b, "carla", "ana"); // ana será a solicitante
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "Consultoria" }));

    expect(idsNaBandeja(b, "ana")).not.toContain(d.id);
    expect(idsNaBandeja(b, "carla")).toContain(d.id); // sem isto, o item ficaria órfão (PROC-06)
  });
});

describe("CA-4 — a decisão delegada registra sob qual autoridade foi tomada", () => {
  it("D-9: ator efetivo, em nome de, limite exercido e a delegação usada", () => {
    const b = montar();
    const del = comDelegacao(b, "carla", "bruno");
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "x" }));
    precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "bruno" }));

    const ev = b.repos.trilha.porDespesa(d.id).find((e) => e.tipo === "APROVADA_NIVEL")!;
    expect(ev.atorId).toBe("bruno");
    expect(ev.emNomeDeId).toBe("carla");
    expect(ev.limiteExercidoCentavos).toBe(5_000_000); // a alçada de CARLA, não a de bruno
    expect(ev.delegacaoId).toBe(del.id);
  });
});

describe("CA-5 — expiração e revogação devolvem o item; o que foi decidido permanece", () => {
  it("D-10: ao expirar a vigência, o item volta à bandeja do delegante", () => {
    const b = montar();
    comDelegacao(b, "carla", "bruno", 3);
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "x" }));
    expect(idsNaBandeja(b, "bruno")).toContain(d.id);

    b.relogio.avancar(dias(5));

    expect(idsNaBandeja(b, "bruno")).not.toContain(d.id);
    expect(idsNaBandeja(b, "carla")).toContain(d.id);
  });

  it("INV-6: decisão tomada DENTRO da vigência permanece válida depois dela", () => {
    const b = montar();
    comDelegacao(b, "carla", "bruno", 3);
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "x" }));
    precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "bruno" })); // nível gerente, em nome de carla

    b.relogio.avancar(dias(30)); // a delegação já expirou há muito

    const ev = b.repos.trilha.porDespesa(d.id).find((e) => e.tipo === "APROVADA_NIVEL")!;
    expect(ev.emNomeDeId).toBe("carla");
    expect(ev.limiteExercidoCentavos).toBe(5_000_000);
    // e a despesa seguiu a cadeia normalmente, sem regredir
    expect(precisa(uc.verTrilha(b.amb, d.id)).despesa.indiceCadeia).toBe(1);
  });

  it("D-11: revogação devolve o item imediatamente", () => {
    const b = montar();
    const del = comDelegacao(b, "carla", "bruno");
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "x" }));
    expect(idsNaBandeja(b, "bruno")).toContain(d.id);

    precisa(uc.revogar(b.amb, { delegacaoId: del.id, atuanteId: "carla", ehAdmin: false }));

    expect(idsNaBandeja(b, "bruno")).not.toContain(d.id);
    expect(idsNaBandeja(b, "carla")).toContain(d.id);
  });

  it("(negativo) só o delegante ou o Admin revogam", () => {
    const b = montar();
    const del = comDelegacao(b, "carla", "bruno");
    expect(erroDe(uc.revogar(b.amb, { delegacaoId: del.id, atuanteId: "dario", ehAdmin: false })).codigo).toBe(
      "NAO_AUTORIZADO",
    );
    expect(uc.revogar(b.amb, { delegacaoId: del.id, atuanteId: "elisa", ehAdmin: true }).ok).toBe(true);
  });
});

describe("CA-6 — cada invariante SoD bloqueia com mensagem própria", () => {
  it("D-12 (negativo) INV-2: ninguém aprova a própria despesa", () => {
    const b = montar();
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "carla", valorCentavos: 800_000, descricao: "x" }));
    // carla é Gerente; a cadeia começa acima dela (diretor). Ela delega e tenta decidir por si.
    const e = erroDe(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "carla" }));
    expect(["AUTO_APROVACAO", "SEM_AUTORIDADE"]).toContain(e.codigo);

    // O caso literal de INV-2: elisa delega a ana, e ana é a solicitante.
    const b2 = montar();
    comDelegacao(b2, "carla", "ana");
    const d2 = precisa(uc.solicitar(b2.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "y" }));
    const e2 = erroDe(uc.aprovar(b2.amb, { despesaId: d2.id, atuanteId: "ana" }));
    expect(e2.codigo).toBe("AUTO_APROVACAO");
    expect(e2.mensagem).toMatch(/solicitante/i);
  });

  it("D-13 (negativo) INV-4: o mesmo ator não decide dois níveis da mesma cadeia", () => {
    const b = montar();
    // elisa (diretora) delega à carla (gerente): carla decidiria o nível 2 e depois o 3.
    comDelegacao(b, "elisa", "carla");
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "x" }));
    precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "carla" })); // nível 2, autoridade própria

    const e = erroDe(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "carla" })); // nível 3, por delegação
    expect(e.codigo).toBe("DUPLO_VOTO");
    expect(e.mensagem).toMatch(/já decidiu/i);

    // PROC-06: e o item NÃO fica órfão — volta para elisa, a delegante.
    expect(idsNaBandeja(b, "elisa")).toContain(d.id);
  });

  it("D-14 (negativo) INV-3: quem exerce autoridade alheia não pode repassá-la", () => {
    const b = montar();
    comDelegacao(b, "carla", "bruno");
    const e = erroDe(
      uc.delegar(b.amb, { deleganteId: "bruno", delegadoId: "dario", inicio: `${HOJE}T00:00:00.000Z`, fim: emDias(2) }),
    );
    expect(e.codigo).toBe("REDELEGACAO");
  });

  it("D-15 (negativo) INV-5: vigências sobrepostas do mesmo delegante", () => {
    const b = montar();
    comDelegacao(b, "carla", "bruno", 5);
    const e = erroDe(
      uc.delegar(b.amb, { deleganteId: "carla", delegadoId: "dario", inicio: emDias(2), fim: emDias(7) }),
    );
    expect(e.codigo).toBe("VIGENCIAS_SOBREPOSTAS");
  });

  it("INV-16 (negativo): delegação antedatada é recusada", () => {
    const b = montar();
    const e = erroDe(
      uc.delegar(b.amb, { deleganteId: "carla", delegadoId: "bruno", inicio: emDias(-3), fim: emDias(2) }),
    );
    expect(e.codigo).toBe("ANTEDATADA");
  });

  it("as quatro mensagens de SoD são distintas — não um erro genérico", () => {
    const b = montar();
    const codigos = new Set<string>();

    comDelegacao(b, "carla", "ana");
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "x" }));
    codigos.add(erroDe(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "ana" })).codigo);
    codigos.add(
      erroDe(uc.delegar(b.amb, { deleganteId: "ana", delegadoId: "dario", inicio: `${HOJE}T00:00:00.000Z`, fim: emDias(2) }))
        .codigo,
    );
    codigos.add(
      erroDe(uc.delegar(b.amb, { deleganteId: "carla", delegadoId: "dario", inicio: `${HOJE}T00:00:00.000Z`, fim: emDias(2) }))
        .codigo,
    );

    const b2 = montar();
    comDelegacao(b2, "elisa", "carla");
    const d2 = precisa(uc.solicitar(b2.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "y" }));
    precisa(uc.aprovar(b2.amb, { despesaId: d2.id, atuanteId: "carla" }));
    codigos.add(erroDe(uc.aprovar(b2.amb, { despesaId: d2.id, atuanteId: "carla" })).codigo);

    expect(codigos).toEqual(new Set(["AUTO_APROVACAO", "REDELEGACAO", "VIGENCIAS_SOBREPOSTAS", "DUPLO_VOTO"]));
  });
});
