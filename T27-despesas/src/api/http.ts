/**
 * M-11 api-http — Fastify: rotas, resolução do usuário atuante em ponto único, limite de
 * corpo, tradução de erro de domínio para status HTTP.
 *
 * V(4)/T3: o cookie carrega APENAS um nonce aleatório; todo POST envia o mesmo nonce em
 * campo e o servidor exige igualdade (duplo envio com valor imprevisível). O id do usuário é
 * público — a tela T1 lista todos — e nunca serviu como token (achado SEC-07).
 * V(4)/T4: a identidade viaja no parâmetro `u` a cada requisição, nunca em cookie: duas abas,
 * dois usuários, como CA-3b e o teste manual de CA-11 exigem (achado UX-08).
 * V(2)/R4: NÃO existe rota de relógio (achado SEC-02).
 */
import Fastify, { type FastifyInstance, type FastifyReply, type FastifyRequest } from "fastify";
import formbody from "@fastify/formbody";
import { randomUUID, randomBytes } from "node:crypto";
import type { Ambiente } from "../app/casos-de-uso.js";
import * as uc from "../app/casos-de-uso.js";
import * as delegacaoDom from "../dominio/delegacao.js";
import { reaisParaCentavos, porId as papelPorId } from "../dominio/matriz-doa.js";
import { diaParaInstante } from "../dominio/relogio.js";
import type { ErroDominio } from "../dominio/resultado.js";
import { paraString, type Html } from "../ui/render.js";
import * as telas from "../ui/telas.js";

const COOKIE_NONCE = "t27_nonce";
/** Achado RES-03: descrição de 10 MB entraria na trilha para sempre. */
const LIMITE_CORPO = 64 * 1024;

/** Erros de SoD e conflito são 409; validação é 400; ausência é 404. */
function statusDe(e: ErroDominio): number {
  if (e.codigo === "NAO_ENCONTRADO") return 404;
  if (["AUTO_APROVACAO", "DUPLO_VOTO", "REDELEGACAO", "VIGENCIAS_SOBREPOSTAS", "CONFLITO", "SEM_AUTORIDADE"].includes(e.codigo))
    return 409;
  return 400;
}

function lerCookie(req: FastifyRequest, nome: string): string | undefined {
  const bruto = req.headers.cookie;
  if (!bruto) return undefined;
  for (const parte of bruto.split(";")) {
    const [k, ...v] = parte.trim().split("=");
    if (k === nome) return decodeURIComponent(v.join("="));
  }
  return undefined;
}

function garantirNonce(req: FastifyRequest, reply: FastifyReply): string {
  const existente = lerCookie(req, COOKIE_NONCE);
  if (existente) return existente;
  const novo = randomBytes(24).toString("base64url");
  reply.header("Set-Cookie", `${COOKIE_NONCE}=${novo}; Path=/; HttpOnly; SameSite=Strict`);
  return novo;
}

