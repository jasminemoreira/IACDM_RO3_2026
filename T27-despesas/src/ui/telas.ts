/**
 * M-12 ui-web (parte 2) — as 6 telas de specs/design/telas.md, server-rendered.
 * Sem build, sem SPA. Identidade viaja no parâmetro `u` a cada requisição (V(4)/T4), nunca
 * em cookie — é o que permite duas abas com dois usuários (achado UX-08, exigido por CA-3b).
 */
import { type Html, html } from "./render.js";
import { formatarBRL } from "../dominio/matriz-doa.js";
import type { Papel } from "../dominio/matriz-doa.js";
import type { Usuario } from "../dominio/portas.js";
import type { Despesa } from "../dominio/despesa.js";
import type { Delegacao } from "../dominio/delegacao.js";
import type { Evento } from "../dominio/trilha.js";
import type { ItemBandeja } from "../dominio/bandeja.js";
import type { Autoridade } from "../dominio/autoridade.js";

const CSS = `
:root{--l:#e2e2e6;--t:#1a1a1c;--b:#fbfbfd;--a:#2f5eaa;--w:#8a5a00;--e:#a33}
*{box-sizing:border-box}
body{font:15px/1.5 system-ui,sans-serif;margin:0;background:var(--b);color:var(--t)}
header{background:#fff;border-bottom:1px solid var(--l);padding:.6rem 1rem;display:flex;
  gap:1rem;align-items:baseline;flex-wrap:wrap;position:sticky;top:0}
header .eu{font-weight:600}
nav a{margin-right:.9rem;color:var(--a)}
main{max-width:56rem;margin:0 auto;padding:1.2rem 1rem 4rem}
h1{font-size:1.35rem;margin:.2rem 0 1rem}
h2{font-size:1.05rem;margin:1.6rem 0 .5rem}
table{border-collapse:collapse;width:100%;background:#fff}
th,td{border:1px solid var(--l);padding:.45rem .6rem;text-align:left;vertical-align:top}
th{background:#f2f2f5;font-weight:600}
.tag{font-size:.75rem;padding:.1rem .4rem;border:1px solid var(--l);border-radius:3px;background:#f6f6f9}
.aviso{border:1px solid var(--w);background:#fff8e8;padding:.7rem .9rem;margin:1rem 0;border-radius:4px}
.erro{border:1px solid var(--e);background:#fdeeee;padding:.7rem .9rem;margin:1rem 0;border-radius:4px}
.ok{border:1px solid #2a7;background:#eefaf3;padding:.7rem .9rem;margin:1rem 0;border-radius:4px}
form.linha{display:flex;gap:.5rem;flex-wrap:wrap;align-items:end;margin:.6rem 0}
label{display:block;font-size:.82rem;color:#555}
input,select{padding:.4rem;border:1px solid var(--l);border-radius:3px;font:inherit}
button{padding:.45rem .9rem;border:1px solid var(--a);background:var(--a);color:#fff;
  border-radius:3px;font:inherit;cursor:pointer}
button.sec{background:#fff;color:var(--t);border-color:var(--l)}
a{color:var(--a)}
small{color:#666}
`;

/**
 * Único `Html` construído sem passar pelo template marcado, e deliberadamente: `CSS` é uma
 * constante literal deste módulo, não dado de usuário — nenhuma entrada externa chega aqui.
 * Não existe função pública que transforme string em `Html`, justamente para que não haja
 * caminho de interpolação crua disponível ao resto do código (achado LING-06).
 */
const ESTILO: Html = { __html: `<style>${CSS}</style>` };

export function pagina(titulo: string, eu: Usuario | null, papel: Papel | null, corpo: Html): Html {
  return html`<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${titulo} — T27 Despesas</title>${ESTILO}</head>
<body>
<header>
  <strong>T27 · Despesas</strong>
  ${eu && papel
    ? html`<span class="eu">Você é: ${eu.nome} (${papel.nome}, alçada ${formatarBRL(papel.limiteCentavos)})</span>
      <nav><a href="/bandeja?u=${eu.id}">Bandeja</a><a href="/nova?u=${eu.id}">Nova despesa</a>
      <a href="/delegacoes?u=${eu.id}">Delegações</a><a href="/auditoria?u=${eu.id}">Auditoria</a>
      <a href="/">Trocar usuário</a></nav>`
    : html`<span class="eu">Nenhum usuário selecionado</span>`}
</header>
<main><h1>${titulo}</h1>${corpo}</main></body></html>`;
}

