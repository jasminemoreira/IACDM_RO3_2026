"""M-03 csv-adapter — porta FonteDeExtrato para CSV dirigido por perfil.

OCP na prática: adicionar um banco é adicionar um PERFIL declarativo, não código.
A semântica do perfil vive em `t26.adapters.perfil`, que é a fonte única lida
também pelo fixture-generator (ARC-08).

Detecção automática de layout foi REJEITADA na Fase 0: é heurística para um
problema com solução determinística conhecida — sinal de alarme do S6.

RES-03 (dívida aceita pelo operador): sem quarentena. Linha inválida ABORTA o
lote nomeando arquivo e linha. Falha explícita, nunca perda silenciosa.

ASM-07 — o encoding declarado é verificado, com uma ressalva que a micro-verificação
S7 revelou e que fica registrada aqui em vez de escondida: confiar em
`UnicodeDecodeError` NÃO basta. Codecs de byte único (cp1252, latin-1) aceitam
quase qualquer sequência, então ler um arquivo UTF-8 declarando cp1252 tem
sucesso e devolve mojibake em silêncio — a descrição muda, o hash canônico muda
e a dedup falha sem sinal. `_conferir_encoding` cobre esse caso com um teste
DETERMINÍSTICO: se o perfil declara codec de byte único e os bytes são UTF-8
válido com sequências multibyte, o arquivo é recusado. A direção inversa
(arquivo cp1252 declarado utf-8) já falha naturalmente com UnicodeDecodeError.
"""

from __future__ import annotations

import csv as _csv  # fronteira do adapter: o núcleo não importa csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from t26.adapters.perfil import (
    Alvo,
    PerfilCSV,
    ValorInvalido,
    aplicar_sinal,
    validar_perfil,
)
from t26.domain.model import Instrumento, RegistroBruto


class ErroLeituraCSV(Exception):
    """Falha de leitura, sempre nomeando arquivo e linha."""


#: Codecs de byte único: aceitam quase toda sequência e por isso não sinalizam
#: um arquivo UTF-8 lido com o encoding errado.
_BYTE_UNICO = {"cp1252", "latin-1", "latin1", "iso-8859-1", "windows-1252", "cp850"}


def _conferir_encoding(dados: bytes, perfil: PerfilCSV, nome: str) -> None:
    """Recusa arquivo UTF-8 declarado como codec de byte único (ASM-07).

    Teste determinístico, não heurística: ou os bytes são UTF-8 válido com
    sequências multibyte, ou não são. Arquivo puramente ASCII passa nos dois
    lados e não é ambíguo.
    """
    if perfil.encoding.lower().replace("_", "-") not in _BYTE_UNICO:
        return
    if dados.isascii():
        return
    try:
        dados.decode("utf-8")
    except UnicodeDecodeError:
        return  # não é UTF-8: o encoding de byte único declarado é plausível
    raise ErroLeituraCSV(
        f"{nome}: os bytes são UTF-8 válido, mas o perfil '{perfil.nome}' declara "
        f"'{perfil.encoding}'. Ler assim produziria mojibake silencioso e quebraria a "
        f"deduplicação — corrija o encoding do perfil."
    )


def ler(caminho: str | Path, perfil: PerfilCSV) -> Iterable[RegistroBruto]:
    p = Path(caminho)
    erros = validar_perfil(perfil)
    if erros:
        detalhe = "; ".join(f"{e.campo}: {e.mensagem}" for e in erros)
        raise ErroLeituraCSV(f"perfil '{perfil.nome}' inválido — {detalhe}")

    dados = p.read_bytes()
    _conferir_encoding(dados, perfil, p.name)
    try:
        texto = dados.decode(perfil.encoding)
    except UnicodeDecodeError as erro:
        raise ErroLeituraCSV(
            f"{p.name}: conteúdo não decodifica em '{perfil.encoding}' declarado no "
            f"perfil '{perfil.nome}' (byte {erro.start}) — encoding do perfil está errado"
        ) from erro

    registros: list[RegistroBruto] = []
    leitor = _csv.DictReader(texto.splitlines(), delimiter=perfil.delimitador)
    colunas = perfil.colunas
    instrumento_padrao = Instrumento(perfil.instrumento_padrao)

    for numero, linha in enumerate(leitor, start=2):  # linha 1 é o cabeçalho
        faltando = [c for c in colunas.values() if c not in linha or linha[c] is None]
        if faltando:
            raise ErroLeituraCSV(
                f"{p.name}:{numero}: colunas ausentes no arquivo: {', '.join(sorted(faltando))} "
                f"(perfil '{perfil.nome}' as declara)"
            )
        try:
            valor_texto = aplicar_sinal(linha, perfil)
        except (ValorInvalido, KeyError) as erro:
            raise ErroLeituraCSV(f"{p.name}:{numero}: valor inválido — {erro}") from erro

        bruto_data = linha[colunas["data"]].strip()
        try:
            data = datetime.strptime(bruto_data, perfil.formato_data).date()
        except ValueError as erro:
            raise ErroLeituraCSV(
                f"{p.name}:{numero}: data {bruto_data!r} não casa com o formato "
                f"{perfil.formato_data!r} do perfil"
            ) from erro

        registros.append(
            RegistroBruto(
                fonte=perfil.nome,
                conta=perfil.conta,
                data=data,
                valor_texto=valor_texto,
                descricao_bruta=linha[colunas["descricao"]].strip(),
                arquivo=p.name,
                linha=numero,
                fitid=None,  # A2: CSV de banco não traz identificador nativo
                instrumento=instrumento_padrao,
            )
        )
    return registros


def e_livro(perfil: PerfilCSV) -> bool:
    return perfil.alvo is Alvo.LIVRO