export function criarServidor(amb: Ambiente): FastifyInstance {
  const app = Fastify({ bodyLimit: LIMITE_CORPO });
  app.register(formbody);

  const enviar = (reply: FastifyReply, h: Html, status = 200) =>
    reply.code(status).type("text/html; charset=utf-8").send(paraString(h));

  /** Ponto ÚNICO de resolução e validação do usuário atuante (achado A-05). */
  const eu = (id: unknown) => (typeof id === "string" ? amb.repos.usuarios.porId(id) : undefined);
  const papelDe = (papelId: string) => papelPorId(amb.matriz, papelId) ?? null;
  const ehAdmin = (usuarioId: string) => usuarioId === "elisa";

  const semUsuario = (reply: FastifyReply) =>
    enviar(
      reply,
      telas.pagina(
        "Selecione um usuário",
        null,
        null,
        telas.t1SelecaoUsuario(amb.repos.usuarios.todos(), amb.matriz.papeis),
      ),
      400,
    );

  const conferirNonce = (req: FastifyRequest, reply: FastifyReply): boolean => {
    const doCookie = lerCookie(req, COOKIE_NONCE);
    const doCampo = (req.body as Record<string, unknown> | undefined)?.["nonce"];
    if (!doCookie || typeof doCampo !== "string" || doCampo !== doCookie) {
      void enviar(
        reply,
        telas.pagina("Requisição recusada", null, null, telas.erroBox(
          "Requisição sem origem confiável (nonce ausente ou divergente). Recarregue a página e tente de novo.",
        )),
        403,
      );
      return false;
    }
    return true;
  };

  // ---- T1 -------------------------------------------------------------------------------
  app.get("/", async (req, reply) => {
    garantirNonce(req, reply);
    return enviar(
      reply,
      telas.pagina("Quem é você?", null, null, telas.t1SelecaoUsuario(amb.repos.usuarios.todos(), amb.matriz.papeis)),
    );
  });

  // ---- T3 bandeja -----------------------------------------------------------------------
  app.get("/bandeja", async (req, reply) => {
    garantirNonce(req, reply);
    const u = eu((req.query as Record<string, unknown>)["u"]);
    if (!u) return semUsuario(reply);
    const r = uc.verBandeja(amb, u.id);
    if (!r.ok) return enviar(reply, telas.pagina("Bandeja", u, papelDe(u.papelId), telas.erroBox(r.erro.mensagem)), statusDe(r.erro));
    const aviso = (req.query as Record<string, unknown>)["ok"];
    return enviar(
      reply,
      telas.pagina("Sua bandeja", u, papelDe(u.papelId), telas.t3Bandeja(u, r.valor, typeof aviso === "string" ? aviso : null)),
    );
  });

  // ---- T2 nova despesa ------------------------------------------------------------------
  app.get("/nova", async (req, reply) => {
    const nonce = garantirNonce(req, reply);
    const u = eu((req.query as Record<string, unknown>)["u"]);
    if (!u) return semUsuario(reply);
    const e = (req.query as Record<string, unknown>)["erro"];
    return enviar(
      reply,
      telas.pagina("Nova despesa", u, papelDe(u.papelId), telas.t2NovaDespesa(u, nonce, typeof e === "string" ? e : null)),
    );
  });

  app.post("/despesas", async (req, reply) => {
    if (!conferirNonce(req, reply)) return reply;
    const corpo = req.body as Record<string, unknown>;
    const u = eu(corpo["u"]);
    if (!u) return semUsuario(reply);

    const valor = reaisParaCentavos(String(corpo["valor"] ?? ""));
    if (!valor.ok) return reply.redirect(`/nova?u=${u.id}&erro=${encodeURIComponent(valor.erro.mensagem)}`);

    const r = uc.solicitar(amb, {
      solicitanteId: u.id,
      valorCentavos: valor.valor,
      descricao: String(corpo["descricao"] ?? ""),
    });
    if (!r.ok) return reply.redirect(`/nova?u=${u.id}&erro=${encodeURIComponent(r.erro.mensagem)}`);
    return reply.redirect(`/despesas/${r.valor.id}?u=${u.id}`);
  });

  // ---- T4 detalhe -----------------------------------------------------------------------
  app.get("/despesas/:id", async (req, reply) => {
    const nonce = garantirNonce(req, reply);
    const u = eu((req.query as Record<string, unknown>)["u"]);
    if (!u) return semUsuario(reply);
    const id = (req.params as { id: string }).id;

    const visao = uc.verTrilha(amb, id);
    if (!visao.ok)
      return enviar(reply, telas.pagina("Despesa", u, papelDe(u.papelId), telas.erroBox(visao.erro.mensagem)), statusDe(visao.erro));

    const solicitante = amb.repos.usuarios.porId(visao.valor.despesa.solicitanteId)!;
    const autorizacao = uc.autoridadeSobre(amb, id, u.id);
    const e = (req.query as Record<string, unknown>)["erro"];

    return enviar(
      reply,
      telas.pagina(
        `Despesa ${id.slice(0, 8)}`,
        u,
        papelDe(u.papelId),
        telas.t4Detalhe({
          eu: u,
          nonce,
          despesa: visao.valor.despesa,
          solicitante,
          cadeia: visao.valor.cadeia,
          eventos: visao.valor.eventos,
          autoridade: autorizacao.ok ? autorizacao.valor : null,
          motivoSemAutoridade: autorizacao.ok ? null : autorizacao.erro.mensagem,
          usuarios: amb.repos.usuarios.todos(),
          delegacoes: amb.repos.delegacoes.todas(),
          erro: typeof e === "string" ? e : null,
        }),
      ),
    );
  });

  app.post("/despesas/:id/aprovar", async (req, reply) => {
    if (!conferirNonce(req, reply)) return reply;
    const corpo = req.body as Record<string, unknown>;
    const u = eu(corpo["u"]);
    if (!u) return semUsuario(reply);
    const id = (req.params as { id: string }).id;
    const r = uc.aprovar(amb, { despesaId: id, atuanteId: u.id });
    if (!r.ok) return reply.redirect(`/despesas/${id}?u=${u.id}&erro=${encodeURIComponent(r.erro.mensagem)}`);
    return reply.redirect(`/despesas/${id}?u=${u.id}`);
  });

  app.post("/despesas/:id/rejeitar", async (req, reply) => {
    if (!conferirNonce(req, reply)) return reply;
    const corpo = req.body as Record<string, unknown>;
    const u = eu(corpo["u"]);
    if (!u) return semUsuario(reply);
    const id = (req.params as { id: string }).id;
    const r = uc.rejeitar(amb, { despesaId: id, atuanteId: u.id, motivo: String(corpo["motivo"] ?? "") });
    if (!r.ok) return reply.redirect(`/despesas/${id}?u=${u.id}&erro=${encodeURIComponent(r.erro.mensagem)}`);
    return reply.redirect(`/despesas/${id}?u=${u.id}`);
  });

  // ---- T5 delegações --------------------------------------------------------------------
  app.get("/delegacoes", async (req, reply) => {
    const nonce = garantirNonce(req, reply);
    const q = req.query as Record<string, unknown>;
    const u = eu(q["u"]);
    if (!u) return semUsuario(reply);
    return enviar(
      reply,
      telas.pagina(
        "Delegações",
        u,
        papelDe(u.papelId),
        telas.t5Delegacoes({
          eu: u,
          nonce,
          minhas: amb.repos.delegacoes.porDelegante(u.id),
          usuarios: amb.repos.usuarios.todos(),
          agora: amb.relogio.agora(),
          erro: typeof q["erro"] === "string" ? (q["erro"] as string) : null,
          ok: typeof q["ok"] === "string" ? (q["ok"] as string) : null,
        }),
      ),
    );
  });

  app.post("/delegacoes", async (req, reply) => {
    if (!conferirNonce(req, reply)) return reply;
    const corpo = req.body as Record<string, unknown>;
    const u = eu(corpo["u"]);
    if (!u) return semUsuario(reply);
    const r = uc.delegar(amb, {
      deleganteId: u.id,
      delegadoId: String(corpo["delegadoId"] ?? ""),
      // Achado A-07: a tela envia DATA; normalizamos para 00:00Z do dia, regra escrita.
      inicio: diaParaInstante(String(corpo["inicio"] ?? "")),
      fim: diaParaInstante(String(corpo["fim"] ?? "")),
    });
    if (!r.ok) return reply.redirect(`/delegacoes?u=${u.id}&erro=${encodeURIComponent(r.erro.mensagem)}`);
    return reply.redirect(`/delegacoes?u=${u.id}&ok=${encodeURIComponent("Delegação criada.")}`);
  });

  app.post("/delegacoes/:id/revogar", async (req, reply) => {
    if (!conferirNonce(req, reply)) return reply;
    const corpo = req.body as Record<string, unknown>;
    const u = eu(corpo["u"]);
    if (!u) return semUsuario(reply);
    const id = (req.params as { id: string }).id;
    const r = uc.revogar(amb, { delegacaoId: id, atuanteId: u.id, ehAdmin: ehAdmin(u.id) });
    if (!r.ok) return reply.redirect(`/delegacoes?u=${u.id}&erro=${encodeURIComponent(r.erro.mensagem)}`);
    return reply.redirect(`/delegacoes?u=${u.id}&ok=${encodeURIComponent("Delegação revogada.")}`);
  });

  // ---- T6 auditoria ---------------------------------------------------------------------
  app.get("/auditoria", async (req, reply) => {
    const nonce = garantirNonce(req, reply);
    const u = eu((req.query as Record<string, unknown>)["u"]);
    if (!u) return semUsuario(reply);
    return enviar(
      reply,
      telas.pagina(
        "Auditoria",
        u,
        papelDe(u.papelId),
        telas.t6Auditoria({
          eu: u,
          nonce,
          despesas: amb.repos.despesas.todas(),
          delegacoes: amb.repos.delegacoes.todas(),
          usuarios: amb.repos.usuarios.todos(),
          ehAdmin: ehAdmin(u.id),
        }),
      ),
    );
  });

  return app;
}
