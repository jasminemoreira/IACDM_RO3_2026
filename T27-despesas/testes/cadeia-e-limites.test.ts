/** CA-1, CA-2, CA-7 e INV-12/INV-14 — a cadeia, a fronteira da alçada e a matriz. */
import { describe, it, expect } from "vitest";
import { montar, precisa, erroDe } from "./ajuda.js";
import * as uc from "../src/app/casos-de-uso.js";
import { cadeiaPara, validar, reaisParaCentavos } from "../src/dominio/matriz-doa.js";
import { SEED_PAPEIS, SEED_USUARIOS } from "../src/adaptadores/sqlite.js";

describe("CA-1 — a despesa percorre exatamente os níveis da cadeia que têm decisor", () => {
  it("D-1: Coordenador pede R$100 → cadeia [gerente], uma aprovação encerra", () => {
    const b = montar();
    const cadeia = precisa(cadeiaPara(b.matriz, 10_000, "coordenador"));
    expect(cadeia.map((p) => p.id)).toEqual(["gerente"]);

    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 10_000, descricao: "Café" }));
    const aprovada = precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "carla" }));
    expect(aprovada.estado).toBe("APROVADA");
  });

  it("D-2: Coordenador pede R$80k → cadeia [gerente, diretor], duas aprovações", () => {
    const b = montar();
    const cadeia = precisa(cadeiaPara(b.matriz, 8_000_000, "coordenador"));
    expect(cadeia.map((p) => p.id)).toEqual(["gerente", "diretor"]);

    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "Servidor" }));
    const apos1 = precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "carla" }));
    expect(apos1.estado).toBe("PENDENTE"); // negativo: um nível NÃO encerra a cadeia
    const apos2 = precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "elisa" }));
    expect(apos2.estado).toBe("APROVADA");

    const aprovacoes = b.repos.trilha.porDespesa(d.id).filter((e) => e.tipo === "APROVADA_NIVEL");
    expect(aprovacoes.map((e) => e.nivel)).toEqual([2, 3]);
  });

  it("a cadeia começa ACIMA do papel do solicitante — um Gerente não passa por Coordenador", () => {
    const b = montar();
    expect(precisa(cadeiaPara(b.matriz, 8_000_000, "gerente")).map((p) => p.id)).toEqual(["diretor"]);
  });

  it("a cadeia NUNCA é vazia quando o valor cabe na alçada do próprio papel do solicitante", () => {
    // Regressão do achado 🔴 IMP-06: em V(2) a fórmula produzia cadeia vazia aqui.
    const b = montar();
    const cadeia = precisa(cadeiaPara(b.matriz, 10_000, "coordenador"));
    expect(cadeia.length).toBeGreaterThan(0);
  });
});

describe("CA-2 — fronteira inclusiva da alçada", () => {
  it("D-3: valor EXATAMENTE igual ao limite encerra naquele papel", () => {
    const b = montar();
    expect(precisa(cadeiaPara(b.matriz, 5_000_000, "coordenador")).map((p) => p.id)).toEqual(["gerente"]);

    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 5_000_000, descricao: "No limite" }));
    expect(precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "carla" })).estado).toBe("APROVADA");
  });

  it("D-4 (negativo): um centavo acima do limite escala para o nível seguinte", () => {
    const b = montar();
    expect(precisa(cadeiaPara(b.matriz, 5_000_001, "coordenador")).map((p) => p.id)).toEqual(["gerente", "diretor"]);
  });
});

describe("CA-7 — despesa sem cadeia possível é recusada na criação", () => {
  it("D-5 (negativo): R$2 milhões excede o maior limite acima do solicitante", () => {
    const b = montar();
    const e = erroDe(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 200_000_000, descricao: "x" }));
    expect(e.codigo).toBe("ACIMA_DO_TETO");
    expect(b.repos.despesas.todas()).toHaveLength(0);
  });

  it("D-6 (negativo): solicitante no topo da hierarquia não tem autoridade acima", () => {
    const b = montar();
    const e = erroDe(uc.solicitar(b.amb, { solicitanteId: "elisa", valorCentavos: 100_000, descricao: "x" }));
    expect(e.codigo).toBe("SEM_AUTORIDADE_ACIMA");
    expect(b.repos.despesas.todas()).toHaveLength(0);
  });
});

describe("INV-14 (negativo) — matriz inválida impede a carga", () => {
  it("recusa níveis não contíguos", () => {
    const e = erroDe(
      validar(
        [
          { id: "a", nome: "A", nivel: 1, limiteCentavos: 100 },
          { id: "c", nome: "C", nivel: 3, limiteCentavos: 300 },
        ],
        [],
      ),
    );
    expect(e.codigo).toBe("NIVEIS_NAO_CONTIGUOS");
  });

  it("recusa limites que não crescem com o nível", () => {
    const e = erroDe(
      validar(
        [
          { id: "a", nome: "A", nivel: 1, limiteCentavos: 500 },
          { id: "b", nome: "B", nivel: 2, limiteCentavos: 100 },
        ],
        [],
      ),
    );
    expect(e.codigo).toBe("LIMITES_NAO_CRESCENTES");
  });

  it("recusa usuário apontando para papel inexistente", () => {
    const e = erroDe(validar(SEED_PAPEIS, [{ id: "x", papelId: "presidente" }]));
    expect(e.codigo).toBe("USUARIO_SEM_PAPEL");
  });

  it("aceita o seed real do sistema", () => {
    expect(validar(SEED_PAPEIS, SEED_USUARIOS).ok).toBe(true);
  });
});

describe("INV-12 — dinheiro é inteiro de centavos, sem ponto flutuante", () => {
  it("converte por parsing de string, não por parseFloat × 100", () => {
    expect(precisa(reaisParaCentavos("19,99"))).toBe(1999);
    expect(precisa(reaisParaCentavos("50.000,00"))).toBe(5_000_000);
    expect(precisa(reaisParaCentavos("80.000,00"))).toBe(8_000_000);
    expect(precisa(reaisParaCentavos("R$ 1.234,56"))).toBe(123_456);
    // A armadilha que specs/examples nomeia: parseFloat("19.99")*100 === 1998.9999999999998
    expect(precisa(reaisParaCentavos("19,99"))).not.toBe(parseFloat("19.99") * 100);
  });

  it("(negativo) recusa valor mal formado", () => {
    expect(reaisParaCentavos("abc").ok).toBe(false);
    expect(reaisParaCentavos("1,234").ok).toBe(false);
  });
});