export const erroBox = (mensagem: string | null): Html =>
  mensagem ? html`<p class="erro">${mensagem}</p>` : html``;
export const okBox = (mensagem: string | null): Html =>
  mensagem ? html`<p class="ok">${mensagem}</p>` : html``;

/** T1 — Seleção de usuário. */
export function t1SelecaoUsuario(usuarios: readonly Usuario[], papeis: readonly Papel[]): Html {
  const linhas = usuarios.map((u) => {
    const p = papeis.find((x) => x.id === u.papelId);
    return html`<li><a href="/bandeja?u=${u.id}">${u.nome}</a> — ${p?.nome ?? u.papelId}
      (aprova até ${formatarBRL(p?.limiteCentavos ?? 0)})</li>`;
  });
  return html`<p>Quem é você? A identidade não tem senha — o objeto deste sistema é alçada e
    delegação, não autenticação.</p>
    <ul>${linhas}</ul>
    <p><small>Para operar dois usuários lado a lado (delegante e delegado), abra duas abas
    comuns: a identidade viaja no endereço, não em cookie.</small></p>`;
}

/** T2 — Nova despesa. */
export function t2NovaDespesa(eu: Usuario, nonce: string, erro: string | null): Html {
  return html`${erroBox(erro)}
    <form method="POST" action="/despesas" class="linha">
      <input type="hidden" name="u" value="${eu.id}">
      <input type="hidden" name="nonce" value="${nonce}">
      <div><label for="valor">Valor (R$)</label>
        <input id="valor" name="valor" required placeholder="80.000,00" size="14"></div>
      <div><label for="descricao">Descrição</label>
        <input id="descricao" name="descricao" required size="40" placeholder="Servidor de backup"></div>
      <button type="submit">Enviar para aprovação</button>
    </form>`;
}

/** T3 — Bandeja, FIFO, mais antiga no topo. */
export function t3Bandeja(eu: Usuario, itens: readonly ItemBandeja[], aviso: string | null): Html {
  if (itens.length === 0) {
    return html`${okBox(aviso)}<p>Nenhuma pendência sua no momento.</p>`;
  }
  const linhas = itens.map(
    (i) => html`<tr>
      <td>${i.despesa.criadaEm.slice(0, 16).replace("T", " ")}</td>
      <td>${formatarBRL(i.despesa.valorCentavos)}</td>
      <td>${i.despesa.descricao}</td>
      <td>${i.origem.tipo === "propria"
        ? html`<span class="tag">PRÓPRIA</span>`
        : html`<span class="tag">EM NOME DE ${i.origem.emNomeDe.nome.toUpperCase()}</span>`}</td>
      <td><a href="/despesas/${i.despesa.id}?u=${eu.id}">Abrir</a></td>
    </tr>`,
  );
  return html`${okBox(aviso)}
    <p><small>Ordenadas: mais antiga primeiro.</small></p>
    <table><thead><tr><th>Criada</th><th>Valor</th><th>Descrição</th><th>Origem</th><th></th></tr></thead>
    <tbody>${linhas}</tbody></table>`;
}

