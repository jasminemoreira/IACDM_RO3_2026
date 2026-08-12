/**
 * Testes de API — as guardas que só existem na borda HTTP.
 *
 * Usa injeção do Fastify (sem porta, sem rede) e banco em memória, com relógio
 * controlado. Cobre CA-negativo, SEG-02 (XSS), SEG-03 (esquema por endpoint) e
 * a autorização das telas de formulário — o defeito que o teste manual do
 * operador encontrou na Fase 5.
 */

import { beforeEach, describe, expect, it } from 'vitest'
import { criarServidor } from '../src/api-http.js'
import { criarCasosDeUso } from '../src/casos-de-uso.js'
import { carregar, instalar } from '../src/configuracao.js'
import { criarRelogioControlado } from '../src/relogio.js'
import { abrirRepositorio } from '../src/repositorio.js'
import type { FastifyInstance } from 'fastify'

const T0 = Date.UTC(2026, 2, 10, 9, 0, 0)
let app: FastifyInstance
let relogio: ReturnType<typeof criarRelogioControlado>
let n = 0

type Sessao = { cookie: string; id: string }

const entrar = async (usuarioId: string): Promise<Sessao> => {
  const r = await app.inject({ method: 'POST', url: '/entrar', payload: { usuarioId } })
  const c = r.headers['set-cookie']
  const bruto = Array.isArray(c) ? c[0]! : (c as string)
  return { cookie: bruto.split(';')[0]!, id: usuarioId }
}

/** Envia com o VÍNCULO DE SESSÃO que a tela emitiria — a identidade que compôs
 *  o formulário. Os testes de troca de aba sobrescrevem `sessaoDe` de propósito. */
const post = (s: Sessao, url: string, payload: Record<string, unknown>) =>
  app.inject({ method: 'POST', url, payload: { sessaoDe: s.id, ...payload }, headers: { cookie: s.cookie } })

const get = (s: Sessao, url: string) => app.inject({ method: 'GET', url, headers: { cookie: s.cookie } })

const abrirChamado = async (s: Sessao, extra: Record<string, unknown> = {}) => {
  const r = await post(s, '/chamados', {
    titulo: 'Impressora do 3º andar',
    descricao: 'Trava ao enviar',
    urgencia: 'MEDIA',
    ...extra,
  })
  return r
}

const idDoRedirect = (r: { headers: Record<string, unknown> }) =>
  String(r.headers['location']).split('/').pop()!

beforeEach(async () => {
  instalar(carregar('politica.json'))
  relogio = criarRelogioControlado(T0)
  const repo = abrirRepositorio(':memory:', 'seed.json')
  const casos = criarCasosDeUso(repo, relogio, () => `c${++n}`)
  app = criarServidor({ casos, repo, segredoCookie: 'segredo-de-teste' })
  await app.ready()
})

describe('CA-negativo — prioridade nunca é entrada', () => {
  it('prioridade_nao_e_entrada_de_api: POST com prioridade → 400', async () => {
    const ana = await entrar('u-ana')
    const r = await abrirChamado(ana, { prioridade: 'P1' })
    expect(r.statusCode).toBe(400)
  })

  it('nem na triagem, nem na reclassificação', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')
    const id = idDoRedirect(await abrirChamado(ana))
    expect((await post(carla, `/chamados/${id}/triagem`, { categoria: 'HARDWARE', impacto: 'BAIXO', prioridade: 'P1' })).statusCode).toBe(400)
    await post(carla, `/chamados/${id}/triagem`, { categoria: 'HARDWARE', impacto: 'BAIXO' })
    expect((await post(carla, `/chamados/${id}/reclassificacao`, { motivo: 'x', prioridade: 'P2' })).statusCode).toBe(400)
  })
})

describe('SEG-03 — esquema por endpoint guarda a separação de autoridade dos eixos', () => {
  it('impacto na abertura é recusado — o impacto é do agente', async () => {
    const ana = await entrar('u-ana')
    expect((await abrirChamado(ana, { impacto: 'ALTO' })).statusCode).toBe(400)
  })

  it('urgência na triagem é recusada — a urgência é do solicitante', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')
    const id = idDoRedirect(await abrirChamado(ana))
    const r = await post(carla, `/chamados/${id}/triagem`, { categoria: 'HARDWARE', impacto: 'BAIXO', urgencia: 'ALTA' })
    expect(r.statusCode).toBe(400)
  })

  it('a recusa é visível, não silenciosa — campo fora do esquema não é apagado', async () => {
    // Regressão do defeito real: o Fastify configura AJV com
    // removeAdditional:true por padrão, e a guarda apagava o campo em silêncio.
    const ana = await entrar('u-ana')
    const r = await abrirChamado(ana, { campoInventado: 'x' })
    expect(r.statusCode).toBe(400)
  })
})

