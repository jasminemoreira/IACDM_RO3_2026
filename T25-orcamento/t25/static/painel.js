// M-10 painel-web — SPA. Consome painel-api; nao fala com o banco.
// Requisitos de UI vindos da critica: exibir QUAL teto estourou e QUANDO volta
// (UX-01), distinguir "sem dados" de "consumo zero" (UX-04), e mostrar o proximo
// reset em UTC de forma explicita (decisao b7fbe77c).

// 4 casas decimais, nao 2: neste dominio o custo de uma requisicao e FRACAO de
// centavo. Com 2 casas, um teto de $0.01 e um consumo de $0.0097 aparecem ambos
// como "$0.01" e o saldo some em "$0.00" — o painel arredondaria justamente a
// informacao que existe para transmitir. E o mesmo erro de escala que fez a
// Fase 1 rejeitar centavos como unidade de armazenamento (specs/models §1).
const USD = (nano) => {
  if (nano === null || nano === undefined) return "—";
  const sinal = nano < 0 ? "-" : "";
  return `${sinal}$${(Math.abs(nano) / 1e9).toFixed(4)}`;
};

let token = null;

async function api(caminho, opcoes = {}) {
  const cabecalhos = { "content-type": "application/json", ...(opcoes.headers || {}) };
  if (token) cabecalhos["x-t25-operador"] = token;
  const r = await fetch(caminho, { ...opcoes, headers: cabecalhos });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).erro || `http ${r.status}`);
  return r.json();
}

document.getElementById("form-login").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const erro = document.getElementById("erro-login");
  erro.textContent = "";
  try {
    const r = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ senha: document.getElementById("senha").value }),
    });
    token = r.token;
    document.getElementById("login").hidden = true;
    document.getElementById("painel").hidden = false;
    await atualizar();
    setInterval(atualizar, 5000);
  } catch (e) {
    erro.textContent =
      e.message === "tentativas_excedidas"
        ? "Tentativas excedidas. Reinicie o gateway para liberar."
        : "Senha inválida.";
  }
});

function estado(cortado, semDados) {
  if (semDados) return '<span class="pill sem-dados">sem dados</span>';
  return cortado
    ? '<span class="pill corte">CORTADA</span>'
    : '<span class="pill ok">ativa</span>';
}

async function atualizar() {
  const d = await api("/api/consumo");
  const reset = new Date(d.proximo_reset_utc);
  document.getElementById("janela").textContent =
    `Janela desde ${d.janela_inicio.slice(0, 10)} · próximo reset em ` +
    `${reset.toISOString().replace("T", " ").slice(0, 16)} UTC`;

  const g = d.global;
  document.getElementById("g-teto").textContent = USD(g.teto_nano);
  document.getElementById("g-confirmado").textContent = USD(g.confirmado_nano);
  document.getElementById("g-reservado").textContent = USD(g.reservado_nano);
  document.getElementById("g-saldo").textContent = USD(g.saldo_nano);
  document.getElementById("g-estado").innerHTML =
    g.teto_nano === null
      ? '<span class="pill corte">teto global não configurado</span>'
      : estado(g.cortado, false);

  const linhas = document.getElementById("linhas");
  linhas.innerHTML = "";
  for (const e of d.entidades) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${e.nome} <span class="sub">${e.id}</span></td>
      <td>${USD(e.teto_nano)}</td>
      <td>${USD(e.confirmado_nano)}</td>
      <td>${USD(e.reservado_nano)}</td>
      <td>${USD(e.saldo_nano)}<br><span class="sub">≤ ${e.max_tokens_que_cabem} tokens de saída (o custo do prompt reduz este limite)</span></td>
      <td>${estado(e.cortada, e.sem_dados && e.teto_nano !== null && !e.cortada)}</td>
      <td><form class="linha-teto" data-id="${e.id}">
            <input type="number" step="0.01" min="0" placeholder="USD" aria-label="novo teto para ${e.nome}">
            <button type="submit">definir</button>
          </form></td>`;
    linhas.appendChild(tr);
  }

  for (const form of linhas.querySelectorAll("form.linha-teto")) {
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const usd = parseFloat(form.querySelector("input").value);
      if (!(usd >= 0)) return;
      await api(`/api/tetos/${form.dataset.id}`, {
        method: "PUT",
        body: JSON.stringify({ valor_nano: Math.round(usd * 1e9) }),
      });
      await atualizar();
    });
  }
}
