"""Coordenador de implantação canário com rollback automático por métrica.

Arquitetura V(3) — ver specs/technical/architecture.md.
12 módulos, hexagonal, núcleo de decisão puro, monothread determinístico.
"""

__all__ = [
    "alvo_de_implantacao",
    "configuracao",
    "contadores",
    "coordenador",
    "fonte_de_metricas",
    "guarda_absoluta",
    "janela",
    "julgamento",
    "relogio",
    "score",
    "simulador_de_cenario",
]
