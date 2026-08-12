/**
 * Testes de web-ui — o modulo com mais achados da Fase 2 (14), incluindo dois 🔴.
 *
 * Cobre por REGRESSAO o que so havia sido verificado a mao: SEC-01 (CSRF forja
 * aprovacao), SEC-02 (XSS via campo de certificado), SEC-03 (bind local),
 * SEC-05/SEC-10 (cookie e rotacao de sessao) e UX-01 (a tela de cadastro existe).
 *
 * O certificado de fixture `cert-xss.pem` tem um payload no subject: quem controla
 * um host varrido controla esse texto, e ele e renderizado na tela do aprovador.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import tls from 'node:tls';
import { readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import type { AddressInfo } from 'node:net';

import { criarRepositorio } from '../src/repositorio.ts';
import { criarSonda } from '../src/sonda-tls.ts';
import { criarRelogio } from '../src/relogio.ts';
import { criarServidor, escapar, BIND } from '../src/web-ui.ts';
import * as gov from '../src/caso-governanca.ts';
import { LIMIARES_PADRAO } from '../src/politica-limiar.ts';

const fx = (n: string) => readFileSync(new URL(`../specs/datasets/${n}`, import.meta.url));
const XSS = { key: fx('key-xss.pem'), cert: fx('cert-xss.pem') };

async function comApp(fn: (ctx: {
  base: string; repo: ReturnType<typeof criarRepositorio>; govDeps: gov.Deps; portaTls: number;
}) => Promise<void>) {
  const banco = join(tmpdir(), `t21web-${randomUUID()}.db`);
  const alvoTls = tls.createServer(XSS, (s) => s.end());
  await new Promise<void>((r) => alvoTls.listen(0, '127.0.0.1', r));
  const portaTls = (alvoTls.address() as AddressInfo).port;

  const repo = criarRepositorio(banco);
  const relogio = criarRelogio();
  const app = criarServidor({ repo, sonda: criarSonda(), relogio });
  await new Promise<void>((r) => app.listen(0, BIND, r));
  const base = `http://${BIND}:${(app.address() as AddressInfo).port}`;

  try {
    await fn({ base, repo, govDeps: { repo, relogio }, portaTls });
  } finally {
    app.close();
    repo.fechar();
    alvoTls.close();
    rmSync(banco, { force: true });
  }
}

const cookieDe = (r: Response) => /sid=([^;]+)/.exec(r.headers.get('set-cookie') ?? '')?.[1] ?? '';
const csrfDe = (html: string) => /name="csrf" value="([^"]+)"/.exec(html)?.[1] ?? '';

async function logar(base: string, nome: string, senha: string) {
  const r = await fetch(`${base}/login`, {
    method: 'POST', redirect: 'manual',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ nome, senha }),
  });
  return { resposta: r, sid: cookieDe(r) };
}

test('escapar neutraliza os metacaracteres de HTML', () => {
  assert.equal(escapar('<img src=x onerror=alert(1)>'), '&lt;img src=x onerror=alert(1)&gt;');
  assert.equal(escapar('a"b\'c&d'), 'a&quot;b&#39;c&amp;d');
});

test('sem sessao, qualquer tela redireciona para /login', async () => {
  await comApp(async ({ base }) => {
    for (const rota of ['/', '/painel', '/trilha', '/atores', '/alvos/novo']) {
      const r = await fetch(base + rota, { redirect: 'manual' });
      assert.equal(r.status, 303, `${rota} deveria redirecionar`);
      assert.equal(r.headers.get('location'), '/login');
    }
  });
});

test('(negativo) senha errada devolve 401 e nao cria sessao', async () => {
  await comApp(async ({ base, govDeps }) => {
    assert.ok(gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123').ok);
    const { resposta, sid } = await logar(base, 'ana', 'senha-ERRADA');
    assert.equal(resposta.status, 401);
    assert.equal(sid, '');
  });
});

test('SEC-05/SEC-10: login emite cookie HttpOnly + SameSite e identificador NOVO', async () => {
  await comApp(async ({ base, govDeps }) => {
    assert.ok(gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123').ok);
    const um = await logar(base, 'ana', 'senha-forte-123');
    const cabecalho = um.resposta.headers.get('set-cookie') ?? '';
    assert.match(cabecalho, /HttpOnly/);
    assert.match(cabecalho, /SameSite=Strict/);
    assert.equal(um.resposta.headers.get('location'), '/painel');

    const dois = await logar(base, 'ana', 'senha-forte-123');
    assert.notEqual(um.sid, dois.sid, 'cada autenticacao emite identificador novo (fixacao de sessao)');
  });
});

test('SEC-01 (negativo): POST sem token CSRF valido e recusado com 403', async () => {
  await comApp(async ({ base, govDeps }) => {
    assert.ok(gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123').ok);
    const { sid } = await logar(base, 'ana', 'senha-forte-123');

    for (const corpo of [{}, { csrf: 'token-forjado' }]) {
      const r = await fetch(`${base}/varrer`, {
        method: 'POST', redirect: 'manual',
        headers: { cookie: `sid=${sid}`, 'content-type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(corpo as Record<string, string>),
      });
      assert.equal(r.status, 403, 'sem CSRF valido, nenhuma acao de escrita passa');
    }
  });
});

test('SEC-01: com o token da propria sessao, o POST passa', async () => {
  await comApp(async ({ base, govDeps }) => {
    assert.ok(gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123').ok);
    const { sid } = await logar(base, 'ana', 'senha-forte-123');
    const painel = await (await fetch(`${base}/painel`, { headers: { cookie: `sid=${sid}` } })).text();
    const r = await fetch(`${base}/varrer`, {
      method: 'POST', redirect: 'manual',
      headers: { cookie: `sid=${sid}`, 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ csrf: csrfDe(painel) }),
    });
    assert.equal(r.status, 303);
  });
});

test('UX-01: a tela de cadastro de alvo existe e tem os campos do caso de uso UC-1', async () => {
  await comApp(async ({ base, govDeps }) => {
    assert.ok(gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123').ok);
    const { sid } = await logar(base, 'ana', 'senha-forte-123');
    const html = await (await fetch(`${base}/alvos/novo`, { headers: { cookie: `sid=${sid}` } })).text();
    for (const campo of ['name="host"', 'name="porta"', 'name="donoId"', 'name="critico"']) {
      assert.ok(html.includes(campo), `falta ${campo}`);
    }
  });
});

test('SEC-02 (negativo): payload no subject do certificado NAO vira HTML executavel', async () => {
  await comApp(async ({ base, repo, govDeps, portaTls }) => {
    const ana = gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123');
    assert.ok(ana.ok);
    const alvo = gov.cadastrarAlvo(govDeps, ana.valor.id, '127.0.0.1', portaTls, ana.valor.id, LIMIARES_PADRAO);
    assert.ok(alvo.ok);

    const { sid } = await logar(base, 'ana', 'senha-forte-123');
    const painel = await (await fetch(`${base}/painel`, { headers: { cookie: `sid=${sid}` } })).text();
    const r = await fetch(`${base}/varrer`, {
      method: 'POST', redirect: 'manual',
      headers: { cookie: `sid=${sid}`, 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ csrf: csrfDe(painel) }),
    });
    assert.equal(r.status, 303);

    const obs = repo.alvos.ultimaObservacao(alvo.valor.id);
    assert.ok(obs?.subject.includes('<img'), 'a fixture precisa mesmo trazer o payload no subject');

    const detalhe = await (await fetch(`${base}/alvo/${alvo.valor.id}`, { headers: { cookie: `sid=${sid}` } })).text();
    assert.ok(detalhe.includes('&lt;img'), 'o payload tem de aparecer escapado');
    assert.ok(!detalhe.includes('<img src=x'), 'e nunca como tag viva');
    assert.ok(!/onerror=alert\(1\)>/.test(detalhe.replace(/&[a-z]+;/g, '')) || detalhe.includes('&lt;img'),
      'nenhum atributo de evento executavel escapa para o HTML');
  });
});

/**
 * Regressao das mensagens — achado do teste exploratorio da Fase 6.
 * O defeito nao era estetico: 'rejeitar sem motivo' devolvia 'transicao-invalida'
 * porque a camada de aplicacao colapsava todo erro de transicao num tipo so,
 * DESCARTANDO a causa que o dominio ja conhecia.
 */
