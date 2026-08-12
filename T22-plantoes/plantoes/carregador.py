"""M-09 carregador — parse e validação da instância de entrada.

Validações que moram aqui por decisão de arquitetura:
- **L4 (CLT art. 59)** é validação de CONFIGURAÇÃO, não restrição de alocação:
  um plantão de 12h num contrato de regime comum é ilegal independentemente de
  quem for alocado. No solver produziria INFEASIBLE mudo; aqui falha cedo
  citando o artigo.
- **SEC-02**: limite de tamanho antes de qualquer parse.
- **RES-03**: erro por campo, com o caminho do campo na mensagem — nunca
  stacktrace bruto no rosto do plantonista.
"""

from __future__ import annotations

from datetime import date, time
from pathlib import Path

import json

from . import restricoes_legais, restricoes_modelo
from .dominio import (
    Contrato,
    Habilitacao,
    Instancia,
    Natureza,
    Pessoa,
    Plantao,
    Preferencia,
    Regime,
    RegraInterna,
    TipoDeTurno,
    TipoPreferencia,
)

LIMITE_BYTES = 20 * 1024 * 1024  # SEC-02
LIMITE_PLANTOES = 20_000
LIMITE_PESSOAS = 2_000


class ErroDeValidacao(Exception):
    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__("\n".join(f"  - {e}" for e in erros))


def _exigir(d: dict, campo: str, onde: str, erros: list[str], tipo=None):
    if campo not in d:
        erros.append(f"{onde}: campo obrigatório '{campo}' ausente")
        return None
    valor = d[campo]
    if tipo is not None and not isinstance(valor, tipo):
        erros.append(
            f"{onde}.{campo}: esperado {tipo.__name__}, veio "
            f"{type(valor).__name__}"
        )
        return None
    return valor


def _hora(texto: str, onde: str, erros: list[str]) -> time | None:
    try:
        h, m = texto.split(":")
        return time(int(h), int(m))
    except Exception:
        erros.append(f"{onde}: hora inválida '{texto}' (esperado HH:MM)")
        return None


def _data(texto: str, onde: str, erros: list[str]) -> date | None:
    try:
        return date.fromisoformat(texto)
    except Exception:
        erros.append(f"{onde}: data inválida '{texto}' (esperado AAAA-MM-DD)")
        return None


def carregar(caminho: str | Path) -> Instancia:
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroDeValidacao([f"arquivo não encontrado: {caminho}"])
    if caminho.stat().st_size > LIMITE_BYTES:
        raise ErroDeValidacao(
            [
                f"arquivo excede {LIMITE_BYTES // (1024*1024)} MB — recusado "
                "antes do parse"
            ]
        )
    try:
        d = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErroDeValidacao(
            [f"JSON malformado na linha {e.lineno}, coluna {e.colno}: {e.msg}"]
        ) from None

    erros: list[str] = []
    return _construir(d, erros)


def carregar_dict(d: dict) -> Instancia:
    return _construir(d, [])


