/**
 * M-12 ui-web — SÓ renderização (V(3)). Recebe dados, devolve HTML.
 *
 * Sem rota própria, sem dependência de módulo algum: quem roteia é `api-http`,
 * a porta única. Isso resolveu ARQ-02 (a UI não faz HTTP para o próprio
 * processo) e ARQ-08 (duas portas com regras de sessão que podiam divergir).
 *
 * ESCAPE AUTOMÁTICO (SEG-02): `html` é um tagged template que escapa TODA
 * interpolação por padrão. Justificativa, fundamentação, título e descrição são
 * texto livre exibido em quatro das sete telas — sem escape, XSS armazenado.
 * Para inserir marcação já montada existe `cru()`, explícito e visível na
 * leitura, que é como deve ser.
 *
 * S6: escapar HTML é problema pequeno e fechado (5 caracteres); um motor de
 * template seria dependência nova fora da stack aprovada na Fase 1, que diz
 * "templates server-side" sem nomear motor. Decisão registrada.
 *
 * depends-on: —
 */

/**
 * `Seguro` marca uma string que JÁ passou pelo escape (ou que é marcação
 * confiável). `escapar` é IDEMPOTENTE por construção: aplicado a um Seguro,
 * devolve-o intacto. Sem isso, um fragmento aninhado seria escapado duas vezes
 * e a página sairia com `&lt;td&gt;` visível — e a tentação de "consertar"
 * removendo o escape é exatamente como XSS armazenado entra.
 */
class Seguro {
  constructor(readonly s: string) {}
}
type Cru = Seguro

/** Marcação confiável, escrita por nós. Explícito e visível na leitura. */
export const cru = (s: string): Seguro => new Seguro(s)

const escaparTexto = (v: unknown): string =>
  v === null || v === undefined
    ? ''
    : String(v)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')

const escapar = (v: unknown): Seguro => (v instanceof Seguro ? v : new Seguro(escaparTexto(v)))

export function html(partes: TemplateStringsArray, ...valores: unknown[]): Seguro {
  let saida = partes[0] ?? ''
  for (let i = 0; i < valores.length; i++) {
    const v = valores[i]
    saida += Array.isArray(v) ? v.map((x) => escapar(x).s).join('') : escapar(v).s
    saida += partes[i + 1] ?? ''
  }
  return new Seguro(saida)
}

const ESTILO = `
:root{--tinta:#1a1a1a;--fraco:#666;--linha:#ddd;--alerta:#b00020;--fundo:#fff}
*{box-sizing:border-box}
body{font:16px/1.5 system-ui,sans-serif;color:var(--tinta);background:var(--fundo);margin:0}
main{max-width:60rem;margin:0 auto;padding:1.5rem}
header{border-bottom:1px solid var(--linha);padding:.75rem 1.5rem;display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap}
h1{font-size:1.3rem;margin:0}h2{font-size:1.05rem;margin:1.5rem 0 .5rem}
a{color:inherit}
table{border-collapse:collapse;width:100%;margin:.5rem 0}
th,td{text-align:left;padding:.4rem .6rem;border-bottom:1px solid var(--linha);vertical-align:top}
th{font-weight:600;font-size:.85rem;color:var(--fraco)}
.violado{color:var(--alerta);font-weight:600}
.fraco{color:var(--fraco);font-size:.9rem}
fieldset{border:1px solid var(--linha);margin:.75rem 0;padding:.75rem}
legend{font-size:.85rem;color:var(--fraco);padding:0 .3rem}
label{display:block;margin:.35rem 0}
input[type=text],textarea,select{width:100%;padding:.4rem;font:inherit;border:1px solid var(--linha);border-radius:3px}
textarea{min-height:5rem}
button{font:inherit;padding:.45rem 1rem;border:1px solid var(--tinta);background:var(--tinta);color:#fff;border-radius:3px;cursor:pointer}
button.secundario{background:transparent;color:var(--tinta)}
.acoes{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:1rem}
.aviso{border-left:3px solid var(--alerta);padding:.5rem .75rem;margin:.75rem 0;background:#fff5f5}
.matriz td.aqui{outline:2px solid var(--tinta);font-weight:700}
.trilha td{font-size:.92rem}
@media(prefers-color-scheme:dark){:root{--tinta:#e8e8e8;--fraco:#999;--linha:#333;--fundo:#141414;--alerta:#ff6b6b}
button{color:#141414}.aviso{background:#2a1515}}
`

