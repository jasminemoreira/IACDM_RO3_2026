"""M-06 matcher — geração de candidatos por blocking + score por rubrica.

Núcleo puro: não importa sqlite3 nem csv. Usa rapidfuzz (S6 Tier 1, aprovado na
Fase 1) apenas para similaridade de string.

TODOS os pesos e cortes vêm de specs/technical/rubrica-score.md e
specs/technical/parametros-matching.md. Nenhuma constante aqui sem linha lá —
essa é a regra que existe contra o AP7.

Decisões de V(3) materializadas:
  - RUBRICA determinística no lugar da estimação de m/u de Fellegi-Sunter
    (SCI-06: calibrar contra ground truth sintético desenhado pelo próprio
    projeto é validação circular). Fellegi-Sunter segue em specs/references como
    fundamentação do desenho, não como algoritmo implementado.
  - Escala do score FIXADA: inteiro 0..100, CRESCENTE (LIN-03). Devolver
    distância normalizada satisfaria um contrato `float` e inverteria todas as
    decisões de fusão.
  - Excedente de bloco vira PENDÊNCIA, nunca é separado por refino silencioso
    (PRF-06). Precedência declarada: corretude (VAL-1, VAL-2) vence desempenho
    (VAL-4). Um par jamais é declarado distinto sem ninguém ter olhado.
  - Perfis de comparação VERSIONADOS (MEC-05): dois perfis de conteúdo diferente
    não circulam com o mesmo par (nome, versao).
  - MetricasBloco devolvida para o cli persistir (OBS-05) — a métrica que revela
    bloco degenerado não pode ser produzida e descartada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable, Sequence

from rapidfuzz.distance import JaroWinkler

from t26.domain.model import Lancamento, Transacao

#: Teto de itens por bloco. Acima disso o bloco é degenerado (tarifas de valor
#: redondo repetido) e o excedente vai para pendência em vez de ser comparado
#: exaustivamente — O(b²) dentro do bloco é o que estoura VAL-4.
#: Alvo de b <= 50 em specs/technical/parametros-matching.md §Orçamento.
TETO_BLOCO = 50

#: specs/technical/parametros-matching.md — P3, P4, P5
CORTE_FUSAO = 95  # P3: >= auto-concilia / funde sem revisão
CORTE_REVISAO = 70  # P5: < isto, não casa; entre P5 e P3, revisão humana

#: specs/technical/rubrica-score.md §1 — cortes de similaridade de contraparte
SIM_ALTA = 90
SIM_MEDIA = 70

#: specs/technical/rubrica-score.md §2 — janela por instrumento, em dias
JANELA_POR_INSTRUMENTO = {
    "pix": 0,
    "ted": 1,
    "boleto": 1,
    "cartao": 32,
    "desconhecido": 3,
}

VETO = -100

#: Piso quando valor e data coincidem exatamente: o par vai no mínimo para
#: revisão humana, nunca para "distintas" (VAL-1, zero falso negativo).
PISO_EVIDENCIA_FORTE = CORTE_REVISAO


@dataclass(frozen=True)
class PerfilComparacao:
    """Rubrica versionada. MEC-05: a versão vai para a trilha e o relatório."""

    nome: str
    versao: str


PERFIL_DEDUP = PerfilComparacao("dedup", "1")
PERFIL_CONCILIACAO = PerfilComparacao("conciliacao", "1")


@dataclass
class MetricasBloco:
    """OBS-05 — o que permite diagnosticar bloco degenerado sem mudar código."""

    blocos: int = 0
    maior_bloco: int = 0
    itens: int = 0
    pares_avaliados: int = 0
    excedentes: int = 0
    blocos_degenerados: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Par:
    esquerda: object
    direita: object
    bloco: str


@dataclass(frozen=True)
class Excedente:
    """Item que não coube no teto do bloco. NÃO é 'distinto' — é pendência.

    PRF-06: separar silenciosamente por refino de chave trocaria um falso
    negativo por desempenho, e VAL-1 exige zero falso negativo.
    """

    item: object
    bloco: str
    tamanho_bloco: int


def chave_bloco(item: Transacao | Lancamento) -> str:
    """Chave de blocking: valor absoluto exato.

    A data NÃO entra na chave porque a janela de tolerância (±1 a ±32 dias
    conforme o instrumento) faria o mesmo evento cair em blocos diferentes nas
    bordas — o que produziria falso negativo, o defeito que VAL-1 proíbe. O
    filtro de data é aplicado na rubrica, não no bloco.

    A7 (limitação conhecida): agrupar por valor ABSOLUTO coloca o estorno no
    mesmo bloco da transação original. A rubrica veta a fusão por sinal oposto,
    mas o inchaço de bloco permanece — a ser medido na Fase 6, não presumido.
    """
    return f"{item.conta}|{item.valor.absoluto()}"


def chave_bloco_cross_source(item: Transacao | Lancamento) -> str:
    """Bloco sem a conta, para duplicata cross-source entre contas distintas."""
    return f"*|{item.valor.absoluto()}"


#: Indexação por DISJUNÇÃO — a união de múltiplos blocos
#: (specs/references/fontes-externas.md §2.2). Uma chave só, incluindo a conta,
#: impediria estruturalmente a detecção de duplicata cross-source entre contas,
#: que é requisito da Fase 0: o par simplesmente nunca seria gerado.
CHAVES_BLOCO = (chave_bloco, chave_bloco_cross_source)


def candidatos(
    itens: Sequence[Transacao | Lancamento],
    existentes: Sequence[Transacao | Lancamento] = (),
    teto: int = TETO_BLOCO,
    chaves=CHAVES_BLOCO,
) -> tuple[list[Par], list[Excedente], MetricasBloco]:
    """Agrupa por bloco (disjunção de chaves) e devolve pares, excedentes e métricas.

    Quando `existentes` é vazio, compara `itens` contra si mesmos (dedup dentro
    do lote). Caso contrário, cada item novo é comparado com os existentes que
    caem em algum dos seus blocos.

    Pares repetidos entre chaves são unidos uma única vez: a disjunção amplia a
    cobertura sem multiplicar o custo de comparação.
    """
    metricas = MetricasBloco(itens=len(itens))
    pares: list[Par] = []
    excedentes: list[Excedente] = []
    vistos: set[tuple[str, str]] = set()
    # A disjunção emite o mesmo item em mais de uma chave; excedentes precisam
    # da mesma deduplicação por identidade que já protege os pares, ou a fila de
    # revisão infla proporcionalmente ao número de chaves.
    excedentes_vistos: set[str] = set()
    blocos_totais: set[str] = set()

    for chave_de in chaves:
        grupos: dict[str, list] = {}
        for item in existentes or itens:
            grupos.setdefault(chave_de(item), []).append(item)
        blocos_totais.update(grupos)
        metricas.maior_bloco = max(
            [metricas.maior_bloco] + [len(v) for v in grupos.values()]
        )

        if existentes:
            for novo in itens:
                bloco = chave_de(novo)
                grupo = grupos.get(bloco, [])
                if len(grupo) > teto:
                    if novo.chave.texto() not in excedentes_vistos:
                        excedentes_vistos.add(novo.chave.texto())
                        excedentes.append(Excedente(novo, bloco, len(grupo)))
                    if bloco not in metricas.blocos_degenerados:
                        metricas.blocos_degenerados.append(bloco)
                    continue
                for outro in grupo:
                    marca = _marca(novo, outro)
                    if marca in vistos:
                        continue
                    vistos.add(marca)
                    pares.append(Par(novo, outro, bloco))
                    metricas.pares_avaliados += 1
            continue

        for bloco, grupo in grupos.items():
            if len(grupo) > teto:
                if bloco not in metricas.blocos_degenerados:
                    metricas.blocos_degenerados.append(bloco)
                for item in grupo:
                    if item.chave.texto() in excedentes_vistos:
                        continue
                    excedentes_vistos.add(item.chave.texto())
                    excedentes.append(Excedente(item, bloco, len(grupo)))
                continue
            for i in range(len(grupo)):
                for j in range(i + 1, len(grupo)):
                    marca = _marca(grupo[i], grupo[j])
                    if marca in vistos:
                        continue
                    vistos.add(marca)
                    pares.append(Par(grupo[i], grupo[j], bloco))
                    metricas.pares_avaliados += 1

    metricas.blocos = len(blocos_totais)
    metricas.excedentes = len(excedentes)
    return pares, excedentes, metricas


def _marca(a, b) -> tuple[str, str]:
    x, y = a.chave.texto(), b.chave.texto()
    return (x, y) if x <= y else (y, x)


def similaridade(a: str, b: str) -> int:
    """Jaro-Winkler em 0..100. specs/technical/rubrica-score.md §1 (campo contraparte)."""
    if not a or not b:
        return -1  # ausente: não é evidência a favor nem contra
    return int(round(JaroWinkler.similarity(a, b) * 100))


def score(par: Par, perfil: PerfilComparacao = PERFIL_DEDUP) -> int:
    """Aplica a rubrica declarada. Escala 0..100, crescente (LIN-03)."""
    if perfil.nome == "dedup":
        bruto = _score_dedup(par.esquerda, par.direita)
    elif perfil.nome == "conciliacao":
        bruto = _score_conciliacao(par.esquerda, par.direita)
    else:
        raise ValueError(f"perfil de comparação desconhecido: {perfil.nome}")
    return max(0, min(100, bruto))


def mesma_origem(a, b) -> bool:
    """Duas observações reportadas separadamente pelo MESMO arquivo da mesma fonte.

    Se a instituição imprimiu duas linhas, houve dois eventos: é a colisão
    legítima que I6 manda preservar. A reimportação da mesma linha tem
    ChaveNatural IDÊNTICA e é capturada em L2, sem nunca chegar ao score — logo
    este veto não pode mascarar uma duplicata de reimportação.
    """
    return (
        a.fonte == b.fonte
        and a.conta == b.conta
        and a.arquivo == b.arquivo
        and a.chave != b.chave
    )


def _score_dedup(a, b) -> int:
    """Rubrica `dedup` — specs/technical/rubrica-score.md §1, tabela 1."""
    # I6 / VAL-2 — veto de mesma origem. Nenhuma rubrica sobre ATRIBUTOS
    # distingue os dois cafés de R$ 12,00 do mesmo dia, porque a diferença não
    # está nos atributos: está em a fonte tê-los reportado separadamente.
    if mesma_origem(a, b):
        return VETO

    if a.valor.valor != b.valor.valor:
        if a.valor.absoluto() == b.valor.absoluto() and a.valor.sinal != b.valor.sinal:
            return VETO  # estorno: sinais opostos, mitigação de A7
        return VETO  # valor diferente: não é o mesmo evento
    pontos = 40

    dias = abs((a.data - b.data).days)
    if dias == 0:
        pontos += 25
    elif dias <= 3:
        pontos += 12
    else:
        pontos -= 40

    sim = similaridade(a.descricao_normalizada(), b.descricao_normalizada())
    if sim < 0:
        pontos += 0  # ausente não penaliza (A6)
    elif sim >= SIM_ALTA:
        pontos += 25
    elif sim >= SIM_MEDIA:
        pontos += 10

    if a.conta == b.conta:
        pontos += 10

    # VAL-1 — piso de evidência forte. Valor idêntico e mesma data é evidência
    # forte demais para descartar sem revisão só porque as fontes escrevem a
    # contraparte de formas diferentes (A6). O par vira PENDÊNCIA, nunca
    # "distintas": a precedência declarada em V(3) é corretude sobre desempenho.
    if a.valor.valor == b.valor.valor and dias == 0:
        pontos = max(pontos, PISO_EVIDENCIA_FORTE)

    return pontos


def _score_conciliacao(transacao, lancamento, tolerancia: Decimal = Decimal("0")) -> int:
    """Rubrica `conciliacao` — specs/technical/rubrica-score.md §1, tabela 2."""
    pontos = 0

    delta = abs(transacao.valor.valor - lancamento.valor.valor)
    if delta == 0:
        pontos += 50
    elif delta <= tolerancia:
        pontos += 30
    else:
        return VETO

    janela = JANELA_POR_INSTRUMENTO.get(
        transacao.instrumento.value, JANELA_POR_INSTRUMENTO["desconhecido"]
    )
    dias = abs((transacao.data - lancamento.data).days)
    if dias <= janela:
        pontos += 30
    else:
        pontos -= 40

    sim = similaridade(
        transacao.descricao_normalizada(), lancamento.descricao_normalizada()
    )
    if sim >= SIM_MEDIA:
        pontos += 20

    return pontos


def score_conciliacao(transacao, lancamento, tolerancia: Decimal = Decimal("0")) -> int:
    """Variante que aceita a tolerância de valor configurada pelo operador (P2)."""
    return max(0, min(100, _score_conciliacao(transacao, lancamento, tolerancia)))


def janela_do_instrumento(instrumento: str) -> int:
    return JANELA_POR_INSTRUMENTO.get(instrumento, JANELA_POR_INSTRUMENTO["desconhecido"])
