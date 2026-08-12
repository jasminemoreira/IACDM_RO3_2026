"""Reestimativa externa das lentes, sobre a arquitetura em vez do enunciado.

    python3 reestimar_lentes.py T13-autoscaler --versao 1
    python3 reestimar_lentes.py T13-autoscaler --versao final --n 3

POR QUE EXISTE
--------------
A predição do §3 é feita sobre o `ENUNCIADO.md` — uma linha. A Fase 2 declara as
lentes depois das Fases 0 e 1. Comparar as duas confunde o que o §3 quer medir
(a ativação depende de quem lê?) com o salto de informação entre uma frase e o
resultado de duas fases. O T05 mostrou isso: os estimadores deduziram MIG, SUS,
OBS e MEC de "ETL com versionamento de esquema", e a Fase 0 fixou arquivos locais,
SQLite, usuário único e telemetria fora de escopo — as quatro caíram por informação
que o enunciado não continha.

Este módulo dá ao estimador a MESMA arquitetura, e mede o que sobra da divergência.

DOIS ESTIMADORES, n=3, EM TODOS OS DOZE — FIXADO EM 2026-08-09
-------------------------------------------------------------
`--modelo qwen3.6:27b` (Ollama local) e `--modelo kimicode` (Kimi Code CLI, headless
em diretório temporário vazio). Os dois em todo projeto, sempre com `--n 3`.

Não é redundância. No T21 os dois lêem partes diferentes da definição da lente: o Qwen
aplica o GATILHO como escrito, o Kimi a PERGUNTA CENTRAL — e em ETI, JOG e LIN os dois
campos apontam para conjuntos diferentes. Com um estimador só, o mesmo projeto reporta
"3 divergências" ou "nenhuma" conforme qual esteja disponível.

CUIDADO AO LER A CONCORDÂNCIA: ela está contaminada pela taxa-base. Com 11 de 12
condicionais ativas, um leitor que dissesse "sim" a tudo acertaria 11. O estimador mais
permissivo concorda mais sem ler melhor. **Nunca reporte concordância sem a contagem de
ativações por rodada ao lado.**

n=3 é fixo. Aumentar no meio do lote trocaria homogeneidade por precisão que não teríamos
como usar — os projetos já rodados não seriam comparáveis aos seguintes.

AS DUAS VERSÕES RESPONDEM PERGUNTAS DIFERENTES
----------------------------------------------
`--versao 1`  → a V(1), que é o que o declarante tinha à vista. Verificado nos dois
  projetos do piloto: a declaração de lentes acontece UMA vez, na primeira passada da
  Fase 2, e não é refeita quando o laço 2↔3 retorna. Logo V(1) é a base
  informacionalmente equivalente à declaração. Mede: dada a mesma informação,
  leitores independentes ativam as mesmas lentes?

`--versao final` → a última versão da arquitetura. NÃO é comparável à declaração —
  o declarante nunca a viu. Mede outra coisa: o conjunto declarado ainda valeria
  depois de a arquitetura mudar? Divergência aqui é evidência de que a ativação
  deveria ser reavaliada a cada iteração do laço, e não fixada na primeira.

Só é possível porque a v0.12.5 fez a Fase 3 ACRESCENTAR `## V(N+1)` em vez de
sobrescrever. Antes disso a V(1) não sobreviveria ao fim do projeto.

O QUE NÃO ENTRA NO PACOTE
-------------------------
O `projectSpec` (stack, constraints, outOfScope, patterns). Suas entradas são listas
de strings sem carimbo de tempo — não há como provar quais existiam quando a Fase 2
declarou. Tentei datá-las cruzando com o texto das decisões anteriores ao gate 1→2 e
o casamento textual falhou (marcou como indeterminado até "8 a 12 módulos", que vem
do enunciado). Excluir subinforma o estimador em relação ao que a Fase 2 viu, e o
viés disso é conservador: empurra para divergir, contra a hipótese de que a ativação
é reprodutível.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingerir_kimi import extrair  # noqa: E402
from predicao_cega import LENTES, REGRA_ATIVACAO  # noqa: E402
from ro3_parser import SIGLA, carregar  # noqa: E402
from rodar_predicao import SCHEMA  # noqa: E402
from rodar_predicao_kimi import _validar  # noqa: E402

SCHEMA_ESTRITO = {
    "type": "object", "additionalProperties": False,
    "required": ["projeto", "modulos_estimados", "lentes"],
    "properties": {
        "projeto": {"type": "string"},
        "modulos_estimados": {"type": "integer"},
        "lentes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["lente", "ativa", "sinal"],
            "properties": {"lente": {"type": "string"}, "ativa": {"type": "boolean"},
                           "sinal": {"type": "string"}}}}}}

RO3 = Path(__file__).resolve().parent.parent
SAIDA = Path(__file__).resolve().parent / "cego"
OLLAMA = "http://localhost:11434/api/chat"
KIMI = Path.home() / ".kimi-code" / "bin" / "kimi"
NOMES = [n for n, _, _ in LENTES]
RE_V = re.compile(r"^#+\s*V\s*\(?(\d+)\)?\b", re.I)

PACOTE = """\
# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> {descricao}

