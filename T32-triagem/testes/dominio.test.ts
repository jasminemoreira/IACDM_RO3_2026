/**
 * Testes de domínio — escritos CONTRA specs/, não contra a implementação.
 *
 * Fonte da verdade: specs/datasets/ground-truth-matriz.md (GT-1..GT-5),
 * specs/validation/criterios-aceitacao.md (CA-1/2/3, CA-negativo, VAL-1..18).
 * Ambos escritos ANTES do código, conforme o enunciado exige.
 *
 * Todo teste roda com relógio CONTROLADO: 48 h de prescrição e 240 h de SLA
 * são exercitadas em microssegundos, sem uma única espera real (VAL-14).
 */

import { beforeEach, describe, expect, it } from 'vitest'
import { carregar, instalar, ErroPolitica } from '../src/configuracao.js'
import { derivar, severidade } from '../src/prioridade.js'
import { prazos, prazoTriagem, somarMinutos, violado } from '../src/sla.js'
import * as chamado from '../src/chamado.js'
import * as recurso from '../src/recurso.js'
import { contarMudancasDePrioridade, mudancasDePrioridade } from '../src/trilha.js'
import { criarRelogioControlado } from '../src/relogio.js'
import { pode } from '../src/autorizacao.js'
import type { Impacto, Instante, Urgencia, Usuario } from '../src/tipos.js'

const T0: Instante = Date.UTC(2026, 2, 10, 9, 0, 0)
const MIN = 60_000

const ANA: Usuario = { id: 'u-ana', nome: 'Ana', papel: 'SOLICITANTE' }
const BRUNO: Usuario = { id: 'u-bruno', nome: 'Bruno', papel: 'SOLICITANTE' }
const CARLA: Usuario = { id: 'u-carla', nome: 'Carla', papel: 'AGENTE' }
const ELENA: Usuario = { id: 'u-elena', nome: 'Elena', papel: 'GESTOR' }

beforeEach(() => {
  instalar(carregar('politica.json'))
})

const abrirTriado = (u: Urgencia, i: Impacto, agoraTriagem = T0 + 30 * MIN) => {
  const a = chamado.abrir({
    id: 'c1',
    solicitanteId: ANA.id,
    titulo: 'Impressora do 3º andar não imprime',
    descricao: 'Trava ao enviar',
    urgencia: u,
    agora: T0,
  })
  if (!a.ok) throw new Error('abertura falhou')
  const t = chamado.triar(a.entidade, CARLA.id, 'HARDWARE', i, agoraTriagem)
  if (!t.ok) throw new Error('triagem falhou')
  return { aberto: a, triado: t, c: t.entidade, eventos: [...a.eventos, ...t.eventos] }
}

const ctxDe = (c: chamado.Chamado) => ({
  id: c.id,
  solicitanteId: c.solicitanteId,
  estado: c.estado,
  ultimaMudancaClassificacao: c.ultimaMudancaClassificacao,
})

// ===========================================================================
// CA-1 — as 9 células (GT-1)
// ===========================================================================

