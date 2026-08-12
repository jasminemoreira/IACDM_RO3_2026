"""M-10 reporter — relatórios de importação e conciliação.

ARC-04 — recebe DADOS, não o banco. A versão anterior lia o repositório
diretamente, o que punha a sub-rotulação de órfãos atrás de I/O e tornava o
módulo intestável sem banco.

SEC-01 — saneamento de prefixo de fórmula na exportação CSV. A descrição vem de
arquivo externo não confiável (baixado ou recebido por e-mail) e o alvo é a
máquina do operador financeiro: um campo começando com `=`, `+`, `-` ou `@` é
executado ao abrir no Excel.

REG-03 / CTL-02 / MEC-05 — cabeçalho com versão do software, parâmetros efetivos
e versão dos perfis. Sem isso o relatório não é reexecutável numa auditoria, e
mudar um limiar reclassifica o histórico em silêncio.

SCI-04 — a sub-rotulação de órfão usa a janela POR INSTRUMENTO de
specs/technical/rubrica-score.md §2, com fonte citada. Órfão não é sinônimo de
erro: 40 a 60% dos não-casados em conciliação real são diferença de tempo, e
misturá-los com anomalias afoga o analista em ruído.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Sequence

from t26.domain.model import Estado5
from t26.matching.matcher import janela_do_instrumento

VERSAO_SOFTWARE = "1.0.0"

#: SEC-01 — caracteres que iniciam fórmula em Excel/LibreOffice.
_PREFIXOS_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def sanear_csv(valor: str) -> str:
    """Prefixa com aspa simples campos que o Excel interpretaria como fórmula."""
    if valor and valor[0] in _PREFIXOS_FORMULA:
        return "'" + valor
    return valor


@dataclass
class ItemRelatorio:
    chave: str
    estado: Estado5
    valor: Decimal
    data: date
    descricao: str
    instrumento: str = "desconhecido"
    detalhe: str = ""


@dataclass
class Relatorio:
    titulo: str
    gerado_em: str
    parametros: dict
    versoes: dict
    contagens: dict[str, int] = field(default_factory=dict)
    subrotulos: dict[str, int] = field(default_factory=dict)
    itens: list[ItemRelatorio] = field(default_factory=list)
    total: int = 0

    def soma_bate(self) -> bool:
        """VAL-3 — a soma das contagens por estado deve dar o total de itens."""
        return sum(self.contagens.values()) == self.total


def classificar_orfao(item: ItemRelatorio, referencia: date) -> str:
    """Órfão ESPERADO (dentro da janela de compensação) ou ANÔMALO (fora dela).

    Não é um sexto estado: é sub-rotulação de relatório. Os 5 estados terminais e
    o critério VAL-3 permanecem intactos.
    """
    janela = janela_do_instrumento(item.instrumento)
    idade = (referencia - item.data).days
    if idade <= janela:
        return "esperado"
    return "anomalo"


def resumo(
    itens: Sequence[ItemRelatorio],
    parametros: dict,
    versoes: dict,
    referencia: date,
    titulo: str = "Conciliação",
    gerado_em: str = "",
) -> Relatorio:
    rel = Relatorio(
        titulo=titulo,
        gerado_em=gerado_em,
        parametros=dict(parametros),
        versoes=dict(versoes),
        total=len(itens),
    )
    for item in itens:
        rel.contagens[item.estado.value] = rel.contagens.get(item.estado.value, 0) + 1
        if item.estado in (Estado5.ORFAO_NO_EXTRATO, Estado5.ORFAO_NO_LIVRO):
            sub = classificar_orfao(item, referencia)
            chave = f"{item.estado.value}:{sub}"
            rel.subrotulos[chave] = rel.subrotulos.get(chave, 0) + 1
            if item.instrumento == "desconhecido":
                rel.subrotulos["instrumento-nao-identificado"] = (
                    rel.subrotulos.get("instrumento-nao-identificado", 0) + 1
                )
    rel.itens = list(itens)
    return rel


def render(relatorio: Relatorio, formato: str = "texto") -> str:
    """UX-04 — os formatos suportados são exatamente estes três, enumerados."""
    if formato == "texto":
        return _render_texto(relatorio)
    if formato == "csv":
        return _render_csv(relatorio)
    if formato == "json":
        return _render_json(relatorio)
    raise ValueError(f"formato desconhecido: {formato!r}. Use texto, csv ou json.")


def _cabecalho(rel: Relatorio) -> list[str]:
    params = ", ".join(f"{k}={v}" for k, v in sorted(rel.parametros.items()))
    versoes = ", ".join(f"{k}={v}" for k, v in sorted(rel.versoes.items()))
    return [
        f"{rel.titulo} — T26 v{VERSAO_SOFTWARE}",
        f"gerado em: {rel.gerado_em}",
        f"parâmetros efetivos: {params}",
        f"versões: {versoes}",
    ]


def _render_texto(rel: Relatorio) -> str:
    linhas = _cabecalho(rel)
    linhas.append("")
    linhas.append(f"{'estado':26s} {'itens':>7s}")
    linhas.append("-" * 34)
    for estado in Estado5:
        n = rel.contagens.get(estado.value, 0)
        if n:
            linhas.append(f"{estado.value:26s} {n:7d}")
    linhas.append("-" * 34)
    linhas.append(f"{'TOTAL':26s} {rel.total:7d}")
    linhas.append(
        f"soma por estado confere com o total (VAL-3): {'sim' if rel.soma_bate() else 'NAO'}"
    )
    if rel.subrotulos:
        linhas.append("")
        linhas.append("órfãos por natureza:")
        for chave, n in sorted(rel.subrotulos.items()):
            linhas.append(f"  {chave:44s} {n:6d}")
    return "\n".join(linhas)


def _render_csv(rel: Relatorio) -> str:
    linhas = ["# " + l for l in _cabecalho(rel)]
    linhas.append("chave;estado;valor;data;instrumento;descricao;detalhe")
    for item in rel.itens:
        campos = [
            item.chave,
            item.estado.value,
            str(item.valor),
            item.data.isoformat(),
            item.instrumento,
            item.descricao,
            item.detalhe,
        ]
        linhas.append(";".join(sanear_csv(c).replace(";", ",") for c in campos))
    return "\n".join(linhas)


def _render_json(rel: Relatorio) -> str:
    return json.dumps(
        {
            "titulo": rel.titulo,
            "software": VERSAO_SOFTWARE,
            "gerado_em": rel.gerado_em,
            "parametros": rel.parametros,
            "versoes": rel.versoes,
            "contagens": rel.contagens,
            "subrotulos": rel.subrotulos,
            "total": rel.total,
            "val3_soma_bate": rel.soma_bate(),
            "itens": [
                {
                    "chave": i.chave,
                    "estado": i.estado.value,
                    "valor": str(i.valor),
                    "data": i.data.isoformat(),
                    "instrumento": i.instrumento,
                    "descricao": i.descricao,
                    "detalhe": i.detalhe,
                }
                for i in rel.itens
            ],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
