/**
 * Composição do processo. Faz a ligação e nada mais — nenhuma regra mora aqui.
 *
 * Ordem obrigatória: carregar e VALIDAR a política antes de qualquer outra
 * coisa. Se a política for inválida, o processo não sobe (MOV-1): subir com
 * matriz errada priorizaria chamados reais com a regra errada, o que é pior que
 * não subir. A mensagem nomeia a célula ou a meta defeituosa (OBS-01).
 */

import { randomUUID } from 'node:crypto'
import { criarCasosDeUso } from './casos-de-uso.js'
import { carregar, ErroPolitica, instalar } from './configuracao.js'
import { criarServidor } from './api-http.js'
import { relogioDoSistema } from './relogio.js'
import { abrirRepositorio } from './repositorio.js'

const CAMINHO_POLITICA = process.env.T32_POLITICA ?? 'politica.json'
const CAMINHO_BANCO = process.env.T32_BANCO ?? 't32.db'
const CAMINHO_SEED = process.env.T32_SEED ?? 'seed.json'
const PORTA = Number(process.env.PORT ?? 3000)

async function principal(): Promise<void> {
  try {
    const politica = carregar(CAMINHO_POLITICA)
    instalar(politica)
    console.log(`política ${politica.versao} carregada e validada`)
  } catch (e) {
    if (e instanceof ErroPolitica) {
      console.error(`\n[T32] O processo não subirá: a política em ${CAMINHO_POLITICA} é inválida.\n`)
      for (const p of e.problemas) console.error(`  · ${p}`)
      console.error('\nCorrija o arquivo e inicie novamente. Não há default de emergência: priorizar')
      console.error('chamados reais com regra errada é pior que não atender.\n')
      process.exit(1)
    }
    throw e
  }

  const repo = abrirRepositorio(CAMINHO_BANCO, CAMINHO_SEED)
  const casos = criarCasosDeUso(repo, relogioDoSistema, () => randomUUID().slice(0, 8))
  const app = criarServidor({
    casos,
    repo,
    segredoCookie: process.env.T32_SEGREDO ?? 'segredo-de-desenvolvimento-t32-nao-use-em-producao',
  })

  await app.listen({ port: PORTA, host: '127.0.0.1' })
  console.log(`T32 triagem em http://127.0.0.1:${PORTA}`)

  const encerrar = async () => {
    await app.close()
    repo.fechar()
    process.exit(0)
  }
  process.on('SIGINT', encerrar)
  process.on('SIGTERM', encerrar)
}

principal().catch((e) => {
  console.error(e)
  process.exit(1)
})