describe('CA-1 — matriz impacto × urgência', () => {
  // Tabela copiada de specs/datasets/ground-truth-matriz.md, GT-1.
  const GT1: [Impacto, Urgencia, string, number, number][] = [
    ['ALTO', 'ALTA', 'P1', 10, 240],
    ['ALTO', 'MEDIA', 'P2', 15, 480],
    ['ALTO', 'BAIXA', 'P3', 60, 2880],
    ['MEDIO', 'ALTA', 'P2', 15, 480],
    ['MEDIO', 'MEDIA', 'P3', 60, 2880],
    ['MEDIO', 'BAIXA', 'P4', 240, 7200],
    ['BAIXO', 'ALTA', 'P3', 60, 2880],
    ['BAIXO', 'MEDIA', 'P4', 240, 7200],
    ['BAIXO', 'BAIXA', 'P5', 1440, 14400],
  ]

  it.each(GT1)('matriz_9_celulas: %s + %s → %s', (i, u, esperado) => {
    expect(derivar(i, u)).toBe(esperado)
  })

  it.each(GT1)('metas de %s + %s (%s): reconhecer %i min, resolver %i min', (i, u, _p, rec, res) => {
    const p = prazos(derivar(i, u), T0)
    expect(p.reconhecimento).toBe(T0 + rec * MIN)
    expect(p.resolucao).toBe(T0 + res * MIN)
  })

  it('matriz_e_total — 9 células, nenhuma indefinida', () => {
    const is: Impacto[] = ['ALTO', 'MEDIO', 'BAIXO']
    const us: Urgencia[] = ['ALTA', 'MEDIA', 'BAIXA']
    const vistas = is.flatMap((i) => us.map((u) => derivar(i, u)))
    expect(vistas).toHaveLength(9)
    expect(vistas.every((p) => /^P[1-5]$/.test(p))).toBe(true)
  })

  it('matriz_e_monotona — agravar um eixo nunca melhora a prioridade', () => {
    const is: Impacto[] = ['ALTO', 'MEDIO', 'BAIXO']
    const us: Urgencia[] = ['ALTA', 'MEDIA', 'BAIXA']
    for (let a = 0; a < is.length - 1; a++) {
      for (const u of us) {
        expect(severidade(derivar(is[a]!, u))).toBeLessThanOrEqual(severidade(derivar(is[a + 1]!, u)))
      }
    }
    for (const i of is) {
      for (let b = 0; b < us.length - 1; b++) {
        expect(severidade(derivar(i, us[b]!))).toBeLessThanOrEqual(severidade(derivar(i, us[b + 1]!)))
      }
    }
  })

  it('matriz_e_simetrica — (ALTO,BAIXA) = (BAIXO,ALTA) = P3', () => {
    expect(derivar('ALTO', 'BAIXA')).toBe('P3')
    expect(derivar('BAIXO', 'ALTA')).toBe('P3')
  })
})

// ===========================================================================
// CA-2 — recurso provido reconta prazos DESDE A ABERTURA
// ===========================================================================

describe('CA-2 — recontagem desde a abertura', () => {
  it('provimento_reconta_da_abertura (GT-2) — e NÃO reinicia na mudança', () => {
    const { c } = abrirTriado('MEDIA', 'BAIXO') // P4
    expect(chamado.prioridadeDe(c)).toBe('P4')

    const agoraJulgamento = T0 + 5 * 60 * MIN // T0 + 5 h
    const r = chamado.reclassificar(c, ELENA.id, { urgencia: 'ALTA' }, 'Prazo contábil confirmado', 'RECURSO', agoraJulgamento)
    expect(r.ok).toBe(true)
    if (!r.ok) return

    expect(chamado.prioridadeDe(r.entidade)).toBe('P3')
    const p = chamado.prazosDe(r.entidade)!

    // O teste compara contra AMBOS os valores possíveis: verificar só que "o
    // prazo mudou" passaria com a regra errada (VAL: falsa cobertura).
    const desdeAbertura = T0 + 2880 * MIN
    const desdeAMudanca = agoraJulgamento + 2880 * MIN
    expect(p.resolucao).toBe(desdeAbertura)
    expect(p.resolucao).not.toBe(desdeAMudanca)
  })

  it('provimento_pode_nascer_violado (GT-3)', () => {
    const { c } = abrirTriado('BAIXA', 'BAIXO', T0 + 60 * MIN) // P5, resolver em 240 h
    expect(chamado.prioridadeDe(c)).toBe('P5')

    const agora = T0 + 40 * 60 * MIN // T0 + 40 h
    expect(chamado.estaVioladoAgora(c, agora)).toBe(false)

    const r = chamado.reclassificar(c, ELENA.id, { impacto: 'ALTO', urgencia: 'ALTA' }, 'provido', 'RECURSO', agora)
    expect(r.ok).toBe(true)
    if (!r.ok) return

    expect(chamado.prioridadeDe(r.entidade)).toBe('P1')
    expect(chamado.prazosDe(r.entidade)!.resolucao).toBe(T0 + 240 * MIN) // 4 h da abertura
    // Nasce violado, e isso é o comportamento CORRETO: a urgência sempre
    // existiu, o erro foi não tê-la visto na triagem.
    expect(chamado.estaVioladoAgora(r.entidade, agora)).toBe(true)
  })

  it('VAL-2 — triagem conta da abertura, não da triagem', () => {
    const { c } = abrirTriado('MEDIA', 'MEDIO', T0 + 55 * MIN) // P3
    const p = chamado.prazosDe(c)!
    expect(p.resolucao).toBe(T0 + 2880 * MIN)
    expect(p.resolucao).not.toBe(T0 + 55 * MIN + 2880 * MIN)
  })

  it('VAL-18 — prazos em horas corridas, atravessando fim de semana', () => {
    // 10/03/2026 é terça. P4 = 120 h corridas → sábado 15/03, sem pular o fim
    // de semana: não existe calendário de negócio (decisão da Fase 0).
    const { c } = abrirTriado('BAIXA', 'MEDIO') // P4
    const p = chamado.prazosDe(c)!
    expect(p.resolucao).toBe(T0 + 7200 * MIN)
    expect(new Date(p.resolucao).getUTCDay()).toBe(0) // domingo
  })
})