describe('SEG-02 — escape impede XSS armazenado', () => {
  it('script na justificativa sai escapado na trilha', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')
    const id = idDoRedirect(await abrirChamado(ana))
    await post(carla, `/chamados/${id}/triagem`, { categoria: 'HARDWARE', impacto: 'BAIXO' })
    await post(ana, `/chamados/${id}/recurso`, {
      eixos: 'URGENCIA',
      justificativa: '<script>alert("xss")</script>',
    })
    const pagina = await get(ana, `/chamados/${id}`)
    expect(pagina.body).not.toContain('<script>alert')
    expect(pagina.body).toContain('&lt;script&gt;')
  })

  it('título com aspas e sinais não quebra a marcação', async () => {
    const ana = await entrar('u-ana')
    const r = await post(ana, '/chamados', {
      titulo: 'Erro "grave" <b>agora</b> & já',
      descricao: 'd',
      urgencia: 'ALTA',
    })
    const pagina = await get(ana, `/chamados/${idDoRedirect(r)}`)
    expect(pagina.body).toContain('&quot;grave&quot;')
    expect(pagina.body).toContain('&lt;b&gt;')
    expect(pagina.body).toContain('&amp;')
  })
})

describe('autorização nas telas de formulário (defeito achado no teste manual)', () => {
  it('solicitante não abre a tela de triagem', async () => {
    const ana = await entrar('u-ana')
    const id = idDoRedirect(await abrirChamado(ana))
    expect((await get(ana, `/chamados/${id}/triagem`)).statusCode).toBe(422)
  })

  it('agente não abre a tela de julgamento', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')
    const id = idDoRedirect(await abrirChamado(ana))
    expect((await get(carla, `/chamados/${id}/julgamento`)).statusCode).toBe(422)
  })

  it('os botões acompanham a máquina de estados', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')
    const id = idDoRedirect(await abrirChamado(ana))

    // NAO_TRIADO: só Triar. Oferecer Encerrar aqui foi o defeito relatado.
    let p = await get(carla, `/chamados/${id}`)
    expect(p.body).toContain('>Triar<')
    expect(p.body).not.toContain('>Encerrar<')
    expect(p.body).not.toContain('>Reconhecer<')

    await post(carla, `/chamados/${id}/triagem`, { categoria: 'HARDWARE', impacto: 'BAIXO' })
    p = await get(carla, `/chamados/${id}`)
    expect(p.body).not.toContain('>Triar<')
    expect(p.body).toContain('>Reconhecer<')
    expect(p.body).toContain('>Encerrar<')

    await post(carla, `/chamados/${id}/encerramento`, {})
    p = await get(carla, `/chamados/${id}`)
    expect(p.body).not.toContain('>Encerrar<')
    expect(p.body).not.toContain('>Reclassificar<')
  })
})

