"""M-04 guarda-absoluta — piso de segurança. FUNÇÃO PURA.

Razão de existir: o teste estatístico exige >=50 pontos por métrica antes de
decidir qualquer coisa (R-03/R-05). Um canário retornando erro em toda
requisição não pode sobreviver aguardando significância estatística. São duas
classes de falha com urgências diferentes — regressão sutil (estatística) e
falha catastrófica (imediata) — e só a segunda justifica curto-circuito.

⚠️ ESTE É O ÚNICO MÓDULO DO SISTEMA CUJOS NÚMEROS NÃO TÊM FONTE BIBLIOGRÁFICA.
Achado SCI-01, atravessou as duas iterações do laço 2-3 sem ser resolvido e está
registrado como RISCO ACEITO. Os limiares são parâmetro OBRIGATÓRIO do operador,
sem valor padrão, e são impressos na saída. Isso melhora a atribuição, não a
fundamentação — e a distinção está declarada em vez de escondida.
"""

from __future__ import annotations

from .alvo_de_implantacao import Papel
from .configuracao import Configuracao
from .janela import Janela
from .julgamento import LATENCIA_P99_SUCESSO, TAXA_DE_ERRO


def dispara(janela: Janela, cfg: Configuracao) -> str | None:
    """Devolve o motivo do rollback imediato, ou None.

    Consultada ANTES da checagem de amostra suficiente — é exatamente aí que
    ela se paga.
    """
    erros = janela.series(Papel.CANARIO, TAXA_DE_ERRO.nome)
    if erros:
        media = sum(erros) / len(erros)
        if media >= cfg.guarda_taxa_erro:
            return (
                f"guarda absoluta: taxa de erro do canário em {media:.3f} "
                f">= limiar {cfg.guarda_taxa_erro:.3f}"
            )

    latencias = janela.series(Papel.CANARIO, LATENCIA_P99_SUCESSO.nome)
    if latencias:
        media = sum(latencias) / len(latencias)
        if media >= cfg.guarda_latencia_p99:
            return (
                f"guarda absoluta: latência p99 do canário em {media:.1f}ms "
                f">= limiar {cfg.guarda_latencia_p99:.1f}ms"
            )

    return None