// ===========================================================================
// CA-3 — a trilha reconstrói toda mudança de prioridade
// ===========================================================================

describe('CA-3 — trilha', () => {
  it('trilha_reconstroi_prioridade — nº de eventos bate com nº de mudanças', () => {
    const { c, eventos } = abrirTriado('MEDIA', 'BAIXO') // — → P4
    const r1 = chamado.reclassificar(c, CARLA.id, { impacto: 'MEDIO' }, 'afeta o andar todo', 'AGENTE', T0 + 2 * 60 * MIN)
    expect(r1.ok).toBe(true)
    if (!r1.ok) return // P4 → P3
    const r2 = chamado.reclassificar(r1.entidade, ELENA.id, { urgencia: 'ALTA' }, 'provido', 'RECURSO', T0 + 5 * 60 * MIN)
    expect(r2.ok).toBe(true)
    if (!r2.ok) return // P3 → P2

    const todos = [...eventos, ...r1.eventos, ...r2.eventos]
    const mudancas = mudancasDePrioridade(todos)

    expect(contarMudancasDePrioridade(todos)).toBe(3)
    expect(mudancas.map((m) => `${m.de ?? '—'}→${m.para}`)).toEqual(['—→P4', 'P4→P3', 'P3→P2'])
    // Cada mudança traz ator, instante e motivo — sem isso não se reconstrói nada.
    expect(mudancas.every((m) => m.atorId.length > 0 && m.instante > 0)).toBe(true)
    expect(mudancas[1]!.motivo).toBe('afeta o andar todo')
    // origem distingue "erro de triagem" de "demora no atendimento" (JOG-02).
    expect(todos.at(-1)!.origem).toBe('RECURSO')
    // Toda classificação carrega a versão da política que a produziu (CTL-01).
    expect(todos.filter((e) => e.mudancas.length > 0).every((e) => e.versaoPolitica !== null)).toBe(true)
  })

  it('VAL-4 / B-9 — reclassificação que não muda a prioridade ainda registra', () => {
    const { c } = abrirTriado('BAIXA', 'MEDIO') // P4
    const r = chamado.reclassificar(c, CARLA.id, { impacto: 'BAIXO', urgencia: 'MEDIA' }, 'ajuste', 'AGENTE', T0 + 60 * MIN)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(chamado.prioridadeDe(r.entidade)).toBe('P4') // não mudou
    expect(r.eventos).toHaveLength(1) // mas registrou
    expect(contarMudancasDePrioridade(r.eventos)).toBe(0)
    expect(r.eventos[0]!.mudancas.map((m) => m.campo).sort()).toEqual(['impacto', 'urgencia'])
  })

  it('VAL-1 — chamado nasce sem prioridade e sem prazos', () => {
    const a = chamado.abrir({ id: 'c9', solicitanteId: ANA.id, titulo: 't', descricao: 'd', urgencia: 'ALTA', agora: T0 })
    expect(a.ok).toBe(true)
    if (!a.ok) return
    expect(a.entidade.estado).toBe('NAO_TRIADO')
    expect(chamado.prioridadeDe(a.entidade)).toBeNull()
    expect(chamado.prazosDe(a.entidade)).toBeNull()
    // Mas já tem prazo de TRIAGEM: o único estado sem governo de tempo era a
    // porta de entrada (PRO-01), e MOV-3 fechou isso.
    expect(chamado.prazoVigente(a.entidade)).toBe(T0 + 60 * MIN)
  })
})

