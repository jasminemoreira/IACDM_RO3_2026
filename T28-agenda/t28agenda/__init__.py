"""T28-agenda — sincronizador bidirecional de calendarios.

Arquitetura: Hexagonal (Ports & Adapters), V(4) em specs/technical/architecture.md.
Nucleo puro (sem I/O): canonical_event, recurrence, normalizer, reconciler,
policies, conflict_queue, overlap_detector.
Adaptadores: providers/*, repository, cli.
"""

__version__ = "1.0.0"
