/**
 * M-12 ui-web (parte 1) — renderização.
 *
 * V(4)/T5, achados SEC-04, IMP-07 e LING-06: "escape por padrão" não é propriedade de
 * template de string em TypeScript — `${x}` interpola cru. Aqui a ÚNICA forma de montar HTML
 * é o template marcado `html`, que escapa todo valor interpolado EXCETO os já do tipo `Html`
 * (produzidos por outro `html`, isto é, sub-templates). Não existe caminho de interpolação
 * crua exposto, portanto não há `${}` a esquecer.
 */
export type Html = { readonly __html: string };

const ehHtml = (v: unknown): v is Html =>
  typeof v === "object" && v !== null && typeof (v as Html).__html === "string";

export function escapar(valor: unknown): string {
  return String(valor)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function html(partes: TemplateStringsArray, ...valores: unknown[]): Html {
  let out = partes[0] ?? "";
  for (let i = 0; i < valores.length; i++) {
    const v = valores[i];
    if (ehHtml(v)) out += v.__html;
    else if (Array.isArray(v)) out += v.map((x) => (ehHtml(x) ? x.__html : escapar(x))).join("");
    else if (v === null || v === undefined || v === false) out += "";
    else out += escapar(v);
    out += partes[i + 1] ?? "";
  }
  return { __html: out };
}

export function paraString(h: Html): string {
  return h.__html;
}
