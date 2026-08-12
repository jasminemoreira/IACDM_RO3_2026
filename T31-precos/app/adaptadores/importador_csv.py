"""M-08 `importador-csv` — ida e volta do formato legado.

V(5)/Y5: parsing e serialização PUROS. A prova de paridade NÃO mora aqui —
foi para `servico-aplicacao` (V(3)/W2), o que devolveu este módulo à condição
de testável sem o motor (ARQ-05).

Decisões acumuladas nas quatro rodadas:
  * SEC-02 — limite de 5 MB e 2.000 linhas (A-18, derivado da escala da P0).
  * ASS-04/LIN-03 — encoding detectado, delimitador inferido, cabeçalho casado
    sem acento, sem caixa e em qualquer ordem.
  * LIN-08/X4 — não existem "dois formatos": existe UM conjunto de colunas,
    algumas opcionais. Ausentes recebem o default legado.
  * LIN-10/Y6 — coluna desconhecida é preservada NO RELATÓRIO, não no modelo
    de regra, e não é reexportada. `Obs` é anotação humana, não atributo.
  * SEC-06 — na exportação, célula iniciada por `=`, `+`, `-` ou `@` recebe
    prefixo `'` (CSV injection).
  * LIN-07/LIN-09/Y3 — na importação o `'` é removido SOMENTE quando precede
    um desses caracteres. Valor que legitimamente começa com apóstrofo
    sobrevive à ida-e-volta.
  * MEC-05/X7 — ambiguidade de separador (`ponto + 3 dígitos, sem vírgula`) é
    parseada pela regra determinística E reportada como aviso.
"""

from __future__ import annotations

import csv
import hashlib
import io
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from ..dominio.dinheiro import Dinheiro, ErroFormato, texto_tem_separador_ambiguo
from ..dominio.modelo_dominio import (
    ESCOPO_GERAL,
    DescontoPct,
    Faixa,
    PrecoUnitario,
    Produto,
    Regra,
    TipoEfeito,
    Vigencia,
    normalizar_sku,
)

LIMITE_BYTES = 5 * 1024 * 1024
LIMITE_LINHAS = 2_000
_FORMULA = ("=", "+", "-", "@")

_ALIAS = {
    "sku": "escopo",
    "escopo": "escopo",
    "produto": "produto",
    "descricao": "produto",
    "precobase": "preco_base",
    "de": "de",
    "qtdde": "de",
    "quantidademin": "de",
    "ate": "ate",
    "qtdate": "ate",
    "quantidademax": "ate",
    "precoun": "preco_un",
    "precounitario": "preco_un",
    "valor": "preco_un",
    "tipo": "tipo_efeito",
    "tipoefeito": "tipo_efeito",
    "prioridade": "prioridade",
    "vigenciade": "vigencia_inicio",
    "vigenciainicio": "vigencia_inicio",
    "vigenciaate": "vigencia_fim",
    "vigenciafim": "vigencia_fim",
}


@dataclass(frozen=True, slots=True)
class Rejeitada:
    linha: int
    motivo: str


@dataclass(frozen=True, slots=True)
class AvisoImportacao:
    linha: int
    descricao: str


@dataclass(frozen=True, slots=True)
class ConflitoBase:
    """Evidência bruta de preço base divergente para o mesmo SKU (V-04).

    Arbitragem do operador (Fase 5): a DETECÇÃO fica aqui, onde o dado bruto
    está; a DECISÃO de bloquear é de `validador-coerencia`. Rejeitar a linha
    faria o sistema escolher silenciosamente um dos dois preços e publicar —
    exatamente a dor #2 que o projeto existe para eliminar.
    """

    sku: str
    valores: tuple[str, ...]
    linhas: tuple[int, ...]


