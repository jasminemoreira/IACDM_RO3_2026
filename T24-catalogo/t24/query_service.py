"""M-05 query_service — as duas consultas do produto.

Dona de ImpactResult, ProvenanceResult e DatasetNotFound (realocacao ARC-07: os tipos
moram com quem os produz).

`impact` e a funcao sobre a qual o CRITERIO DE ACERTO do projeto e medido. Por ser pura e
receber e devolver apenas tipos de dominio, a asserção de igualdade de conjuntos e feita
diretamente sobre ela, sem atravessar arquivo nem stdout.

UX-01 — `ImpactResult` ja carrega os afetados AGRUPADOS POR DONO. A promessa do produto e
"quem eu preciso avisar"; uma lista plana de datasets entrega o dado e nao a resposta.
UX-02 — dataset inexistente levanta DatasetNotFound; dataset sem impacto devolve resultado
VAZIO. Sao situacoes distintas e nao podem produzir a mesma saida.
A6 — o proprio dataset consultado nunca aparece no resultado.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import DatasetId, Owner
from .validation import LoadedCatalog


class DatasetNotFound(Exception):
    def __init__(self, id_: DatasetId) -> None:
        self.id = id_
        super().__init__(f"dataset '{id_}' nao esta declarado no catalogo")


@dataclass(frozen=True)
class ImpactResult:
    """Resposta de 'se eu mexer em X, o que quebra e quem eu aviso?'."""

    consultado: DatasetId
    afetados: frozenset[DatasetId]
    responsaveis: tuple[tuple[Owner, frozenset[DatasetId]], ...]

    @property
    def donos(self) -> frozenset[Owner]:
        return frozenset(dono for dono, _ in self.responsaveis)

    @property
    def vazio(self) -> bool:
        return not self.afetados


@dataclass(frozen=True)
class ProvenanceResult:
    """Resposta de 'de onde vem este dado?'."""

    consultado: DatasetId
    origens: frozenset[DatasetId]
    dominios: frozenset[str]

    @property
    def vazio(self) -> bool:
        return not self.origens


class QueryService:
    def __init__(self, carregado: LoadedCatalog) -> None:
        self._catalogo = carregado.catalogo
        self._grafo = carregado.grafo

    def _exigir(self, id_: DatasetId) -> None:
        if not self._catalogo.has(id_):
            raise DatasetNotFound(id_)

    def impact(self, id_: DatasetId) -> ImpactResult:
        self._exigir(id_)
        afetados = self._grafo.downstream(id_)

        por_dono: dict[Owner, set[DatasetId]] = {}
        for afetado in afetados:
            dono = self._catalogo.effective_owner(afetado)
            por_dono.setdefault(dono, set()).add(afetado)

        # Ordem estavel na apresentacao; a igualdade medida pelo criterio de acerto e de
        # CONJUNTO, mas saida nao-deterministica atrapalharia teste e leitura humana.
        agrupado = tuple(
            (dono, frozenset(datasets))
            for dono, datasets in sorted(por_dono.items(), key=lambda par: par[0].nome)
        )
        return ImpactResult(
            consultado=id_,
            afetados=frozenset(afetados),
            responsaveis=agrupado,
        )

    def provenance(self, id_: DatasetId) -> ProvenanceResult:
        self._exigir(id_)
        origens = self._grafo.upstream(id_)
        return ProvenanceResult(
            consultado=id_,
            origens=frozenset(origens),
            dominios=frozenset(o.dominio for o in origens),
        )
