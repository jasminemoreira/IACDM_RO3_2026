"""M-08 formatters — Strategy de saida. UNICO modulo do sistema que produz string.

ARC-02 — a renderizacao tem um dono so. Nenhum outro modulo formata mensagem.
UX-01 — a saida de impacto e AGRUPADA POR DONO: a pergunta do produto e "quem eu aviso".
UX-03 — impacto vazio imprime frase EXPLICITA; silencio seria indistinguivel de falha.
UX-06 / GAME-01 — a ressalva de escopo aparece UMA vez: rodape no modo texto, campo
`escopo: "declarado"` no modo JSON. O resultado e limite INFERIOR do conjunto real de
afetados, porque a completude do grafo depende da diligencia de quem declara — e isso e
propriedade social, nao tecnica. Declarar a limitacao e a resposta honesta possivel.
UX-04 — idioma: dominio e interface em portugues; flags seguem o ecossistema (`--json`).
"""

from __future__ import annotations

import json
from typing import Protocol, Sequence

from .query_service import ImpactResult, ProvenanceResult
from .validation import Violation

RESSALVA = (
    "Escopo: o resultado cobre apenas dependencias DECLARADAS no catalogo. "
    "E um limite inferior do conjunto real de afetados."
)


class Formatter(Protocol):
    def format_impact(self, resultado: ImpactResult) -> str: ...
    def format_provenance(self, resultado: ProvenanceResult) -> str: ...
    def format_violations(self, violacoes: Sequence[Violation]) -> str: ...


class TextFormatter:
    def format_impact(self, resultado: ImpactResult) -> str:
        if resultado.vazio:
            return (
                f"'{resultado.consultado}' nao alimenta nenhum dataset declarado: "
                f"nenhum impacto a jusante, ninguem a avisar.\n\n{RESSALVA}"
            )
        linhas = [
            f"Mexer em '{resultado.consultado}' afeta {len(resultado.afetados)} "
            f"dataset(s) e exige avisar {len(resultado.responsaveis)} responsavel(is):",
            "",
        ]
        for dono, datasets in resultado.responsaveis:
            linhas.append(f"  {dono.nome} <{dono.contato}>")
            for id_ in sorted(str(d) for d in datasets):
                linhas.append(f"      - {id_}")
        linhas.append("")
        linhas.append(RESSALVA)
        return "\n".join(linhas)

    def format_provenance(self, resultado: ProvenanceResult) -> str:
        if resultado.vazio:
            return (
                f"'{resultado.consultado}' nao e alimentado por nenhum dataset "
                f"declarado: e uma origem.\n\n{RESSALVA}"
            )
        dominios = ", ".join(sorted(resultado.dominios))
        linhas = [
            f"'{resultado.consultado}' vem de {len(resultado.origens)} dataset(s), "
            f"atravessando os dominios: {dominios}",
            "",
        ]
        for id_ in sorted(str(o) for o in resultado.origens):
            linhas.append(f"  - {id_}")
        linhas.append("")
        linhas.append(RESSALVA)
        return "\n".join(linhas)

    def format_violations(self, violacoes: Sequence[Violation]) -> str:
        cabecalho = f"Catalogo invalido: {len(violacoes)} violacao(oes) encontrada(s)."
        corpo = [f"  - {v}" for v in violacoes]
        return "\n".join([cabecalho, ""] + corpo)


class JsonFormatter:
    def format_impact(self, resultado: ImpactResult) -> str:
        payload = {
            "consultado": str(resultado.consultado),
            "afetados": sorted(str(d) for d in resultado.afetados),
            "responsaveis": [
                {
                    "nome": dono.nome,
                    "contato": dono.contato,
                    "datasets": sorted(str(d) for d in datasets),
                }
                for dono, datasets in resultado.responsaveis
            ],
            "escopo": "declarado",
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def format_provenance(self, resultado: ProvenanceResult) -> str:
        payload = {
            "consultado": str(resultado.consultado),
            "origens": sorted(str(o) for o in resultado.origens),
            "dominios": sorted(resultado.dominios),
            "escopo": "declarado",
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def format_violations(self, violacoes: Sequence[Violation]) -> str:
        payload = {
            "valido": False,
            "violacoes": [
                {
                    "arquivo": v.arquivo,
                    "linha": v.linha,
                    "dominio": v.dominio,
                    "mensagem": v.mensagem,
                }
                for v in violacoes
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


def escolher(json_mode: bool) -> Formatter:
    return JsonFormatter() if json_mode else TextFormatter()
