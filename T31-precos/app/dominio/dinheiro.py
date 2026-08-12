"""M-01 `dinheiro` — valor monetário decimal exato.

Invariante I-5: ponto flutuante binário é PROIBIDO no caminho do preço.
O valor vive como inteiro de centavos; a aritmética passa por Decimal com
arredondamento half-up de 2 casas, aplicado só no resultado final (A-13).

Contrato restaurado em V(5)/Y5: `de_texto` devolve `Dinheiro | ErroFormato`.
A detecção de AMBIGUIDADE de separador é responsabilidade de `importador-csv`,
que examina o texto bruto linha a linha e tem relatório onde escrever — este
módulo não tem canal para "sucesso com ressalva" e não deve ganhar um (MEC-06).

Regra determinística de separador (V(3)/W6, caso-armadilha N-06):
  - havendo vírgula, ela é o separador decimal e o ponto é milhar;
  - não havendo vírgula, o ponto é decimal APENAS se seguido de exatamente
    1 ou 2 dígitos; caso contrário é separador de milhar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

CENTAVOS = Decimal("0.01")

# MEC-02: normalizar por PRINCÍPIO — remover tudo que não seja dígito ou sinal
# decimal. Os codepoints vão em ESCAPE de propósito: escritos como literais, o
# espaço não-quebrável colapsa em espaço comum ao gravar o arquivo, e a
# tolerância passaria a existir apenas no comentário.
_ESPACOS = (" ", " ", " ", " ", " ", "\t")
_LIXO = str.maketrans({c: "" for c in (*_ESPACOS, "R", "$")})
_MENOS_UNICODE = ("−", "–", "—")  # menos, en dash, em dash
_NUMERO = re.compile(r"^\d+(\.\d{1,2})?$")
_AMBIGUO = re.compile(r"\.\d{3}(?!\d)")


@dataclass(frozen=True, slots=True)
class ErroFormato:
    """Falha de parsing, com o motivo que vai literal para o relatório."""

    motivo: str


@dataclass(frozen=True, slots=True, order=True)
class Dinheiro:
    centavos: int

    def __post_init__(self) -> None:
        if self.centavos < 0:
            raise ValueError("Dinheiro não pode ser negativo")

    # -- construção ------------------------------------------------------

    @staticmethod
    def de_texto(s: str | None) -> "Dinheiro | ErroFormato":
        if s is None or not s.strip():
            return ErroFormato("preço ausente")

        original = s.strip()
        t = original
        for uni in _MENOS_UNICODE:
            t = t.replace(uni, "-")
        t = t.translate(_LIXO)

        if not t:
            return ErroFormato("preço ausente")
        if "%" in t:
            return ErroFormato(f"valor não-monetário em campo de preço: '{original}'")

        negativo = t.startswith("-")
        if negativo:
            t = t[1:]

        t = _aplicar_regra_de_separador(t)

        if not _NUMERO.match(t):
            return ErroFormato(f"formato de preço inválido: '{original}'")
        if negativo:
            return ErroFormato(f"preço negativo: {original}")

        return Dinheiro.de_decimal(Decimal(t))

    @staticmethod
    def de_decimal(d: Decimal) -> "Dinheiro":
        return Dinheiro(int(d.quantize(CENTAVOS, rounding=ROUND_HALF_UP) * 100))

    @staticmethod
    def zero() -> "Dinheiro":
        return Dinheiro(0)

    # -- aritmética ------------------------------------------------------

    def multiplicar(self, quantidade: int) -> "Dinheiro":
        """Modelo VOLUME (A-10): o unitário vale para toda a quantidade."""
        return Dinheiro(self.centavos * quantidade)

    def aplicar_pct(self, pct: Decimal) -> "Dinheiro":
        """`pct` é o percentual RESULTANTE, não o desconto.

        Um desconto de 10% chama `aplicar_pct(Decimal(90))`. Arredonda
        half-up a 2 casas uma única vez (A-13).
        """
        return Dinheiro.de_decimal(self.como_decimal() * pct / Decimal(100))

    # -- leitura ---------------------------------------------------------

    def como_decimal(self) -> Decimal:
        return (Decimal(self.centavos) / Decimal(100)).quantize(CENTAVOS)

    def iso(self) -> str:
        """Forma NORMATIVA do contrato (V(3)/W10): decimal em string."""
        return f"{self.como_decimal():.2f}"

    def __str__(self) -> str:
        """Forma de APRESENTAÇÃO, derivada — nunca normativa."""
        inteiro, _, frac = self.iso().partition(".")
        milhar = f"{int(inteiro):,}".replace(",", ".")
        return f"R$ {milhar},{frac}"


def _aplicar_regra_de_separador(t: str) -> str:
    """Regra determinística de V(3)/W6 — ver caso-armadilha N-06."""
    if "," in t:
        # Vírgula é o decimal; todo ponto é milhar.
        return t.replace(".", "").replace(",", ".")
    if "." in t:
        casas = len(t) - t.rfind(".") - 1
        if casas in (1, 2):
            # Último ponto é decimal; os anteriores são milhar.
            cabeca, _, cauda = t.rpartition(".")
            return cabeca.replace(".", "") + "." + cauda
        # `1.299` -> 1299 (milhar). Ambiguidade real, resolvida em favor de
        # pt-BR e SINALIZADA por `importador-csv` (V(5)/Y5).
        return t.replace(".", "")
    return t


def texto_tem_separador_ambiguo(s: str) -> bool:
    """Ponto seguido de exatamente 3 dígitos, sem vírgula no valor.

    Exposto para `importador-csv` emitir o aviso de ambiguidade (V(5)/Y5) — é
    uma consulta sobre o TEXTO, não um segundo canal de retorno do parsing.
    """
    t = (s or "").strip().translate(_LIXO)
    return "," not in t and bool(_AMBIGUO.search(t))
