/** CA-1b, CA-1c, CA-8, CA-9, CA-10 e D-22 — regra do pulo, rejeição, trilha, restart, conflito. */
import { describe, it, expect } from "vitest";
import { montar, precisa, erroDe, USUARIOS_SEM_GERENTE, USUARIOS_SO_COORDENADORES, T0 } from "./ajuda.js";
import * as uc from "../src/app/casos-de-uso.js";
import { abrir, SEED_PAPEIS, SEED_USUARIOS } from "../src/adaptadores/sqlite.js";
import { validar } from "../src/dominio/matriz-doa.js";
import { relogioControlavel } from "../src/dominio/relogio.js";
import { unlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

describe("CA-1b — nível intermediário sem decisor é pulado, e o pulo vai para a trilha", () => {
  it("D-20: empresa sem nenhum Gerente → o Diretor aprova sozinho", () => {
    const b = montar({ usuarios: USUARIOS_SEM_GERENTE });
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "Servidor" }));

    // A cadeia continua sendo [gerente, diretor]; o nível 2 é pulado por falta de decisor.
    const aprovada = precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "elisa" }));
    expect(aprovada.estado).toBe("APROVADA");

    const eventos = b.repos.trilha.porDespesa(d.id);
    const pulo = eventos.find((e) => e.tipo === "NIVEL_PULADO");
    expect(pulo).toBeDefined();
    expect(pulo!.nivel).toBe(2);
    expect(pulo!.motivo).toMatch(/nenhum titular/i);
    expect(eventos.filter((e) => e.tipo === "APROVADA_NIVEL")).toHaveLength(1);
  });
});

describe("CA-1c — nenhum nível com decisor recusa a criação (INV-17/INV-18)", () => {
  it("D-21 (negativo): empresa só de Coordenadores", () => {
    const b = montar({ usuarios: USUARIOS_SO_COORDENADORES });
    const e = erroDe(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "x" }));
    expect(e.codigo).toBe("SEM_DECISOR");
    // A transação reverteu: nem a despesa nem os eventos de pulo persistiram.
    expect(b.repos.despesas.todas()).toHaveLength(0);
  });

  it("nenhuma despesa chega a APROVADA sem ao menos uma aprovação humana", () => {
    const b = montar({ usuarios: USUARIOS_SEM_GERENTE });
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "x" }));
    expect(precisa(uc.verTrilha(b.amb, d.id)).despesa.estado).toBe("PENDENTE");
    precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "elisa" }));
    const eventos = b.repos.trilha.porDespesa(d.id);
    expect(eventos.filter((e) => e.tipo === "APROVADA_NIVEL").length).toBeGreaterThanOrEqual(1);
  });
});

describe("CA-8 — rejeição", () => {
  it("D-16 (negativo): sem motivo é recusada", () => {
    const b = montar();
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "x" }));
    const e = erroDe(uc.rejeitar(b.amb, { despesaId: d.id, atuanteId: "carla", motivo: "   " }));
    expect(e.codigo).toBe("MOTIVO_AUSENTE");
    expect(precisa(uc.verTrilha(b.amb, d.id)).despesa.estado).toBe("PENDENTE");
  });

  it("D-17: com motivo encerra REJEITADA e não volta a nenhuma fila", () => {
    const b = montar();
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "x" }));
    const r = precisa(uc.rejeitar(b.amb, { despesaId: d.id, atuanteId: "carla", motivo: "sem verba" }));
    expect(r.estado).toBe("REJEITADA");

    for (const u of ["ana", "bruno", "carla", "dario", "elisa", "fabio"]) {
      expect(precisa(uc.verBandeja(b.amb, u)).map((i) => i.despesa.id)).not.toContain(d.id);
    }
    // INV-11: terminal. Nem o Diretor consegue reabrir.
    expect(erroDe(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "elisa" })).codigo).toBe("CONFLITO");
    expect(b.repos.trilha.porDespesa(d.id).find((e) => e.tipo === "REJEITADA")!.motivo).toBe("sem verba");
  });
});

describe("CA-9 — trilha completa e imutável", () => {
  it("D-18: recupera a sequência completa, na ordem", () => {
    const b = montar();
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "x" }));
    precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "carla" }));
    precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "elisa" }));

    expect(b.repos.trilha.porDespesa(d.id).map((e) => e.tipo)).toEqual([
      "CRIADA",
      "APROVADA_NIVEL",
      "APROVADA_NIVEL",
    ]);
  });

  it("(negativo) INV-8: não há caminho de alteração, e evento anterior não muda", () => {
    const b = montar();
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "x" }));
    const antes = JSON.stringify(b.repos.trilha.porDespesa(d.id)[0]);

    precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "carla" }));

    expect(JSON.stringify(b.repos.trilha.porDespesa(d.id)[0])).toBe(antes);
    // O contrato do repositório não expõe atualizar nem apagar.
    expect(Object.keys(b.repos.trilha).sort()).toEqual(["anexar", "porDespesa"]);
  });
});

describe("CA-10 — o estado sobrevive ao restart do processo", () => {
  it("D-19: mesma bandeja e mesma trilha depois de fechar e reabrir o banco", () => {
    const caminho = join(tmpdir(), `t27-teste-${process.pid}-${Date.now()}.db`);
    try {
      const repos1 = abrir(caminho);
      repos1.semear(SEED_PAPEIS, SEED_USUARIOS);
      const m = validar(repos1.papeis.todos(), repos1.usuarios.todos());
      if (!m.ok) throw new Error("seed inválido");
      let n = 0;
      const amb1 = { repos: repos1, matriz: m.valor, relogio: relogioControlavel(T0), novoId: () => `p-${++n}` };
      const d = precisa(uc.solicitar(amb1, { solicitanteId: "ana", valorCentavos: 8_000_000, descricao: "Persistente" }));
      precisa(uc.aprovar(amb1, { despesaId: d.id, atuanteId: "carla" }));
      repos1.fechar();

      const repos2 = abrir(caminho);
      const m2 = validar(repos2.papeis.todos(), repos2.usuarios.todos());
      if (!m2.ok) throw new Error("seed inválido após restart");
      const amb2 = { repos: repos2, matriz: m2.valor, relogio: relogioControlavel(T0), novoId: () => "x" };

      expect(precisa(uc.verBandeja(amb2, "elisa")).map((i) => i.despesa.id)).toContain(d.id);
      expect(repos2.trilha.porDespesa(d.id).map((e) => e.tipo)).toEqual(["CRIADA", "APROVADA_NIVEL"]);
      repos2.fechar();
    } finally {
      for (const sufixo of ["", "-wal", "-shm"]) {
        try {
          unlinkSync(caminho + sufixo);
        } catch {
          /* arquivo pode não existir */
        }
      }
    }
  });
});

describe("D-22 (negativo) — duas decisões no mesmo item", () => {
  it("a segunda encontra o estado já mudado e falha com conflito determinístico", () => {
    const b = montar();
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "x" }));
    precisa(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "carla" })); // encerra: cadeia de 1 nível
    const e = erroDe(uc.aprovar(b.amb, { despesaId: d.id, atuanteId: "dario" }));
    expect(e.codigo).toBe("CONFLITO");
    expect(e.mensagem).toMatch(/outra pessoa decidiu antes/i);
  });
});