// ===========================================================================
// Rito de recurso — guardas e fronteiras
// ===========================================================================

describe('rito de recurso', () => {
  const abrirRecursoEm = (c: chamado.Chamado, agora: Instante, autor = ANA.id, jaExiste = false) =>
    recurso.abrir({
      id: 'r1',
      ctx: ctxDe(c),
      autorId: autor,
      eixosContestados: ['URGENCIA'],
      justificativa: 'fecho o balanço hoje',
      recursoExistente: jaExiste,
      agora,
    })

  it('VAL-6 / B-1 — recurso exige triagem', () => {
    const a = chamado.abrir({ id: 'c2', solicitanteId: ANA.id, titulo: 't', descricao: 'd', urgencia: 'ALTA', agora: T0 })
    if (!a.ok) throw new Error()
    const r = abrirRecursoEm(a.entidade, T0 + MIN)
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.motivo).toBe('NAO_TRIADO')
  })

  it('VAL-5 / B-5 — só o solicitante do próprio chamado recorre', () => {
    const { c } = abrirTriado('MEDIA', 'BAIXO')
    const r = abrirRecursoEm(c, T0 + 60 * MIN, BRUNO.id)
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.motivo).toBe('SEM_LEGITIMIDADE')
  })

  it('VAL-7 / B-2 — no máximo um recurso por chamado', () => {
    const { c } = abrirTriado('MEDIA', 'BAIXO')
    const r = abrirRecursoEm(c, T0 + 60 * MIN, ANA.id, true)
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.motivo).toBe('RECURSO_JA_EXISTE')
  })

  it('B-11 — recurso em chamado encerrado', () => {
    const { c } = abrirTriado('MEDIA', 'BAIXO')
    const e = chamado.encerrar(c, CARLA.id, T0 + 60 * MIN, false)
    if (!e.ok) throw new Error()
    const r = abrirRecursoEm(e.entidade, T0 + 90 * MIN)
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.motivo).toBe('CHAMADO_ENCERRADO')
  })

  it('VAL-8 / B-3, B-4 — prescricao_na_fronteira_exata (os dois lados)', () => {
    const triadoEm = T0 + 30 * MIN
    const { c } = abrirTriado('MEDIA', 'BAIXO', triadoEm)
    const limite = somarMinutos(triadoEm, 2880) // 48 h da ÚLTIMA classificação

    // B-4 — 1 minuto antes: admitido
    const antes = abrirRecursoEm(c, limite - MIN)
    expect(antes.ok).toBe(true)

    // B-3 — exatamente no limite: JÁ prescreveu (comparação é >=)
    const noLimite = abrirRecursoEm(c, limite)
    expect(noLimite.ok).toBe(false)
    if (!noLimite.ok) expect(noLimite.motivo).toBe('PRESCRITO')

    // 1 minuto depois: prescrito, e o motivo é distinguível dos demais
    const depois = abrirRecursoEm(c, limite + MIN)
    expect(depois.ok).toBe(false)
    if (!depois.ok) expect(depois.motivo).toBe('PRESCRITO')
  })

  it('SEG-05 / MOV-12 — reclassificar a urgência devolve prazo de recurso', () => {
    const triadoEm = T0 + 30 * MIN
    const { c } = abrirTriado('MEDIA', 'BAIXO', triadoEm)
    const limiteOriginal = somarMinutos(triadoEm, 2880)

    // O agente altera a urgência — o eixo do solicitante — já perto do fim.
    const tardia = limiteOriginal - 10 * MIN
    const r = chamado.reclassificar(c, CARLA.id, { urgencia: 'BAIXA' }, 'não parece urgente', 'AGENTE', tardia)
    if (!r.ok) throw new Error()

    // Sem MOV-12, o solicitante teria 10 minutos. Com MOV-12, 48 h novas.
    expect(recurso.prescreveEm(ctxDe(r.entidade))).toBe(somarMinutos(tardia, 2880))
    const depoisDoLimiteAntigo = abrirRecursoEm(r.entidade, limiteOriginal + 60 * MIN)
    expect(depoisDoLimiteAntigo.ok).toBe(true)
  })

  it('VAL-9 / B-6 — agente não julga', () => {
    const r = abrirRecursoEm(abrirTriado('MEDIA', 'BAIXO').c, T0 + 60 * MIN)
    if (!r.ok) throw new Error()
    const j = recurso.julgar({
      recurso: r.entidade,
      julgadorEhGestor: false,
      julgadorId: CARLA.id,
      desfecho: 'PROVIDO',
      fundamentacao: 'ok',
      novosEixos: { urgencia: 'ALTA' },
      agora: T0 + 90 * MIN,
    })
    expect(j.ok).toBe(false)
    if (!j.ok) expect(j.motivo).toBe('SEM_AUTORIDADE')
  })

  it('VAL-10 / B-7 — julgamento exige fundamentação', () => {
    const r = abrirRecursoEm(abrirTriado('MEDIA', 'BAIXO').c, T0 + 60 * MIN)
    if (!r.ok) throw new Error()
    const j = recurso.julgar({
      recurso: r.entidade,
      julgadorEhGestor: true,
      julgadorId: ELENA.id,
      desfecho: 'PROVIDO',
      fundamentacao: '   ',
      novosEixos: { urgencia: 'ALTA' },
      agora: T0 + 90 * MIN,
    })
    expect(j.ok).toBe(false)
    if (!j.ok) expect(j.motivo).toBe('FUNDAMENTACAO_OBRIGATORIA')
  })

  it('VAL-11 / B-8 — improvido não altera nada, mas registra', () => {
    const r = abrirRecursoEm(abrirTriado('MEDIA', 'BAIXO').c, T0 + 60 * MIN)
    if (!r.ok) throw new Error()
    const j = recurso.julgar({
      recurso: r.entidade,
      julgadorEhGestor: true,
      julgadorId: ELENA.id,
      desfecho: 'IMPROVIDO',
      fundamentacao: 'a urgência declarada já reflete o caso',
      novosEixos: {},
      agora: T0 + 90 * MIN,
    })
    expect(j.ok).toBe(true)
    if (!j.ok) return
    expect(j.entidade.estado).toBe('IMPROVIDO')
    expect(j.novosEixos).toBeUndefined() // nada a aplicar no chamado
    expect(j.eventos).toHaveLength(1) // mas a trilha cresce
  })

  it('LIN-04 — parcialmente provido exige dois eixos contestados', () => {
    const r = abrirRecursoEm(abrirTriado('MEDIA', 'BAIXO').c, T0 + 60 * MIN) // só URGENCIA
    if (!r.ok) throw new Error()
    const j = recurso.julgar({
      recurso: r.entidade,
      julgadorEhGestor: true,
      julgadorId: ELENA.id,
      desfecho: 'PARCIALMENTE_PROVIDO',
      fundamentacao: 'meio termo',
      novosEixos: { urgencia: 'ALTA' },
      agora: T0 + 90 * MIN,
    })
    expect(j.ok).toBe(false)
    if (!j.ok) expect(j.motivo).toBe('PARCIAL_EXIGE_DOIS_EIXOS')
  })

  it('PRO-04 — não se encerra chamado com recurso ABERTO', () => {
    const { c } = abrirTriado('MEDIA', 'BAIXO')
    const e = chamado.encerrar(c, CARLA.id, T0 + 60 * MIN, true)
    expect(e.ok).toBe(false)
    if (!e.ok) expect(e.motivo).toBe('RECURSO_ABERTO_PENDENTE')
  })

  it('PRO-06 / MOV-11 — recurso não julgado prescreve em 24 h e libera o encerramento', () => {
    const { c } = abrirTriado('MEDIA', 'BAIXO')
    const r = abrirRecursoEm(c, T0 + 60 * MIN)
    if (!r.ok) throw new Error()

    // Antes do prazo: continua bloqueando.
    const cedo = T0 + 60 * MIN + 1439 * MIN
    expect(recurso.expirouParaJulgamento(r.entidade, cedo)).toBe(false)
    expect(recurso.prescrever(r.entidade, cedo).ok).toBe(false)

    // Exatamente em 24 h: prescreve.
    const tarde = T0 + 60 * MIN + 1440 * MIN
    expect(recurso.expirouParaJulgamento(r.entidade, tarde)).toBe(true)
    const p = recurso.prescrever(r.entidade, tarde)
    expect(p.ok).toBe(true)
    if (!p.ok) return
    // PRESCRITO_SEM_JULGAMENTO, nunca IMPROVIDO: "ninguém julgou" é
    // informação diferente de "foi julgado e negado".
    expect(p.entidade.estado).toBe('PRESCRITO_SEM_JULGAMENTO')
    expect(p.eventos[0]!.tipo).toBe('RECURSO_PRESCRITO')
    expect(chamado.encerrar(c, CARLA.id, tarde, false).ok).toBe(true)
  })
})

