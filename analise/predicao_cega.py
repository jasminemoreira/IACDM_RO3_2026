"""Gera o pacote de predição cega — o texto a entregar a um segundo modelo.

    python3 predicao_cega.py T01-ratelimit          # imprime o pacote
    python3 predicao_cega.py T01-ratelimit --salvar # grava em cego/<taskId>-predicao.md

O QUE O MODELO PREDITOR PODE VER
--------------------------------
Só o `ENUNCIADO.md` do projeto e a definição das 12 lentes condicionais. Nunca:

  - `PROJETOS.md` — tem a coluna "lentes esperadas", que é a resposta;
  - `BATCH-PROTOCOL.md` — tem a mesma coluna, mais a contagem por lente;
  - qualquer predição anterior, sua ou de outro modelo.

As definições das lentes são parte do método, não da resposta: sem elas não há como
predizer nada. A coluna do §2 é a resposta e fica fora.

O QUE O PACOTE DELIBERADAMENTE NÃO DIZ
--------------------------------------
Que isto integra um estudo sobre redundância da taxonomia. Um preditor que soubesse
que se investiga se há lentes demais poderia encolher a lista; que se investiga se
há de menos, inflá-la. A tarefa é entregue como o que ela é do ponto de vista dele —
ler um enunciado e dizer o que aquele projeto aciona.

DURAÇÃO NÃO É PEDIDA
--------------------
O §3 pede duração estimada na predição da operadora. Um modelo não tem base para
estimar quanto TEMPO uma pessoa leva; pedir produziria número inventado. Fica só na
predição da operadora.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RO3 = Path(__file__).resolve().parent.parent
SAIDA = Path(__file__).resolve().parent / "cego"

# As 19 lentes vêm do BUNDLE INSTALADO, não de uma cópia à mão.
#
# Copiar a tabela já falhou três vezes nesta pesquisa: gatilhos encurtados na tradução
# (cloud-native → nuvem), uma regra nova da guidance que não foi replicada no pacote, e
# confusão sobre qual versão o pacote espelhava. Enquanto o estimador e a Fase 2 jogarem
# com textos diferentes, a divergência medida é do analista, não do julgamento.
#
# Desde a v0.14.1 a tabela é DADO em `rules/lenses.ts` (LensDef: name, question,
# failureClass, trigger), então dá para lê-la. Falha alto se não conseguir: um pacote
# montado com tabela vazia ou parcial produziria estimativa que parece válida e não é.

_RE_LENSDEF = re.compile(
    r'\{\s*name:\s*"([^"]+)",\s*question:\s*"((?:[^"\\]|\\.)*)",'
    r'\s*failureClass:\s*"((?:[^"\\]|\\.)*)"'
    r'(?:,\s*trigger:\s*"((?:[^"\\]|\\.)*)")?\s*\}')


def _bundle() -> Path:
    """server.js do instrumento. Exige versão única — se houver mais de uma, qual delas
    o estimador espelha vira pergunta que só a máquina responde.

    Mesma ordem de busca do `ro3_parser`: `$VERSUS_BUNDLE`, depois a cópia arquivada em
    `instrumento/server.js`, e só então o que está instalado no VSCode. A cópia arquivada
    existe para o artefato publicado não depender do estado da máquina — em 2026-08-12,
    com as correções pós-lote sendo aplicadas, passaram a coexistir 0.14.2, 0.15.0 e
    0.16.0, e o guard travou a análise do lote já fechado.
    """
    import os as _os
    pino = _os.environ.get("VERSUS_BUNDLE")
    if pino and Path(pino).is_file():
        return Path(pino)
    arquivado = Path(__file__).resolve().parent.parent / "instrumento" / "server.js"
    if arquivado.is_file():
        return arquivado
    base = Path.home() / ".vscode-server" / "extensions"
    achadas = sorted(base.glob("jasminemoreira.versus-claude-*/out/bundle/server.js"))
    if not achadas:
        raise SystemExit("ERRO: nenhum bundle versus-claude instalado — o pacote de "
                         "estimativa não pode ser montado sem a tabela de lentes.")
    if len(achadas) > 1:
        vs = ", ".join(p.parts[-4].split("claude-")[-1] for p in achadas)
        raise SystemExit(f"ERRO: {len(achadas)} versões instaladas ({vs}). Desinstale as "
                         f"antigas: o estimador precisa espelhar uma só.")
    return achadas[0]


def _carregar_lentes() -> list[tuple[str, str, str]]:
    txt = _bundle().read_text(encoding="utf-8", errors="replace")
    defs = _RE_LENSDEF.findall(txt)
    # O bundle guarda as strings como literais JS entre aspas duplas, com escapes
    # unicode (\u2014). Decodificar como string JSON é exatamente o formato certo —
    # tentei latin-1 antes e ela descartava o travessão em silêncio.
    def limpa(x: str) -> str:
        try:
            return json.loads(f'"{x}"')
        except json.JSONDecodeError:
            return x

    cond = [(limpa(n), limpa(q), limpa(g)) for n, q, _f, g in defs if g]
    if len(defs) != 19 or len(cond) != 12:
        raise SystemExit(
            f"ERRO: extraí {len(defs)} lentes ({len(cond)} condicionais) do bundle; "
            f"esperado 19 e 12. O formato de LensDef mudou — corrija _RE_LENSDEF antes "
            f"de gerar qualquer estimativa.")
    return cond


# Só as 12 condicionais: as universais rodam sempre e não são objeto da predição.
LENTES = _carregar_lentes()

# ÚNICA fonte das regras de ativação entregues ao estimador. Importada também pelo
# reestimar_lentes.py: já aconteceu duas vezes de eu corrigir num template e esquecer
# o outro, e a divergência faz o estimador jogar com regra diferente da Fase 2.
REGRA_ATIVACAO = """**A ativação é por SINAL DO PROJETO, e só.** Que outra lente pareça cobrir a mesma
classe de falha **não** é motivo para deixar uma de fora: não achar nada já é um
resultado válido, e decidir de antemão que duas lentes se sobrepõem é conclusão, não
premissa. Nunca marque `false` por redundância com outra lente — o motivo tem que ser
um sinal do projeto ("não há dependência externa", "não há superfície de usuário"),
nunca "já coberta pela lente X"."""

PACOTE = """\
# Tarefa — prever quais lentes de crítica um projeto vai acionar

