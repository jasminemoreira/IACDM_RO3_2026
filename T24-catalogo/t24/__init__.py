"""T24 — catalogo de dados com donos declarados por dominio e linhagem entre eles.

Arquitetura V(3), 9 modulos (ver specs/technical/architecture.md):

  nucleo puro  : model, catalog, lineage_graph, validation, query_service
  bordas       : yaml_loader, catalog_mapper, formatters, cli

Regra de dependencia: borda -> nucleo, nunca o inverso.
"""

__version__ = "0.1.0"
