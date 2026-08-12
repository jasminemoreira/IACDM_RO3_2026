"""T22 — distribuidor de plantões com restrições, trocas entre pessoas e aprovação.

Arquitetura hexagonal, 11 módulos (specs/technical/architecture.md, seção V(3)).
Núcleo puro: dominio, restricoes_legais, restricoes_modelo, avaliador, troca.
Adaptadores: solver_cpsat, repositorio_json, carregador, cli.
"""

__version__ = "1.0.0"
