"""M-05 `validador-coerencia` — o portão que a planilha não tem.

Ataca a dor #2 da Fase 0 (erros silenciosos). I-6: incoerência é barrada AQUI,
na validação, NUNCA em runtime.

Regra de colisão especificada em V(2)/IMP-02: duas regras colidem quando
escopo, faixa e vigência se interceptam E prioridade e especificidade empatam
— ou seja, exatamente quando `resolvedor-precedencia` levantaria
`EmpateInsoluvel`. O conflito real do domínio é ENTRE escopos (`*` vs SKU),
não só dentro do mesmo escopo.

Lacuna de cobertura é AVISO, não bloqueio (AMB-5, decisão do operador na
Fase 0): lacuna é frequentemente intencional, e em runtime cai no preço base.

KISS: uma lista de funções de checagem. Chain of Responsibility foi
explicitamente rejeitado na Fase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .modelo_dominio import ESCOPO_GERAL, Produto, Regra


@dataclass(frozen=True, slots=True)
class Erro:
    tipo: str
    descricao: str
    regra_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Aviso:
    tipo: str
    descricao: str
    sku: str | None = None


@dataclass(slots=True)
class Relatorio:
    erros: list[Erro] = field(default_factory=list)
    avisos: list[Aviso] = field(default_factory=list)

    @property
    def bloqueia_publicacao(self) -> bool:
        return bool(self.erros)


def validar(
    regras: list[Regra],
    produtos: dict[str, Produto],
    conflitos_base: list | None = None,
) -> Relatorio:
    """`conflitos_base` é evidência bruta vinda de `importador-csv` (V-04).

    Arbitragem do operador na Fase 5: a detecção do preço base divergente fica
    onde o dado bruto está, mas a DECISÃO de bloquear a publicação é daqui —
    porque rejeitar a linha na importação faria o sistema escolher em silêncio
    um dos dois preços base e publicar assim mesmo.
    """
    rel = Relatorio()
    _checar_escopo_existente(regras, produtos, rel)
    _checar_colisoes(regras, rel)
    _checar_preco_base(conflitos_base or [], regras, rel)
    _checar_lacunas(regras, produtos, rel)
    return rel


def _checar_preco_base(conflitos, regras: list[Regra], rel: Relatorio) -> None:
    """O conflito só bloqueia enquanto for RELEVANTE.

    DEFEITO CORRIGIDO NA FASE 6: a evidência de preço base divergente descreve
    um fato sobre o ARQUIVO IMPORTADO, mas estava sendo aplicada como restrição
    sobre o ESTADO ATUAL do rascunho. Os dois divergem assim que o analista
    edita — e o operador excluiu todas as regras do SKU em conflito, o que é a
    tentativa óbvia e correta, sem que o bloqueio jamais cedesse. Onze
    tentativas sem saída. Um fato histórico não pode ser uma restrição eterna.
    """
    escopos_ativos = {r.escopo for r in regras}
    for c in conflitos:
        if c.sku not in escopos_ativos:
            # Sem regra alguma para este SKU, o preço base dele não é usado
            # por ninguém — o conflito deixou de ter consequência.
            continue
        rel.erros.append(
            Erro(
                tipo="preco_base_inconsistente",
                descricao=(
                    f"preço base de {c.sku} aparece como "
                    + " e ".join(c.valores)
                    + " (linhas "
                    + ", ".join(str(x) for x in c.linhas)
                    + ") — o sistema não pode escolher por você. "
                    "Excluir regras NÃO resolve: corrija o preço base na "
                    f"planilha e reimporte, ou remova todas as regras de {c.sku}."
                ),
            )
        )


def _checar_escopo_existente(
    regras: list[Regra], produtos: dict[str, Produto], rel: Relatorio
) -> None:
    for r in regras:
        if r.escopo != ESCOPO_GERAL and r.escopo not in produtos:
            rel.erros.append(
                Erro(
                    tipo="sku_inexistente",
                    descricao=f"regra {r.id} aponta para SKU inexistente no catálogo: {r.escopo}",
                    regra_ids=(r.id,),
                )
            )


def _checar_colisoes(regras: list[Regra], rel: Relatorio) -> None:
    """Colisão = mesma prioridade E mesma especificidade E interseção tripla.

    O par é reportado com o INTERVALO em que colide — "as regras X e Y colidem"
    sem dizer onde é um aviso que o analista não consegue agir.
    """
    for i, a in enumerate(regras):
        for b in regras[i + 1 :]:
            if a.prioridade != b.prioridade:
                continue
            if a.e_especifica != b.e_especifica:
                continue  # a especificidade desempata — não é colisão
            if a.e_especifica and a.escopo != b.escopo:
                continue  # SKUs diferentes nunca competem
            if not a.faixa.sobrepoe(b.faixa):
                continue
            if not a.vigencia.sobrepoe(b.vigencia):
                continue
            rel.erros.append(
                Erro(
                    tipo="colisao",
                    descricao=(
                        f"regras {a.id} e {b.id} colidem no intervalo "
                        f"{_intersecao(a, b)} (prioridade {a.prioridade}, "
                        "mesma especificidade) — empate insolúvel em runtime"
                    ),
                    regra_ids=(a.id, b.id),
                )
            )


def _intersecao(a: Regra, b: Regra) -> str:
    inicio = max(a.faixa.minimo, b.faixa.minimo)
    fins = [f for f in (a.faixa.maximo, b.faixa.maximo) if f is not None]
    fim = min(fins) if len(fins) == 2 else (fins[0] if fins else None)
    return f"{inicio}–{fim if fim is not None else '∞'} un"


def _checar_lacunas(
    regras: list[Regra], produtos: dict[str, Produto], rel: Relatorio
) -> None:
    """AVISO, nunca bloqueio (AMB-5). Reporta o intervalo descoberto.

    Só considera regras de SKU: uma regra `*` cobre todos os produtos e
    tornaria a checagem de lacuna por produto sem sentido.
    """
    if any(r.escopo == ESCOPO_GERAL for r in regras):
        return
    for sku in sorted(produtos):
        faixas = sorted(
            (r.faixa for r in regras if r.escopo == sku),
            key=lambda f: f.minimo,
        )
        if not faixas:
            continue
        buracos: list[str] = []
        if faixas[0].minimo > 1:
            buracos.append(f"1–{faixas[0].minimo - 1}")
        cursor = faixas[0].maximo
        for f in faixas[1:]:
            if cursor is None:
                break
            if f.minimo > cursor + 1:
                buracos.append(f"{cursor + 1}–{f.minimo - 1}")
            cursor = None if f.maximo is None else max(cursor, f.maximo)
        if cursor is not None:
            buracos.append(f"{cursor + 1}+")
        if buracos:
            rel.avisos.append(
                Aviso(
                    tipo="lacuna",
                    sku=sku,
                    descricao=(
                        f"{sku} sem cobertura para {', '.join(buracos)} un — "
                        "cairá no preço base"
                    ),
                )
            )