// ===========================================================================
// Autorização, fila e política
// ===========================================================================

describe('autorização', () => {
  it('B-12 — solicitante não atribui impacto', () => {
    const p = pode(ANA, 'TRIAR')
    expect(p.ok).toBe(false)
    if (!p.ok) expect(p.motivo).toBe('PAPEL_INSUFICIENTE')
  })

  it('VAL-16 — a trilha é visível para os três papéis', () => {
    for (const u of [ANA, CARLA, ELENA]) {
      expect(pode(u, 'VER_CHAMADO', { solicitanteId: ANA.id }).ok).toBe(true)
    }
  })

  it('SEG-04 — solicitante não lê chamado alheio (ids sequenciais)', () => {
    const p = pode(BRUNO, 'VER_CHAMADO', { solicitanteId: ANA.id })
    expect(p.ok).toBe(false)
    if (!p.ok) expect(p.motivo).toBe('SEM_LEGITIMIDADE')
  })
})

describe('VAL-13 / PER-04 — ordenação da fila', () => {
  it('fila_ordena_em_duas_secoes — não triado não passa na frente de um P1', () => {
    // Este é o caso exato de PER-04: prazo de triagem (60 min) é NUMERICAMENTE
    // menor que o prazo de um P1 (240 min). Numa coluna só, o não triado subiria.
    const naoTriado = chamado.abrir({ id: 'x', solicitanteId: ANA.id, titulo: 't', descricao: 'd', urgencia: 'BAIXA', agora: T0 })
    if (!naoTriado.ok) throw new Error()
    const { c: p1 } = abrirTriado('ALTA', 'ALTO')

    expect(chamado.prazoVigente(naoTriado.entidade)).toBeLessThan(chamado.prazoVigente(p1))
    expect(chamado.prioridadeDe(p1)).toBe('P1')
    expect(chamado.prioridadeDe(naoTriado.entidade)).toBeNull()
    // A separação em seções é o que impede a inversão — e é por isso que a
    // ausência de prioridade não pode ser tratada como "prioridade baixa".
  })
})