test('UX-05: as mensagens de erro sao frases, nunca codigo interno vazando', async () => {
  await comApp(async ({ base, govDeps, portaTls }) => {
    const ana = gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123');
    assert.ok(ana.ok);
    const alvo = gov.cadastrarAlvo(govDeps, ana.valor.id, '127.0.0.1', portaTls, ana.valor.id, LIMIARES_PADRAO);
    assert.ok(alvo.ok);
    const { sid } = await logar(base, 'ana', 'senha-forte-123');
    const cab = { cookie: `sid=${sid}`, 'content-type': 'application/x-www-form-urlencoded' };
    const postar = async (rota: string, corpo: Record<string, string>, csrfToken: string) =>
      (await fetch(base + rota, { method: 'POST', redirect: 'manual', headers: cab,
        body: new URLSearchParams({ ...corpo, csrf: csrfToken }) })).text();

    const novo = await (await fetch(`${base}/alvos/novo`, { headers: { cookie: `sid=${sid}` } })).text();
    const t = csrfDe(novo);

    const dup = await postar('/alvos', { host: '127.0.0.1', porta: String(portaTls),
      donoId: ana.valor.id, aviso: '90', atencao: '60', critico: '30' }, t);
    assert.ok(dup.includes('já estão cadastrados'), 'host duplicado precisa de frase, nao de "alvo-duplicado"');
    assert.ok(!dup.includes('alvo-duplicado'), 'o codigo interno nao pode aparecer na tela');

    const pedido = gov.abrirPedido(govDeps, ana.valor, alvo.valor.id);
    assert.ok(pedido.ok);
    const tela = await (await fetch(`${base}/pedido/${pedido.valor.id}`, { headers: { cookie: `sid=${sid}` } })).text();
    const rej = await postar(`/pedidos/${pedido.valor.id}/rejeitar`, { motivo: '   ' }, csrfDe(tela));
    assert.ok(rej.includes('Informe o motivo da recusa'),
      'a causa real (motivo obrigatorio) tem de chegar na tela');
    assert.ok(!rej.includes('transicao-invalida'), 'a causa nao pode ser descartada no caminho');
  });
});