/** T4 — Detalhe + decisão. O bloco de autoridade é obrigatório antes do clique (achado UX-01). */
export function t4Detalhe(entrada: {
  eu: Usuario;
  nonce: string;
  despesa: Despesa;
  solicitante: Usuario;
  cadeia: readonly Papel[];
  eventos: readonly Evento[];
  autoridade: Autoridade | null;
  motivoSemAutoridade: string | null;
  usuarios: readonly Usuario[];
  delegacoes: readonly Delegacao[];
  erro: string | null;
}): Html {
  const { despesa, cadeia, eventos, eu } = entrada;
  const nomeDe = (id: string | null) =>
    id ? (entrada.usuarios.find((u) => u.id === id)?.nome ?? id) : "—";
  const papelAtual = despesa.indiceCadeia !== null ? cadeia[despesa.indiceCadeia] : null;

  const blocoAutoridade = entrada.autoridade
    ? entrada.autoridade.emNomeDe
      ? html`<div class="aviso">⚠ Você está decidindo <strong>EM NOME DE
          ${entrada.autoridade.emNomeDe.nome}</strong> (${papelAtual?.nome}), exercendo a alçada
          dele(a): <strong>${formatarBRL(entrada.autoridade.limiteExercidoCentavos)}</strong>.
          ${(() => {
            const d = entrada.delegacoes.find((x) => x.id === entrada.autoridade!.delegacaoId);
            return d
              ? html`<br>Delegação nº ${d.id.slice(0, 8)}, vigente de ${d.inicio.slice(0, 10)} a ${d.fim.slice(0, 10)}.`
              : html``;
          })()}</div>`
      : html`<div class="aviso">Você está decidindo por <strong>autoridade própria</strong>,
          alçada ${formatarBRL(entrada.autoridade.limiteExercidoCentavos)}.</div>`
    : html`<p class="erro">${entrada.motivoSemAutoridade ?? "Você não pode decidir esta despesa."}</p>`;

  const acoes = entrada.autoridade
    ? html`<form method="POST" action="/despesas/${despesa.id}/aprovar" class="linha">
          <input type="hidden" name="u" value="${eu.id}"><input type="hidden" name="nonce" value="${entrada.nonce}">
          <button type="submit">Aprovar</button>
        </form>
        <h2>Rejeitar</h2>
        <p><small>Esta ação <strong>ENCERRA</strong> a despesa e não pode ser desfeita.</small></p>
        <form method="POST" action="/despesas/${despesa.id}/rejeitar" class="linha">
          <input type="hidden" name="u" value="${eu.id}"><input type="hidden" name="nonce" value="${entrada.nonce}">
          <div><label for="motivo">Motivo (obrigatório)</label>
            <input id="motivo" name="motivo" size="40" required></div>
          <button type="submit" class="sec">Confirmar rejeição</button>
        </form>`
    : html``;

  const trilhaLinhas = eventos.map(
    (e) => html`<tr>
      <td>${e.ocorridoEm.slice(0, 16).replace("T", " ")}</td>
      <td>${e.tipo}${e.nivel !== null ? html` nível ${e.nivel}` : html``}</td>
      <td>${e.atorId ? nomeDe(e.atorId) : html`<em>—</em>`}</td>
      <td>${e.emNomeDeId ? html`em nome de ${nomeDe(e.emNomeDeId)}` : html`—`}</td>
      <td>${e.limiteExercidoCentavos !== null ? formatarBRL(e.limiteExercidoCentavos) : "—"}</td>
      <td>${e.motivo ?? "—"}</td>
    </tr>`,
  );

  return html`${erroBox(entrada.erro)}
    <p><strong>${formatarBRL(despesa.valorCentavos)}</strong> — "${despesa.descricao}"<br>
    Solicitante: ${entrada.solicitante.nome} · Criada: ${despesa.criadaEm.slice(0, 16).replace("T", " ")}<br>
    Estado: <strong>${despesa.estado}</strong> ·
    Cadeia: ${cadeia.map((p) => p.nome).join(" → ")}
    ${papelAtual ? html` · Aguardando: <strong>${papelAtual.nome}</strong> (nível ${papelAtual.nivel})` : html``}</p>
    ${despesa.estado === "PENDENTE" ? blocoAutoridade : html``}
    ${despesa.estado === "PENDENTE" ? acoes : html``}
    <h2>Trilha</h2>
    <table><thead><tr><th>Quando</th><th>Evento</th><th>Ator</th><th>Autoridade</th>
    <th>Limite exercido</th><th>Motivo</th></tr></thead><tbody>${trilhaLinhas}</tbody></table>`;
}

