/**
 * Composition root — nao e um modulo da arquitetura: e o ponto onde as portas sao
 * ligadas aos adaptadores. Aplicacao SOB DEMANDA (decisao da Fase 0): o operador
 * inicia, usa e encerra. Sem daemon, sem agendador.
 */

import { criarRepositorio } from './repositorio.ts';
import { criarSonda } from './sonda-tls.ts';
import { criarRelogio } from './relogio.ts';
import { criarPrimeiroAprovador, type Deps as DepsGov } from './caso-governanca.ts';
import { reconciliarVarredurasOrfas } from './caso-varredura.ts';
import { criarServidor, BIND } from './web-ui.ts';

const BANCO = process.env['T21_BANCO'] ?? 'certificados.db';
const PORTA = Number(process.env['T21_PORTA'] ?? 8721);

const repo = criarRepositorio(BANCO);
const relogio = criarRelogio();
const deps = { repo, sonda: criarSonda(), relogio };

if (process.argv.includes('--init')) {
  // ASS-06: sem um Aprovador o sistema nasce travado. Este comando o cria.
  const nome = process.argv[process.argv.indexOf('--init') + 1] ?? 'admin';
  const senha = process.argv[process.argv.indexOf('--init') + 2] ?? 'trocar-esta-senha';
  const r = criarPrimeiroAprovador({ repo, relogio } satisfies DepsGov, nome, senha);
  console.log(r.ok ? `Aprovador criado: ${nome}` : `Falhou: ${JSON.stringify(r.erro)}`);
  repo.fechar();
  process.exit(0);
}

// RES-06: varredura que ficou sem `concluida_em` porque o processo morreu.
const orfas = reconciliarVarredurasOrfas(deps);
if (orfas > 0) console.log(`${orfas} varredura(s) marcada(s) como interrompida(s).`);

const servidor = criarServidor(deps);
servidor.listen(PORTA, BIND, () => {
  console.log(`T21 certificados em http://${BIND}:${PORTA}  (banco: ${BANCO})`);
  console.log('Encerre com Ctrl+C. Primeiro uso: npm run init -- <nome> <senha>');
});

const encerrar = () => { servidor.close(); repo.fechar(); process.exit(0); };
process.on('SIGINT', encerrar);
process.on('SIGTERM', encerrar);