describe('fluxo completo UC-1 → UC-6 com relógio controlado', () => {
  it('abrir, triar, recorrer, julgar: prioridade e prazos recontados da abertura', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')
    const elena = await entrar('u-elena')

    const id = idDoRedirect(await abrirChamado(ana))
    relogio.avancarMinutos(30)
    await post(carla, `/chamados/${id}/triagem`, { categoria: 'HARDWARE', impacto: 'BAIXO' })

    let p = await get(ana, `/chamados/${id}`)
    expect(p.body).toContain('<strong>P4</strong>')

    relogio.avancarMinutos(90)
    const rec = await post(ana, `/chamados/${id}/recurso`, {
      eixos: 'URGENCIA',
      justificativa: 'fecho o balanço hoje',
    })
    expect(rec.statusCode).toBe(302)

    relogio.avancarMinutos(180)
    const jul = await post(elena, `/chamados/${id}/julgamento`, {
      desfecho: 'PROVIDO',
      fundamentacao: 'prazo contábil confirmado',
      urgencia: 'ALTA',
    })
    expect(jul.statusCode).toBe(302)

    p = await get(ana, `/chamados/${id}`)
    expect(p.body).toContain('<strong>P3</strong>')
    // A trilha, visível ao SOLICITANTE, reconstrói as duas mudanças (CA-3).
    expect(p.body).toContain('prioridade: — → P4')
    expect(p.body).toContain('prioridade: P4 → P3')
    // O prazo mostrado é o de P3 contado da ABERTURA (T0 + 2880 min), e não
    // do julgamento — que teria sido T0 + 300 + 2880.
    const esperado = new Date(T0 + 2880 * 60_000).toISOString().replace('T', ' ').slice(0, 16)
    expect(p.body).toContain(esperado)
  })

  it('B-6 pela borda HTTP — agente não julga', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')
    const id = idDoRedirect(await abrirChamado(ana))
    await post(carla, `/chamados/${id}/triagem`, { categoria: 'HARDWARE', impacto: 'BAIXO' })
    await post(ana, `/chamados/${id}/recurso`, { eixos: 'URGENCIA', justificativa: 'j' })
    const r = await post(carla, `/chamados/${id}/julgamento`, {
      desfecho: 'PROVIDO',
      fundamentacao: 'f',
      urgencia: 'ALTA',
    })
    expect(r.statusCode).toBe(422)
  })

  it('sem sessão, tudo redireciona para a entrada', async () => {
    const r = await app.inject({ method: 'GET', url: '/' })
    expect(r.statusCode).toBe(302)
    expect(r.headers['location']).toBe('/entrar')
  })
})

/**
 * Regressão do defeito encontrado pelo OPERADOR no teste manual exploratório —
 * a classe que nenhum teste automatizado tinha alcançado, porque exige duas
 * abas e uma troca de identidade no meio.
 */
describe('vínculo de sessão — troca de usuário em outra aba', () => {
  it('formulário composto por Ana e enviado sob a sessão de Carla é RECUSADO', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')

    // A aba 1 renderizou o formulário como Ana (sessaoDe = u-ana); a aba 2
    // trocou o usuário, e o cookie do navegador agora é o de Carla.
    const r = await app.inject({
      method: 'POST',
      url: '/chamados',
      payload: { sessaoDe: ana.id, titulo: 'escrito pela Ana', descricao: 'd', urgencia: 'ALTA' },
      headers: { cookie: carla.cookie },
    })

    expect(r.statusCode).toBe(409)
    expect(r.body).toContain('a sessão mudou em outra aba')

    // E nada foi registrado — nem para Ana, nem para Carla.
    expect((await get(ana, '/')).body).not.toContain('escrito pela Ana')
    expect((await get(carla, '/')).body).not.toContain('escrito pela Ana')
  })

  it('vale para toda escrita, não só para a abertura', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')
    const elena = await entrar('u-elena')
    const id = idDoRedirect(await abrirChamado(ana))

    const alheio = { sessaoDe: elena.id }
    expect(
      (await app.inject({
        method: 'POST',
        url: `/chamados/${id}/triagem`,
        payload: { ...alheio, categoria: 'HARDWARE', impacto: 'BAIXO' },
        headers: { cookie: carla.cookie },
      })).statusCode,
    ).toBe(409)

    await post(carla, `/chamados/${id}/triagem`, { categoria: 'HARDWARE', impacto: 'BAIXO' })
    expect(
      (await app.inject({
        method: 'POST',
        url: `/chamados/${id}/recurso`,
        payload: { ...alheio, eixos: 'URGENCIA', justificativa: 'j' },
        headers: { cookie: ana.cookie },
      })).statusCode,
    ).toBe(409)
  })

  it('a tela emite o vínculo em todo formulário de escrita', async () => {
    const ana = await entrar('u-ana')
    const carla = await entrar('u-carla')
    const id = idDoRedirect(await abrirChamado(ana))

    for (const [s, url] of [
      [ana, '/chamados/novo'],
      [carla, `/chamados/${id}/triagem`],
    ] as const) {
      const p = await get(s, url)
      expect(p.body).toContain(`name="sessaoDe" value="${s.id}"`)
    }
  })

  it('envio sem o vínculo é recusado — formulário antigo em cache não passa', async () => {
    const ana = await entrar('u-ana')
    const r = await app.inject({
      method: 'POST',
      url: '/chamados',
      payload: { titulo: 't', descricao: 'd', urgencia: 'ALTA' },
      headers: { cookie: ana.cookie },
    })
    expect(r.statusCode).toBe(400)
  })
})
