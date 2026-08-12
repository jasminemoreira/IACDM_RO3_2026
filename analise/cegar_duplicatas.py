"""Remarcação cega de duplicatas por um segundo modelo, e concordância com a operadora.

    python3 cegar_duplicatas.py exportar T01-ratelimit
    python3 cegar_duplicatas.py comparar T01-ratelimit cego/T01-ratelimit-resposta.json

POR QUE EXISTE
--------------
O BATCH-PROTOCOL §7 declara, como limitação não resolvida:

    "Idealmente a marcação de duplicatas seria refeita por um terceiro cego a qual
     lente produziu cada achado; enquanto isso não existe, é limitação declarada,
     não resolvida."

A marcação `duplica` é o discriminante central da RO3 — mesmo defeito (sobreposição)
vs. defeito distinto (ortogonalidade).

QUEM MARCA, DE FATO: o MODELO GERADOR, na Fase 2. Não a operadora. O §7 do
BATCH-PROTOCOL descreve a fragilidade como L6 ("quem marca é a proponente"), mas o
mecanismo real é outro e pior: o mesmo agente que produziu os achados julga quais
são o mesmo defeito. Isso é autoavaliação — precisamente o que o modelo AG/AV afirma
que um LLM não faz. A operadora aprova a saída da fase no gate; não adjudica cada
marcação. O §7 precisa ser corrigido nesse ponto.

Este módulo converte a limitação em medida: um segundo modelo, cego às lentes,
reagrupa os achados, e a concordância entre as duas marcações é reportada. A
comparação é MODELO GERADOR × MODELO CEGO INDEPENDENTE.

Alta concordância → a marcação do gerador deixa de ser ponto fraco.
Baixa concordância → ISSO É O RESULTADO, e é mais informativo que a contribuição
exclusiva: diz que o discriminante central da RO3 não é reprodutível.

O QUE É CEGADO, E O QUE NÃO DÁ PARA CEGAR
-----------------------------------------
Cegado:
  - a coluna `lente`;
  - o **id**, que vaza a lente pelo prefixo (`P-01` diz Premissas, `R-02` diz
    Resilience). Sem reetiquetar, o cegamento seria fictício;
  - a **ordem**, que agrupa por lente na matriz original e vazaria o mesmo. O
    embaralhamento é determinístico (hash do taskId + id), então é reproduzível e
    auditável, não aleatório;
  - a marcação `duplica: <id>` no texto, que é literalmente a resposta.

NÃO cegado, e é limitação a declarar: o **conteúdo** do achado. "premissa não
declarada" ou "vetor de ataque" denunciam a lente por si. O cegamento é do rótulo,
não da semântica. Isso ATENUA a independência dos juízes — não a garante. O efeito
esperado é inflar a concordância, ou seja, é conservador contra a conclusão
"a marcação é reprodutível".

Um vazamento específico, descoberto testando este módulo contra o fixture: o
marcador `duplica:` é removido, mas a PROSA de um achado duplicado costuma
referenciar o original — "mesmo defeito de relógio, visto pelo acoplamento ao
store" entrega que é duplicata sem dizer de quê. Mitigação, que é regra de escrita
da matriz e não de código:

    Ao registrar um achado marcado `duplica:`, descreva o DEFEITO por si, como se
    fosse o único. A relação com o outro achado vive na marcação `duplica: <id>`,
    não no texto.

Sem isso, o juiz cego recebe a resposta parcialmente escrita, e κ sai inflado.

CRITÉRIO IDÊNTICO PARA OS DOIS JUÍZES
-------------------------------------
O prompt entrega ao segundo modelo o mesmo critério do §3 e o mesmo viés
conservador ("na dúvida, não agrupe"). Se os dois juízes recebessem instruções
diferentes, a discordância mediria diferença de instrução, não de julgamento.

COMO A CONCORDÂNCIA É CALCULADA (fixado antes da coleta)
--------------------------------------------------------
Agrupamento não é rótulo categórico, então κ não se aplica direto. A conversão
padrão: cada PAR de achados do mesmo projeto vira uma decisão binária — "mesmo
defeito? sim/não" — e κ de Cohen é calculado sobre essas decisões pareadas.

Reporta-se κ em duas janelas, e as duas entram no relato:
  - **todos os pares** do projeto (escopo real da marcação);
  - **só pares do mesmo módulo** (sensibilidade). Pares de módulos diferentes são
    quase todos "não" trivial, e inflam a concordância observada.

κ, e não concordância bruta, justamente porque os pares são desbalanceados: quase
todo par é "não duplicata", e a concordância bruta ficaria ~99% sem significar nada.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ro3_analise import clusters  # noqa: E402
from ro3_parser import RE_DUPLICA, ErroDeFormato, carregar  # noqa: E402

RO3 = Path(__file__).resolve().parent.parent
SAIDA = Path(__file__).resolve().parent / "cego"
RE_LINHA_MODULO = __import__("re").compile(r"^\|\s*M-\d+\s*\|")

PROMPT = """\
# Reagrupamento cego de achados — {task_id}