## A arquitetura

{arquitetura}

---

## Como funcionam as lentes

Um processo de crítica arquitetural aplica lentes: cada uma faz uma pergunta central
a cada módulo, e detecta uma classe de falha que as outras não detectam.

**Sete são universais** — rodam sempre e não estão em questão: Premissas, Arquitetura,
Implementabilidade, Rigor científico, Segurança, Desempenho, Conformidade regulatória.
**Não as inclua na resposta.**

**Doze são condicionais**, e são essas que você vai avaliar.

{regra}


| lente | pergunta central | ativa quando |
|---|---|---|
{tabela}

---

## O que responder

Para **cada uma das 12**: `ativa` (true/false) e `sinal` — uma frase curta dizendo **o
que na arquitetura** aciona, ou não aciona, a lente. Preencha o `sinal` também nas
`false`. E `modulos_estimados`: quantos módulos a arquitetura tem.

As 12 têm que aparecer, com o nome exato da tabela. Só o JSON, sem preâmbulo:

```json
{{
  "projeto": "{task_id}",
  "modulos_estimados": 0,
  "lentes": [{{"lente": "Resilience", "ativa": true, "sinal": "..."}}]
}}
```
"""


def fatiar(texto: str, alvo: str) -> tuple[str, int]:
    """Devolve o trecho da versão pedida e o número dela.

    `alvo` é "1" (a primeira) ou "final" (da última seção de versão em diante).
    O corte é por cabeçalho `## V(N)`, o formato que a v0.12.5 impôs.
    """
    linhas = texto.splitlines()
    marcas = [(n, int(m.group(1))) for n, l in enumerate(linhas)
              if (m := RE_V.match(l.strip()))]
    if not marcas:
        raise SystemExit("ERRO: architecture.md sem seções de versão (`## V(N)`). "
                         "Projeto anterior à v0.12.5 — a V(1) não sobreviveu.")
    versoes = sorted({v for _, v in marcas})
    escolhida = versoes[0] if alvo == "1" else versoes[-1]
    ini = min(n for n, v in marcas if v == escolhida)
    posteriores = [n for n, v in marcas if v > escolhida]
    fim = min(posteriores) if posteriores else len(linhas)
    return "\n".join(linhas[ini:fim]).strip(), escolhida


def _ollama(prompt: str, modelo: str, temp: float, seed: int) -> dict:
    """Ollama aceita `format` como JSON Schema, então a validação é do servidor."""
    corpo = json.dumps({"model": modelo, "messages": [{"role": "user", "content": prompt}],
                        "stream": False, "think": False, "format": SCHEMA,
                        "options": {"temperature": temp, "seed": seed}}).encode()
    req = urllib.request.Request(OLLAMA, data=corpo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=2400) as f:
        return json.loads(json.loads(f.read())["message"]["content"])


REMOTOS = {
    "qwen3.6-27b": ("https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions", "QWEN_API_KEY"),
    "gpt-5.4-2026-03-05": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
}


def _remoto(prompt: str, modelo: str, seed: int) -> dict:
    """Estimadores por API OpenAI-compatível, acrescentados em 2026-08-12.

    POR QUE FORAM ACRESCENTADOS
    ---------------------------
    A remarcação cega dos doze mostrou que o `qwen3.6:27b` LOCAL (Q4_K_M) é outlier:
    marcou 87 pares de duplicata contra 71 do gerador, mas compartilha só 17 com sua
    própria versão full e 24 com o GPT. Não marca pouco — marca outra coisa. Isso põe
    sob suspeita também as estimativas de lente dele, que sustentam o Resultado 2
    (80% de concordância com a Fase 2, contra 87% do Kimi).

    `qwen3.6-27b` full isola a quantização; `gpt-5.4` acrescenta uma terceira família.
    Os resultados do local NÃO são descartados — viram o dado sobre modelo quantizado.

    É possível fazer isto retrospectivamente porque o pacote é reproduzível byte a byte
    a partir da V(1) congelada (verificado). Não há informação futura vazando: o
    estimador vê a mesma arquitetura que veria na época.

    Modelo PINADO por data onde o serviço oferece — 'gpt-5.4' flutuante tornaria o
    resultado irreprodutível num artefato de pesquisa.

    STREAMING nos modelos de raciocínio, pela mesma razão do `cegar_duplicatas.py`: sem
    ele a conexão fica muda enquanto o modelo pensa e o read timeout dispara.
    """
    import os
    url, var = REMOTOS[modelo]
    chave = os.environ.get(var)
    if not chave:
        raise SystemExit(f"ERRO: {var} não está no ambiente.")
    corpo = {"model": modelo, "messages": [{"role": "user", "content": prompt}]}
    if "gpt" in modelo:
        corpo["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "estimativa", "strict": True, "schema": SCHEMA_ESTRITO}}
        corpo["seed"] = seed
    else:
        # SEM `response_format: json_object` de propósito. Com ele, o qwen3.6-27b emite o
        # JSON ESCAPADO dentro de uma string — `">{\\n \\"projeto\\": ...` — e o parse
        # falha. Sem ele o conteúdo sai limpo, em cerca-de-código markdown, que o corte
        # entre a primeira `{` e a última `}` já resolve. O pacote pede JSON puro.
        # (O gpt aceita json_schema estrito e não tem esse problema.)
        corpo["stream"] = True
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(),
                                 headers={"Authorization": f"Bearer {chave}",
                                          "Content-Type": "application/json"})
    if not corpo.get("stream"):
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
                for ch in json.loads(dado).get("choices", []):
                    partes.append(ch.get("delta", {}).get("content") or "")
        txt = "".join(partes)
    resp = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    problemas = _validar(resp)
    if problemas:
        raise RuntimeError(f"{modelo} fora do contrato: " + "; ".join(problemas))
    return resp


def _kimicode(prompt: str) -> dict:
    """Kimi Code CLI, headless, em diretório descartável.

    Roda em sandbox vazio porque o CLI é agente: com acesso ao repositório ele
    poderia LER os projetos, a matriz de cobertura ou este próprio código, e a
    estimativa deixaria de ser cega. O `-p` já desliga a sessão interativa; o
    sandbox é a garantia de que não há nada para encontrar.

    Sem `--temp` e sem `seed`: o CLI não expõe nenhum dos dois. A variação entre
    rodadas é a que o serviço der, e o critério de estabilidade (3/3 ou 0/3)
    continua valendo — apenas não é o mesmo mecanismo de variação do Ollama, o
    que precisa constar de qualquer comparação entre os dois estimadores.

    O CLI não aceita JSON Schema, então `_validar` faz o trabalho aqui e formato
    inválido é erro visível, nunca resultado parcial silencioso.
    """
    with tempfile.TemporaryDirectory(prefix="kimi-sb-") as sb:
        r = subprocess.run([str(KIMI), "-p", prompt], cwd=sb,
                           capture_output=True, text=True, timeout=2400)
    if r.returncode != 0:
        raise RuntimeError(f"kimi saiu com {r.returncode}: {(r.stderr or r.stdout)[-800:]}")
    # `extrair` devolve TODOS os objetos de nível superior — o CLI narra antes de
    # responder, e a narração pode conter JSON. Exigir exatamente um com `lentes`
    # em vez de pegar o primeiro ou o último: se houver dois, qual é a resposta é
    # adivinhação, e adivinhar aqui contamina a estimativa em silêncio.
    candidatos = [o for o in extrair(r.stdout) if isinstance(o, dict) and "lentes" in o]
    if len(candidatos) != 1:
        raise RuntimeError(f"esperava 1 objeto com `lentes` na saída do kimi, achei "
                           f"{len(candidatos)}:\n{r.stdout[-1200:]}")
    resp = candidatos[0]
    problemas = _validar(resp)
    if problemas:
        raise RuntimeError("resposta do kimi fora do contrato: " + "; ".join(problemas))
    return resp


def main(argv):
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    task_id = argv[0]
    alvo = argv[argv.index("--versao") + 1] if "--versao" in argv else "1"
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 3
    modelo = argv[argv.index("--modelo") + 1] if "--modelo" in argv else "qwen3.6:27b"
    temp = float(argv[argv.index("--temp") + 1] if "--temp" in argv else 0.7)

    ws = RO3 / task_id
    arq, versao = fatiar((ws / "specs" / "technical" / "architecture.md").read_text(encoding="utf-8"), alvo)
    linhas = (ws / "ENUNCIADO.md").read_text(encoding="utf-8").splitlines()
    descricao = next(l.strip() for l in linhas[1:] if l.strip() and not l.startswith("#"))
    tabela = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in LENTES)
    prompt = PACOTE.format(task_id=task_id, descricao=descricao, arquitetura=arq,
                           tabela=tabela, regra=REGRA_ATIVACAO)

    SAIDA.mkdir(exist_ok=True)
    (SAIDA / f"{task_id}-reestimativa-V{versao}-pacote.md").write_text(prompt, encoding="utf-8")
    # O CLI do Kimi não expõe temperatura nem seed; imprimir 0.7 ali seria mentira.
    print(f"{task_id} · V{versao} ({len(arq.splitlines())} linhas de arquitetura) · "
          f"{modelo} · {'temp/seed não expostos pelo CLI' if modelo == 'kimicode' else f'temp {temp}'}"
          f" · {n} rodadas\n")

    votos, ok = Counter(), 0
    for i in range(1, n + 1):
        if modelo == "kimicode":
            r = _kimicode(prompt)
        elif modelo in REMOTOS:
            r = _remoto(prompt, modelo, i)
        else:
            r = _ollama(prompt, modelo, temp, i)
        (SAIDA / f"{task_id}-reestimativa-V{versao}-{modelo.replace(':', '_')}-r{i}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        for l in r["lentes"]:
            if l["ativa"]:
                votos[l["lente"]] += 1
        ok += 1

    proj = carregar(ws)
    # A comparação é contra a declaração DAQUELA ITERAÇÃO, não contra a união.
    #
    # Nos cinco primeiros projetos o conjunto não mudou entre iterações, então união e
    # iteração 1 eram o mesmo e o erro ficava invisível. O T26-extratos é o primeiro em
    # que muda: MIG não está na it1 e entra na it2, contra a V(3). Comparar a estimativa
    # sobre a V(1) com a união contava MIG como "declarada" e transformava um ACERTO dos
    # dois estimadores em divergência.
    #
    # Toda a razão de ser deste módulo é a equivalência informacional (ver o cabeçalho):
    # a V(1) é o que o declarante tinha à vista na primeira passada da Fase 2. Comparar
    # com um conjunto que só existe depois de duas voltas do laço quebra exatamente isso.
    it_alvo = min(proj.condicionais_por_iteracao) if alvo == "1" else max(proj.condicionais_por_iteracao)
    declarado = set(proj.condicionais_por_iteracao[it_alvo])
    if len(set(map(frozenset, proj.condicionais_por_iteracao.values()))) > 1:
        print(f"nota: o conjunto declarado MUDA entre iterações; comparando contra a it{it_alvo} "
              f"({len(declarado)} condicionais), não contra a união "
              f"({len(proj.condicionais_ativas)}).\n")
    estavel = {x for x in NOMES if votos[x] == ok}
    nunca = {x for x in NOMES if votos[x] == 0}
    osc = {x for x in NOMES if 0 < votos[x] < ok}

    print(f"{'lente':<34} {'estimado V' + str(versao):<14} {'Fase 2 declarou'}")
    certos = errados = 0
    for l in NOMES:
        v = votos[l]
        est = "sim" if v == ok else ("não" if v == 0 else f"{v}/{ok}")
        real = l in declarado
        marca = ""
        if l in estavel or l in nunca:
            if (l in estavel) == real:
                certos += 1
            else:
                errados += 1
                marca = "   ← DIVERGE"
        print(f"{SIGLA[l] + ' ' + l:<34} {est:<14} {'SIM' if real else 'não'}{marca}")
    print(f"\ndecisões estáveis: {certos} coincidem, {errados} divergem"
          f"{f' · oscilou em {len(osc)}' if osc else ''}")
    print(f"conjunto declarado : {', '.join(sorted(SIGLA[l] for l in declarado))}")
    print(f"conjunto estimado  : {', '.join(sorted(SIGLA[l] for l in estavel)) or '—'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