export type Sessao = { id: string; nome: string; papel: string } | null

/**
 * VÍNCULO DE SESSÃO — todo formulário carrega a identidade que o compôs.
 *
 * Sem isto, a autoria da ação é decidida no ENVIO pelo cookie ambiente: com um
 * formulário aberto como Ana e uma troca de usuário em outra aba, o chamado que
 * Ana escreveu era registrado como sendo de Carla. Num sistema cuja tese é
 * atribuição auditável, a trilha passaria a mentir sobre quem fez o quê.
 *
 * O servidor compara este campo com o cookie e recusa a divergência. Não tenta
 * adivinhar qual identidade é a "certa" — porque não sabe, e chutar seria pior
 * que recusar.
 */
export const vinculoSessao = (sessao: Sessao): Cru =>
  sessao ? html`<input type="hidden" name="sessaoDe" value="${sessao.id}">` : cru('')

function moldura(titulo: string, sessao: Sessao, corpo: Cru): string {
  const pagina = html`<header>
      <h1><a href="/" style="text-decoration:none">T32 · Triagem</a></h1>
      <div class="fraco">
        ${sessao ? `${sessao.nome} — ${sessao.papel.toLowerCase()}` : 'não identificado'}
        ${sessao ? cru(' · <a href="/entrar">trocar</a>') : ''}
      </div>
    </header>
    <main>${corpo}</main>`
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escaparTexto(titulo)} · T32 Triagem</title><style>${ESTILO}</style></head><body>
${pagina.s}
</body></html>`
}

const dt = (ms: number | null): string =>
  ms === null ? '—' : new Date(ms).toISOString().replace('T', ' ').slice(0, 16) + ' UTC'

const NOMES: Record<string, string> = {
  NAO_TRIADO: 'não triado',
  TRIADO: 'triado',
  RECONHECIDO: 'reconhecido',
  ENCERRADO: 'encerrado',
  ABERTO: 'aberto',
  PROVIDO: 'provido',
  PARCIALMENTE_PROVIDO: 'parcialmente provido',
  IMPROVIDO: 'improvido',
  PRESCRITO_SEM_JULGAMENTO: 'prescrito sem julgamento',
  SEM_LEGITIMIDADE: 'este chamado não é seu',
  RECURSO_JA_EXISTE: 'você já recorreu deste chamado — o recurso é único',
  PRESCRITO: 'o prazo para recorrer já passou',
  NAO_TRIADO_RECURSO: 'ainda não há classificação a contestar',
  CHAMADO_ENCERRADO: 'o chamado já foi encerrado',
  PAPEL_INSUFICIENTE: 'seu papel não permite esta ação',
  RECURSO_ABERTO_PENDENTE: 'há recurso em aberto — julgue ou aguarde o prazo de julgamento',
  SESSAO_TROCADA:
    'este formulário foi preenchido por outro usuário — a sessão mudou em outra aba. ' +
    'Nada foi registrado: gravar a ação em nome de quem está logado agora faria a trilha ' +
    'atribuir a alguém algo que essa pessoa não escreveu. Entre novamente e refaça.',
}
const legivel = (s: string | null): string => (s === null ? '' : (NOMES[s] ?? s.toLowerCase().replace(/_/g, ' ')))

// --- T-0 entrada ------------------------------------------------------------

export function telaEntrada(usuarios: readonly { id: string; nome: string; papel: string }[]): string {
  return moldura(
    'Entrar',
    null,
    html`<h2>Entrar</h2>
      <p class="fraco">
        Não há senha: a identidade é declarada, não provada — risco aceito e registrado (premissa A8).
        O cookie assinado impede forjar o papel a cada requisição; não substitui autenticação.
      </p>
      <form method="post" action="/entrar">
        <fieldset>
          <legend>Usuário</legend>
          ${usuarios.map(
            (u) =>
              escapar(html`<label><input type="radio" name="usuarioId" value="${u.id}" required>
                ${u.nome} — <span class="fraco">${legivel(u.papel)}</span></label>`),
          )}
        </fieldset>
        <button type="submit">Entrar</button>
      </form>`,
  )
}

// --- T-1 abrir --------------------------------------------------------------

const DEF_URGENCIA: [string, string, string][] = [
  ['ALTA', 'Alta', 'Precisa ser resolvido imediatamente: há prazo duro, operação bloqueada, ou o atraso causa falhas em cascata.'],
  ['MEDIA', 'Média', 'Precisa ser resolvido dentro do dia. Afeta produtividade, mas há contorno de curto prazo.'],
  ['BAIXA', 'Baixa', 'Pode ser agendado. Sem prazo imediato; a operação normal segue.'],
]

const DEF_IMPACTO: [string, string, string][] = [
  ['ALTO', 'Alto', 'A organização inteira é afetada: sistema central parado, operações interrompidas, ou risco a receita, conformidade ou reputação.'],
  ['MEDIO', 'Médio', 'Um departamento ou grupo significativo é afetado. Fluxos-chave prejudicados, organização parcialmente operante.'],
  ['BAIXO', 'Baixo', 'Um único usuário ou sistema não-crítico. O dia a dia do resto da organização continua normal.'],
]

export function telaAbrir(sessao: Sessao, erro?: string): string {
  return moldura(
    'Novo chamado',
    sessao,
    html`<h2>Novo chamado</h2>
      ${erro ? html`<div class="aviso">${legivel(erro)}</div>` : ''}
      <form method="post" action="/chamados">${vinculoSessao(sessao)}
        <label>Título <input type="text" name="titulo" required maxlength="120"></label>
        <label>Descrição <textarea name="descricao" required maxlength="4000"></textarea></label>
        <fieldset>
          <legend>Urgência — quanto isso corre para você</legend>
          ${DEF_URGENCIA.map(
            ([v, rot, def]) =>
              escapar(html`<label><input type="radio" name="urgencia" value="${v}" required> <strong>${rot}</strong>
                <span class="fraco">— ${def}</span></label>`),
          )}
        </fieldset>
        <p class="fraco">
          Você não declara impacto, categoria nem prioridade. O impacto é do agente, e a prioridade
          é derivada dos dois — nunca digitada por ninguém.
        </p>
        <button type="submit">Abrir chamado</button>
      </form>`,
  )
}

// --- T-2 fila ---------------------------------------------------------------

type LinhaFila = {
  chamado: { id: string; titulo: string; categoria: string | null; estado: string }
  prioridade: string | null
  prazo: number
  violado: boolean
}

export function telaFila(
  sessao: Sessao,
  dados: { triados: readonly LinhaFila[]; naoTriados: readonly LinhaFila[] },
  filtro: string | null,
  categorias: readonly string[],
): string {
  const linha = (l: LinhaFila) => html`<tr>
    <td>${l.prioridade ?? '—'}</td>
    <td><a href="/chamados/${l.chamado.id}">${l.chamado.titulo}</a></td>
    <td class="fraco">${l.chamado.categoria ? legivel(l.chamado.categoria) : '—'}</td>
    <td class="fraco">${dt(l.prazo)}</td>
    <td>${l.violado ? cru('<span class="violado">VIOLADO</span>') : 'no prazo'}</td>
  </tr>`

  return moldura(
    'Fila',
    sessao,
    html`<h2>Fila</h2>
      <form method="get" action="/fila">
        <label>Categoria
          <select name="categoria" onchange="this.form.submit()">
            <option value="">Todas</option>
            ${categorias.map((c) => escapar(html`<option value="${c}" ${filtro === c ? cru('selected') : ''}>${legivel(c)}</option>`))}
          </select>
        </label>
      </form>

      <h2>Triados — por severidade</h2>
      <table><tr><th>P</th><th>Chamado</th><th>Categoria</th><th>Resolver até</th><th>Situação</th></tr>
        ${dados.triados.map((l) => escapar(linha(l)))}
      </table>
      ${dados.triados.length === 0 ? cru('<p class="fraco">nenhum chamado triado em aberto</p>') : ''}

      <h2>Não triados — por prazo de triagem</h2>
      <p class="fraco">
        Seção separada de propósito: a ausência de prioridade não é "prioridade baixa", e comparar
        prazo de triagem com prazo de resolução na mesma coluna faria um não triado passar na frente
        de um P1.
      </p>
      <table><tr><th>P</th><th>Chamado</th><th>Categoria</th><th>Triar até</th><th>Situação</th></tr>
        ${dados.naoTriados.map((l) => escapar(linha(l)))}
      </table>
      ${dados.naoTriados.length === 0 ? cru('<p class="fraco">nenhum chamado aguardando triagem</p>') : ''}`,
  )
}

// --- T-3 triar --------------------------------------------------------------

export function telaTriar(
  sessao: Sessao,
  c: { id: string; titulo: string; descricao: string; urgencia: string },
  matriz: Record<string, Record<string, string>>,
  erro?: string,
): string {
  const cabecalho = ['ALTA', 'MEDIA', 'BAIXA']
  return moldura(
    'Triar',
    sessao,
    html`<h2>Triar — ${c.titulo}</h2>
      ${erro ? html`<div class="aviso">${legivel(erro)}</div>` : ''}
      <p class="fraco">${c.descricao}</p>
      <p>Urgência declarada pelo solicitante: <strong>${legivel(c.urgencia)}</strong></p>

      <h2>Matriz vigente</h2>
      <table class="matriz">
        <tr><th>impacto \\ urgência</th>${cabecalho.map((u) => escapar(html`<th>${legivel(u)}</th>`))}</tr>
        ${['ALTO', 'MEDIO', 'BAIXO'].map((i) =>
          escapar(html`<tr><th>${legivel(i)}</th>${cabecalho.map((u) =>
            escapar(html`<td class="${u === c.urgencia ? 'aqui' : ''}">${matriz[i]?.[u]}</td>`),
          )}</tr>`),
        )}
      </table>
      <p class="fraco">
        A coluna da urgência declarada está destacada: a prioridade que cada impacto produzirá está
        visível antes da escolha, sem JavaScript. A prioridade não é um campo — é o cruzamento.
      </p>

      <form method="post" action="/chamados/${c.id}/triagem">${vinculoSessao(sessao)}
        <label>Categoria
          <select name="categoria" required>
            ${['HARDWARE', 'SOFTWARE', 'REDE', 'ACESSO', 'OUTRO'].map(
              (k) => escapar(html`<option value="${k}">${legivel(k)}</option>`),
            )}
          </select>
        </label>
        <fieldset>
          <legend>Impacto — quanto do negócio isso atinge</legend>
          ${DEF_IMPACTO.map(
            ([v, rot, def]) =>
              escapar(html`<label><input type="radio" name="impacto" value="${v}" required> <strong>${rot}</strong>
                <span class="fraco">— ${def}</span></label>`),
          )}
        </fieldset>
        <button type="submit">Triar</button>
      </form>`,
  )
}

// --- T-4 chamado + trilha ---------------------------------------------------

type EventoVista = {
  tipo: string
  atorNome: string
  instante: number
  origem: string
  motivo: string | null
  versaoPolitica: string | null
  mudancas: readonly { campo: string; de: string | null; para: string | null }[]
}

export function telaChamado(
  sessao: Sessao,
  v: {
    chamado: { id: string; titulo: string; descricao: string; estado: string; urgencia: string; impacto: string | null; categoria: string | null; abertoEm: number; solicitanteNome: string }
    prioridade: string | null
    prazoVigente: number
    violado: boolean
    recurso: { estado: string; justificativa: string; fundamentacao: string | null; eixosContestados: readonly string[] } | null
    podeRecorrer: boolean
    motivoNaoPodeRecorrer: string | null
    prescreveEm: number | null
    eventos: readonly EventoVista[]
  },
  papel: string,
  erro?: string,
): string {
  const operador = papel === 'AGENTE' || papel === 'GESTOR'
  return moldura(
    v.chamado.titulo,
    sessao,
    html`<h2>${v.chamado.titulo}</h2>
      ${erro ? html`<div class="aviso">${legivel(erro)}</div>` : ''}
      <p>
        <strong>${v.prioridade ?? 'sem prioridade'}</strong> ·
        ${legivel(v.chamado.estado)} ·
        ${v.violado ? cru('<span class="violado">VIOLADO</span>') : 'no prazo'}
      </p>
      <p class="fraco">
        ${v.chamado.solicitanteNome} · ${v.chamado.categoria ? legivel(v.chamado.categoria) : 'sem categoria'} ·
        impacto ${v.chamado.impacto ? legivel(v.chamado.impacto) : '—'} · urgência ${legivel(v.chamado.urgencia)}<br>
        aberto em ${dt(v.chamado.abertoEm)} · ${v.chamado.estado === 'NAO_TRIADO' ? 'triar até' : 'resolver até'}
        ${dt(v.prazoVigente)}
      </p>
      <p>${v.chamado.descricao}</p>

      ${
        v.recurso
          ? escapar(html`<h2>Recurso</h2>
              <p>Estado: <strong>${legivel(v.recurso.estado)}</strong> ·
                contesta ${v.recurso.eixosContestados.map((e) => e.toLowerCase()).join(' e ')}</p>
              <p class="fraco">"${v.recurso.justificativa}"</p>
              ${v.recurso.fundamentacao ? escapar(html`<p class="fraco">Decisão: "${v.recurso.fundamentacao}"</p>`) : ''}`)
          : ''
      }

      <h2>Histórico de classificação</h2>
      <p class="fraco">
        Mesma trilha para os três papéis: uma classificação só é contestável se for visível, e não se
        recorre do que não se pode ler.
      </p>
      <table class="trilha"><tr><th>quando</th><th>quem</th><th>o quê</th><th>mudanças</th><th>motivo</th></tr>
        ${v.eventos.map((e) =>
          escapar(html`<tr>
            <td class="fraco">${dt(e.instante)}</td>
            <td>${e.atorNome}</td>
            <td>${legivel(e.tipo)}${e.origem === 'RECURSO' ? cru('<br><span class="fraco">via recurso</span>') : ''}</td>
            <td>${e.mudancas.map((m) => escapar(html`<div>${m.campo}: ${m.de ?? '—'} → ${m.para ?? '—'}</div>`))}
              ${e.versaoPolitica ? escapar(html`<div class="fraco">política ${e.versaoPolitica}</div>`) : ''}</td>
            <td class="fraco">${e.motivo ?? ''}</td>
          </tr>`),
        )}
      </table>

      <div class="acoes">
        ${v.podeRecorrer ? escapar(html`<a href="/chamados/${v.chamado.id}/recurso"><button type="button">Recorrer</button></a>`) : ''}
        ${
          // Cada ação aparece SÓ quando a transição existe no estado atual.
          // Oferecer um botão que o domínio recusa é beco sem saída: foi assim
          // que "Encerrar" num chamado não triado devolveu "não triado".
          operador && v.chamado.estado === 'NAO_TRIADO'
            ? escapar(html`<a href="/chamados/${v.chamado.id}/triagem"><button type="button">Triar</button></a>`)
            : ''
        }
        ${
          operador && v.chamado.estado === 'TRIADO'
            ? escapar(html`<form method="post" action="/chamados/${v.chamado.id}/reconhecimento">${vinculoSessao(sessao)}<button class="secundario">Reconhecer</button></form>`)
            : ''
        }
        ${
          operador && (v.chamado.estado === 'TRIADO' || v.chamado.estado === 'RECONHECIDO')
            ? escapar(html`
                <form method="post" action="/chamados/${v.chamado.id}/encerramento">${vinculoSessao(sessao)}<button class="secundario">Encerrar</button></form>
                <a href="/chamados/${v.chamado.id}/reclassificacao"><button type="button" class="secundario">Reclassificar</button></a>`)
            : ''
        }
        ${
          papel === 'GESTOR' && v.recurso?.estado === 'ABERTO'
            ? escapar(html`<a href="/chamados/${v.chamado.id}/julgamento"><button type="button">Julgar recurso</button></a>`)
            : ''
        }
      </div>
      ${
        !v.podeRecorrer && v.motivoNaoPodeRecorrer && papel === 'SOLICITANTE'
          ? escapar(html`<p class="fraco">Recurso indisponível: ${legivel(v.motivoNaoPodeRecorrer)}${
              v.motivoNaoPodeRecorrer === 'PRESCRITO' && v.prescreveEm ? ` (prazo encerrado em ${dt(v.prescreveEm)})` : ''
            }</p>`)
          : ''
      }`,
  )
}

// --- T-5 recorrer -----------------------------------------------------------

export function telaRecorrer(
  sessao: Sessao,
  c: { id: string; titulo: string; urgencia: string; impacto: string | null },
  prescreveEm: number | null,
  erro?: string,
): string {
  return moldura(
    'Recurso',
    sessao,
    html`<h2>Recurso do chamado</h2>
      ${erro ? html`<div class="aviso">${legivel(erro)}</div>` : ''}
      <p>${c.titulo}</p>
      <p class="fraco">Você pode recorrer até <strong>${dt(prescreveEm)}</strong>. Este é seu único recurso neste chamado.</p>
      <form method="post" action="/chamados/${c.id}/recurso">${vinculoSessao(sessao)}
        <fieldset>
          <legend>Contesto</legend>
          <label><input type="checkbox" name="eixos" value="URGENCIA"> a urgência (${legivel(c.urgencia)}) — declarada por você</label>
          <label><input type="checkbox" name="eixos" value="IMPACTO"> o impacto (${c.impacto ? legivel(c.impacto) : '—'}) — atribuído pelo agente</label>
        </fieldset>
        <label>Por quê <textarea name="justificativa" required maxlength="2000"></textarea></label>
        <button type="submit">Enviar recurso</button>
      </form>`,
  )
}

// --- T-6 julgar -------------------------------------------------------------

export function telaJulgar(
  sessao: Sessao,
  dados: {
    chamado: { id: string; titulo: string; urgencia: string; impacto: string | null }
    recurso: { justificativa: string; eixosContestados: readonly string[]; abertoEm: number }
    solicitanteNome: string
    recursosEm30Dias: number
    prioridadeAtual: string | null
  },
  erro?: string,
): string {
  const contesta = (e: string) => dados.recurso.eixosContestados.includes(e)
  return moldura(
    'Julgar recurso',
    sessao,
    html`<h2>Julgar recurso — ${dados.chamado.titulo}</h2>
      ${erro ? html`<div class="aviso">${legivel(erro)}</div>` : ''}
      <p>${dados.solicitanteNome} contesta ${dados.recurso.eixosContestados.map((e) => e.toLowerCase()).join(' e ')}:</p>
      <p class="fraco">"${dados.recurso.justificativa}"</p>
      <p>Classificação atual: impacto ${dados.chamado.impacto ? legivel(dados.chamado.impacto) : '—'} ·
         urgência ${legivel(dados.chamado.urgencia)} · <strong>${dados.prioridadeAtual ?? '—'}</strong></p>
      <p class="fraco">${dados.recursosEm30Dias}º recurso de ${dados.solicitanteNome} nos últimos 30 dias.</p>

      <div class="aviso">
        Se provido, os prazos são recontados <strong>desde a abertura</strong> do chamado — o chamado
        pode passar a constar violado. Isso é o comportamento correto: a classificação certa sempre
        valeu, e a trilha registrará a violação como decorrente de recurso, não de demora no atendimento.
      </div>

      <form method="post" action="/chamados/${dados.chamado.id}/julgamento">${vinculoSessao(sessao)}
        <fieldset>
          <legend>Desfecho</legend>
          <label><input type="radio" name="desfecho" value="PROVIDO" required> Provido</label>
          <label><input type="radio" name="desfecho" value="PARCIALMENTE_PROVIDO"
            ${dados.recurso.eixosContestados.length < 2 ? cru('disabled') : ''}> Parcialmente provido
            ${dados.recurso.eixosContestados.length < 2 ? cru('<span class="fraco">— exige dois eixos contestados</span>') : ''}</label>
          <label><input type="radio" name="desfecho" value="IMPROVIDO"> Improvido</label>
        </fieldset>
        ${
          contesta('URGENCIA')
            ? escapar(html`<label>Nova urgência
                <select name="urgencia"><option value="">manter</option>
                  ${['ALTA', 'MEDIA', 'BAIXA'].map((u) => escapar(html`<option value="${u}">${legivel(u)}</option>`))}
                </select></label>`)
            : ''
        }
        ${
          contesta('IMPACTO')
            ? escapar(html`<label>Novo impacto
                <select name="impacto"><option value="">manter</option>
                  ${['ALTO', 'MEDIO', 'BAIXO'].map((i) => escapar(html`<option value="${i}">${legivel(i)}</option>`))}
                </select></label>`)
            : ''
        }
        <label>Fundamentação <textarea name="fundamentacao" required maxlength="2000"></textarea></label>
        <button type="submit">Julgar</button>
      </form>`,
  )
}

// --- T-7 meus chamados ------------------------------------------------------

export function telaMeusChamados(
  sessao: Sessao,
  linhas: readonly LinhaFila[],
  papel: string,
): string {
  return moldura(
    'Meus chamados',
    sessao,
    html`<h2>Meus chamados</h2>
      <div class="acoes">
        <a href="/chamados/novo"><button type="button">Abrir chamado</button></a>
        ${papel !== 'SOLICITANTE' ? cru('<a href="/fila"><button type="button" class="secundario">Ver fila</button></a>') : ''}
      </div>
      <table><tr><th>P</th><th>Chamado</th><th>Categoria</th><th>Prazo</th><th>Situação</th></tr>
        ${linhas.map((l) =>
          escapar(html`<tr>
            <td>${l.prioridade ?? '—'}</td>
            <td><a href="/chamados/${l.chamado.id}">${l.chamado.titulo}</a></td>
            <td class="fraco">${l.chamado.categoria ? legivel(l.chamado.categoria) : '—'}</td>
            <td class="fraco">${dt(l.prazo)}</td>
            <td>${l.violado ? cru('<span class="violado">VIOLADO</span>') : legivel(l.chamado.estado)}</td>
          </tr>`),
        )}
      </table>
      ${linhas.length === 0 ? cru('<p class="fraco">nenhum chamado ainda</p>') : ''}`,
  )
}

export function telaReclassificar(
  sessao: Sessao,
  c: { id: string; titulo: string; urgencia: string; impacto: string | null; categoria: string | null },
  erro?: string,
): string {
  return moldura(
    'Reclassificar',
    sessao,
    html`<h2>Reclassificar — ${c.titulo}</h2>
      ${erro ? html`<div class="aviso">${legivel(erro)}</div>` : ''}
      <p class="fraco">
        Alterar a urgência devolve ao solicitante um novo prazo de recurso: o prazo conta da última
        mudança de classificação, não da triagem.
      </p>
      <form method="post" action="/chamados/${c.id}/reclassificacao">${vinculoSessao(sessao)}
        <label>Categoria
          <select name="categoria"><option value="">manter (${c.categoria ? legivel(c.categoria) : '—'})</option>
            ${['HARDWARE', 'SOFTWARE', 'REDE', 'ACESSO', 'OUTRO'].map((k) => escapar(html`<option value="${k}">${legivel(k)}</option>`))}
          </select></label>
        <label>Impacto
          <select name="impacto"><option value="">manter (${c.impacto ? legivel(c.impacto) : '—'})</option>
            ${['ALTO', 'MEDIO', 'BAIXO'].map((i) => escapar(html`<option value="${i}">${legivel(i)}</option>`))}
          </select></label>
        <label>Urgência
          <select name="urgencia"><option value="">manter (${legivel(c.urgencia)})</option>
            ${['ALTA', 'MEDIA', 'BAIXA'].map((u) => escapar(html`<option value="${u}">${legivel(u)}</option>`))}
          </select></label>
        <label>Motivo <textarea name="motivo" required maxlength="2000"></textarea></label>
        <button type="submit">Reclassificar</button>
      </form>`,
  )
}

export function telaErro(sessao: Sessao, mensagem: string): string {
  return moldura('Erro', sessao, html`<h2>Não foi possível</h2><div class="aviso">${legivel(mensagem)}</div>
    <p><a href="/">voltar</a></p>`)
}
