/**
 * M-02 configuracao — política e só política (MOV-7).
 *
 * Carrega UMA vez na inicialização, VALIDA com diagnóstico nomeado, e congela.
 * Imutável durante a execução do processo (MOV-1): não existe "estado que muda
 * debaixo do sistema em execução", e por isso a pergunta "por que este chamado
 * é P4?" tem resposta única e datada.
 *
 * A `versao` é o HASH DO CONTEÚDO, nunca declarada à mão (CTL-03): dois
 * conteúdos distintos não podem compartilhar versão, e ninguém precisa lembrar
 * de incrementar nada.
 *
 * O seed NÃO mora aqui (ARQ-07) — dado de arranque é lido por M-09 repositorio.
 *
 * Fonte dos valores: specs/technical/matriz-prioridade.md.
 * depends-on: —
 */

import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import type { Impacto, RotuloPrioridade, Urgencia } from './tipos.js'

export type Meta = { readonly reconhecerMin: number; readonly resolverMin: number }

export type Politica = {
  readonly matriz: Readonly<Record<Impacto, Readonly<Record<Urgencia, RotuloPrioridade>>>>
  readonly metas: Readonly<Record<RotuloPrioridade, Meta>>
  readonly prazoTriagemMin: number
  readonly prazoRecorrerMin: number
  readonly prazoJulgarMin: number
  /** sha256 do conteúdo do arquivo, 12 primeiros dígitos hex. */
  readonly versao: string
}

export class ErroPolitica extends Error {
  constructor(public readonly problemas: readonly string[]) {
    super('Política inválida:\n  - ' + problemas.join('\n  - '))
    this.name = 'ErroPolitica'
  }
}

const IMPACTOS: readonly Impacto[] = ['ALTO', 'MEDIO', 'BAIXO']
const URGENCIAS: readonly Urgencia[] = ['ALTA', 'MEDIA', 'BAIXA']
const ROTULOS: readonly RotuloPrioridade[] = ['P1', 'P2', 'P3', 'P4', 'P5']

const severidade = (r: RotuloPrioridade): number => ROTULOS.indexOf(r) + 1

let politicaCarregada: Politica | null = null

/**
 * Carrega e valida. Lança ErroPolitica com a lista COMPLETA de problemas,
 * cada um nomeando a célula ou a meta defeituosa (OBS-01) — falha rápida sem
 * mensagem diagnóstica seria apenas opacidade.
 *
 * Não há default de emergência (RES-03, aceito): subir com matriz errada é
 * pior que não subir, porque priorizaria chamados reais com regra errada.
 */
