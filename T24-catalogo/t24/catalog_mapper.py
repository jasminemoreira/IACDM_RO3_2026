"""M-07 catalog_mapper — dicionarios crus para entidades, e a INVERSAO da aresta.

Duas responsabilidades, apenas (ARC-06, corrigido na V(3)): mapear e inverter. Nao
constroi o grafo (isso e de lineage_graph), nao valida invariantes de catalogo inteiro e
nao certifica (isso e de validation).

LING-01 — A INVERSAO MORA SO AQUI. No YAML declara-se `alimentado_por`, que aponta do
consumidor para o produtor; a aresta do grafo vai na direcao do FLUXO, do produtor para o
consumidor. Deste modulo para dentro do sistema so existe a direcao do fluxo, e por isso
duas implementacoes do contrato nao podem divergir sobre ela.

Verifica aqui INV-1 (unicidade de dominio entre arquivos e de dataset dentro do dominio),
porque duplicatas so sao visiveis enquanto os documentos crus ainda estao separados.
"""

from __future__ import annotations

from typing import Sequence

from .catalog import Catalog
from .model import (
    Dataset,
    DatasetId,
    Domain,
    LineageEdge,
    NomeInvalido,
    Owner,
    RawDomainDoc,
)
from .validation import Violation


def _owner(bruto: dict) -> Owner:
    return Owner(nome=bruto["nome"].strip(), contato=bruto["contato"].strip())


def to_catalog(
    docs: Sequence[RawDomainDoc],
) -> tuple[Catalog, list[LineageEdge], list[Violation], dict[str, str]]:
    """Mapeia os documentos e produz o catalogo, as arestas e as violacoes de mapeamento.

    Devolve tambem `arquivo_por_dominio`, para que as violacoes de `validation` possam
    apontar o arquivo certo (RES-04 exige arquivo em toda Violation).
    """
    violacoes: list[Violation] = []
    arquivo_por_dominio: dict[str, str] = {}
    dominios: list[Domain] = []
    arestas: list[LineageEdge] = []
    declaracoes: list[tuple[str, str, str, list[str]]] = []  # arquivo, dominio, dataset, alimentado_por

    for doc in docs:
        arquivo = doc.arquivo
        bruto = doc.conteudo
        nome_dominio_bruto = bruto["dominio"].strip()

        # ASM-01 / A10: nome com ponto e recusado na construcao, nao mais tarde.
        try:
            DatasetId(nome_dominio_bruto, "_sonda_")
        except NomeInvalido as erro:
            violacoes.append(Violation(arquivo, str(erro), nome_dominio_bruto))
            continue
        nome_dominio = nome_dominio_bruto

        # INV-1: nome de dominio unico entre arquivos.
        if nome_dominio in arquivo_por_dominio:
            violacoes.append(
                Violation(
                    arquivo,
                    f"dominio '{nome_dominio}' ja declarado em "
                    f"'{arquivo_por_dominio[nome_dominio]}'",
                    nome_dominio,
                )
            )
            continue
        arquivo_por_dominio[nome_dominio] = arquivo

        datasets: list[Dataset] = []
        vistos: set[str] = set()
        for indice, ds_bruto in enumerate(bruto["datasets"]):
            nome_ds = ds_bruto["nome"].strip()
            try:
                id_ = DatasetId(nome_dominio, nome_ds)
            except NomeInvalido as erro:
                violacoes.append(
                    Violation(arquivo, f"datasets[{indice}]: {erro}", nome_dominio)
                )
                continue

            # INV-1: nome de dataset unico dentro do dominio.
            if nome_ds in vistos:
                violacoes.append(
                    Violation(
                        arquivo,
                        f"datasets[{indice}]: dataset '{nome_ds}' declarado mais de uma "
                        f"vez no dominio '{nome_dominio}'",
                        nome_dominio,
                    )
                )
                continue
            vistos.add(nome_ds)

            datasets.append(
                Dataset(
                    id=id_,
                    descricao=ds_bruto.get("descricao"),
                    dono=_owner(ds_bruto["dono"]) if "dono" in ds_bruto else None,
                )
            )
            declaracoes.append(
                (arquivo, nome_dominio, nome_ds, list(ds_bruto.get("alimentado_por") or []))
            )

        dominios.append(
            Domain(nome=nome_dominio, dono=_owner(bruto["dono"]), datasets=tuple(datasets))
        )

    # ---------------------------------------------------------------- inversao da aresta
    for arquivo, nome_dominio, nome_ds, produtores in declaracoes:
        consumidor = DatasetId(nome_dominio, nome_ds)
        for texto in produtores:
            try:
                produtor = DatasetId.parse(texto)
            except NomeInvalido as erro:
                violacoes.append(
                    Violation(
                        arquivo,
                        f"'{consumidor}' declara alimentado_por '{texto}': {erro}",
                        nome_dominio,
                    )
                )
                continue
            # Declara-se "sou alimentado por X"; a aresta e X -> eu.
            arestas.append(LineageEdge(origem=produtor, destino=consumidor))

    return Catalog(tuple(dominios)), arestas, violacoes, arquivo_por_dominio