Você recebe {n} achados de uma crítica arquitetural. Cada um tem um id anônimo, o
módulo onde ocorre, a severidade e uma descrição de uma linha.

**Sua tarefa:** agrupar os achados que apontam o MESMO DEFEITO.

Atenção a defeitos **replicados**: quando dois módulos são implementações irmãs do
mesmo contrato, o mesmo defeito pode aparecer em ambos. Se uma única correção na
abstração compartilhada resolveria os dois, é o mesmo defeito.

**Critério, e é o único que vale:**

> Dois achados são o mesmo defeito quando apontam o mesmo problema no mesmo local,
> com a mesma causa raiz. Regra operacional: **se corrigir um resolveria
> automaticamente o outro, é o mesmo defeito.** Se cada um exige uma correção
> própria, são defeitos distintos — mesmo que estejam no mesmo módulo e sejam
> parecidos.

**Viés conservador, obrigatório:** na dúvida, **NÃO** agrupe. Agrupar a mais é o erro
mais caro aqui.

Não explique, não comente, não reordene. Responda **só** com este JSON:

```json
{{"grupos": [["F-03", "F-07"], ["F-11", "F-02", "F-19"]]}}
```

Cada lista interna é um grupo de achados que são o mesmo defeito. Achados que não
são duplicata de nenhum outro **não aparecem** — grupos de um só elemento são
implícitos. Se nenhum achado for duplicata de outro, responda `{{"grupos": []}}`.

## A arquitetura

Os módulos do sistema, para você saber o que cada nome significa e quais são irmãos
entre si:

{modulos}

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
{tabela}
"""

SEV_EMOJI = {"critico": "🔴", "importante": "🟡", "sugestao": "🟢"}


def _ordem_cega(task_id: str, id_original: str) -> str:
    """Chave de ordenação determinística — embaralha sem RNG, e é reproduzível."""
    return hashlib.sha256(f"{task_id}::{id_original}".encode()).hexdigest()


def exportar(task_id: str) -> int:
    try:
        proj = carregar(RO3 / task_id)
    except ErroDeFormato as e:
        print(f"ERRO DE FORMATO: {e}", file=sys.stderr)
        return 1

    SAIDA.mkdir(exist_ok=True)
    ordenados = sorted(proj.achados, key=lambda a: _ordem_cega(task_id, a.id))
    mapa = {f"F-{i:02d}": a.id for i, a in enumerate(ordenados, start=1)}
    inverso = {v: k for k, v in mapa.items()}

    linhas = []
    for cego, a in ((inverso[a.id], a) for a in ordenados):
        # A marcação `duplica:` é a resposta — sai do texto entregue ao juiz.
        desc = RE_DUPLICA.sub("", a.descricao).strip(" —-|").strip()
        desc = " ".join(desc.split())
        linhas.append(f"| {cego} | {a.modulo} | {SEV_EMOJI[a.severidade]} | {desc} |")

    # A tabela de módulos vai junto: sem ela o juiz vê "csv-reader" e "jsonl-reader"
    # como dois módulos quaisquer e nunca junta um defeito replicado nos dois. O
    # gerador tinha essa informação; o juiz não tinha, e a assimetria empurrava a
    # contribuição exclusiva para cima — a favor da hipótese. Não vaza lente: a tabela
    # traz módulo, responsabilidade, interface e dependências, nada mais.
    arq = (RO3 / task_id / "specs" / "technical" / "architecture.md").read_text(encoding="utf-8")
    mods = [l for l in arq.splitlines() if RE_LINHA_MODULO.match(l.strip())]
    tabela_mod = ("| id | módulo | responsabilidade | interface | depende-de |\n"
                  "|---|---|---|---|---|\n" + "\n".join(mods)) if mods else "_(indisponível)_"

    pacote = SAIDA / f"{task_id}-cego.md"
    pacote.write_text(PROMPT.format(task_id=task_id, n=len(ordenados), modulos=tabela_mod,
                                    tabela="\n".join(linhas)), encoding="utf-8")

    chave = SAIDA / f"{task_id}-mapa.json"
    chave.write_text(json.dumps({
        "task_id": task_id,
        "aviso": "NÃO entregue este arquivo ao modelo juiz — ele desfaz o cegamento.",
        "cego_para_original": mapa,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    n_dup = sum(1 for a in proj.achados if a.duplica)
    print(f"exportado  {task_id}  ({len(ordenados)} achados, {n_dup} marcados `duplica` pela operadora)")
    print(f"  pacote para o juiz : {pacote}")
    print(f"  mapa (NÃO entregar): {chave}")
    print(f"\nEntregue SÓ o pacote a um segundo modelo — de preferência outra família, não o\n"
          f"que operou o projeto. Salve a resposta em {SAIDA / f'{task_id}-resposta.json'}.")
    return 0


# ------------------------------------------------------------------- comparação

def _pares_positivos(grupos: list[list[str]]) -> set[frozenset]:
    """Todo par dentro de um mesmo grupo é uma decisão 'mesmo defeito = sim'."""
    return {frozenset(p) for g in grupos for p in combinations(sorted(set(g)), 2)}


def _kappa(op: set, juiz: set, universo: list[frozenset]) -> tuple[float | None, dict]:
    n11 = sum(1 for p in universo if p in op and p in juiz)
    n10 = sum(1 for p in universo if p in op and p not in juiz)
    n01 = sum(1 for p in universo if p not in op and p in juiz)
    n00 = len(universo) - n11 - n10 - n01
    n = len(universo)
    tabela = {"ambos_sim": n11, "so_gerador": n10, "so_juiz": n01, "ambos_nao": n00, "pares": n}
    if n == 0:
        return None, tabela
    po = (n11 + n00) / n
    p_op, p_ju = (n11 + n10) / n, (n11 + n01) / n
    pe = p_op * p_ju + (1 - p_op) * (1 - p_ju)
    if abs(1 - pe) < 1e-12:
        return None, tabela          # degenerado: nenhum dos dois marcou nada
    k = (po - pe) / (1 - pe)
    return (0.0 if abs(k) < 1e-9 else k), tabela   # evita -0.000 virar "pior que acaso"


# Abaixo disto κ é numericamente instável: uma única discordância move o valor de
# ponta a ponta, e a etiqueta qualitativa passa a descrever ruído. O caso não é
# "concordam" nem "discordam" — é "os dois juízes quase não marcaram nada, e sobre
# tão pouco não se calcula concordância".
MIN_POSITIVOS = 5


def _interpretar(k: float | None, positivos: int = 999) -> str:
    if positivos < MIN_POSITIVOS:
        return (f"NÃO INFORMATIVO — os dois juízes somam {positivos} par(es) marcado(s) como "
                f"duplicata em toda a matriz. κ é instável nessa esparsidade e o rótulo "
                f"qualitativo descreveria ruído. O que o dado diz é que ambos veem "
                f"pouquíssima sobreposição — não que concordam ou discordam sobre ela.")
    if k is None:
        return ("indefinido — nenhum dos dois juízes marcou duplicata alguma, ou marcaram "
                "todas. κ não é calculável e a concordância bruta não significa nada aqui.")
    if k < 0:
        return "pior que acaso — as marcações discordam sistematicamente."
    if k < 0.20:
        return "desprezível — a marcação de duplicatas NÃO é reprodutível entre juízes."
    if k < 0.40:
        return "fraca — o discriminante central da RO3 depende de quem marca."
    if k < 0.60:
        return "moderada — reportar como limitação quantificada, não resolvida."
    if k < 0.80:
        return "substancial — a marcação do gerador se sustenta razoavelmente."
    return "quase perfeita — a marcação deixa de ser ponto fraco do desenho."


OLLAMA = "http://localhost:11434/api/chat"
SCHEMA_JUIZ = {"type": "object", "required": ["grupos"], "properties": {
    "grupos": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}}}


# --- juízes remotos, acrescentados em 2026-08-12 -----------------------------
# Motivo: o teste no T21 mostrou que o `qwen3.6:27b` LOCAL (quantizado Q4_K_M) marca
# duplicatas de forma que não concorda com ninguém — nem com o gerador, nem com o GPT,
# nem com sua própria versão full. κ contra o gerador: −0,001 no Q4, 0,333 no full.
# Os κ baixos do lote mediam, em boa parte, o instrumento; não o construto.
REMOTOS = {
    "qwen3.8-max": ("https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions", "QWEN_API_KEY"),
    "qwen3.6-27b": ("https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions", "QWEN_API_KEY"),
    "gpt-5.4-2026-03-05": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
}


def _remoto(prompt: str, modelo: str) -> dict:
    """Juiz por API OpenAI-compatível. Modelo PINADO por data onde o serviço oferece —
    'gpt-5.4' flutuante tornaria o resultado irreprodutível num artefato de pesquisa."""
    import os, urllib.request
    url, var = REMOTOS[modelo]
    chave = os.environ.get(var)
    if not chave:
        raise SystemExit(f"ERRO: {var} não está no ambiente. Exporte antes de rodar.")
    corpo = {"model": modelo, "messages": [{"role": "user", "content": prompt}]}
    if "gpt" in modelo:
        corpo["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "grupos", "strict": True,
            "schema": {"type": "object", "additionalProperties": False, "required": ["grupos"],
                       "properties": {"grupos": {"type": "array",
                                                 "items": {"type": "array", "items": {"type": "string"}}}}}}}
    else:
        corpo["response_format"] = {"type": "json_object"}
    # STREAMING nos modelos de raciocínio. Sem ele a conexão fica muda enquanto o modelo
    # pensa e o read timeout dispara: o `qwen3.6-27b` estourou 1800 s no pacote do T21
    # (110 achados) e nunca respondeu. Com stream a mesma chamada fecha em 233 s.
    #
    # A alternativa — `enable_thinking: false` — resolve o tempo (5 s) e DEGRADA o
    # julgamento: 4 grupos contra 13 no T21, esparso como o modelo local quantizado.
    # Rapidez pela via errada estragaria justamente o que este juiz existe para medir.
    stream = "qwen" in modelo
    if stream:
        corpo["stream"] = True
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(),
                                 headers={"Authorization": f"Bearer {chave}",
                                          "Content-Type": "application/json"})
    if not stream:
        with urllib.request.urlopen(req, timeout=1800) as f:
            txt = json.loads(f.read())["choices"][0]["message"]["content"]
    else:
        partes = []
        with urllib.request.urlopen(req, timeout=1800) as f:
            for bruto in f:
                linha = bruto.decode("utf-8").strip()
                if not linha.startswith("data:"):
                    continue
                dado = linha[5:].strip()
                if dado == "[DONE]":
                    break
                j = json.loads(dado)
                for ch in j.get("choices", []):
                    partes.append(ch.get("delta", {}).get("content") or "")
        txt = "".join(partes)
    return json.loads(txt[txt.index("{"):txt.rindex("}") + 1])


def julgar(task_id: str, modelo: str = "qwen3.6:27b") -> int:
    """Submete o pacote cego ao segundo modelo pela API do Ollama e grava a resposta.

    POR QUE API E NÃO `ollama run`
    ------------------------------
    O CLI redesenha a linha enquanto escreve, e as sequências de terminal entram no
    arquivo mesmo com stdout redirecionado. No T23-canario vieram três `cursor-left`
    seguidos de `erase-line`: caracteres foram SOBRESCRITOS, e o JSON saiu truncado no
    meio de um id (`"F-24", "F-3` seguido de `"F-37"`).

    Falhou alto — o JSON nem parseou, e o `comparar` ainda valida cada id contra o
    pacote, então id inventado é recusado. Mas depender de duas redes de proteção contra
    um defeito de transporte é ruim: bastaria a sobrescrita produzir um id VÁLIDO para
    a corrupção passar calada. T22 e T24 não têm nenhum cursor-left; o T21 passou pela
    validação de ids. Só o T23 foi atingido.

    A API não desenha nada e aceita o schema, então o formato é garantido na origem.
    Mesmo modelo e mesmos parâmetros do Modelfile — não passo `options`, para não trocar
    o que o CLI usava por outra coisa no meio do lote.
    """
    pacote = SAIDA / f"{task_id}-cego.md"
    if not pacote.exists():
        print(f"ERRO: {pacote} não existe — rode `exportar` antes.", file=sys.stderr)
        return 1
    texto = pacote.read_text(encoding="utf-8")
    if modelo in REMOTOS:
        resp = _remoto(texto, modelo)
    else:
        corpo = json.dumps({"model": modelo, "stream": False, "think": False,
                            "format": SCHEMA_JUIZ,
                            "messages": [{"role": "user", "content": texto}]}).encode()
        req = urllib.request.Request(OLLAMA, data=corpo, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3600) as f:
            resp = json.loads(json.loads(f.read())["message"]["content"])
    sufixo = "" if modelo == "qwen3.6:27b" else "-" + modelo.replace(":", "_").replace(".", "_")
    destino = SAIDA / f"{task_id}-resposta{sufixo}.json"
    destino.write_text(json.dumps(resp, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{task_id}: {len(resp['grupos'])} grupo(s) do juiz cego -> {destino}")
    return 0


def comparar(task_id: str, caminho_resposta: str) -> int:
    try:
        proj = carregar(RO3 / task_id)
    except ErroDeFormato as e:
        print(f"ERRO DE FORMATO: {e}", file=sys.stderr)
        return 1

    mapa_arq = SAIDA / f"{task_id}-mapa.json"
    if not mapa_arq.exists():
        print(f"ERRO: {mapa_arq} não existe — rode `exportar` antes.", file=sys.stderr)
        return 1
    mapa = json.loads(mapa_arq.read_text(encoding="utf-8"))["cego_para_original"]

    bruto = json.loads(Path(caminho_resposta).read_text(encoding="utf-8"))
    if "grupos" not in bruto:
        print("ERRO: resposta sem a chave 'grupos'.", file=sys.stderr)
        return 1

    desconhecidos = [c for g in bruto["grupos"] for c in g if c not in mapa]
    if desconhecidos:
        print(f"ERRO: o juiz citou ids que não existem no pacote: {', '.join(sorted(set(desconhecidos)))}. "
              f"Resposta inválida — não é remapeável.", file=sys.stderr)
        return 1

    grupos_juiz = [[mapa[c] for c in g] for g in bruto["grupos"]]
    grupos_op = [[a.id for a in g] for g in clusters(proj) if len(g) > 1]

    pares_op, pares_juiz = _pares_positivos(grupos_op), _pares_positivos(grupos_juiz)
    ids = sorted(a.id for a in proj.achados)
    modulo = {a.id: a.modulo for a in proj.achados}

    todos = [frozenset(p) for p in combinations(ids, 2)]
    mesmo_mod = [p for p in todos if len({modulo[i] for i in p}) == 1]

    print(f"# Remarcação cega de duplicatas — {task_id}\n")
    print(f"Achados: {len(ids)}  ·  grupos do modelo gerador: {len(grupos_op)}  ·  "
          f"grupos do juiz cego: {len(grupos_juiz)}\n")

    for rotulo, universo in (("todos os pares", todos), ("só pares do mesmo módulo", mesmo_mod)):
        k, t = _kappa(pares_op, pares_juiz, universo)
        positivos = t['ambos_sim'] + t['so_gerador'] + t['so_juiz']
        print(f"## κ — {rotulo}\n")
        print(f"  κ de Cohen           {'indefinido' if k is None else f'{k:.3f}'}")
        print(f"  interpretação        {_interpretar(k, positivos)}")
        print(f"  pares avaliados      {t['pares']}")
        print(f"  ambos: duplicata     {t['ambos_sim']}")
        print(f"  só o modelo gerador  {t['so_gerador']}")
        print(f"  só o juiz cego       {t['so_juiz']}")
        print(f"  ambos: distintos     {t['ambos_nao']}\n")

    so_op = sorted(pares_op - pares_juiz)
    so_ju = sorted(pares_juiz - pares_op)
    if so_op or so_ju:
        print("## Discordâncias, uma a uma\n")
        for par in so_op:
            a, b = sorted(par)
            print(f"  gerador agrupou, juiz não:  {a} + {b}  ({modulo[a]} / {modulo[b]})")
        for par in so_ju:
            a, b = sorted(par)
            print(f"  juiz cego agrupou, gerador não: {a} + {b}  ({modulo[a]} / {modulo[b]})")
        print("\nCada discordância é um caso concreto para o texto do paper. `só o juiz cego`\n"
              "é o achado mais interessante: sobreposição que o GERADOR não viu nos achados\n"
              "que ele mesmo produziu — autoavaliação falhando onde o cego enxerga.")
    else:
        print("Nenhuma discordância par a par.")
    return 0


def main(argv):
    if len(argv) == 2 and argv[0] == "exportar":
        return exportar(argv[1])
    if len(argv) in (2, 3) and argv[0] == "julgar":
        return julgar(argv[1], *(argv[2:]))
    if len(argv) == 3 and argv[0] == "comparar":
        return comparar(argv[1], argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