/** T5 — Delegações. */
export function t5Delegacoes(entrada: {
  eu: Usuario;
  nonce: string;
  minhas: readonly Delegacao[];
  usuarios: readonly Usuario[];
  agora: string;
  erro: string | null;
  ok: string | null;
}): Html {
  const nomeDe = (id: string) => entrada.usuarios.find((u) => u.id === id)?.nome ?? id;
  const dias = (fim: string) =>
    Math.ceil((Date.parse(fim) - Date.parse(entrada.agora)) / 86_400_000);

  const linhas = entrada.minhas.map((d) => {
    const ativa = d.estado === "ATIVA" && d.inicio <= entrada.agora && entrada.agora < d.fim;
    return html`<tr>
      <td>${d.id.slice(0, 8)}</td><td>${nomeDe(d.delegadoId)}</td>
      <td>${d.inicio.slice(0, 10)} → ${d.fim.slice(0, 10)}</td>
      <td>${d.estado === "REVOGADA"
        ? "revogada"
        : ativa
          ? html`<strong>ATIVA</strong> (termina em ${dias(d.fim)} dia(s))`
          : entrada.agora >= d.fim
            ? "encerrada"
            : "futura"}</td>
      <td>${d.estado === "ATIVA"
        ? html`<form method="POST" action="/delegacoes/${d.id}/revogar">
            <input type="hidden" name="u" value="${entrada.eu.id}">
            <input type="hidden" name="nonce" value="${entrada.nonce}">
            <button class="sec" type="submit">Revogar</button></form>`
        : html`—`}</td>
    </tr>`;
  });

  const opcoes = entrada.usuarios
    .filter((u) => u.id !== entrada.eu.id)
    .map((u) => html`<option value="${u.id}">${u.nome}</option>`);

  return html`${erroBox(entrada.erro)}${okBox(entrada.ok)}
    <h2>Minhas delegações</h2>
    ${entrada.minhas.length === 0
      ? html`<p>Você ainda não delegou sua autoridade.</p>`
      : html`<table><thead><tr><th>nº</th><th>Para</th><th>Vigência</th><th>Situação</th><th></th></tr></thead>
        <tbody>${linhas}</tbody></table>`}
    <h2>Delegar minha autoridade</h2>
    <form method="POST" action="/delegacoes" class="linha">
      <input type="hidden" name="u" value="${entrada.eu.id}">
      <input type="hidden" name="nonce" value="${entrada.nonce}">
      <div><label for="para">Para</label><select id="para" name="delegadoId">${opcoes}</select></div>
      <div><label for="de">De</label><input id="de" type="date" name="inicio" required></div>
      <div><label for="ate">Até</label><input id="ate" type="date" name="fim" required></div>
      <button type="submit">Delegar</button>
    </form>`;
}

/** T6 — Auditoria. */
export function t6Auditoria(entrada: {
  eu: Usuario;
  nonce: string;
  despesas: readonly Despesa[];
  delegacoes: readonly Delegacao[];
  usuarios: readonly Usuario[];
  ehAdmin: boolean;
}): Html {
  const nomeDe = (id: string) => entrada.usuarios.find((u) => u.id === id)?.nome ?? id;
  const linhasDespesa = entrada.despesas.map(
    (d) => html`<tr><td><a href="/despesas/${d.id}?u=${entrada.eu.id}">${d.id.slice(0, 8)}</a></td>
      <td>${nomeDe(d.solicitanteId)}</td><td>${formatarBRL(d.valorCentavos)}</td>
      <td>${d.descricao}</td><td>${d.estado}</td></tr>`,
  );
  const linhasDeleg = entrada.delegacoes.map(
    (d) => html`<tr><td>${d.id.slice(0, 8)}</td><td>${nomeDe(d.deleganteId)}</td>
      <td>${nomeDe(d.delegadoId)}</td><td>${d.inicio.slice(0, 10)} → ${d.fim.slice(0, 10)}</td>
      <td>${d.estado}</td>
      <td>${entrada.ehAdmin && d.estado === "ATIVA"
        ? html`<form method="POST" action="/delegacoes/${d.id}/revogar">
            <input type="hidden" name="u" value="${entrada.eu.id}">
            <input type="hidden" name="nonce" value="${entrada.nonce}">
            <button class="sec" type="submit">Revogar</button></form>`
        : html`—`}</td></tr>`,
  );
  return html`<h2>Despesas</h2>
    <table><thead><tr><th>id</th><th>Solicitante</th><th>Valor</th><th>Descrição</th><th>Estado</th></tr></thead>
    <tbody>${linhasDespesa}</tbody></table>
    <h2>Delegações de todos</h2>
    ${entrada.ehAdmin
      ? html`<p><small>Como Admin, você pode revogar delegação de terceiros — válvula de escape
        quando o delegante está indisponível.</small></p>`
      : html`<p><small>Apenas o Admin revoga delegação de terceiros.</small></p>`}
    <table><thead><tr><th>nº</th><th>Delegante</th><th>Delegado</th><th>Vigência</th><th>Estado</th><th></th></tr></thead>
    <tbody>${linhasDeleg}</tbody></table>`;
}
