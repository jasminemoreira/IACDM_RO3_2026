/**
 * Fumaça de UI via `fastify.inject()` — ferramenta escolhida pelo operador na Fase 6.
 * Exercita rota, nonce anti-CSRF, redirecionamento e o HTML efetivamente renderizado.
 * Não cobre layout visual: isso é o gate manual humano, que continua obrigatório.
 */
import { describe, it, expect } from "vitest";
import { montar, precisa } from "./ajuda.js";
import { criarServidor } from "../src/api/http.js";
import * as uc from "../src/app/casos-de-uso.js";
import { html, escapar, paraString } from "../src/ui/render.js";

function nonceDe(cabecalho: string | string[] | undefined): string {
  const bruto = Array.isArray(cabecalho) ? cabecalho[0]! : (cabecalho ?? "");
  return /t27_nonce=([^;]+)/.exec(bruto)?.[1] ?? "";
}

describe("fluxo pela UI — do formulário até APROVADA", () => {
  it("UC-1 → UC-2 de ponta a ponta por HTTP", async () => {
    const b = montar();
    const app = criarServidor(b.amb);

    const inicial = await app.inject({ method: "GET", url: "/nova?u=ana" });
    expect(inicial.statusCode).toBe(200);
    const nonce = nonceDe(inicial.headers["set-cookie"]);
    expect(nonce).not.toBe("");
    const cookie = `t27_nonce=${nonce}`;

    const criacao = await app.inject({
      method: "POST",
      url: "/despesas",
      headers: { cookie },
      payload: { u: "ana", nonce, valor: "80.000,00", descricao: "Servidor de backup" },
    });
    expect(criacao.statusCode).toBe(302);
    const id = /\/despesas\/([^?]+)/.exec(criacao.headers["location"] as string)![1]!;

    const bandejaCarla = await app.inject({ method: "GET", url: `/bandeja?u=carla`, headers: { cookie } });
    expect(bandejaCarla.body).toContain("Servidor de backup");
    const bandejaAna = await app.inject({ method: "GET", url: `/bandeja?u=ana`, headers: { cookie } });
    expect(bandejaAna.body).toContain("Nenhuma pendência");

    // UX-01: a tela de decisão diz sob QUAL autoridade se está agindo, antes do clique.
    const detalhe = await app.inject({ method: "GET", url: `/despesas/${id}?u=carla`, headers: { cookie } });
    expect(detalhe.body).toContain("autoridade própria");
    expect(detalhe.body).toContain("R$ 50.000,00");

    for (const quem of ["carla", "elisa"]) {
      const r = await app.inject({
        method: "POST",
        url: `/despesas/${id}/aprovar`,
        headers: { cookie },
        payload: { u: quem, nonce },
      });
      expect(r.statusCode).toBe(302);
    }
    const final = await app.inject({ method: "GET", url: `/despesas/${id}?u=elisa`, headers: { cookie } });
    expect(final.body).toContain("APROVADA");
    await app.close();
  });

  it("UX-01 — decidindo por delegação, a tela nomeia o delegante e a alçada exercida", async () => {
    const b = montar();
    precisa(
      uc.delegar(b.amb, {
        deleganteId: "carla",
        delegadoId: "bruno",
        inicio: "2026-08-11T00:00:00.000Z",
        fim: "2026-08-20T00:00:00.000Z",
      }),
    );
    const d = precisa(uc.solicitar(b.amb, { solicitanteId: "ana", valorCentavos: 800_000, descricao: "Consultoria" }));
    const app = criarServidor(b.amb);
    const g = await app.inject({ method: "GET", url: `/despesas/${d.id}?u=bruno` });
    expect(g.body).toContain("EM NOME DE");
    expect(g.body).toContain("Carla Dias");
    expect(g.body).toContain("R$ 50.000,00");
    await app.close();
  });
});

describe("(negativo) anti-CSRF — o nonce do cookie precisa bater com o do formulário", () => {
  it("recusa POST com nonce divergente", async () => {
    const b = montar();
    const app = criarServidor(b.amb);
    const inicial = await app.inject({ method: "GET", url: "/nova?u=ana" });
    const cookie = `t27_nonce=${nonceDe(inicial.headers["set-cookie"])}`;

    const r = await app.inject({
      method: "POST",
      url: "/despesas",
      headers: { cookie },
      payload: { u: "ana", nonce: "valor-adivinhado", valor: "100,00", descricao: "x" },
    });
    expect(r.statusCode).toBe(403);
    expect(b.repos.despesas.todas()).toHaveLength(0);
    await app.close();
  });

  it("recusa POST sem cookie nenhum", async () => {
    const b = montar();
    const app = criarServidor(b.amb);
    const r = await app.inject({
      method: "POST",
      url: "/despesas",
      payload: { u: "ana", nonce: "qualquer", valor: "100,00", descricao: "x" },
    });
    expect(r.statusCode).toBe(403);
    await app.close();
  });
});

describe("(negativo) SEC-04 — a renderização escapa dado vindo do usuário", () => {
  it("descrição com HTML sai escapada, e sub-template Html não", () => {
    const perigo = '<script>alert("xss")</script>';
    expect(paraString(html`<p>${perigo}</p>`)).toBe(`<p>${escapar(perigo)}</p>`);
    expect(paraString(html`<p>${perigo}</p>`)).not.toContain("<script>");

    const filho = html`<b>ok</b>`;
    expect(paraString(html`<p>${filho}</p>`)).toBe("<p><b>ok</b></p>");
  });

  it("a descrição maliciosa chega escapada na página de detalhe", async () => {
    const b = montar();
    const d = precisa(
      uc.solicitar(b.amb, {
        solicitanteId: "ana",
        valorCentavos: 800_000,
        descricao: '<img src=x onerror="alert(1)">',
      }),
    );
    const app = criarServidor(b.amb);
    const g = await app.inject({ method: "GET", url: `/despesas/${d.id}?u=carla` });
    expect(g.body).not.toContain("<img src=x");
    expect(g.body).toContain("&lt;img src=x");
    await app.close();
  });
});

describe("(negativo) identidade inexistente é tratada em ponto único", () => {
  it("usuário desconhecido cai na tela de seleção, não em erro cru", async () => {
    const b = montar();
    const app = criarServidor(b.amb);
    const r = await app.inject({ method: "GET", url: "/bandeja?u=ninguem" });
    expect(r.statusCode).toBe(400);
    expect(r.body).toContain("Quem é você");
    await app.close();
  });
});
