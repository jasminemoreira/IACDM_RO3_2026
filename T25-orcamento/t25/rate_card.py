"""M-05 rate-card — precos com vigencia; recusa modelo sem preco vigente.

Decisao 52af7cb9: modelo ausente do rate card => requisicao NEGADA. Nunca preco
zero, nunca preco estimado: preco ausente que virasse zero tornaria o invariante
do teto verdadeiro por omissao de dados.

Achado MEC-03 (V(3)): recusa apenas os MODELOS vencidos, nao a inicializacao
inteira — nao converter problema de contabilidade em queda total programada.

Todos os valores em NANO-unidades monetarias por token (10^-9). Fonte de cada
numero no proprio rate_card.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

CATEGORIAS = (
    "entrada",
    "cache_leitura",
    "cache_escrita_5m",
    "cache_escrita_1h",
    "saida",
)


class ModeloSemPreco(Exception):
    """Nao ha preco vigente para (modelo, categoria) no instante dado."""


@dataclass(frozen=True)
class _Preco:
    nano_por_token: int
    vigente_desde: date
    vigente_ate: date | None
    fonte: str

    def vigente_em(self, dia: date) -> bool:
        if dia < self.vigente_desde:
            return False
        return self.vigente_ate is None or dia <= self.vigente_ate


class RateCard:
    def __init__(self, precos: dict[tuple[str, str], list[_Preco]]) -> None:
        self._precos = precos

    @classmethod
    def carregar(cls, caminho: str | Path) -> "RateCard":
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        precos: dict[tuple[str, str], list[_Preco]] = {}
        for linha in dados["precos"]:
            if linha["categoria"] not in CATEGORIAS:
                raise ValueError(f"categoria desconhecida: {linha['categoria']}")
            if not linha.get("fonte"):
                # Invariante I5 (specs/models): preco sem fonte nao entra.
                raise ValueError(f"preco sem fonte: {linha}")
            if int(linha["nano_por_token"]) < 0:
                raise ValueError(f"preco negativo: {linha}")
            chave = (linha["modelo"], linha["categoria"])
            precos.setdefault(chave, []).append(
                _Preco(
                    nano_por_token=int(linha["nano_por_token"]),
                    vigente_desde=date.fromisoformat(linha["vigente_desde"]),
                    vigente_ate=(
                        date.fromisoformat(linha["vigente_ate"])
                        if linha.get("vigente_ate")
                        else None
                    ),
                    fonte=linha["fonte"],
                )
            )
        return cls(precos)

    def preco(self, modelo: str, categoria: str, instante: datetime) -> int:
        """Nano-unidades por token. Levanta ModeloSemPreco se nao houver vigente."""
        dia = instante.date()
        for p in self._precos.get((modelo, categoria), ()):
            if p.vigente_em(dia):
                return p.nano_por_token
        raise ModeloSemPreco(
            f"sem preco vigente em {dia.isoformat()} para modelo={modelo} categoria={categoria}"
        )

    def preco_saida_mais_caro(self, instante: datetime) -> int:
        """Maior preco de saida vigente entre os modelos conhecidos.

        Usado pelo painel para responder "quantos tokens de saida ainda cabem no
        saldo?" — no pior caso de modelo. Derivado do rate card, sem parametro
        inventado.
        """
        precos = []
        for modelo in self.modelos_conhecidos():
            try:
                precos.append(self.preco(modelo, "saida", instante))
            except ModeloSemPreco:
                continue
        return max(precos) if precos else 0

    def modelos_conhecidos(self) -> set[str]:
        return {modelo for (modelo, _cat) in self._precos}

    def modelos_vencidos(self, instante: datetime) -> list[str]:
        """Modelos conhecidos que NAO tem preco vigente completo no instante.

        Usado por /health: o gateway continua subindo, mas expoe quais modelos
        deixarao de ser atendidos.
        """
        vencidos = []
        for modelo in sorted(self.modelos_conhecidos()):
            for categoria in CATEGORIAS:
                try:
                    self.preco(modelo, categoria, instante)
                except ModeloSemPreco:
                    vencidos.append(modelo)
                    break
        return vencidos