@dataclass(slots=True)
class ResultadoImportacao:
    rascunho: list[Regra] = field(default_factory=list)
    produtos: list[Produto] = field(default_factory=list)
    rejeitadas: list[Rejeitada] = field(default_factory=list)
    avisos: list[AvisoImportacao] = field(default_factory=list)
    conflitos_base: list[ConflitoBase] = field(default_factory=list)
    colunas_desconhecidas: list[str] = field(default_factory=list)
    # CS-1: (linha, sku, qtd de teste, valor ORIGINAL da planilha em ISO).
    # É contra esta coluna que a paridade compara — nunca contra a saída do
    # motor. LIMITAÇÃO DECLARADA: o valor passa pelo mesmo parser dos dois
    # lados; um erro no parser seria invisível aqui, e é por isso que N-06
    # tem casos-armadilha próprios com valores esperados escritos à mão.
    paridade_esperada: list[tuple[int, str, int, str]] = field(default_factory=list)
    sha256: str = ""

    @property
    def importadas(self) -> int:
        return len(self.rascunho)


class ErroDeImportacao(Exception):
    """Falha que impede sequer produzir relatório linha a linha."""


def importar(conteudo: bytes, hoje: date) -> ResultadoImportacao:
    if len(conteudo) > LIMITE_BYTES:
        raise ErroDeImportacao(
            f"arquivo com {len(conteudo) // 1024} KB excede o limite de "
            f"{LIMITE_BYTES // 1024 // 1024} MB"
        )

    texto = _decodificar(conteudo)
    linhas_brutas = texto.splitlines()
    if len(linhas_brutas) - 1 > LIMITE_LINHAS:
        raise ErroDeImportacao(
            f"arquivo com {len(linhas_brutas) - 1} linhas excede o limite de "
            f"{LIMITE_LINHAS}"
        )

    delimitador = _inferir_delimitador(linhas_brutas[0] if linhas_brutas else "")
    leitor = csv.reader(io.StringIO(texto), delimiter=delimitador)
    try:
        cabecalho = next(leitor)
    except StopIteration:
        raise ErroDeImportacao("arquivo vazio") from None

    mapa, desconhecidas = _mapear_cabecalho(cabecalho)
    faltando = {"escopo", "de", "preco_un"} - set(mapa.values())
    if faltando:
        raise ErroDeImportacao(
            "cabeçalho não reconhecido: faltam as colunas "
            + ", ".join(sorted(faltando))
        )

    res = ResultadoImportacao(
        colunas_desconhecidas=desconhecidas,
        sha256=hashlib.sha256(conteudo).hexdigest(),
    )
    bases: dict[str, tuple[Dinheiro, int]] = {}
    descricoes: dict[str, str] = {}
    vistas: set[tuple] = set()

    # IMP-03: numeração 1-based CONTANDO o cabeçalho; linha em branco não
    # consome número de dado, mas conta na posição do arquivo.
    for pos, campos in enumerate(leitor, start=2):
        if not any((c or "").strip() for c in campos):
            continue
        v = {alvo: _celula(campos, idx) for idx, alvo in mapa.items()}
        _processar_linha(pos, v, res, bases, descricoes, vistas, hoje)

    _consolidar_produtos(bases, descricoes, res)
    return res