def _construir(d: dict, erros: list[str]) -> Instancia:
    periodo = _exigir(d, "periodo", "raiz", erros, dict) or {}
    inicio = _data(periodo.get("inicio", ""), "periodo.inicio", erros)
    fim = _data(periodo.get("fim", ""), "periodo.fim", erros)
    if inicio and fim and fim < inicio:
        erros.append("periodo: fim é anterior ao início")

    habilitacoes = tuple(
        Habilitacao(h["id"], h.get("nome", h["id"]))
        for h in d.get("habilitacoes", [])
    )

    tipos = []
    for i, t in enumerate(d.get("tipos_de_turno", [])):
        onde = f"tipos_de_turno[{i}]"
        ini = _hora(t.get("inicio", ""), f"{onde}.inicio", erros)
        f = _hora(t.get("fim", ""), f"{onde}.fim", erros)
        if ini and f:
            vira = t.get("vira_o_dia")
            if vira is None:  # LIN-03: explícito, mas com padrão declarado
                vira = f <= ini
            tipos.append(
                TipoDeTurno(t["id"], t.get("nome", t["id"]), ini, f, bool(vira))
            )

    contratos = []
    for i, c in enumerate(d.get("contratos", [])):
        onde = f"contratos[{i}]"
        try:
            regime = Regime(c.get("regime", "comum"))
        except ValueError:
            erros.append(
                f"{onde}.regime: '{c.get('regime')}' inválido "
                "(use 'comum' ou '12x36')"
            )
            continue
        contratos.append(
            Contrato(
                id=c["id"],
                regime=regime,
                min_plantoes=c.get("min_plantoes", 0),
                max_plantoes=c.get("max_plantoes", 31),
                max_dias_consecutivos=c.get("max_dias_consecutivos", 2),
                min_dias_consecutivos=c.get("min_dias_consecutivos", 1),
                min_folgas_consecutivas=c.get("min_folgas_consecutivas", 1),
                max_fins_de_semana=c.get("max_fins_de_semana", 3),
                exige_fim_de_semana_completo=c.get(
                    "exige_fim_de_semana_completo", False
                ),
                horizonte_meses=c.get("horizonte_meses", 1),
            )
        )

    pessoas = tuple(
        Pessoa(
            p["id"],
            p.get("nome", p["id"]),
            p["contrato_id"],
            tuple(p.get("habilitacoes", [])),
        )
        for p in d.get("pessoas", [])
    )

    plantoes = []
    for i, p in enumerate(d.get("plantoes", [])):
        onde = f"plantoes[{i}]"
        dt = _data(p.get("data", ""), f"{onde}.data", erros)
        if dt:
            plantoes.append(
                Plantao(
                    id=p["id"],
                    data=dt,
                    tipo_de_turno_id=p["tipo_de_turno_id"],
                    habilitacao_id=p["habilitacao_id"],
                    demanda_minima=p.get("demanda_minima", 1),
                    demanda_otima=p.get("demanda_otima", p.get("demanda_minima", 1)),
                )
            )

    preferencias = []
    for i, p in enumerate(d.get("preferencias", [])):
        onde = f"preferencias[{i}]"
        if "plantao_id" in p:
            erros.append(
                f"{onde}: use 'data' (e opcionalmente 'tipo_de_turno_id'); "
                "'plantao_id' não é aceito — há uma única forma de declarar "
                "preferência"
            )
            continue
        dt = _data(p.get("data", ""), f"{onde}.data", erros)
        try:
            tipo = TipoPreferencia(p.get("tipo", "indesejado"))
        except ValueError:
            erros.append(
                f"{onde}.tipo: '{p.get('tipo')}' inválido "
                "(use 'indesejado' ou 'indisponivel')"
            )
            continue
        if dt:
            preferencias.append(
                Preferencia(p["pessoa_id"], dt, tipo, p.get("tipo_de_turno_id"))
            )

    regras = []
    for i, r in enumerate(d.get("regras_internas", [])):
        onde = f"regras_internas[{i}]"
        try:
            natureza = Natureza(r.get("natureza", "flexivel"))
        except ValueError:
            erros.append(f"{onde}.natureza: use 'rigida' ou 'flexivel'")
            continue
        regras.append(
            RegraInterna(
                id=r["id"],
                descricao=r.get("descricao", r["id"]),
                natureza=natureza,
                parametros=r.get("parametros", {}),
                peso=r.get("peso"),
            )
        )

    if len(pessoas) > LIMITE_PESSOAS:
        erros.append(f"pessoas: {len(pessoas)} excede o limite de {LIMITE_PESSOAS}")
    if len(plantoes) > LIMITE_PLANTOES:
        erros.append(f"plantoes: {len(plantoes)} excede o limite de {LIMITE_PLANTOES}")

    if erros:
        raise ErroDeValidacao(erros)

    inst = Instancia(
        inicio=inicio,
        fim=fim,
        habilitacoes=habilitacoes,
        tipos_de_turno=tuple(tipos),
        contratos=tuple(contratos),
        pessoas=pessoas,
        plantoes=tuple(plantoes),
        preferencias=tuple(preferencias),
        regras_internas=tuple(regras),
    )

    # --- integridade referencial ---
    ids_turno = {t.id for t in inst.tipos_de_turno}
    ids_hab = {h.id for h in inst.habilitacoes}
    ids_contrato = {c.id for c in inst.contratos}
    ids_pessoa = {p.id for p in inst.pessoas}
    for p in inst.plantoes:
        if p.tipo_de_turno_id not in ids_turno:
            erros.append(f"plantao '{p.id}': tipo de turno '{p.tipo_de_turno_id}' não existe")
        if p.habilitacao_id not in ids_hab:
            erros.append(f"plantao '{p.id}': habilitação '{p.habilitacao_id}' não existe")
        if not (inst.inicio <= p.data <= inst.fim):
            erros.append(f"plantao '{p.id}': data {p.data} fora do período")
    for pe in inst.pessoas:
        if pe.contrato_id not in ids_contrato:
            erros.append(f"pessoa '{pe.id}': contrato '{pe.contrato_id}' não existe")
        for h in pe.habilitacoes:
            if h not in ids_hab:
                erros.append(f"pessoa '{pe.id}': habilitação '{h}' não existe")
    for pref in inst.preferencias:
        if pref.pessoa_id not in ids_pessoa:
            erros.append(f"preferencia: pessoa '{pref.pessoa_id}' não existe")

    # --- L4: validação de configuração, com o artigo citado ---
    erros.extend(restricoes_legais.validar_configuracao(inst))
    # --- guarda de peso das regras internas (REG-04, dona é restricoes_modelo) ---
    erros.extend(restricoes_modelo.validar_pesos_internos(inst))

    if erros:
        raise ErroDeValidacao(erros)
    return inst