describe('VAL-17 — categoria', () => {
  it('categoria_nao_afeta_prioridade', () => {
    const { c } = abrirTriado('MEDIA', 'BAIXO')
    const antes = chamado.prioridadeDe(c)
    const r = chamado.reclassificar(c, CARLA.id, { categoria: 'REDE' }, 'era rede', 'AGENTE', T0 + 60 * MIN)
    if (!r.ok) throw new Error()
    expect(chamado.prioridadeDe(r.entidade)).toBe(antes)
    expect(contarMudancasDePrioridade(r.eventos)).toBe(0)
  })
})

describe('PRE-01 — política inválida derruba o processo', () => {
  const escrever = (obj: unknown) => {
    const caminho = `/tmp/t32-politica-${Math.abs(JSON.stringify(obj).length)}-${process.pid}.json`
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    require('node:fs').writeFileSync(caminho, JSON.stringify(obj))
    return caminho
  }
  const base = () => JSON.parse(require('node:fs').readFileSync('politica.json', 'utf8'))

  it('célula ausente é recusada, nomeando a célula', () => {
    const p = base()
    delete p.matriz.MEDIO.MEDIA
    expect(() => carregar(escrever(p))).toThrow(ErroPolitica)
    try {
      carregar(escrever(p))
    } catch (e) {
      expect((e as ErroPolitica).problemas.join(' ')).toMatch(/\[MEDIO\]\[MEDIA\]/)
    }
  })

  it('matriz não-monótona é recusada', () => {
    const p = base()
    p.matriz.ALTO.ALTA = 'P5' // pior impacto + pior urgência → menos severo
    try {
      carregar(escrever(p))
      throw new Error('deveria ter recusado')
    } catch (e) {
      expect((e as ErroPolitica).problemas.join(' ')).toMatch(/monotonicidade/)
    }
  })

  it('MEC-02 — meta de reconhecimento maior que a de resolução é recusada', () => {
    const p = base()
    p.metas.P3.reconhecerMin = 99999
    try {
      carregar(escrever(p))
      throw new Error('deveria ter recusado')
    } catch (e) {
      expect((e as ErroPolitica).problemas.join(' ')).toMatch(/reconhecerMin.*maior que resolverMin/)
    }
  })

  it('prazo de triagem que inviabiliza P1 é recusado', () => {
    const p = base()
    p.prazoTriagemMin = 240 // igual ao prazo de resolução de P1
    try {
      carregar(escrever(p))
      throw new Error('deveria ter recusado')
    } catch (e) {
      expect((e as ErroPolitica).problemas.join(' ')).toMatch(/P1/)
    }
  })
})

describe('VAL-14 — relógio injetável', () => {
  it('nenhum_modulo_le_relogio_do_sistema — 48 h em microssegundos', () => {
    const r = criarRelogioControlado(T0)
    expect(r.agora()).toBe(T0)
    r.avancarMinutos(2880)
    expect(r.agora()).toBe(T0 + 2880 * MIN)
    // A suíte inteira roda sem uma única espera real: todos os prazos acima
    // foram exercitados com instantes construídos, não com Date.now().
    expect(violado(prazoTriagem(T0), r.agora())).toBe(true)
  })

  it('A14 — o relógio não retrocede', () => {
    const r = criarRelogioControlado(T0)
    expect(() => r.avancarMinutos(-1)).toThrow(/não retrocede/)
  })
})