test('CA-5 na UI: a mensagem diz o numero e o que fazer, nao so o nome do erro', async () => {
  await comApp(async ({ base, govDeps, portaTls }) => {
    const ana = gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123');
    assert.ok(ana.ok);
    const alvo = gov.cadastrarAlvo(govDeps, ana.valor.id, '127.0.0.1', portaTls,
      ana.valor.id, { aviso: 30, atencao: 20, critico: 10 });
    assert.ok(alvo.ok);
    const { sid } = await logar(base, 'ana', 'senha-forte-123');

    const painel = await (await fetch(`${base}/painel`, { headers: { cookie: `sid=${sid}` } })).text();
    await fetch(`${base}/varrer`, { method: 'POST', redirect: 'manual',
      headers: { cookie: `sid=${sid}`, 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ csrf: csrfDe(painel) }) });

    const tela = await (await fetch(`${base}/alvo/${alvo.valor.id}`, { headers: { cookie: `sid=${sid}` } })).text();
    const r = await (await fetch(`${base}/alvos/${alvo.valor.id}/limiares`, {
      method: 'POST', redirect: 'manual',
      headers: { cookie: `sid=${sid}`, 'content-type': 'application/x-www-form-urlencoded' },
      // O host de teste serve cert-xss.pem, de 100 dias: para violar o invariante
      // o limiar precisa ser MAIOR que 100. Com 90/60/30 a configuracao seria valida
      // e o teste passaria a exercitar o caminho feliz sem avisar.
      body: new URLSearchParams({ csrf: csrfDe(tela), aviso: '200', atencao: '150', critico: '120' }),
    })).text();

    assert.ok(r.includes('é maior que a vida total do certificado'));
    assert.ok(r.includes('100 dias'), 'a mensagem tem de dizer QUAL e a vida do certificado');
    assert.ok(r.includes('Use um valor menor que 100'), 'e o que fazer em seguida');
  });
});

test('CA-4 na UI: a tela de trilha declara tamper-evident, nao tamper-proof', async () => {
  await comApp(async ({ base, govDeps }) => {
    assert.ok(gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123').ok);
    const { sid } = await logar(base, 'ana', 'senha-forte-123');
    const html = await (await fetch(`${base}/trilha`, { headers: { cookie: `sid=${sid}` } })).text();
    assert.ok(html.includes('VÁLIDA'));
    assert.ok(html.includes('tamper-evident'), 'a UI nao pode prometer mais do que o sistema garante');
    assert.ok(html.includes('reescrever a cadeia inteira'));
  });
});