Você vai ler o enunciado de um projeto de software e dizer **quais lentes de crítica
arquitetural aquele projeto aciona**, e por qual sinal do enunciado.

Não escreva código, não faça perguntas, não busque nada fora deste texto. Responda
só o que se pede, no formato do fim.

---

## O enunciado

> {descricao}

Porte previsto: 8 a 12 módulos, uma sessão de trabalho.

Isto é tudo o que existe sobre o projeto. Não há especificação adicional, e a
ausência de detalhe é proposital — o que se quer saber é o que **este enunciado**
já sinaliza.

---

## Como funcionam as lentes

Um processo de crítica arquitetural aplica lentes: cada uma faz uma pergunta central
a cada módulo do sistema e detecta uma classe de falha que as outras não detectam.

**Sete lentes são universais** — rodam em todo projeto, sempre, e não estão em
questão aqui: Premissas, Arquitetura, Implementabilidade, Rigor científico,
Segurança, Desempenho e Conformidade regulatória. **Não as inclua na resposta.**

**Doze são condicionais**: só entram quando algo no projeto as justifica. São essas
que você vai avaliar.

{regra}

> A tabela abaixo está em inglês porque é o **texto literal** que o processo de crítica
> usa. Traduzi-la já encurtou gatilhos numa versão anterior deste pacote, e o que se
> mediria depois seria a tradução, não o julgamento.

| lente | pergunta central | ativa quando |
|---|---|---|
{tabela}

---

## O que responder

Para **cada uma das 12** lentes condicionais:

1. `ativa`: `true` se o projeto aciona a lente, `false` se não.
2. `sinal`: uma frase curta dizendo **o que no enunciado** aciona (ou não aciona) a
   lente. Esta é a parte que importa — "ativa Resilience" sem dizer por quê não
   serve. Preencha o `sinal` também para as `false`.

E ainda:

3. `modulos_estimados`: em quantos módulos você acha que este projeto se decompõe.

Não omita lente nenhuma: as 12 têm que aparecer, com o nome exatamente como está na
tabela acima.

Sem preâmbulo, sem comentário, sem texto fora do bloco. Responda só isto:

```json
{{
  "projeto": "{task_id}",
  "modulos_estimados": 0,
  "lentes": [
    {{"lente": "Resilience", "ativa": true, "sinal": "..."}},
    {{"lente": "UI/UX", "ativa": false, "sinal": "..."}}
  ]
}}
```
"""


def gerar(task_id: str, salvar: bool) -> int:
    enunciado = RO3 / task_id / "ENUNCIADO.md"
    if not enunciado.exists():
        print(f"ERRO: {enunciado} não existe. Rode `preparar.py estrutura`.", file=sys.stderr)
        return 1

    # Só a linha do enunciado — o resto do arquivo é instrução interna e não vai junto.
    linhas = enunciado.read_text(encoding="utf-8").splitlines()
    descricao = next((l.strip() for l in linhas[1:] if l.strip() and not l.startswith("#")), "")
    if not descricao:
        print(f"ERRO: não achei a descrição em {enunciado}.", file=sys.stderr)
        return 1

    tabela = "\n".join(f"| {n} | {p} | {q} |" for n, p, q in LENTES)
    texto = PACOTE.format(task_id=task_id, descricao=descricao, tabela=tabela,
                          regra=REGRA_ATIVACAO)

    if salvar:
        SAIDA.mkdir(exist_ok=True)
        destino = SAIDA / f"{task_id}-predicao.md"
        destino.write_text(texto, encoding="utf-8")
        print(f"gravado em {destino}")
        print(f"Entregue este arquivo ao modelo preditor. Salve a resposta em "
              f"{SAIDA / f'{task_id}-predicao-resposta.json'}.")
    else:
        print(texto)
    return 0


def main(argv):
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    return gerar(argv[0], "--salvar" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
