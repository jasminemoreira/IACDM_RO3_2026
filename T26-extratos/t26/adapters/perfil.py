"""Gramática do PerfilCSV — especificação declarada (LIN-01, LIN-08, IMP-03).

Este arquivo É a fonte única da semântica do perfil. O `csv-adapter` (M-03) e o
`fixture-generator` (M-12) leem daqui: o gerador não reimplementa a semântica por
conta própria, o que era o defeito ARC-08 (deriva entre gerador e parser), nem
depende do adapter, o que era o defeito ARC-03 (o teste cancelando o próprio erro).

LIN-01 — a ambiguidade que motivou fechar esta gramática: "convenção de sinal"
admitia duas leituras corretas e opostas. Aqui `sinal` é um enum fechado de três
valores com semântica declarada, e o caso `colunas_debito_credito` tem os dois
casos degenerados especificados (LIN-08).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ConvencaoSinal(Enum):
    """Como a fonte expressa débito e crédito. Enum FECHADO (LIN-01)."""

    #: Uma coluna de valor já assinada: débito vem negativo.
    VALOR_ASSINADO = "valor_assinado"
    #: Coluna de valor sem sinal + coluna indicadora ("D"/"C").
    COLUNA_INDICADORA = "coluna_indicadora"
    #: Duas colunas separadas: débito e crédito.
    COLUNAS_DEBITO_CREDITO = "colunas_debito_credito"


class Alvo(Enum):
    """O que este perfil produz: linhas de extrato ou linhas do livro interno."""

    EXTRATO = "extrato"
    LIVRO = "livro"


class ErroPerfil(Exception):
    pass


@dataclass(frozen=True)
class Erro:
    campo: str
    mensagem: str


@dataclass(frozen=True)
class PerfilCSV:
    """Esquema declarado do perfil (IMP-03: sem isso `validar_perfil` é impossível).

    Campos obrigatórios: nome, versao, alvo, delimitador, encoding, formato_data,
    separador_decimal, sinal, colunas.
    """

    nome: str
    versao: str
    alvo: Alvo
    delimitador: str
    encoding: str
    formato_data: str
    separador_decimal: str
    separador_milhar: str
    sinal: ConvencaoSinal
    colunas: dict[str, str]
    conta: str
    instrumento_padrao: str = "desconhecido"

    @classmethod
    def de_dict(cls, dados: dict) -> "PerfilCSV":
        faltando = [c for c in _OBRIGATORIOS if c not in dados]
        if faltando:
            raise ErroPerfil(f"perfil sem campos obrigatórios: {', '.join(faltando)}")
        return cls(
            nome=dados["nome"],
            versao=str(dados["versao"]),
            alvo=Alvo(dados["alvo"]),
            delimitador=dados["delimitador"],
            encoding=dados["encoding"],
            formato_data=dados["formato_data"],
            separador_decimal=dados["separador_decimal"],
            separador_milhar=dados.get("separador_milhar", ""),
            sinal=ConvencaoSinal(dados["sinal"]),
            colunas=dict(dados["colunas"]),
            conta=dados["conta"],
            instrumento_padrao=dados.get("instrumento_padrao", "desconhecido"),
        )


_OBRIGATORIOS = (
    "nome",
    "versao",
    "alvo",
    "delimitador",
    "encoding",
    "formato_data",
    "separador_decimal",
    "sinal",
    "colunas",
    "conta",
)

#: Colunas exigidas por convenção de sinal. A gramática torna verificável o que
#: antes era prosa.
_COLUNAS_POR_SINAL = {
    ConvencaoSinal.VALOR_ASSINADO: ("data", "valor", "descricao"),
    ConvencaoSinal.COLUNA_INDICADORA: ("data", "valor", "descricao", "indicador"),
    ConvencaoSinal.COLUNAS_DEBITO_CREDITO: ("data", "debito", "credito", "descricao"),
}


def carregar_perfil(caminho: str | Path) -> PerfilCSV:
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return PerfilCSV.de_dict(dados)


def validar_perfil(perfil: PerfilCSV) -> list[Erro]:
    """Devolve a lista de erros do perfil. Lista vazia = perfil válido."""
    erros: list[Erro] = []
    exigidas = _COLUNAS_POR_SINAL[perfil.sinal]
    for col in exigidas:
        if col not in perfil.colunas:
            erros.append(
                Erro("colunas", f"convenção {perfil.sinal.value} exige a coluna '{col}'")
            )
    if len(perfil.delimitador) != 1:
        erros.append(Erro("delimitador", "deve ter exatamente 1 caractere"))
    if perfil.separador_decimal not in (",", "."):
        erros.append(Erro("separador_decimal", "deve ser ',' ou '.'"))
    if perfil.separador_decimal == perfil.separador_milhar:
        erros.append(Erro("separador_milhar", "não pode ser igual ao separador decimal"))
    if perfil.alvo is Alvo.LIVRO and "documento" not in perfil.colunas:
        erros.append(Erro("colunas", "perfil de livro exige a coluna 'documento'"))
    return erros


def normalizar_valor(bruto: str, perfil: PerfilCSV) -> str:
    """Texto do arquivo -> texto decimal canônico, preservando a escala da fonte.

    Não converte para Decimal aqui: quem constrói `Dinheiro` é o domínio (I1).
    """
    texto = bruto.strip()
    if perfil.separador_milhar:
        texto = texto.replace(perfil.separador_milhar, "")
    if perfil.separador_decimal != ".":
        texto = texto.replace(perfil.separador_decimal, ".")
    texto = texto.replace(" ", "")
    if not texto:
        raise ValorInvalido("valor vazio")
    return texto


class ValorInvalido(Exception):
    pass


def aplicar_sinal(linha: dict[str, str], perfil: PerfilCSV) -> str:
    """Resolve o valor com sinal segundo a convenção declarada (LIN-01, LIN-08).

    I2: o sinal é semântico e vem da convenção do perfil — nunca é inferido.
    """
    c = perfil.colunas
    if perfil.sinal is ConvencaoSinal.VALOR_ASSINADO:
        return normalizar_valor(linha[c["valor"]], perfil)

    if perfil.sinal is ConvencaoSinal.COLUNA_INDICADORA:
        valor = normalizar_valor(linha[c["valor"]], perfil).lstrip("+-")
        indicador = linha[c["indicador"]].strip().upper()
        if indicador in ("D", "DEBITO", "DÉBITO"):
            return f"-{valor}"
        if indicador in ("C", "CREDITO", "CRÉDITO"):
            return valor
        raise ValorInvalido(f"indicador de sinal irreconhecível: {indicador!r}")

    # COLUNAS_DEBITO_CREDITO — os dois casos degenerados, especificados (LIN-08)
    bruto_d = linha[c["debito"]].strip()
    bruto_c = linha[c["credito"]].strip()
    tem_d = _preenchida(bruto_d, perfil)
    tem_c = _preenchida(bruto_c, perfil)
    if tem_d and tem_c:
        raise ValorInvalido("débito e crédito preenchidos na mesma linha")
    if not tem_d and not tem_c:
        raise ValorInvalido("débito e crédito ambos vazios")
    if tem_d:
        return f"-{normalizar_valor(bruto_d, perfil).lstrip('+-')}"
    return normalizar_valor(bruto_c, perfil).lstrip("+-")


def _preenchida(bruto: str, perfil: PerfilCSV) -> bool:
    """Uma coluna débito/crédito conta como PREENCHIDA se traz número não-zero.

    Regra declarada, não inferida: exports reais preenchem a coluna não usada com
    string vazia OU com "0,00". Tratar o zero como preenchido faria toda linha
    cair no caso degenerado "ambas preenchidas" e abortar o lote — logo zero
    conta como vazio. Texto não numérico não é vazio nem preenchido: é linha
    inválida, e `aplicar_sinal` levanta ValorInvalido no caso "ambas vazias",
    nomeando a linha.
    """
    if not bruto:
        return False
    try:
        texto = normalizar_valor(bruto, perfil)
    except ValorInvalido:
        return False
    corpo = texto.lstrip("+-")
    if not corpo.replace(".", "").isdigit():
        return False
    return any(ch not in "0." for ch in corpo)
