"""Prepara o workspace de um projeto do lote — ou todos.

    python3 preparar.py estrutura          # cria as 12 pastas + ENUNCIADO.md + PROJETOS.md
    python3 preparar.py workspace T01-ratelimit   # instala o Versus na pasta do projeto
    python3 preparar.py estado             # mostra em que pé está cada projeto

`workspace` copia os bundles da extensão INSTALADA MAIS RECENTE e escreve
`.mcp.json` e `.claude/settings.json` com os 7 hooks. Rode logo antes de começar o
projeto, não meses antes: assim o projeto roda na versão vigente, e não numa cópia
velha esquecida na pasta. A versão usada vai para o LOG-OPERACAO.md.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

RO3 = Path(__file__).resolve().parent.parent
EXT_DIR = Path.home() / ".vscode-server" / "extensions"

# Congelado no BATCH-PROTOCOL §2. A coluna `lentes` NÃO vai para dentro do
# workspace — é predição, e a sessão que opera o projeto não pode vê-la antes da
# Fase 2 declarar as lentes ativas.
PROJETOS = [
    ("T21-certificados", "Monitor de validade de certificados com renovação antecipada "
     "e registro de quem aprovou cada emissão", "RES · CTR · OBS · GOV"),
    ("T22-plantoes", "Distribuidor de plantões com restrições, trocas entre pessoas e "
     "aprovação", "ETI · PRO · JOG · GOV · UX"),
    ("T23-canario", "Coordenador de implantação canário com rollback automático por "
     "métrica, convivendo com a versão estável", "CTR · RES · OBS · MIG · PRO"),
    ("T24-catalogo", "Catálogo de dados com donos declarados por domínio e linhagem "
     "entre eles", "GOV · LIN · MEC"),
    ("T25-orcamento", "Painel de consumo com teto de orçamento e corte automático ao "
     "atingir o limite", "SUS · OBS · CTR · UX"),
    ("T26-extratos", "Importador de extratos de múltiplas fontes externas, com "
     "deduplicação e conciliação", "LIN · RES · SUS · MIG"),
    ("T27-despesas", "Fila de aprovação de despesas com alçadas por valor e delegação "
     "temporária", "PRO · GOV · JOG · UX"),
    ("T28-agenda", "Sincronizador entre dois calendários externos, com detecção e "
     "resolução de conflito", "RES · LIN · CTR · PRO"),
    ("T29-retencao", "Compactador de séries temporais com política de retenção e troca "
     "do formato de armazenamento", "SUS · MIG · MEC · LIN"),
    ("T30-notifica", "Serviço de notificação com preferências por pessoa, supressão e "
     "canais externos", "RES · PRO · UX · ETI · OBS · SUS"),
    ("T31-precos", "Motor de regras de preço com faixas, histórico e explicação da "
     "decisão, substituindo uma tabela legada", "ETI · GOV · MEC · LIN · MIG"),
    ("T32-triagem", "Triagem de chamados com prioridade automática, reclassificação e "
     "recurso do solicitante", "ETI · CTR · PRO · UX · MEC · JOG"),
]
PILOTO = {"T21-certificados", "T24-catalogo"}

# Ciclo 1 descartado integralmente em 2026-08-08 — ver _lote-1-descartado/MOTIVO.md.
# Os sete projetos e a lista de enunciados antiga não são reaproveitados.
DESCARTADOS = [
    ("ciclo 1 — 7 projetos", "2026-08-08", "T01, T13, T05, T14, T15, T02, T03. Descarte "
     "integral para que os doze rodem sob instrumento único — ver "
     "_lote-1-descartado/MOTIVO.md"),
    ("T21-quotas", "2026-08-09", "coluna `lente` da matriz sem validação — 4 achados com "
     "nome abreviado. Corrigido na v0.14.0; slot reaproveitado pela 2ª vez"),
    ("T21-cofre", "2026-08-08", "reset do laço 2↔3 era assimétrico: os critérios da Fase 3 "
     "sobreviviam à volta, e o gate 3→4 passou com o carimbo da iteração 1. Corrigido na "
     "v0.13.1; slot reaproveitado com enunciado novo"),
]

HOOKS = ["inject-context.js", "phase-gate.js", "loop-detector.js", "test-outcome.js",
         "truncation-check.js", "block-destructive.js", "stop-verify.js", "server.js"]
FERRAMENTAS = ["get_phase_state", "get_decisions", "get_exit_criteria", "advance_phase",
               "start_iteration", "record_decision", "update_score", "mark_exit_criterion",
               "check_safeguard", "check_all_safeguards", "check_specs_status", "init_project",
               "get_phase_guidance", "update_project_spec", "start_new_cycle"]
GERAIS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "WebFetch", "WebSearch", "NotebookEdit"]
SPECS = ["domain", "references", "technical", "examples", "design", "models", "datasets",
         "validation", "competitors"]

ENUNCIADO = """\
# {task_id}