export function carregar(caminho: string): Politica {
  const bruto = readFileSync(caminho, 'utf8')
  const versao = createHash('sha256').update(bruto).digest('hex').slice(0, 12)

  let json: unknown
  try {
    json = JSON.parse(bruto)
  } catch (e) {
    throw new ErroPolitica([`arquivo ${caminho} não é JSON válido: ${(e as Error).message}`])
  }

  const problemas: string[] = []
  const p = json as Record<string, any>

  // --- matriz: totalidade das 9 células e rótulos válidos --------------------
  const matriz: Record<string, Record<string, RotuloPrioridade>> = {}
  for (const i of IMPACTOS) {
    matriz[i] = {}
    for (const u of URGENCIAS) {
      const v = p?.matriz?.[i]?.[u]
      if (v === undefined || v === null) {
        problemas.push(`matriz: célula ausente em [${i}][${u}] — a matriz deve ser total (9 células)`)
      } else if (!ROTULOS.includes(v)) {
        problemas.push(`matriz: célula [${i}][${u}] = "${v}" fora do domínio P1..P5`)
      } else {
        matriz[i]![u] = v
      }
    }
  }

  // --- matriz: monotonicidade nos dois eixos ---------------------------------
  // Agravar um eixo mantendo o outro nunca pode MELHORAR a prioridade.
  if (problemas.length === 0) {
    for (let i = 0; i < IMPACTOS.length - 1; i++) {
      for (const u of URGENCIAS) {
        const pior = matriz[IMPACTOS[i]!]![u]!
        const melhor = matriz[IMPACTOS[i + 1]!]![u]!
        if (severidade(pior) > severidade(melhor)) {
          problemas.push(
            `matriz: monotonicidade violada — [${IMPACTOS[i]}][${u}]=${pior} é menos severa que ` +
              `[${IMPACTOS[i + 1]}][${u}]=${melhor}, mas o impacto é pior`,
          )
        }
      }
    }
    for (const i of IMPACTOS) {
      for (let u = 0; u < URGENCIAS.length - 1; u++) {
        const pior = matriz[i]![URGENCIAS[u]!]!
        const melhor = matriz[i]![URGENCIAS[u + 1]!]!
        if (severidade(pior) > severidade(melhor)) {
          problemas.push(
            `matriz: monotonicidade violada — [${i}][${URGENCIAS[u]}]=${pior} é menos severa que ` +
              `[${i}][${URGENCIAS[u + 1]}]=${melhor}, mas a urgência é pior`,
          )
        }
      }
    }
  }

  // --- metas: presença, inteiros positivos, faixas coerentes (MEC-02) --------
  const metas: Record<string, Meta> = {}
  for (const r of ROTULOS) {
    const m = p?.metas?.[r]
    if (!m) {
      problemas.push(`metas: prioridade ${r} sem meta declarada`)
      continue
    }
    const rec = m.reconhecerMin
    const res = m.resolverMin
    if (!Number.isInteger(rec) || rec <= 0) {
      problemas.push(`metas.${r}.reconhecerMin = ${rec} — precisa ser inteiro de minutos maior que zero`)
    }
    if (!Number.isInteger(res) || res <= 0) {
      problemas.push(`metas.${r}.resolverMin = ${res} — precisa ser inteiro de minutos maior que zero`)
    }
    if (Number.isInteger(rec) && Number.isInteger(res) && rec > res) {
      problemas.push(
        `metas.${r}: reconhecerMin (${rec}) é maior que resolverMin (${res}) — ` +
          `reconhecer depois de resolver não faz sentido`,
      )
    }
    if (Number.isInteger(rec) && Number.isInteger(res)) metas[r] = { reconhecerMin: rec, resolverMin: res }
  }
  for (let k = 0; k < ROTULOS.length - 1; k++) {
    const a = metas[ROTULOS[k]!]
    const b = metas[ROTULOS[k + 1]!]
    if (a && b && a.resolverMin > b.resolverMin) {
      problemas.push(
        `metas: ${ROTULOS[k]} tem prazo de resolução (${a.resolverMin}) maior que ${ROTULOS[k + 1]} ` +
          `(${b.resolverMin}) — prioridade mais severa não pode ter prazo mais folgado`,
      )
    }
  }

  // --- prazos de triagem e do rito ------------------------------------------
  const triagem = p?.prazoTriagemMin
  if (!Number.isInteger(triagem) || triagem <= 0) {
    problemas.push(`prazoTriagemMin = ${triagem} — precisa ser inteiro de minutos maior que zero`)
  }
  const menorResolucao = metas['P1']?.resolverMin
  if (Number.isInteger(triagem) && menorResolucao !== undefined && triagem >= menorResolucao) {
    problemas.push(
      `prazoTriagemMin (${triagem}) não é menor que o prazo de resolução de P1 (${menorResolucao}) — ` +
        `a triagem consome o orçamento do P1, então um P1 nasceria impossível`,
    )
  }
  const recorrer = p?.rito?.prazoRecorrerMin
  const julgar = p?.rito?.prazoJulgarMin
  if (!Number.isInteger(recorrer) || recorrer <= 0) {
    problemas.push(`rito.prazoRecorrerMin = ${recorrer} — precisa ser inteiro de minutos maior que zero`)
  }
  if (!Number.isInteger(julgar) || julgar <= 0) {
    problemas.push(`rito.prazoJulgarMin = ${julgar} — precisa ser inteiro de minutos maior que zero`)
  }

  if (problemas.length > 0) throw new ErroPolitica(problemas)

  return Object.freeze({
    matriz: Object.freeze(matriz) as Politica['matriz'],
    metas: Object.freeze(metas) as Politica['metas'],
    prazoTriagemMin: triagem as number,
    prazoRecorrerMin: recorrer as number,
    prazoJulgarMin: julgar as number,
    versao,
  })
}

/** Instala a política do processo. Chamado uma vez, na inicialização. */
export function instalar(politica: Politica): void {
  politicaCarregada = politica
}

/** A política vigente. Imutável durante toda a execução (A16: mudar exige reiniciar). */
export function politica(): Politica {
  if (!politicaCarregada) throw new Error('configuracao: política não instalada — chame instalar() na inicialização')
  return politicaCarregada
}

export const matriz = () => politica().matriz
export const metas = () => politica().metas
export const prazoTriagem = () => politica().prazoTriagemMin
export const prazosRito = () => ({
  recorrerMin: politica().prazoRecorrerMin,
  julgarMin: politica().prazoJulgarMin,
})
export const versao = () => politica().versao
