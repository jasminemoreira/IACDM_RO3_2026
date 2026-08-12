/**
 * M-12 web-ui — adaptador de entrada. NENHUMA regra de dominio.
 *
 * HTML renderizado no servidor, formularios, zero JavaScript de cliente.
 *
 * Seguranca (achados da Fase 2):
 *  SEC-01 token CSRF por sessao, exigido em todo POST, comparado em tempo constante.
 *  SEC-02 TODO dado vindo de certificado passa por `escapar` — subject, issuer e SAN
 *         sao controlados por quem opera o host varrido, nao por nos.
 *  SEC-03 bind fixo em 127.0.0.1 — a aplicacao e local, nunca de rede.
 *  SEC-05 cookie HttpOnly; SameSite=Strict e sessao com expiracao por inatividade.
 *  SEC-10 rotacao do identificador de sessao apos autenticar (fixacao de sessao).
 *
 * Divida conhecida e aceita (ARC-07): sessao, CSRF, roteamento e render convivem
 * aqui porque separa-los criaria um 13o modulo, acima do limite de 12 do enunciado.
 */

import http from 'node:http';
import { randomBytes, randomUUID, timingSafeEqual } from 'node:crypto';
import type { Ator } from './autorizacao.ts';
import { LIMIARES_PADRAO, type ErroConfig } from './politica-limiar.ts';
import { cadeiaExpiraAntes } from './certificado.ts';
import * as gov from './caso-governanca.ts';
import { varrer, estadoDoAlvo, type Deps as DepsVarredura } from './caso-varredura.ts';

export const BIND = '127.0.0.1';
/** Sem fonte normativa; decisao de projeto declarada (SCI-05). */
export const SESSAO_MS = 30 * 60 * 1000;

type Sessao = { atorId: string; csrf: string; expiraEm: number };

