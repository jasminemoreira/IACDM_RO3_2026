"""M-02 catalog — agregado do Domain Model.

Responsabilidade unica: guardar os dominios e RESOLVER O DONO EFETIVO de um dataset.

LING-02: dono DECLARADO e dono EFETIVO sao coisas distintas e recebem nomes distintos.
  - `Domain.dono`        -> declarado no dominio
  - `effective_owner(id)` -> o que vale para aquele dataset, apos sobrescrita

ASM-03: a sobrescrita e TOTAL. Um dataset com `dono` proprio substitui nome e contato;
nao existe sobrescrita parcial (validada em yaml_loader).
"""

from __future__ import annotations

from .model import Dataset, DatasetId, Domain, Owner


class Catalog:
    """Colecao imutavel de dominios, indexada por identidade de dataset."""

    def __init__(self, dominios: tuple[Domain, ...]) -> None:
        self._dominios = dominios
        self._por_id: dict[DatasetId, Dataset] = {}
        self._dono_do_dominio: dict[str, Owner] = {}
        for dominio in dominios:
            self._dono_do_dominio[dominio.nome] = dominio.dono
            for ds in dominio.datasets:
                self._por_id[ds.id] = ds

    def has(self, id_: DatasetId) -> bool:
        return id_ in self._por_id

    def dataset(self, id_: DatasetId) -> Dataset:
        return self._por_id[id_]

    def effective_owner(self, id_: DatasetId) -> Owner:
        """Dono que vale para este dataset: o proprio, se sobrescrito; senao o do dominio.

        Levanta KeyError para dataset nao declarado — quem consulta deve ter checado
        `has()` antes. A traducao para DatasetNotFound e de query_service.
        """
        ds = self._por_id[id_]
        if ds.dono is not None:
            return ds.dono
        return self._dono_do_dominio[id_.dominio]

    def domains(self) -> tuple[Domain, ...]:
        return self._dominios

    def datasets(self) -> tuple[Dataset, ...]:
        return tuple(self._por_id.values())

    def ids(self) -> tuple[DatasetId, ...]:
        return tuple(self._por_id.keys())
