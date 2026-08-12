"""M-09 cli — composition root.

I/O de diretorio, wiring das dependencias, subcomandos e codigos de saida.

Fluxo de carregamento da V(3), com dono unico por passo:
  ler diretorio -> yaml_loader.load_files -> (aborta se houver violacao, LING-05)
  -> catalog_mapper.to_catalog -> lineage_graph.build -> validation.certify
  -> LoadedCatalog -> query_service

ARC-04 / IMPL-06 — nao ha caminho alternativo: query_service exige um LoadedCatalog, e
LoadedCatalog e inconstruivel enquanto houver violacao. Burlar a validacao nao e questao
de disciplina aqui, e impossivel.
UX-04 — subcomandos e mensagens em portugues; flags seguem a convencao do ecossistema.
RES-02 — diretorio inexistente ou ilegivel produz erro nomeado, nao stack trace.

Codigos de saida: 0 sucesso | 1 catalogo invalido | 2 erro de uso.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import catalog_mapper, formatters, lineage_graph, validation, yaml_loader
from .model import NomeInvalido
from .query_service import DatasetNotFound, QueryService
from .validation import CatalogInvalid, LoadedCatalog

OK = 0
CATALOGO_INVALIDO = 1
ERRO_DE_USO = 2


def carregar(diretorio: Path) -> LoadedCatalog:
    """Unico caminho de entrada de dados do sistema."""
    bruto = yaml_loader.load_files(diretorio)

    # LING-05: havendo violacao de forma, os docs parciais NAO sao usados.
    if not bruto.ok:
        raise CatalogInvalid(validation.ordenar(bruto.violacoes))

    catalogo, arestas, violacoes, arquivo_por_dominio = catalog_mapper.to_catalog(bruto.docs)
    grafo = lineage_graph.LineageGraph.build(catalogo.ids(), arestas)
    return validation.certify(catalogo, grafo, arestas, arquivo_por_dominio, violacoes)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="t24",
        description=(
            "Catalogo de dados com donos declarados por dominio e linhagem entre eles."
        ),
    )
    p.add_argument(
        "--catalogo",
        type=Path,
        default=Path("catalog"),
        metavar="DIR",
        help="diretorio com os arquivos YAML de dominio (padrao: ./catalog)",
    )
    p.add_argument("--json", action="store_true", help="saida em JSON em vez de texto")

    sub = p.add_subparsers(dest="comando", required=True)

    def _com_json(sp: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Aceita --json TAMBEM depois do subcomando.

        O argparse so reconhece flags do parser principal ANTES do subcomando, e
        `t24 impacto X --json` e a ordem que o usuario escreve naturalmente.
        `SUPPRESS` faz o subparser nao sobrescrever o valor quando a flag veio antes.
        """
        sp.add_argument(
            "--json",
            action="store_true",
            default=argparse.SUPPRESS,
            help="saida em JSON em vez de texto",
        )
        return sp

    _com_json(sub.add_parser("validar", help="valida o catalogo e reporta todas as violacoes"))

    imp = _com_json(
        sub.add_parser("impacto", help="quem quebra e quem avisar se este dataset mudar")
    )
    imp.add_argument("dataset", help="identidade no formato dominio.dataset")

    proc = _com_json(sub.add_parser("procedencia", help="de onde vem este dataset"))
    proc.add_argument("dataset", help="identidade no formato dominio.dataset")

    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    fmt = formatters.escolher(args.json)

    try:
        carregado = carregar(args.catalogo)
    except yaml_loader.DiretorioInvalido as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return ERRO_DE_USO
    except CatalogInvalid as erro:
        print(fmt.format_violations(erro.violacoes), file=sys.stderr)
        return CATALOGO_INVALIDO

    if args.comando == "validar":
        catalogo = carregado.catalogo
        total_datasets = len(catalogo.ids())
        total_arestas = len(carregado.grafo.arestas())
        if args.json:
            import json

            print(
                json.dumps(
                    {
                        "valido": True,
                        "dominios": len(catalogo.domains()),
                        "datasets": total_datasets,
                        "arestas": total_arestas,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(
                f"Catalogo valido: {len(catalogo.domains())} dominio(s), "
                f"{total_datasets} dataset(s), {total_arestas} aresta(s) de linhagem."
            )
        return OK

    from .model import DatasetId

    try:
        alvo = DatasetId.parse(args.dataset)
    except NomeInvalido as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return ERRO_DE_USO

    servico = QueryService(carregado)
    try:
        if args.comando == "impacto":
            print(fmt.format_impact(servico.impact(alvo)))
        else:
            print(fmt.format_provenance(servico.provenance(alvo)))
    except DatasetNotFound as erro:
        # UX-02: "nao existe" e distinto de "existe e nao afeta ninguem".
        print(f"erro: {erro}", file=sys.stderr)
        return ERRO_DE_USO

    return OK


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    run()