def _processar_linha(pos, v, res, bases, descricoes, vistas, hoje) -> None:
    assinatura = tuple(sorted(v.items()))
    if assinatura in vistas:
        res.rejeitadas.append(Rejeitada(pos, "linha duplicada (idêntica a uma anterior)"))
        return
    vistas.add(assinatura)

    escopo_bruto = v.get("escopo", "")
    escopo = ESCOPO_GERAL if escopo_bruto.strip() == ESCOPO_GERAL else normalizar_sku(escopo_bruto)
    if not escopo:
        res.rejeitadas.append(Rejeitada(pos, "SKU ausente"))
        return

    try:
        minimo = int(v["de"])
    except (ValueError, KeyError):
        res.rejeitadas.append(
            Rejeitada(pos, f"campo 'De' não numérico: '{v.get('de', '')}'")
        )
        return

    maximo = _ate(v.get("ate", ""))
    if maximo is _INVALIDO:
        res.rejeitadas.append(
            Rejeitada(pos, f"campo 'Ate' não numérico: '{v.get('ate', '')}'")
        )
        return

    try:
        faixa = Faixa(minimo, maximo)
    except ValueError as e:
        res.rejeitadas.append(Rejeitada(pos, str(e)))
        return

    tipo = _tipo_efeito(v.get("tipo_efeito", ""))
    bruto_valor = v.get("preco_un", "")

    if texto_tem_separador_ambiguo(bruto_valor):
        res.avisos.append(
            AvisoImportacao(
                pos,
                f"'{bruto_valor.strip()}' tem ponto seguido de 3 dígitos sem vírgula — "
                "lido como separador de milhar (regra pt-BR declarada)",
            )
        )

    if tipo is TipoEfeito.DESCONTO_PCT:
        try:
            efeito = DescontoPct(Decimal(bruto_valor.strip().rstrip("%").replace(",", ".")))
        except (InvalidOperation, ValueError) as e:
            res.rejeitadas.append(Rejeitada(pos, f"desconto inválido: '{bruto_valor}' ({e})"))
            return
    else:
        valor = Dinheiro.de_texto(bruto_valor)
        if isinstance(valor, ErroFormato):
            res.rejeitadas.append(Rejeitada(pos, valor.motivo))
            return
        efeito = PrecoUnitario(valor)

    base_txt = v.get("preco_base", "")
    if escopo != ESCOPO_GERAL and base_txt.strip():
        base = Dinheiro.de_texto(base_txt)
        if isinstance(base, ErroFormato):
            res.rejeitadas.append(Rejeitada(pos, f"preço base: {base.motivo}"))
            return
        anterior = bases.get(escopo)
        if anterior and anterior[0] != base:
            # A linha NÃO é rejeitada: quem decide bloquear é o validador.
            existente = next(
                (c for c in res.conflitos_base if c.sku == escopo), None
            )
            if existente is None:
                res.conflitos_base.append(
                    ConflitoBase(
                        sku=escopo,
                        valores=(str(anterior[0]), str(base)),
                        linhas=(anterior[1], pos),
                    )
                )
            elif str(base) not in existente.valores:
                res.conflitos_base.remove(existente)
                res.conflitos_base.append(
                    ConflitoBase(
                        sku=escopo,
                        valores=(*existente.valores, str(base)),
                        linhas=(*existente.linhas, pos),
                    )
                )
        bases.setdefault(escopo, (base, pos))
        if v.get("produto", "").strip():
            descricoes.setdefault(escopo, v["produto"].strip())

    prioridade = _inteiro(v.get("prioridade", ""), padrao=0)
    inicio = _data(v.get("vigencia_inicio", ""), padrao=hoje)
    fim = _data(v.get("vigencia_fim", ""), padrao=None)

    res.rascunho.append(
        Regra(
            id=f"R-{escopo}-{minimo}-{maximo if maximo is not None else 'INF'}",
            escopo=escopo,
            faixa=faixa,
            efeito=efeito,
            prioridade=prioridade,
            vigencia=Vigencia(inicio, fim),
        )
    )
    if escopo != ESCOPO_GERAL and tipo is TipoEfeito.PRECO_UNITARIO:
        qtd_teste = minimo if maximo is None else (minimo + maximo) // 2
        res.paridade_esperada.append((pos, escopo, qtd_teste, efeito.valor.iso()))


def _consolidar_produtos(bases, descricoes, res: ResultadoImportacao) -> None:
    res.produtos = [
        Produto(sku, descricoes.get(sku, sku), base)
        for sku, (base, _) in sorted(bases.items())
    ]
    catalogo = {p.sku for p in res.produtos}
    sobreviventes: list[Regra] = []
    for r in res.rascunho:
        if r.escopo != ESCOPO_GERAL and r.escopo not in catalogo:
            res.rejeitadas.append(
                Rejeitada(0, f"SKU inexistente no catálogo: {r.escopo}")
            )
            continue
        sobreviventes.append(r)
    res.rascunho = sobreviventes


# -- exportação ---------------------------------------------------------------

