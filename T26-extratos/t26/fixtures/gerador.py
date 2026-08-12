"""M-12 fixture-generator — dataset sintético determinístico com ground truth.

É o módulo que torna VAL-1 e VAL-2 VERIFICÁVEIS: sem duplicatas plantadas e
colisões legítimas plantadas, "zero falso negativo" e "zero falso positivo" são
frases sem teste possível — não há como falhar.

Determinismo: seed fixa, sem `random` global, sem relógio. A mesma seed produz
byte a byte os mesmos arquivos, que é o que permite VAL-5 ser medido por digest.

ARC-08 — NÃO depende de `csv-adapter`, mas também NÃO reimplementa a semântica
do perfil: lê o MESMO arquivo de perfil que o parser lê, via
`t26.adapters.perfil`, que é a fonte única da gramática. Cortar a dependência
sem isso teria trocado acoplamento por deriva — o ground truth rotulando sob uma
interpretação de `sinal` que o parser não usa.

SEC-05 — escrita CONFINADA ao diretório de destino declarado. Um caminho errado
não pode sobrescrever dados reais do analista.

O que é plantado, e por quê cada um:
  - duplicata de reimportação em janela SOBREPOSTA (não o mesmo arquivo): é o
    UC-2, e foi o caso que V(2) quebrou sem ninguém notar até a Iteração 2.
  - duplicata cross-source com descrição divergente: exercita A6 e o piso de
    evidência forte.
  - colisão legítima (duas transações iguais no mesmo arquivo): é o caso que
    mede VAL-2; sem ele, nenhum teste de falso positivo pode falhar.
  - ESTORNO: a premissa A7 segue aberta desde a Fase 0, e a Fase 6 precisa medir
    os três casos que a mitigação não cobre, em vez de presumi-los.
  - bloco degenerado de tarifas de mesmo valor: exercita PRF-06 e o teto.
  - arquivo NÃO CONFORME deliberado: exercita o caminho de erro dos adapters.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from t26.adapters.perfil import Alvo, ConvencaoSinal, PerfilCSV, carregar_perfil

DATA_BASE = date(2026, 7, 1)

_SIGNON = (
    "<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>"
    "<DTSERVER>20260731120000</DTSERVER><LANGUAGE>POR</LANGUAGE></SONRS></SIGNONMSGSRSV1>"
)
_CABECALHO_OFX = (
    "OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\nENCODING:USASCII\n"
    "CHARSET:1252\nCOMPRESSION:NONE\nOLDFILEUID:NONE\nNEWFILEUID:NONE\n\n"
)

CONTRAPARTES = [
    "PIX ENVIADO JOAO", "PAGTO FORNEC ACME", "ALUGUEL IMOVEL", "SALARIO FOLHA",
    "ENERGIA ELETRICA", "TELEFONIA MOVEL", "SEGURO FROTA", "MATERIAL ESCRITORIO",
    "SERVICOS TI", "MANUTENCAO PREDIAL",
]


@dataclass
class GroundTruth:
    """Rótulos que a Fase 6 usa para aferir VAL-1 e VAL-2."""

    duplicatas_reimportacao: list[tuple[str, str]] = field(default_factory=list)
    duplicatas_cross_source: list[tuple[str, str]] = field(default_factory=list)
    colisoes_legitimas: list[tuple[str, str]] = field(default_factory=list)
    estornos: list[tuple[str, str]] = field(default_factory=list)
    casamentos_esperados: list[tuple[str, str]] = field(default_factory=list)
    total_transacoes: int = 0

    def para_json(self) -> str:
        return json.dumps(
            {
                "duplicatas_reimportacao": self.duplicatas_reimportacao,
                "duplicatas_cross_source": self.duplicatas_cross_source,
                "colisoes_legitimas": self.colisoes_legitimas,
                "estornos": self.estornos,
                "casamentos_esperados": self.casamentos_esperados,
                "total_transacoes": self.total_transacoes,
            },
            ensure_ascii=False,
            indent=2,
        )


class _Aleatorio:
    """Gerador determinístico próprio: sem `random` global e sem relógio.

    Usa SHA-256 do (seed, contador) — reproduz a mesma sequência em qualquer
    máquina e versão de Python, o que `random` não garante entre versões.
    """

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._n = 0

    def _proximo(self) -> int:
        self._n += 1
        material = f"{self._seed}:{self._n}".encode()
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")

    def inteiro(self, minimo: int, maximo: int) -> int:
        return minimo + self._proximo() % (maximo - minimo + 1)

    def escolha(self, itens):
        return itens[self._proximo() % len(itens)]

    def valor(self) -> Decimal:
        centavos = self.inteiro(500, 900000)
        return (Decimal(centavos) / Decimal(100)).quantize(Decimal("0.01"))


def _confinar(destino: Path, nome: str) -> Path:
    """SEC-05 — recusa qualquer caminho que escape do destino declarado."""
    alvo = (destino / nome).resolve()
    raiz = destino.resolve()
    if not str(alvo).startswith(str(raiz) + "/") and alvo != raiz:
        raise ValueError(f"escrita fora do destino declarado: {alvo}")
    return alvo


def _ofx(transacoes: list[dict], conta: str) -> str:
    corpo = []
    for t in transacoes:
        corpo.append(
            f"<STMTTRN><TRNTYPE>{t['tipo']}</TRNTYPE>"
            f"<DTPOSTED>{t['data'].strftime('%Y%m%d')}</DTPOSTED>"
            f"<TRNAMT>{t['valor']}</TRNAMT><FITID>{t['fitid']}</FITID>"
            f"<NAME>{t['descricao']}</NAME></STMTTRN>"
        )
    return (
        _CABECALHO_OFX
        + "<OFX>" + _SIGNON
        + "<BANKMSGSRSV1><STMTTRNRS><TRNUID>1</TRNUID>"
        "<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>"
        f"<STMTRS><CURDEF>BRL</CURDEF><BANKACCTFROM><BANKID>001</BANKID>"
        f"<ACCTID>{conta}</ACCTID><ACCTTYPE>CHECKING</ACCTTYPE></BANKACCTFROM>"
        "<BANKTRANLIST><DTSTART>20260701</DTSTART><DTEND>20260831</DTEND>"
        + "".join(corpo)
        + "</BANKTRANLIST><LEDGERBAL><BALAMT>0.00</BALAMT><DTASOF>20260831</DTASOF>"
        "</LEDGERBAL></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>\n"
    )


def _csv(transacoes: list[dict], perfil: PerfilCSV) -> str:
    """Emite CSV conforme a gramática do perfil — a MESMA que o parser lê."""
    c = perfil.colunas
    dec = perfil.separador_decimal

    def fmt(v: Decimal) -> str:
        return f"{v:.2f}".replace(".", dec) if dec != "." else f"{v:.2f}"

    if perfil.sinal is ConvencaoSinal.VALOR_ASSINADO:
        cabecalho = [c["data"], c["valor"], c["descricao"]]
        linhas = [
            [t["data"].strftime(perfil.formato_data), fmt(t["valor"]), t["descricao"]]
            for t in transacoes
        ]
    elif perfil.sinal is ConvencaoSinal.COLUNA_INDICADORA:
        cabecalho = [c["data"], c["valor"], c["indicador"], c["descricao"]]
        linhas = [
            [
                t["data"].strftime(perfil.formato_data),
                fmt(abs(t["valor"])),
                "D" if t["valor"] < 0 else "C",
                t["descricao"],
            ]
            for t in transacoes
        ]
    else:  # COLUNAS_DEBITO_CREDITO
        cabecalho = [c["data"], c["debito"], c["credito"], c["descricao"]]
        linhas = [
            [
                t["data"].strftime(perfil.formato_data),
                fmt(abs(t["valor"])) if t["valor"] < 0 else "",
                fmt(t["valor"]) if t["valor"] > 0 else "",
                t["descricao"],
            ]
            for t in transacoes
        ]
    # Perfil de livro exige a coluna de documento (validar_perfil a impõe): o
    # gerador emite a MESMA gramática que o parser lê, senão o dataset não passa
    # pela validação que ele existe para exercitar.
    if perfil.alvo is Alvo.LIVRO and "documento" in c:
        cabecalho.append(c["documento"])
        for i, t in enumerate(transacoes):
            linhas[i].append(t.get("documento", f"AP-{i:05d}"))

    d = perfil.delimitador
    return d.join(cabecalho) + "\n" + "\n".join(d.join(l) for l in linhas) + "\n"


def gerar(
    seed: int,
    n: int,
    destino: str | Path,
    perfil_csv: str | Path,
    perfil_livro: str | Path,
) -> GroundTruth:
    """Gera o dataset completo e devolve o ground truth rotulado."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    rnd = _Aleatorio(seed)
    perfil = carregar_perfil(perfil_csv)
    perfil_l = carregar_perfil(perfil_livro)
    gt = GroundTruth()

    base: list[dict] = []
    for i in range(n):
        dia = DATA_BASE + timedelta(days=rnd.inteiro(0, 44))
        valor = -rnd.valor()
        base.append(
            {
                "data": dia,
                "valor": valor,
                "descricao": f"{rnd.escolha(CONTRAPARTES)} {i:05d}",
                "fitid": f"F{seed}{i:07d}",
                "tipo": "XFER",
            }
        )

    # --- colisão legítima: duas linhas idênticas no MESMO arquivo (mede VAL-2)
    colisoes = []
    for i in range(max(2, n // 50)):
        modelo = base[rnd.inteiro(0, len(base) - 1)]
        gemea = dict(modelo, fitid=f"F{seed}C{i:06d}")
        base.append(gemea)
        colisoes.append((modelo["fitid"], gemea["fitid"]))
    gt.colisoes_legitimas = colisoes

    # --- estorno: mesmo valor absoluto, sinal oposto (premissa A7, ainda aberta)
    estornos = []
    for i in range(max(2, n // 100)):
        modelo = base[rnd.inteiro(0, n - 1)]
        est = dict(
            modelo,
            valor=-modelo["valor"],
            fitid=f"F{seed}E{i:06d}",
            descricao="ESTORNO " + modelo["descricao"],
        )
        base.append(est)
        estornos.append((modelo["fitid"], est["fitid"]))
    gt.estornos = estornos

    # --- bloco degenerado: tarifas de valor idêntico (exercita PRF-06 e o teto)
    for i in range(60):
        base.append(
            {
                "data": DATA_BASE + timedelta(days=i % 30),
                "valor": Decimal("-30.00"),
                "descricao": f"TARIFA MENSAL {i:03d}",
                "fitid": f"F{seed}T{i:06d}",
                "tipo": "SRVCHG",
            }
        )

    base.sort(key=lambda t: (t["data"], t["fitid"]))
    gt.total_transacoes = len(base)

    corte = int(len(base) * 0.7)
    janela_a = base[:corte]
    janela_b = base[int(len(base) * 0.5) :]  # SOBREPOSTA — é o UC-2
    sobrepostas = {t["fitid"] for t in janela_a} & {t["fitid"] for t in janela_b}
    gt.duplicatas_reimportacao = [(f, f) for f in sorted(sobrepostas)]

    _confinar(destino, "extrato-jul.ofx").write_text(_ofx(janela_a, perfil.conta))
    _confinar(destino, "extrato-julago.ofx").write_text(_ofx(janela_b, perfil.conta))

    # --- cross-source: mesmas transações por CSV, com descrição divergente (A6)
    cross = base[: max(5, n // 20)]
    cross_csv = [
        dict(t, descricao=t["descricao"].split()[0] + " " + t["descricao"].split()[-1])
        for t in cross
    ]
    _confinar(destino, "extrato-outrafonte.csv").write_text(
        _csv(cross_csv, perfil), encoding=perfil.encoding
    )
    gt.duplicatas_cross_source = [(t["fitid"], t["descricao"]) for t in cross]

    # --- livro interno: metade dos lançamentos casa, o resto é órfão
    livro = []
    for t in base[: len(base) // 2]:
        livro.append(dict(t, descricao="FORNEC " + t["descricao"]))
        gt.casamentos_esperados.append((t["fitid"], t["descricao"]))
    _confinar(destino, "livro.csv").write_text(
        _csv(livro, perfil_l), encoding=perfil_l.encoding
    )

    # --- arquivo NÃO CONFORME deliberado (exercita o caminho de erro)
    _confinar(destino, "nao-conforme.ofx").write_text(
        _CABECALHO_OFX + "<OFX><BANKMSGSRSV1><STMTTRNRS></STMTTRNRS></BANKMSGSRSV1></OFX>\n"
    )
    _confinar(destino, "ground-truth.json").write_text(gt.para_json(), encoding="utf-8")
    return gt
