"""M-01 model — entidades e value objects puros.

Nao conhece arquivo, YAML nem terminal. Nao depende de nenhum outro modulo do projeto.

Decisoes da Fase 2/3 materializadas aqui:
  ASM-01 / A10 : nomes de dominio e dataset REJEITAM ponto na construcao. A identidade
                 ambigua deixa de ser construivel, em vez de depender de checagem
                 espalhada.
  IMPL-05      : Owner e congelado e hasheavel, para que a deduplicacao de donos exigida
                 pelo criterio de acerto seja possivel.
  GOV-03       : a identidade de Owner e o contato normalizado, e nao o par nome+contato,
                 para que a mesma pessoa grafada de dois modos nao vire dois donos.
  GOV-04       : o caso inverso (duas pessoas, mesmo contato) NAO e resolvido aqui — e
                 detectado por `validation`, que exige desambiguacao em vez de colapsar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

SEPARADOR = "."


class NomeInvalido(ValueError):
    """Nome de dominio ou dataset que viola a regra de formacao (A10)."""


def _nome_valido(valor: Any, papel: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise NomeInvalido(f"{papel} ausente ou vazio")
    limpo = valor.strip()
    if SEPARADOR in limpo:
        raise NomeInvalido(
            f"{papel} '{limpo}' contem '{SEPARADOR}'; o ponto e o separador da "
            f"identidade dominio.dataset e nao pode aparecer no nome"
        )
    return limpo


@dataclass(frozen=True)
class DatasetId:
    """Identidade de um dataset: `dominio.nome`. A chave carrega o dominio."""

    dominio: str
    nome: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "dominio", _nome_valido(self.dominio, "nome de dominio"))
        object.__setattr__(self, "nome", _nome_valido(self.nome, "nome de dataset"))

    @staticmethod
    def parse(texto: Any) -> "DatasetId":
        """Le 'dominio.dataset'. Exige EXATAMENTE um separador.

        'vendas.br.pedidos' e recusado em vez de lido como dominio 'vendas' e dataset
        'br.pedidos' — que resolveria o dono errado em silencio (ASM-01).
        """
        if not isinstance(texto, str) or not texto.strip():
            raise NomeInvalido("identidade de dataset ausente ou vazia")
        partes = texto.strip().split(SEPARADOR)
        if len(partes) != 2:
            raise NomeInvalido(
                f"identidade '{texto.strip()}' invalida: esperado exatamente "
                f"'dominio{SEPARADOR}dataset'"
            )
        return DatasetId(partes[0], partes[1])

    def __str__(self) -> str:
        return f"{self.dominio}{SEPARADOR}{self.nome}"


@dataclass(frozen=True, eq=False)
class Owner:
    """Responsavel declarado. A identidade e o contato normalizado (GOV-03)."""

    nome: str
    contato: str

    @property
    def chave(self) -> str:
        return self.contato.strip().lower()

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, Owner) and self.chave == outro.chave

    def __hash__(self) -> int:
        return hash(self.chave)

    def __str__(self) -> str:
        return f"{self.nome} <{self.contato}>"


@dataclass(frozen=True)
class Dataset:
    """Unidade catalogada. `dono` presente SOBRESCREVE o dono do dominio, por inteiro."""

    id: DatasetId
    descricao: Optional[str] = None
    dono: Optional[Owner] = None


@dataclass(frozen=True)
class Domain:
    """Dominio de negocio. Unidade de propriedade (Data Mesh, principio 1)."""

    nome: str
    dono: Owner
    datasets: tuple[Dataset, ...] = ()


@dataclass(frozen=True)
class LineageEdge:
    """Aresta na direcao do FLUXO do dado: origem alimenta destino.

    A declaracao no YAML e `alimentado_por`, que aponta na direcao OPOSTA. A inversao e
    responsabilidade exclusiva de catalog_mapper (LING-01); deste tipo para dentro do
    sistema so existe a direcao do fluxo.
    """

    origem: DatasetId
    destino: DatasetId


@dataclass(frozen=True)
class RawDomainDoc:
    """Documento YAML de um dominio, ainda cru. Produzido por yaml_loader."""

    arquivo: str
    conteudo: dict
