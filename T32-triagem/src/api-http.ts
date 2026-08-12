/**
 * M-11 api-http — a PORTA ÚNICA (V(3)).
 *
 * GET e POST vivem aqui; `ui-web` só renderiza. Antes eram duas entradas para o
 * mesmo núcleo, com regras de sessão que podiam divergir sem que ninguém visse
 * (ARQ-08).
 *
 * ESQUEMA POR ENDPOINT (SEG-03) — é a guarda da descoberta central do projeto:
 * a separação de autoridade dos eixos. A abertura aceita `urgencia` e mais
 * nada; a triagem aceita `categoria` e `impacto` e mais nada. `additionalProperties:
 * false` faz o Fastify recusar o resto, e nenhum endpoint aceita `prioridade`
 * em hipótese alguma (CA-negativo).
 *
 * depends-on: casos-de-uso, ui-web
 */

import cookie from '@fastify/cookie'
import formbody from '@fastify/formbody'
import Fastify, { type FastifyInstance, type FastifyReply, type FastifyRequest } from 'fastify'
import { pode } from './autorizacao.js'
import { matriz } from './configuracao.js'
import type { CasosDeUso } from './casos-de-uso.js'
import type { Repositorio } from './repositorio.js'
import * as ui from './ui-web.js'
import type { Categoria, Eixo, Usuario } from './tipos.js'

const COOKIE = 't32sessao'
const CATEGORIAS: readonly Categoria[] = ['HARDWARE', 'SOFTWARE', 'REDE', 'ACESSO', 'OUTRO']

const enumOpcional = (valores: readonly string[]) => ({ type: 'string' as const, enum: [...valores, ''] })
const texto = (max: number) => ({ type: 'string' as const, minLength: 1, maxLength: max })

/**
 * VÍNCULO DE SESSÃO — presente em todo endpoint de escrita exceto a entrada.
 *
 * Carrega a identidade que COMPÔS o formulário, para ser comparada com a que o
 * ENVIA. Sem isso, a autoria da ação era decidida no envio pelo cookie
 * ambiente: com um formulário aberto como Ana e uma troca de usuário em outra
 * aba, o chamado que Ana escreveu era gravado como sendo de Carla.
 */
const sessaoDe = { type: 'string' as const, minLength: 1, maxLength: 80 }

/** Um esquema por endpoint. Nenhum aceita `prioridade`. */
const ESQUEMAS = {
  entrar: {
    type: 'object',
    required: ['usuarioId'],
    additionalProperties: false,
    properties: { usuarioId: texto(80) },
  },
  abrirChamado: {
    type: 'object',
    required: ['sessaoDe', 'titulo', 'descricao', 'urgencia'],
    additionalProperties: false,
    properties: {
      sessaoDe,
      titulo: texto(120),
      descricao: texto(4000),
      // Só a urgência. O impacto é do agente — enviá-lo aqui é recusado.
      urgencia: { type: 'string', enum: ['ALTA', 'MEDIA', 'BAIXA'] },
    },
  },
  triagem: {
    type: 'object',
    required: ['sessaoDe', 'categoria', 'impacto'],
    additionalProperties: false,
    properties: {
      sessaoDe,
      categoria: { type: 'string', enum: [...CATEGORIAS] },
      // Só o impacto. A urgência é do solicitante — alterá-la aqui é recusado;
      // para isso existe a reclassificação, que devolve prazo de recurso.
      impacto: { type: 'string', enum: ['ALTO', 'MEDIO', 'BAIXO'] },
    },
  },
  reclassificacao: {
    type: 'object',
    required: ['sessaoDe', 'motivo'],
    additionalProperties: false,
    properties: {
      sessaoDe,
      categoria: enumOpcional(CATEGORIAS),
      impacto: enumOpcional(['ALTO', 'MEDIO', 'BAIXO']),
      urgencia: enumOpcional(['ALTA', 'MEDIA', 'BAIXA']),
      motivo: texto(2000),
    },
  },
  recurso: {
    type: 'object',
    required: ['sessaoDe', 'justificativa'],
    additionalProperties: false,
    properties: {
      sessaoDe,
      eixos: {
        anyOf: [
          { type: 'string', enum: ['URGENCIA', 'IMPACTO'] },
          { type: 'array', items: { type: 'string', enum: ['URGENCIA', 'IMPACTO'] } },
        ],
      },
      justificativa: texto(2000),
    },
  },
  julgamento: {
    type: 'object',
    required: ['sessaoDe', 'desfecho', 'fundamentacao'],
    additionalProperties: false,
    properties: {
      sessaoDe,
      desfecho: { type: 'string', enum: ['PROVIDO', 'PARCIALMENTE_PROVIDO', 'IMPROVIDO'] },
      fundamentacao: texto(2000),
      urgencia: enumOpcional(['ALTA', 'MEDIA', 'BAIXA']),
      impacto: enumOpcional(['ALTO', 'MEDIO', 'BAIXO']),
    },
  },
} as const

