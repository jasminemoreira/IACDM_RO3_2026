"""M-02 ofx-adapter — porta FonteDeExtrato para arquivos OFX.

S6 Tier 1: usa `ofxtools` (aprovado na Fase 1), não parser próprio. Escrever um
parser de OFXv1 SGML à mão foi rejeitado como AP7 e como risco de corretude nos
desvios reais dos bancos.

Semântica dos campos em specs/references/fontes-externas.md §1.1:
  STMTTRN obrigatórios: TRNTYPE, DTPOSTED, TRNAMT, FITID.
  FITID é único DENTRO DA CONTA, não entre instituições — daí a ChaveNatural
  incluir fonte e conta (§1.2).

SEC-02 / IMP-10 — verificado empiricamente, não assumido:
  xml.etree (o que o ofxtools usa) RECUSA entidades externas: um SYSTEM
  "file:///etc/passwd" resulta em ParseError "undefined entity". A metade XXE
  está fechada pela plataforma. Mas entidades INTERNAS SÃO expandidas, então o
  vetor de expansão exponencial é real e é tratado aqui, na entrada: payload
  contendo <!DOCTYPE ou <!ENTITY é recusado, e há teto de tamanho.

MEC-01: a versão de ofxtools é fixada em pyproject. A biblioteca valida contra a
especificação e RECUSA arquivos não conformes; uma atualização mais estrita passa
a recusar extratos que antes importavam.

RES-02 (dívida aceita pelo operador): não há quarentena de linhas. Linha inválida
ABORTA o lote com erro nomeando arquivo e linha — falha explícita, sem perda
silenciosa.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Iterable, Iterator

from t26.domain.model import Instrumento, RegistroBruto

#: Teto de tamanho do arquivo OFX. Não é limite de negócio: é o anteparo contra
#: expansão de entidades e contra arquivo hostil. 64 MiB cobre folgadamente um
#: extrato anual de 50k transações (~250 bytes/transação => ~12 MiB).
TETO_BYTES = 64 * 1024 * 1024

_DECLARACAO_PERIGOSA = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)

#: TRNTYPE -> instrumento, para escolher a janela de compensação
#: (specs/technical/rubrica-score.md §2). O que não mapeia vira DESCONHECIDO e é
#: sinalizado no relatório — conservadorismo declarado, não resultado.
_INSTRUMENTO_POR_TRNTYPE = {
    "XFER": Instrumento.TED,
    "DIRECTDEP": Instrumento.TED,
    "DIRECTDEBIT": Instrumento.BOLETO,
    "PAYMENT": Instrumento.BOLETO,
    "REPEATPMT": Instrumento.BOLETO,
    "CHECK": Instrumento.BOLETO,
    "POS": Instrumento.CARTAO,
    "ATM": Instrumento.DESCONHECIDO,
}


class ErroLeituraOFX(Exception):
    """Falha de leitura nomeando arquivo e, quando aplicável, a transação."""


def _verificar_payload(caminho: Path) -> bytes:
    dados = caminho.read_bytes()
    if len(dados) > TETO_BYTES:
        raise ErroLeituraOFX(
            f"{caminho}: arquivo com {len(dados)} bytes excede o teto de {TETO_BYTES}"
        )
    achado = _DECLARACAO_PERIGOSA.search(dados)
    if achado:
        raise ErroLeituraOFX(
            f"{caminho}: payload contém declaração {achado.group(1).decode()} — "
            "recusado (expansão de entidades)"
        )
    return dados


def _para_date(valor) -> date:
    """DTPOSTED chega como datetime do ofxtools; a data de postagem é o que importa.

    ASM-05: o componente de fuso é descartado explicitamente aqui, e não ignorado
    por acidente. Uma transação perto da meia-noite fica ancorada na data que a
    instituição reportou, que é a que o extrato imprime e o analista compara.
    """
    return valor.date() if hasattr(valor, "date") else valor


def ler(caminho: str | Path, fonte: str) -> Iterable[RegistroBruto]:
    """Lê um arquivo OFX e devolve registros brutos, na ordem do arquivo.

    `fonte` identifica a origem `(instituição, conta, formato)` do glossário; a
    conta vem do próprio arquivo (ACCTID), não do parâmetro.
    """
    return list(_ler(Path(caminho), fonte))


def _ler(caminho: Path, fonte: str) -> Iterator[RegistroBruto]:
    from ofxtools.Parser import OFXTree  # import local: fronteira do adapter

    _verificar_payload(caminho)

    arvore = OFXTree()
    try:
        arvore.parse(str(caminho))
        ofx = arvore.convert()
    except Exception as erro:  # ofxtools levanta tipos variados por formato
        raise ErroLeituraOFX(f"{caminho}: OFX ilegível — {type(erro).__name__}: {erro}") from erro

    linha = 0
    for extrato in ofx.statements:
        conta = str(getattr(extrato.account, "acctid", "") or "")
        if not conta:
            raise ErroLeituraOFX(f"{caminho}: extrato sem ACCTID — conta é parte da chave natural")
        for trn in extrato.transactions:
            linha += 1
            if trn.dtposted is None or trn.trnamt is None:
                raise ErroLeituraOFX(
                    f"{caminho}: transação {linha} sem DTPOSTED ou TRNAMT (campos obrigatórios)"
                )
            descricao = (trn.name or "") or (trn.memo or "")
            trntype = str(trn.trntype or "").upper()
            yield RegistroBruto(
                fonte=fonte,
                conta=conta,
                data=_para_date(trn.dtposted),
                valor_texto=str(trn.trnamt),
                descricao_bruta=descricao.strip(),
                arquivo=caminho.name,
                linha=linha,
                fitid=str(trn.fitid) if trn.fitid else None,
                instrumento=_INSTRUMENTO_POR_TRNTYPE.get(trntype, Instrumento.DESCONHECIDO),
            )