CABECALHO_EXPORTACAO = [
    "SKU",
    "Produto",
    "Preco base",
    "De",
    "Ate",
    "Tipo",
    "Valor",
    "Prioridade",
    "Vigencia de",
    "Vigencia ate",
]


def exportar(regras: list[Regra], produtos: dict[str, Produto]) -> bytes:
    """Formato ESTENDIDO com o legado como caso degenerado (V(3)/W4).

    O ciclo importar→exportar→importar é idempotente: escopo `*`, prioridade,
    vigência e tipo de efeito têm coluna própria. É o caminho de rollback
    aprovado pelo operador em resposta a MIG-01.
    """
    buf = io.StringIO(newline="")
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow(CABECALHO_EXPORTACAO)
    for r in sorted(regras, key=lambda x: (x.escopo, x.faixa.minimo)):
        p = produtos.get(r.escopo)
        valor = (
            r.efeito.valor.iso()
            if r.efeito.tipo is TipoEfeito.PRECO_UNITARIO
            else str(r.efeito.pct)
        )
        w.writerow(
            [
                _escapar(r.escopo),
                _escapar(p.descricao if p else ""),
                p.preco_base.iso() if p else "",
                r.faixa.minimo,
                r.faixa.maximo if r.faixa.maximo is not None else "",
                r.efeito.tipo.value,
                valor,
                r.prioridade,
                r.vigencia.inicio.isoformat(),
                r.vigencia.fim.isoformat() if r.vigencia.fim else "",
            ]
        )
    return buf.getvalue().encode("utf-8")


def _escapar(v: str) -> str:
    """SEC-06 — neutraliza fórmula ao abrir em planilha."""
    return f"'{v}" if v.startswith(_FORMULA) else v


def _desescapar(v: str) -> str:
    """LIN-09/Y3 — inverso EXATO de `_escapar`.

    Remove o apóstrofo somente quando ele precede caractere de fórmula, para
    que um valor que legitimamente começa com `'` sobreviva à ida-e-volta.
    """
    if len(v) > 1 and v[0] == "'" and v[1] in _FORMULA:
        return v[1:]
    return v


# -- leitura de campos --------------------------------------------------------

_INVALIDO = object()


def _decodificar(b: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ErroDeImportacao("não foi possível decodificar o arquivo")


def _inferir_delimitador(primeira: str) -> str:
    return ";" if primeira.count(";") >= primeira.count(",") else ","


def _normalizar_nome(s: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return "".join(ch for ch in sem_acento.lower() if ch.isalnum())


def _mapear_cabecalho(cabecalho: list[str]) -> tuple[dict[int, str], list[str]]:
    mapa: dict[int, str] = {}
    desconhecidas: list[str] = []
    for idx, nome in enumerate(cabecalho):
        alvo = _ALIAS.get(_normalizar_nome(nome))
        if alvo:
            mapa[idx] = alvo
        elif nome.strip():
            desconhecidas.append(nome.strip())
    return mapa, desconhecidas


def _celula(campos: list[str], idx: int) -> str:
    return _desescapar(campos[idx].strip()) if idx < len(campos) else ""


def _ate(bruto: str):
    t = bruto.strip()
    if not t:
        return None
    if t.isdigit():
        return int(t)
    if any(ch.isdigit() for ch in t) and _normalizar_nome(t).startswith("acima"):
        return None  # "acima de 200" = aberto à direita (N-01)
    return _INVALIDO


def _tipo_efeito(bruto: str) -> TipoEfeito:
    n = _normalizar_nome(bruto)
    if n in ("descontopct", "desconto", "descontopercentual", "pct"):
        return TipoEfeito.DESCONTO_PCT
    return TipoEfeito.PRECO_UNITARIO


def _inteiro(bruto: str, padrao: int) -> int:
    t = bruto.strip()
    return int(t) if t.lstrip("-").isdigit() else padrao


def _data(bruto: str, padrao):
    t = bruto.strip()
    if not t:
        return padrao
    try:
        return date.fromisoformat(t)
    except ValueError:
        return padrao