export function escapar(v: unknown): string {
  return String(v ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

const CSS = `body{font-family:system-ui,sans-serif;margin:0;background:#f6f7f9;color:#1c2024}
header{background:#1c2024;color:#fff;padding:12px 20px;display:flex;gap:18px;align-items:center}
header a{color:#9ec1ff;text-decoration:none} main{padding:20px;max-width:1100px}
table{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 2px #0001}
th,td{border-bottom:1px solid #e3e5e8;padding:8px 10px;text-align:left;font-size:14px}
th{background:#eef0f3} .ok{color:#1a7f37} .aviso{color:#9a6700} .atencao{color:#bc4c00}
.critico,.expirado{color:#cf222e;font-weight:600} .indisponivel{color:#57606a;font-style:italic}
.badge{background:#cf222e;color:#fff;border-radius:10px;padding:1px 8px;font-size:12px}
.escalado{background:#bc4c00;color:#fff;border-radius:10px;padding:1px 8px;font-size:12px}
form{background:#fff;padding:16px;margin:12px 0;box-shadow:0 1px 2px #0001;max-width:640px}
label{display:block;margin:8px 0 2px;font-size:13px} input,select{padding:6px;width:100%;max-width:380px}
button{margin-top:12px;padding:7px 14px;background:#1c2024;color:#fff;border:0;cursor:pointer}
.aviso-box{background:#fff8c5;border:1px solid #d4a72c;padding:10px;margin:12px 0;font-size:13px}
.erro{background:#ffebe9;border:1px solid #cf222e;padding:10px;margin:12px 0}`;

function pagina(titulo: string, ator: Ator | null, corpo: string): string {
  const nav = ator
    ? `<a href="/painel">Painel</a><a href="/trilha">Trilha</a><a href="/alvos/novo">Novo alvo</a>
       <a href="/atores">Atores</a><span style="margin-left:auto">${escapar(ator.nome)} (${escapar(ator.papel)})</span>`
    : '';
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escapar(titulo)} — T21 certificados</title><style>${CSS}</style></head><body>
<header><strong>T21 certificados</strong>${nav}</header><main>${corpo}</main></body></html>`;
}

export function criarServidor(deps: DepsVarredura) {
  const { repo, relogio } = deps;
  const govDeps: gov.Deps = { repo, relogio };
  const sessoes = new Map<string, Sessao>();

  const novaSessao = (atorId: string): string => {
    const sid = randomUUID();
    sessoes.set(sid, { atorId, csrf: randomBytes(32).toString('hex'), expiraEm: Date.now() + SESSAO_MS });
    return sid;
  };

  const lerSessao = (req: http.IncomingMessage): { sid: string; s: Sessao; ator: Ator } | null => {
    const sid = /(?:^|;\s*)sid=([^;]+)/.exec(req.headers.cookie ?? '')?.[1];
    if (!sid) return null;
    const s = sessoes.get(sid);
    if (!s) return null;
    if (s.expiraEm < Date.now()) { sessoes.delete(sid); return null; }
    const ator = repo.atores.buscarPorId(s.atorId);
    if (!ator) { sessoes.delete(sid); return null; }
    s.expiraEm = Date.now() + SESSAO_MS;
    return { sid, s, ator };
  };

  const csrfValido = (s: Sessao, enviado: string): boolean => {
    const a = Buffer.from(s.csrf);
    const b = Buffer.from(enviado);
    return a.length === b.length && timingSafeEqual(a, b);
  };

  const corpoForm = (req: http.IncomingMessage): Promise<URLSearchParams> =>
    new Promise((resolve) => {
      let bruto = '';
      req.on('data', (c) => { bruto += c; if (bruto.length > 64_000) req.destroy(); });
      req.on('end', () => resolve(new URLSearchParams(bruto)));
    });

  const html = (res: http.ServerResponse, corpo: string, status = 200) => {
    res.writeHead(status, { 'content-type': 'text/html; charset=utf-8' });
    res.end(corpo);
  };
  const redirect = (res: http.ServerResponse, para: string) => {
    res.writeHead(303, { location: para });
    res.end();
  };

  const campoCsrf = (s: Sessao) => `<input type="hidden" name="csrf" value="${escapar(s.csrf)}">`;

  // ------------------------------------------------------------------ telas

  const telaLogin = (msg?: string) =>
    pagina('Entrar', null, `${msg ? `<div class="erro">${escapar(msg)}</div>` : ''}
      <form method="post" action="/login"><h2>Entrar</h2>
      <label>Nome</label><input name="nome" autofocus>
      <label>Senha</label><input name="senha" type="password">
      <button>Entrar</button></form>`);

  const telaPainel = (ator: Ator, s: Sessao) => {
    const agora = relogio.agora();
    const ultima = repo.varreduras.ultima();
    const linhas = repo.alvos.listar().map((alvo) => {
      const e = estadoDoAlvo(repo, alvo, agora);
      const destaque = gov.destaqueAtivo(repo, alvo.id);
      const idade = e.obs ? `${Math.floor((agora.getTime() - e.obs.vistoUltimaVez.getTime()) / 60000)} min` : '—';
      return `<tr>
        <td><a href="/alvo/${escapar(alvo.id)}">${escapar(alvo.host)}:${escapar(alvo.porta)}</a></td>
        <td class="${escapar(e.urgencia)}">${escapar(e.urgencia)}${e.semExpiracao ? ' (sem expiração)' : ''}</td>
        <td>${e.obs ? escapar(e.obs.notAfterFolha.toISOString().slice(0, 10)) : '—'}
            ${e.obs && cadeiaExpiraAntes(e.obs) ? ' <span class="badge">cadeia expira antes</span>' : ''}</td>
        <td>${e.configInvalida ? `<span class="badge" title="${escapar(e.configInvalida.tipo)}">config inválida</span>` : ''}
            ${e.escalado ? '<span class="escalado">escalado</span>' : ''}
            ${destaque ? '<span class="badge">troca não autorizada</span>' : ''}
            ${e.trocasNaoAutorizadas > 0 ? `<span title="contador permanente">⚑ ${e.trocasNaoAutorizadas}</span>` : ''}</td>
        <td>${e.pedido ? `<a href="/pedido/${escapar(e.pedido.id)}">${escapar(e.pedido.estado)}</a>` : '—'}</td>
        <td>${escapar(idade)}</td></tr>`;
    });

    return pagina('Painel', ator, `<h2>Inventário</h2>
      <p style="font-size:13px">Última varredura:
        ${ultima ? escapar(ultima.iniciadaEm.toISOString()) : 'nunca'}
        ${ultima?.interrompida ? ' <span class="badge">interrompida</span>' : ''}</p>
      <form method="post" action="/varrer">${campoCsrf(s)}<button>Varrer agora</button></form>
      <table><tr><th>Alvo</th><th>Estado</th><th>Expira</th><th>Sinalizações</th><th>Pedido</th><th>Idade do dado</th></tr>
      ${linhas.join('')}</table>
      ${linhas.length === 0 ? '<p>Nenhum alvo cadastrado. <a href="/alvos/novo">Cadastre o primeiro</a>.</p>' : ''}`);
  };

  const telaNovoAlvo = (ator: Ator, s: Sessao, msg?: string) => {
    const donos = repo.atores.listar()
      .map((a) => `<option value="${escapar(a.id)}">${escapar(a.nome)}</option>`).join('');
    return pagina('Novo alvo', ator, `${msg ? `<div class="erro">${escapar(msg)}</div>` : ''}
      <form method="post" action="/alvos">${campoCsrf(s)}<h2>Cadastrar alvo</h2>
      <label>Host</label><input name="host" required>
      <label>Porta</label><input name="porta" type="number" value="443" required>
      <label>Dono (quem responde por este certificado)</label><select name="donoId">${donos}</select>
      <label>Limiar aviso (dias)</label><input name="aviso" type="number" value="${LIMIARES_PADRAO.aviso}">
      <label>Limiar atenção (dias)</label><input name="atencao" type="number" value="${LIMIARES_PADRAO.atencao}">
      <label>Limiar crítico (dias)</label><input name="critico" type="number" value="${LIMIARES_PADRAO.critico}">
      <button>Cadastrar</button></form>
      <p style="font-size:13px">O alvo precisa falar <strong>TLS direto</strong> na porta.
      STARTTLS (SMTP, IMAP, PostgreSQL) não é suportado — limitação declarada.</p>`);
  };

  const telaAlvo = (ator: Ator, s: Sessao, alvoId: string, msg?: string) => {
    const alvo = repo.alvos.buscarPorId(alvoId);
    if (!alvo) return pagina('Alvo', ator, '<p>Alvo desconhecido.</p>');
    const agora = relogio.agora();
    const e = estadoDoAlvo(repo, alvo, agora);
    const destaque = gov.destaqueAtivo(repo, alvo.id);
    const o = e.obs;
    return pagina(`${alvo.host}:${alvo.porta}`, ator, `
      ${msg ? `<div class="erro">${escapar(msg)}</div>` : ''}
      <h2>${escapar(alvo.host)}:${escapar(alvo.porta)}</h2>
      <table>
        <tr><th>Estado</th><td class="${escapar(e.urgencia)}">${escapar(e.urgencia)}</td></tr>
        <tr><th>Dono</th><td>${escapar(repo.atores.buscarPorId(alvo.donoId)?.nome ?? '—')}</td></tr>
        <tr><th>Limiares</th><td>${alvo.limiares.aviso}/${alvo.limiares.atencao}/${alvo.limiares.critico} dias
            ${e.configInvalida ? `<span class="badge">inválido: ${escapar(e.configInvalida.tipo)}</span>` : ''}</td></tr>
        <tr><th>Subject</th><td>${escapar(o?.subject ?? '—')}</td></tr>
        <tr><th>Issuer</th><td>${escapar(o?.issuer ?? '—')}</td></tr>
        <tr><th>Serial</th><td>${escapar(o?.serial ?? '—')}</td></tr>
        <tr><th>SAN</th><td>${escapar(o?.san.join(', ') ?? '—')}</td></tr>
        <tr><th>Fingerprint</th><td>${escapar(o?.fingerprint256 ?? '—')}</td></tr>
        <tr><th>notBefore</th><td>${escapar(o?.notBefore.toISOString() ?? '—')}</td></tr>
        <tr><th>notAfter (folha)</th><td>${escapar(o?.notAfterFolha.toISOString() ?? '—')}</td></tr>
        <tr><th>notAfter (cadeia)</th><td>${escapar(o?.notAfterEfetivo.toISOString() ?? '—')}
            ${o && cadeiaExpiraAntes(o) ? '<span class="badge">cadeia expira antes da folha</span>' : ''}</td></tr>
        <tr><th>Trocas não autorizadas</th><td>${e.trocasNaoAutorizadas} <em>(contador permanente)</em></td></tr>
      </table>
      ${destaque ? `<form method="post" action="/alvo/${escapar(alvo.id)}/justificar">${campoCsrf(s)}
        <h3>Justificar troca não autorizada</h3>
        <div class="aviso-box">A justificativa <strong>não apaga</strong> o registro: ela é anexada
        referenciando o evento e fica atribuída ao seu nome. O contador acima não zera.</div>
        <label>Justificativa</label><input name="justificativa" required>
        <button>Registrar justificativa</button></form>` : ''}
      ${e.pedido === null
        ? `<form method="post" action="/pedidos">${campoCsrf(s)}
           <input type="hidden" name="alvoId" value="${escapar(alvo.id)}">
           <button>Abrir pedido de renovação</button></form>`
        : `<p>Pedido em aberto: <a href="/pedido/${escapar(e.pedido.id)}">${escapar(e.pedido.estado)}</a></p>`}
      <form method="post" action="/alvos/${escapar(alvo.id)}/limiares">${campoCsrf(s)}
        <h3>Alterar limiares</h3>
        <label>Aviso</label><input name="aviso" type="number" value="${alvo.limiares.aviso}">
        <label>Atenção</label><input name="atencao" type="number" value="${alvo.limiares.atencao}">
        <label>Crítico</label><input name="critico" type="number" value="${alvo.limiares.critico}">
        <button>Alterar</button></form>
      <form method="post" action="/alvos/${escapar(alvo.id)}/remover">${campoCsrf(s)}
        <button>Remover alvo (remoção lógica)</button></form>`);
  };

  const telaPedido = (ator: Ator, s: Sessao, pedidoId: string, msg?: string) => {
    const p = repo.pedidos.buscarPorId(pedidoId);
    if (!p) return pagina('Pedido', ator, '<p>Pedido desconhecido.</p>');
    const alvo = repo.alvos.buscarPorId(p.alvoId);
    const acoes = p.estado === 'pendente'
      ? `<form method="post" action="/pedidos/${escapar(p.id)}/aprovar">${campoCsrf(s)}
           <button>Aprovar</button></form>
         <form method="post" action="/pedidos/${escapar(p.id)}/rejeitar">${campoCsrf(s)}
           <label>Motivo da recusa (obrigatório)</label><input name="motivo" required>
           <button>Rejeitar</button></form>
         <form method="post" action="/pedidos/${escapar(p.id)}/cancelar">${campoCsrf(s)}
           <button>Cancelar pedido</button></form>`
      : '<p>Pedido não está pendente — nenhuma ação disponível.</p>';
    return pagina('Pedido', ator, `${msg ? `<div class="erro">${escapar(msg)}</div>` : ''}
      <h2>Pedido ${escapar(p.id.slice(0, 8))}</h2>
      <table>
        <tr><th>Alvo</th><td>${escapar(alvo ? `${alvo.host}:${alvo.porta}` : '—')}</td></tr>
        <tr><th>Estado</th><td>${escapar(p.estado)}</td></tr>
        <tr><th>Solicitante</th><td>${escapar(repo.atores.buscarPorId(p.solicitanteId)?.nome ?? '—')}</td></tr>
        <tr><th>Aprovador</th><td>${escapar(p.aprovadorId ? repo.atores.buscarPorId(p.aprovadorId)?.nome ?? '—' : '—')}</td></tr>
        <tr><th>Motivo</th><td>${escapar(p.motivo ?? '—')}</td></tr>
        <tr><th>Aberto em</th><td>${escapar(p.abertoEm.toISOString())}</td></tr>
        <tr><th>Decidido em</th><td>${escapar(p.decididoEm?.toISOString() ?? '—')}</td></tr>
        <tr><th>Fechado em</th><td>${escapar(p.fechadoEm?.toISOString() ?? '—')}</td></tr>
      </table>${acoes}`);
  };

  const telaTrilha = (ator: Ator) => {
    const v = gov.verificarIntegridade(govDeps);
    const linhas = gov.auditar(govDeps).map((e) => `<tr>
      <td>${e.i}</td><td>${escapar(e.tipo)}</td>
      <td>${escapar(e.atorId ? repo.atores.buscarPorId(e.atorId)?.nome ?? e.atorId : 'sistema')}</td>
      <td>${escapar(e.registradoEm.toISOString())}</td>
      <td>${escapar(e.refIndice ?? '')}</td>
      <td><code style="font-size:11px">${escapar(JSON.stringify(e.dados))}</code></td>
      <td><code style="font-size:11px">${escapar(e.hash.slice(0, 12))}</code></td></tr>`);
    return pagina('Trilha', ator, `<h2>Trilha de auditoria</h2>
      <div class="${v.valida ? 'aviso-box' : 'erro'}">
        Verificação da cadeia: <strong>${v.valida ? 'VÁLIDA' : `INVÁLIDA na entrada ${v.quebraNoIndice}`}</strong>.
        Esta garantia é <strong>tamper-evident</strong>, não tamper-proof: ela detecta alteração
        pontual de um registro. Quem controla esta máquina pode reescrever a cadeia inteira de
        forma coerente, e nenhuma verificação local acusaria.
      </div>
      <table><tr><th>#</th><th>Evento</th><th>Ator</th><th>Quando</th><th>Ref</th><th>Dados</th><th>Hash</th></tr>
      ${linhas.join('')}</table>`);
  };

  const telaAtores = (ator: Ator, s: Sessao, msg?: string) => {
    const linhas = repo.atores.listar().map((a) => `<tr>
      <td>${escapar(a.nome)}</td><td>${escapar(a.papel)}</td>
      <td>${a.ativo ? 'ativo' : 'desativado'}</td>
      <td>${a.ativo ? `<form method="post" action="/atores/${escapar(a.id)}/desativar">${campoCsrf(s)}
        <button>Desativar</button></form>` : ''}</td></tr>`);
    return pagina('Atores', ator, `${msg ? `<div class="erro">${escapar(msg)}</div>` : ''}
      <h2>Atores</h2>
      <table><tr><th>Nome</th><th>Papel</th><th>Situação</th><th></th></tr>${linhas.join('')}</table>
      <form method="post" action="/atores">${campoCsrf(s)}<h3>Novo ator</h3>
      <label>Nome</label><input name="nome" required>
      <label>Senha</label><input name="senha" type="password" required>
      <label>Papel</label><select name="papel">
        <option value="solicitante">solicitante</option>
        <option value="aprovador">aprovador</option>
        <option value="auditor">auditor</option></select>
      <button>Criar</button></form>`);
  };

  /**
   * Toda variante tem frase propria. O teste exploratorio da Fase 6 mostrou o custo
   * de nao ter: o operador recebia 'alvo-duplicado' e 'transicao-invalida' — codigo
   * interno vazando para quem so queria saber o que fazer em seguida.
   */
  const msgConfig = (c: ErroConfig): string => {
    switch (c.tipo) {
      case 'limiar-maior-que-vida':
        return `O limiar de ${c.valor} dias (${c.qual}) é maior que a vida total do certificado `
          + `(${Math.floor(c.vidaTotalDias)} dias). Ele dispararia alerta desde a emissão. `
          + `Use um valor menor que ${Math.floor(c.vidaTotalDias)}.`;
      case 'limiares-fora-de-ordem':
        return 'Os limiares precisam estar em ordem decrescente: aviso > atenção > crítico.';
      case 'limiar-nao-positivo':
        return `O limiar "${c.qual}" precisa ser um número de dias maior que zero (recebido: ${c.valor}).`;
    }
  };

  const msgErro = (e: gov.ErroGovernanca): string => {
    switch (e.tipo) {
      case 'config-invalida': return msgConfig(e.causa);
      case 'papel-insuficiente': return `Esta ação exige o papel "${e.exigido}". Sua conta não o tem.`;
      case 'ja-existe-pedido-aberto': return 'Já existe um pedido em aberto para este alvo. Conclua-o antes de abrir outro.';
      case 'motivo-obrigatorio': return 'Informe o motivo da recusa — ele fica registrado na trilha.';
      case 'estado-invalido': return `Não é possível ${e.acao} um pedido que está "${e.de}".`;
      case 'alvo-duplicado': return 'Este host e porta já estão cadastrados.';
      case 'alvo-desconhecido': return 'Alvo não encontrado.';
      case 'pedido-desconhecido': return 'Pedido não encontrado.';
      case 'ator-desconhecido': return 'Ator não encontrado.';
      case 'sem-troca-para-justificar': return 'Não há troca não autorizada pendente de justificativa neste alvo.';
      case 'relogio-retrocedeu':
        return `Operação recusada: o relógio da máquina retrocedeu ${Math.round(e.deltaMs / 1000)} s `
          + 'em relação ao último registro da trilha. Corrija o relógio antes de continuar.';
    }
  };

  // ------------------------------------------------------------------ rotas

  return http.createServer((req, res) => {
    void (async () => {
      const url = new URL(req.url ?? '/', `http://${BIND}`);
      const rota = url.pathname;
      const sessao = lerSessao(req);

      if (rota === '/login' && req.method === 'GET') return html(res, telaLogin());
      if (rota === '/login' && req.method === 'POST') {
        const f = await corpoForm(req);
        const ator = gov.autenticarAtor(govDeps, f.get('nome') ?? '', f.get('senha') ?? '');
        if (!ator) return html(res, telaLogin('Nome ou senha inválidos.'), 401);
        // SEC-10: identificador NOVO apos autenticar.
        const sid = novaSessao(ator.id);
        res.writeHead(303, {
          location: '/painel',
          'set-cookie': `sid=${sid}; HttpOnly; SameSite=Strict; Path=/`,
        });
        return res.end();
      }

      if (!sessao) return redirect(res, '/login');
      const { s, ator } = sessao;

      if (req.method === 'POST') {
        const f = await corpoForm(req);
        if (!csrfValido(s, f.get('csrf') ?? '')) { // SEC-01
          return html(res, pagina('Erro', ator, '<div class="erro">Token CSRF inválido.</div>'), 403);
        }

        if (rota === '/logout') { sessoes.delete(sessao.sid); return redirect(res, '/login'); }

        if (rota === '/varrer') { await varrer(deps); return redirect(res, '/painel'); }

        if (rota === '/alvos') {
          const r = gov.cadastrarAlvo(govDeps, ator.id, f.get('host') ?? '', Number(f.get('porta')),
            f.get('donoId') ?? '', {
              aviso: Number(f.get('aviso')), atencao: Number(f.get('atencao')), critico: Number(f.get('critico')),
            });
          return r.ok ? redirect(res, '/painel') : html(res, telaNovoAlvo(ator, s, msgErro(r.erro)), 400);
        }

        if (rota === '/pedidos') {
          const r = gov.abrirPedido(govDeps, ator, f.get('alvoId') ?? '');
          return r.ok ? redirect(res, `/pedido/${r.valor.id}`)
                      : html(res, telaAlvo(ator, s, f.get('alvoId') ?? '', msgErro(r.erro)), 400);
        }

        const mAlvo = /^\/alvos\/([^/]+)\/(remover|limiares)$/.exec(rota);
        if (mAlvo) {
          const id = mAlvo[1]!;
          const r = mAlvo[2] === 'remover'
            ? gov.removerAlvo(govDeps, ator.id, id)
            : gov.alterarLimiares(govDeps, ator.id, id, {
                aviso: Number(f.get('aviso')), atencao: Number(f.get('atencao')), critico: Number(f.get('critico')),
              });
          return r.ok ? redirect(res, mAlvo[2] === 'remover' ? '/painel' : `/alvo/${id}`)
                      : html(res, telaAlvo(ator, s, id, msgErro(r.erro)), 400);
        }

        const mPedido = /^\/pedidos\/([^/]+)\/(aprovar|rejeitar|cancelar)$/.exec(rota);
        if (mPedido) {
          const id = mPedido[1]!;
          const r = mPedido[2] === 'aprovar' ? gov.aprovarPedido(govDeps, ator, id)
            : mPedido[2] === 'rejeitar' ? gov.rejeitarPedido(govDeps, ator, id, f.get('motivo') ?? '')
            : gov.cancelarPedido(govDeps, ator, id);
          return r.ok ? redirect(res, `/pedido/${id}`) : html(res, telaPedido(ator, s, id, msgErro(r.erro)), 400);
        }

        const mJust = /^\/alvo\/([^/]+)\/justificar$/.exec(rota);
        if (mJust) {
          const id = mJust[1]!;
          const r = gov.justificarTroca(govDeps, ator, id, f.get('justificativa') ?? '');
          return r.ok ? redirect(res, `/alvo/${id}`) : html(res, telaAlvo(ator, s, id, msgErro(r.erro)), 400);
        }

        if (rota === '/atores') {
          const r = gov.novoAtor(govDeps, ator.id, f.get('nome') ?? '', f.get('senha') ?? '',
            (f.get('papel') ?? 'solicitante') as Ator['papel']);
          return r.ok ? redirect(res, '/atores') : html(res, telaAtores(ator, s, msgErro(r.erro)), 400);
        }

        const mDesat = /^\/atores\/([^/]+)\/desativar$/.exec(rota);
        if (mDesat) {
          const r = gov.desativarAtor(govDeps, ator.id, mDesat[1]!);
          return r.ok ? redirect(res, '/atores') : html(res, telaAtores(ator, s, msgErro(r.erro)), 400);
        }
      }

      if (rota === '/' || rota === '/painel') return html(res, telaPainel(ator, s));
      if (rota === '/alvos/novo') return html(res, telaNovoAlvo(ator, s));
      if (rota === '/trilha') return html(res, telaTrilha(ator));
      if (rota === '/atores') return html(res, telaAtores(ator, s));
      const gAlvo = /^\/alvo\/([^/]+)$/.exec(rota);
      if (gAlvo) return html(res, telaAlvo(ator, s, gAlvo[1]!));
      const gPedido = /^\/pedido\/([^/]+)$/.exec(rota);
      if (gPedido) return html(res, telaPedido(ator, s, gPedido[1]!));

      html(res, pagina('Não encontrado', ator, '<p>Rota não encontrada.</p>'), 404);
    })();
  });
}
