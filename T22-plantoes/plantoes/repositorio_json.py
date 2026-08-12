"""M-08 repositorio-json — dono do artefato único `snapshot + eventos`.

E1 (V(3)): o módulo `diario` foi eliminado e o histórico passou a viver dentro
do arquivo da escala. Consequências, cada uma resolvendo um crítico:

- **LIN-05** — a ordem dos eventos é a POSIÇÃO na lista JSON. O carimbo de
  tempo é informativo e nunca ordena.
- **RES-04** — não existe append parcial: o arquivo inteiro é escrito num
  temporário e renomeado (`os.replace` é atômico no mesmo sistema de arquivos).
  Interrupção deixa o arquivo anterior intacto.
- **ARQ-05** — `carregar_escala` devolve a escala VIGENTE. O snapshot cru não é
  exposto; não há como chamar a leitura errada por engano.

SEC-03: o id vira nome de arquivo e é sanitizado — `../` não escapa do
diretório de dados.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, time
from pathlib import Path

from .dominio import (
    Alocacao,
    Escala,
    EstadoEscala,
    EstadoTroca,
    Evento,
    TipoEvento,
)
from .troca import Troca

ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
LIMITE_BYTES = 20 * 1024 * 1024  # SEC-02


class ErroDeRepositorio(Exception):
    pass


def _sanitizar(id_: str) -> str:
    if not ID_VALIDO.match(id_):
        raise ErroDeRepositorio(
            f"id inválido: '{id_}'. Use apenas letras, dígitos, ponto, hífen e "
            "sublinhado (até 64 caracteres)."
        )
    return id_


def _escrever_atomico(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, caminho)  # atômico


def _ler(caminho: Path) -> dict:
    """Lê um arquivo de dados do próprio sistema.

    D-01 (encontrado no teste exploratório da Fase 6): estes arquivos podem ter
    sido editados à mão, truncados por uma interrupção ou corrompidos no disco.
    Deixar o JSONDecodeError escapar produzia traceback bruto — o modo de falha
    exato que o achado RES-03 identificou e que o design declarou resolvido.
    O `carregador` já tratava a instância de entrada; faltava tratar o que o
    sistema grava.
    """
    if caminho.stat().st_size > LIMITE_BYTES:
        raise ErroDeRepositorio(
            f"arquivo '{caminho.name}' excede {LIMITE_BYTES // (1024 * 1024)} MB"
        )
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErroDeRepositorio(
            f"o arquivo '{caminho.name}' está corrompido: JSON inválido na "
            f"linha {e.lineno}, coluna {e.colno} ({e.msg}). Ele foi gravado "
            "pelo próprio sistema — se foi editado à mão, restaure a versão "
            "anterior."
        ) from None
    except UnicodeDecodeError:
        raise ErroDeRepositorio(
            f"o arquivo '{caminho.name}' não está em UTF-8 e não pode ser lido."
        ) from None


class Repositorio:
    def __init__(self, diretorio: str | Path = "dados"):
        self.dir = Path(diretorio)

    # ---------------- escala ----------------

    def _caminho_escala(self, escala_id: str) -> Path:
        return self.dir / f"escala_{_sanitizar(escala_id)}.json"

    def existe(self, escala_id: str) -> bool:
        return self._caminho_escala(escala_id).exists()

    def salvar_escala(self, escala: Escala) -> None:
        _escrever_atomico(self._caminho_escala(escala.id), _escala_para_json(escala))

    def _carregar(self, escala_id: str) -> Escala:
        caminho = self._caminho_escala(escala_id)
        if not caminho.exists():
            raise ErroDeRepositorio(
                f"escala '{escala_id}' não encontrada em {self.dir}/"
            )
        dados = _ler(caminho)
        try:
            return _escala_de_json(dados)
        except (KeyError, TypeError, ValueError) as e:
            # D-01: JSON sintaticamente válido mas com forma errada — mesmo
            # motivo, mesmo tratamento: erro explicado, nunca traceback.
            raise ErroDeRepositorio(
                f"o arquivo '{caminho.name}' tem JSON válido mas estrutura "
                f"inesperada ({type(e).__name__}: {e}). Ele foi gravado pelo "
                "próprio sistema — se foi editado à mão, restaure a versão "
                "anterior."
            ) from None

    def carregar_escala(self, escala_id: str) -> Escala:
        """Devolve a escala VIGENTE (snapshot + eventos aplicados)."""
        return self._carregar(escala_id).vigente()

    def carregar_bruta(self, escala_id: str) -> Escala:
        """Uso interno: snapshot + eventos sem aplicar. Necessário para anexar
        evento sem reescrever o histórico."""
        return self._carregar(escala_id)

    def proximo_id_de_regeracao(self, escala_id: str) -> str:
        """B-01: `--force` não sobrescreve — gera uma escala NOVA, como V(3)
        especifica. A anterior continua existindo e imutável, e as trocas que
        a referenciam continuam apontando para um artefato real."""
        n = 1
        while self.existe(f"{escala_id}-r{n}"):
            n += 1
        return f"{escala_id}-r{n}"

    def anexar_evento(self, escala_id: str, evento: Evento) -> None:
        bruta = self.carregar_bruta(escala_id)
        from dataclasses import replace

        atualizada = replace(bruta, eventos=bruta.eventos + (evento,))
        self.salvar_escala(atualizada)

    def listar_escalas(self) -> list[str]:
        if not self.dir.exists():
            return []
        return sorted(
            p.stem[len("escala_") :]
            for p in self.dir.glob("escala_*.json")
        )

    # ---------------- trocas ----------------

    @property
    def _caminho_trocas(self) -> Path:
        return self.dir / "trocas.json"

    def listar_trocas(self) -> list[Troca]:
        if not self._caminho_trocas.exists():
            return []
        return [_troca_de_json(t) for t in _ler(self._caminho_trocas)]

    def salvar_trocas(self, trocas: list[Troca]) -> None:
        _escrever_atomico(
            self._caminho_trocas, [_troca_para_json(t) for t in trocas]
        )

    def salvar_troca(self, troca: Troca) -> None:
        trocas = [t for t in self.listar_trocas() if t.id != troca.id]
        trocas.append(troca)
        self.salvar_trocas(sorted(trocas, key=lambda t: t.id))


# --------------------------------------------------------------------------
# Serialização
# --------------------------------------------------------------------------


def _escala_para_json(e: Escala) -> dict:
    return {
        "id": e.id,
        "inicio": e.inicio.isoformat(),
        "fim": e.fim.isoformat(),
        "estado_escala": e.estado_escala.value,
        "status_solver": e.status_solver,
        "otimalidade_provada": e.otimalidade_provada,
        "custo": e.custo,
        "custo_por_restricao": e.custo_por_restricao,
        "snapshot_publicado": [
            {"pessoa_id": a.pessoa_id, "plantao_id": a.plantao_id}
            for a in e.alocacoes
        ],
        "eventos": [
            {
                "tipo": ev.tipo.value,
                "quem": ev.quem,
                "quando": ev.quando,
                "dados": ev.dados,
            }
            for ev in e.eventos
        ],
    }


def _escala_de_json(d: dict) -> Escala:
    return Escala(
        id=d["id"],
        inicio=date.fromisoformat(d["inicio"]),
        fim=date.fromisoformat(d["fim"]),
        estado_escala=EstadoEscala(d["estado_escala"]),
        alocacoes=tuple(
            Alocacao(a["pessoa_id"], a["plantao_id"]) for a in d["snapshot_publicado"]
        ),
        eventos=tuple(
            Evento(TipoEvento(ev["tipo"]), ev["quem"], ev["quando"], ev["dados"])
            for ev in d.get("eventos", [])
        ),
        status_solver=d.get("status_solver", ""),
        otimalidade_provada=d.get("otimalidade_provada", False),
        custo=d.get("custo", 0),
        custo_por_restricao=d.get("custo_por_restricao", {}),
    )


def _troca_para_json(t: Troca) -> dict:
    return {
        "id": t.id,
        "escala_id": t.escala_id,
        "solicitante_id": t.solicitante_id,
        "destinatario_id": t.destinatario_id,
        "plantao_do_solicitante_id": t.plantao_do_solicitante_id,
        "plantao_do_destinatario_id": t.plantao_do_destinatario_id,
        "estado_troca": t.estado_troca.value,
        "criada_em": t.criada_em,
        "decidida_em": t.decidida_em,
        "motivo": t.motivo,
    }


def _troca_de_json(d: dict) -> Troca:
    return Troca(
        id=d["id"],
        escala_id=d["escala_id"],
        solicitante_id=d["solicitante_id"],
        destinatario_id=d["destinatario_id"],
        plantao_do_solicitante_id=d["plantao_do_solicitante_id"],
        plantao_do_destinatario_id=d["plantao_do_destinatario_id"],
        estado_troca=EstadoTroca(d["estado_troca"]),
        criada_em=d.get("criada_em", ""),
        decidida_em=d.get("decidida_em", ""),
        motivo=d.get("motivo", ""),
    )