const vazioParaIndefinido = <T extends string>(v: unknown): T | undefined =>
  typeof v === 'string' && v !== '' ? (v as T) : undefined

export function criarServidor(opcoes: {
  casos: CasosDeUso
  repo: Repositorio
  segredoCookie: string
}): FastifyInstance {
  const { casos, repo } = opcoes
  // `removeAdditional: false` é deliberado e não é default: o Fastify remove
  // silenciosamente campos fora do esquema, e silêncio não é guarda. Enviar
  // `impacto` na abertura ou `prioridade` em qualquer lugar precisa FALHAR de
  // forma visível (SEG-03, CA-negativo), não ser apagado sem que ninguém veja.
  const app = Fastify({
    logger: false,
    ajv: { customOptions: { removeAdditional: false, coerceTypes: false, allErrors: true } },
  })

  app.register(formbody)
  app.register(cookie, { secret: opcoes.segredoCookie })

  const sessao = (req: FastifyRequest): Usuario | null => {
    const assinado = req.cookies[COOKIE]
    if (!assinado) return null
    const { valid, value } = req.unsignCookie(assinado)
    if (!valid || !value) return null
    return repo.usuario(value)
  }

  const vistaSessao = (u: Usuario | null) => (u ? { id: u.id, nome: u.nome, papel: u.papel } : null)

  const exigirSessao = (req: FastifyRequest, res: FastifyReply): Usuario | null => {
    const u = sessao(req)
    if (!u) {
      res.redirect('/entrar')
      return null
    }
    return u
  }

  const enviar = (res: FastifyReply, corpo: string, status = 200) =>
    res.status(status).type('text/html; charset=utf-8').send(corpo)

  const falhar = (res: FastifyReply, u: Usuario | null, motivo: string, status = 422) =>
    enviar(res, ui.telaErro(vistaSessao(u), motivo), status)

  /**
   * Sessão para ESCRITA: além de existir, precisa ser a MESMA que compôs o
   * formulário. O cookie é do navegador inteiro; trocar de usuário numa aba
   * troca em todas, e um formulário já preenchido em outra aba seria enviado
   * sob a identidade nova. Gravar assim faria a trilha atribuir a alguém uma
   * ação que essa pessoa não escreveu — num sistema cuja tese é atribuição
   * auditável, é o pior defeito possível.
   *
   * A recusa é deliberada: o sistema NÃO sabe qual das duas identidades é a
   * certa, e adivinhar seria pior que recusar. 409 (conflito), não 422.
   */
  const exigirSessaoVinculada = (req: FastifyRequest, res: FastifyReply): Usuario | null => {
    const u = exigirSessao(req, res)
    if (!u) return null
    const declarada = (req.body as { sessaoDe?: string } | undefined)?.sessaoDe
    if (declarada !== u.id) {
      falhar(res, u, 'SESSAO_TROCADA', 409)
      return null
    }
    return u
  }

  const nomeDe = (id: string): string => repo.usuario(id)?.nome ?? id

  // --- T-0 entrada -----------------------------------------------------------

  app.get('/entrar', async (_req, res) => enviar(res, ui.telaEntrada(repo.usuarios())))

  app.post('/entrar', { schema: { body: ESQUEMAS.entrar } }, async (req, res) => {
    const { usuarioId } = req.body as { usuarioId: string }
    if (!repo.usuario(usuarioId)) return falhar(res, null, 'USUARIO_INEXISTENTE')
    res.setCookie(COOKIE, usuarioId, { path: '/', httpOnly: true, sameSite: 'lax', signed: true })
    return res.redirect('/')
  })

  // --- T-7 meus chamados / raiz ---------------------------------------------

  app.get('/', async (req, res) => {
    const u = exigirSessao(req, res)
    if (!u) return res
    return enviar(res, ui.telaMeusChamados(vistaSessao(u), casos.meusChamados(u), u.papel))
  })

  // --- T-2 fila --------------------------------------------------------------

  app.get('/fila', async (req, res) => {
    const u = exigirSessao(req, res)
    if (!u) return res
    const filtro = vazioParaIndefinido<Categoria>((req.query as Record<string, unknown>)?.categoria)
    const r = casos.consultarFila(u, filtro)
    if (!r.ok) return falhar(res, u, r.motivo)
    return enviar(res, ui.telaFila(vistaSessao(u), r.valor, filtro ?? null, CATEGORIAS))
  })

  // --- T-1 abrir -------------------------------------------------------------

  app.get('/chamados/novo', async (req, res) => {
    const u = exigirSessao(req, res)
    if (!u) return res
    return enviar(res, ui.telaAbrir(vistaSessao(u)))
  })

  app.post('/chamados', { schema: { body: ESQUEMAS.abrirChamado } }, async (req, res) => {
    const u = exigirSessaoVinculada(req, res)
    if (!u) return res
    const b = req.body as { titulo: string; descricao: string; urgencia: 'ALTA' | 'MEDIA' | 'BAIXA' }
    const r = casos.abrirChamado(u, b)
    if (!r.ok) return enviar(res, ui.telaAbrir(vistaSessao(u), r.motivo), 422)
    return res.redirect(`/chamados/${r.valor.id}`)
  })

  // --- T-4 chamado + trilha --------------------------------------------------

  app.get('/chamados/:id', async (req, res) => {
    const u = exigirSessao(req, res)
    if (!u) return res
    const { id } = req.params as { id: string }
    const r = casos.consultarChamado(u, id)
    if (!r.ok) return falhar(res, u, r.motivo)
    const v = r.valor
    return enviar(
      res,
      ui.telaChamado(
        vistaSessao(u),
        {
          chamado: { ...v.chamado, solicitanteNome: nomeDe(v.chamado.solicitanteId) },
          prioridade: v.prioridade,
          prazoVigente: v.prazoVigente,
          violado: v.violado,
          recurso: v.recurso,
          podeRecorrer: v.podeRecorrer,
          motivoNaoPodeRecorrer: v.motivoNaoPodeRecorrer,
          prescreveEm: v.prescreveEm,
          eventos: v.eventos.map((e) => ({ ...e, atorNome: nomeDe(e.atorId) })),
        },
        u.papel,
      ),
    )
  })

  // --- T-3 triar -------------------------------------------------------------

  app.get('/chamados/:id/triagem', async (req, res) => {
    const u = exigirSessao(req, res)
    if (!u) return res
    // A MESMA guarda do POST vale no GET: abrir um formulário que a ação vai
    // recusar depois é beco sem saída, e a lente UI/UX chamaria isso de
    // dead-end state. Autorizar só na escrita protege o dado e maltrata a pessoa.
    const p = pode(u, 'TRIAR')
    if (!p.ok) return falhar(res, u, p.motivo)
    const c = repo.chamado((req.params as { id: string }).id)
    if (!c) return falhar(res, u, 'CHAMADO_INEXISTENTE')
    if (c.estado !== 'NAO_TRIADO') return falhar(res, u, 'JA_TRIADO')
    return enviar(res, ui.telaTriar(vistaSessao(u), c, matriz() as Record<string, Record<string, string>>))
  })

  app.post('/chamados/:id/triagem', { schema: { body: ESQUEMAS.triagem } }, async (req, res) => {
    const u = exigirSessaoVinculada(req, res)
    if (!u) return res
    const { id } = req.params as { id: string }
    const b = req.body as { categoria: Categoria; impacto: 'ALTO' | 'MEDIO' | 'BAIXO' }
    const r = casos.triar(u, id, b)
    if (!r.ok) return falhar(res, u, r.motivo)
    return res.redirect(`/chamados/${id}`)
  })

  // --- reclassificação -------------------------------------------------------

  app.get('/chamados/:id/reclassificacao', async (req, res) => {
    const u = exigirSessao(req, res)
    if (!u) return res
    const p = pode(u, 'RECLASSIFICAR')
    if (!p.ok) return falhar(res, u, p.motivo)
    const c = repo.chamado((req.params as { id: string }).id)
    if (!c) return falhar(res, u, 'CHAMADO_INEXISTENTE')
    if (c.estado === 'NAO_TRIADO') return falhar(res, u, 'NAO_TRIADO')
    if (c.estado === 'ENCERRADO') return falhar(res, u, 'CHAMADO_ENCERRADO')
    return enviar(res, ui.telaReclassificar(vistaSessao(u), c))
  })

  app.post('/chamados/:id/reclassificacao', { schema: { body: ESQUEMAS.reclassificacao } }, async (req, res) => {
    const u = exigirSessaoVinculada(req, res)
    if (!u) return res
    const { id } = req.params as { id: string }
    const b = req.body as Record<string, string>
    const r = casos.reclassificar(u, id, {
      categoria: vazioParaIndefinido<Categoria>(b.categoria),
      impacto: vazioParaIndefinido<'ALTO' | 'MEDIO' | 'BAIXO'>(b.impacto),
      urgencia: vazioParaIndefinido<'ALTA' | 'MEDIA' | 'BAIXA'>(b.urgencia),
      motivo: b.motivo ?? '',
    })
    if (!r.ok) return falhar(res, u, r.motivo)
    return res.redirect(`/chamados/${id}`)
  })

  // --- reconhecer / encerrar -------------------------------------------------

  app.post('/chamados/:id/reconhecimento', async (req, res) => {
    const u = exigirSessaoVinculada(req, res)
    if (!u) return res
    const { id } = req.params as { id: string }
    const r = casos.reconhecer(u, id)
    if (!r.ok) return falhar(res, u, r.motivo)
    return res.redirect(`/chamados/${id}`)
  })

  app.post('/chamados/:id/encerramento', async (req, res) => {
    const u = exigirSessaoVinculada(req, res)
    if (!u) return res
    const { id } = req.params as { id: string }
    const r = casos.encerrar(u, id)
    if (!r.ok) return falhar(res, u, r.motivo)
    return res.redirect(`/chamados/${id}`)
  })

  // --- T-5 recorrer ----------------------------------------------------------

  app.get('/chamados/:id/recurso', async (req, res) => {
    const u = exigirSessao(req, res)
    if (!u) return res
    const { id } = req.params as { id: string }
    const r = casos.consultarChamado(u, id)
    if (!r.ok) return falhar(res, u, r.motivo)
    if (!r.valor.podeRecorrer) return falhar(res, u, r.valor.motivoNaoPodeRecorrer ?? 'PRESCRITO')
    return enviar(res, ui.telaRecorrer(vistaSessao(u), r.valor.chamado, r.valor.prescreveEm))
  })

  app.post('/chamados/:id/recurso', { schema: { body: ESQUEMAS.recurso } }, async (req, res) => {
    const u = exigirSessaoVinculada(req, res)
    if (!u) return res
    const { id } = req.params as { id: string }
    const b = req.body as { eixos?: string | string[]; justificativa: string }
    const eixos = (Array.isArray(b.eixos) ? b.eixos : b.eixos ? [b.eixos] : []) as Eixo[]
    const r = casos.abrirRecurso(u, id, { eixos, justificativa: b.justificativa })
    if (!r.ok) return falhar(res, u, r.motivo)
    return res.redirect(`/chamados/${id}`)
  })

  // --- T-6 julgar ------------------------------------------------------------

  app.get('/chamados/:id/julgamento', async (req, res) => {
    const u = exigirSessao(req, res)
    if (!u) return res
    const p = pode(u, 'JULGAR_RECURSO')
    if (!p.ok) return falhar(res, u, p.motivo)
    const { id } = req.params as { id: string }
    const r = casos.consultarChamado(u, id)
    if (!r.ok) return falhar(res, u, r.motivo)
    const v = r.valor
    if (!v.recurso) return falhar(res, u, 'RECURSO_INEXISTENTE')
    return enviar(
      res,
      ui.telaJulgar(vistaSessao(u), {
        chamado: v.chamado,
        recurso: v.recurso,
        solicitanteNome: nomeDe(v.chamado.solicitanteId),
        recursosEm30Dias: casos.contextoJulgamento(v.chamado.solicitanteId),
        prioridadeAtual: v.prioridade,
      }),
    )
  })

  app.post('/chamados/:id/julgamento', { schema: { body: ESQUEMAS.julgamento } }, async (req, res) => {
    const u = exigirSessaoVinculada(req, res)
    if (!u) return res
    const { id } = req.params as { id: string }
    const b = req.body as Record<string, string>
    const r = casos.julgarRecurso(u, id, {
      desfecho: b.desfecho as 'PROVIDO' | 'PARCIALMENTE_PROVIDO' | 'IMPROVIDO',
      fundamentacao: b.fundamentacao ?? '',
      novosEixos: {
        urgencia: vazioParaIndefinido<'ALTA' | 'MEDIA' | 'BAIXA'>(b.urgencia),
        impacto: vazioParaIndefinido<'ALTO' | 'MEDIO' | 'BAIXO'>(b.impacto),
      },
    })
    if (!r.ok) return falhar(res, u, r.motivo)
    return res.redirect(`/chamados/${id}`)
  })

  // Entrada malformada (inclusive campo fora do esquema do endpoint) devolve
  // 400 com a razão, em vez de 500 opaco.
  app.setErrorHandler((erro, req, res) => {
    const u = sessao(req)
    return enviar(res, ui.telaErro(vistaSessao(u), erro.message), erro.statusCode ?? 500)
  })

  return app
}