{descricao}

---

## O que é este arquivo

O enunciado congelado do projeto, como está no `BATCH-PROTOCOL.md` §2. **Não o
expanda aqui** — detalhar o problema é trabalho da Fase 0, e é justamente o que o
método está medindo.

As lentes condicionais que se espera que ativem existem, mas ficam **fora** desta
pasta de propósito (em `RO3/PROJETOS.md` e na sua predição selada). Se estivessem
aqui, a sessão as leria antes da Fase 2 declarar as lentes ativas, e a comparação
predição × declaração — que é a medição — ficaria contaminada.

## Forma e porte (§2, congelado)

- 8 a 12 módulos.
- Sessão única, 2 a 4 horas.
- Critério de acerto objetivo, escrito **antes** de codar (vai na sua predição e
  reaparece na Fase 0). É o que torna o retrabalho mensurável.
- Sem exposição prévia: nada do corpus antigo.
"""


def _extensao(pedida: str | None = None) -> tuple[Path, str]:
    """Extensão versus-claude na versão PEDIDA.

    Escolher sozinho a mais alta instalada foi como o T07 acabou preparado na 0.12.8
    enquanto os quatro projetos válidos rodavam na 0.12.7 — heterogeneidade de
    instrumento no meio da coleta, que é o que já custou três descartes. Num lote que
    depende de versão única, a versão é argumento obrigatório.
    """
    achadas = []
    for d in EXT_DIR.glob("jasminemoreira.versus-claude-*"):
        m = re.search(r"-(\d+)\.(\d+)\.(\d+)$", d.name)
        if m and (d / "out" / "bundle" / "server.js").exists():
            achadas.append((tuple(int(x) for x in m.groups()), d))
    if not achadas:
        raise SystemExit(f"ERRO: nenhuma extensão versus-claude com bundle em {EXT_DIR}")
    achadas.sort()
    disponiveis = [".".join(map(str, v)) for v, _ in achadas]
    if pedida is None:
        raise SystemExit(
            f"ERRO: informe a versão explicitamente — `--versao <x.y.z>`.\n"
            f"  instaladas: {', '.join(disponiveis)}\n"
            f"  Escolher a mais alta automaticamente já causou heterogeneidade de "
            f"instrumento no meio de um lote.")
    for v, d in achadas:
        if ".".join(map(str, v)) == pedida:
            return d, pedida
    raise SystemExit(f"ERRO: versão {pedida} não instalada. Disponíveis: {', '.join(disponiveis)}")


def _hooks(ws: Path) -> dict:
    def cmd(nome, timeout=None):
        h = {"type": "command", "command": f'node "{ws / ".versus" / nome}"'}
        if timeout:
            h["timeout"] = timeout
        return h
    return {
        "UserPromptSubmit": [{"hooks": [cmd("inject-context.js")]}],
        "PreToolUse": [
            {"matcher": "Edit|Write", "hooks": [cmd("phase-gate.js")]},
            {"matcher": "Bash", "hooks": [cmd("loop-detector.js")]},
            {"matcher": "Bash", "hooks": [cmd("block-destructive.js")]},
        ],
        "PostToolUse": [
            {"matcher": "Grep|Bash", "hooks": [cmd("truncation-check.js")]},
            {"matcher": "Bash", "hooks": [cmd("test-outcome.js")]},
        ],
        "Stop": [{"hooks": [cmd("stop-verify.js", 120)]}],
    }


def estrutura() -> int:
    for task_id, descricao, _ in PROJETOS:
        ws = RO3 / task_id
        ws.mkdir(exist_ok=True)
        alvo = ws / "ENUNCIADO.md"
        if not alvo.exists():
            alvo.write_text(ENUNCIADO.format(task_id=task_id, descricao=descricao), encoding="utf-8")

    linhas = ["# Os 12 projetos do lote\n",
              "Congelado no `BATCH-PROTOCOL.md` §2. `taskId` é o nome da pasta E o nome do",
              "projeto no `init_project` — sem variação, ou o pareamento futuro se perde.\n",
              "> As **lentes esperadas** ficam nesta tabela, fora das pastas dos projetos. É",
              "> predição: se estivesse dentro do workspace, a sessão a leria antes da Fase 2",
              "> declarar as lentes ativas, e a medição ia embora.\n",
              "| # | taskId | o que é | lentes esperadas | piloto |",
              "|---|---|---|---|---|"]
    for i, (task_id, descricao, lentes) in enumerate(PROJETOS, start=1):
        linhas.append(f"| {i} | `{task_id}` | {descricao} | {lentes} | "
                      f"{'sim' if task_id in PILOTO else ''} |")
    if DESCARTADOS:
        linhas += ["\n## Descartados\n",
                   "| taskId | data | motivo |", "|---|---|---|"]
        linhas += [f"| `{t}` | {d} | {m} |" for t, d, m in DESCARTADOS]
    linhas += ["\nO piloto (§6) é T21 e T24, que exercitam grupos de lentes disjuntos. O objetivo",
               "dele não é dado: é descobrir se o formato do achado sobrevive ao uso real.",
               "Depois do piloto, os dez restantes em qualquer ordem.\n",
               "Estado de cada projeto: `python3 analise/preparar.py estado`"]
    (RO3 / "PROJETOS.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"12 pastas com ENUNCIADO.md + PROJETOS.md em {RO3}")
    return 0


def workspace(task_id: str, versao: str | None = None) -> int:
    if task_id not in {t for t, _, _ in PROJETOS}:
        raise SystemExit(f"ERRO: '{task_id}' não é um taskId do lote. Veja PROJETOS.md.")
    ws = RO3 / task_id
    if (ws / ".versus" / "state.json").exists():
        print(f"aviso: {task_id} já foi iniciado (state.json existe). "
              f"Atualizando bundles sem tocar no estado.")
    ext, versao = _extensao(versao)

    (ws / ".versus").mkdir(parents=True, exist_ok=True)
    for f in HOOKS:
        shutil.copyfile(ext / "out" / "bundle" / f, ws / ".versus" / f)
    (ws / ".versus" / "package.json").write_text(json.dumps({"type": "commonjs"}, indent=2) + "\n")

    (ws / ".mcp.json").write_text(json.dumps({"mcpServers": {"versus-claude": {
        "type": "stdio", "command": "node", "args": [str(ws / ".versus" / "server.js")], "env": {},
    }}}, indent=2) + "\n", encoding="utf-8")

    (ws / ".claude").mkdir(exist_ok=True)
    (ws / ".claude" / "settings.json").write_text(json.dumps({
        "permissions": {"allow": [f"mcp__versus-claude__{t}" for t in FERRAMENTAS] + GERAIS},
        "hooks": _hooks(ws),
    }, indent=2) + "\n", encoding="utf-8")

    for d in SPECS:
        (ws / "specs" / d).mkdir(parents=True, exist_ok=True)

    faltando = [f for f in HOOKS if not (ws / ".versus" / f).exists()]
    if faltando:
        raise SystemExit(f"ERRO: hooks não copiados: {', '.join(faltando)}")
    print(f"preparado  {task_id}  (versus-claude {versao})")
    print(f"  anote a versão {versao} no LOG-OPERACAO.md")
    print(f"  abra uma conversa NOVA em {ws} e digite: start")
    return 0


def estado() -> int:
    print(f"{'projeto':<18} {'predição':<10} {'selo':<8} {'preparado':<11} {'iniciado':<10} matriz")
    for task_id, _, _ in PROJETOS:
        ws = RO3 / task_id
        pred = "sim" if (RO3 / "_predicoes" / f"{task_id}.md").exists() else "—"
        selo = "sim" if (ws / "PREDICAO-HASH.txt").exists() else "—"
        prep = "sim" if (ws / ".versus" / "server.js").exists() else "—"
        ini = "sim" if (ws / ".versus" / "state.json").exists() else "—"
        mat = "sim" if (ws / "specs" / "design" / "coverage-matrix.md").exists() else "—"
        print(f"{task_id:<18} {pred:<10} {selo:<8} {prep:<11} {ini:<10} {mat}")
    print("\nordem por projeto: predição → selo → preparado → iniciado → matriz")
    return 0


def main(argv):
    if len(argv) == 1 and argv[0] == "estrutura":
        return estrutura()
    if len(argv) == 1 and argv[0] == "estado":
        return estado()
    if len(argv) >= 2 and argv[0] == "workspace":
        v = argv[argv.index("--versao") + 1] if "--versao" in argv else None
        return workspace(argv[1], v)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
