"""M-03 restricoes-modelo — restrições do INRC-II e regras internas.

Porte literal (S6 Tier 2) da formulação do INRC-II: H1-H4 rígidas, S1-S7
flexíveis com os PESOS PUBLICADOS. Fonte: specs/references/nrp-inrc2.md
(Ceschia et al., arXiv:1501.04177). Nenhum peso arbitrado aqui.

Regras internas vivem neste módulo porque têm a mesma forma paramétrica; o que
as distingue é o campo `origem`, e a guarda de peso mora aqui — dona da
semântica de peso — para valer por qualquer caminho, inclusive o gerador
sintético (REG-04).

DIVERGÊNCIA DECLARADA EM RELAÇÃO AO INRC-II (encontrada na micro-verificação S7
da Fase 5, com justificativa registrada em decisão de projeto):

    S1 no INRC-II penaliza APENAS a cobertura abaixo do ótimo, porque as
    instâncias da competição são de demanda exata. Medindo o porte de
    referência, o solver entregou 183 alocações para 150 vagas ótimas: com
    custo zero alcançável e nada penalizando o excesso, qualquer solução de
    custo zero serve, e superlotar plantões é gratuito. Num hospital isso
    significa escalar gente que não era necessária.

    Este módulo penaliza o excesso SIMETRICAMENTE, reutilizando o peso
    publicado de S1 (30). Nenhum número novo foi inventado — a extensão é de
    forma, não de calibração.
"""

from __future__ import annotations

from datetime import timedelta

from .dominio import (
    Contexto,
    Escala,
    Instancia,
    Natureza,
    Origem,
    Plantao,
    Preferencia,
    TipoPreferencia,
    Violacao,
)

# Pesos publicados do INRC-II — specs/references/nrp-inrc2.md §2.2
PESO = {
    "S1": 30,  # cobertura ótima insuficiente
    "S2_turno": 15,  # consecutividade por tipo de turno
    "S2": 30,  # consecutividade de dias trabalhados
    "S3": 30,  # folgas consecutivas
    "S4": 10,  # preferências (o MENOR do conjunto — ver ETI-02)
    "S5": 30,  # fim de semana completo
    "S6": 20,  # total de plantões no horizonte
    "S7": 30,  # fins de semana trabalhados
}

PESO_MAXIMO_INTERNO = max(PESO.values())  # 30 — guarda de CIE-01

FONTE_MODELO = {k: f"INRC-II {k.split('_')[0]}" for k in PESO}


def validar_pesos_internos(inst: Instancia) -> list[str]:
    """Guarda de CIE-01: uma regra interna sem fonte não pode dominar as
    restrições calibradas da literatura."""
    erros = []
    for regra in inst.regras_internas:
        if regra.natureza is Natureza.FLEXIVEL:
            if regra.peso is None:
                erros.append(f"regra interna '{regra.id}' é flexível e não tem peso")
            elif regra.peso > PESO_MAXIMO_INTERNO:
                erros.append(
                    f"regra interna '{regra.id}' tem peso {regra.peso}, acima do "
                    f"maior peso publicado do INRC-II ({PESO_MAXIMO_INTERNO}). "
                    "Uma regra sem fonte bibliográfica não pode dominar as "
                    "calibradas."
                )
        elif regra.peso is not None:
            erros.append(f"regra interna '{regra.id}' é rígida e não deve ter peso")
    return erros


def _viol(rid, natureza, fonte, descricao, origem=Origem.MODELO, peso=0, **kw):
    return Violacao(
        restricao_id=rid,
        origem=origem,
        natureza=natureza,
        fonte=fonte,
        descricao=descricao,
        peso=peso,
        **kw,
    )


def _indesejados(inst: Instancia, pessoa_id: str) -> list[Preferencia]:
    return [
        p
        for p in inst.preferencias
        if p.pessoa_id == pessoa_id and p.tipo is TipoPreferencia.INDESEJADO
    ]


# --------------------------------------------------------------------------
# Modo GERAÇÃO
# --------------------------------------------------------------------------


def aplicar(modelo, x, ctx: Contexto) -> list:
    """Aplica H1-H3 e S1-S7 + regras internas. Devolve os termos do objetivo.

    H4 não aparece: a variável não é criada quando a pessoa não tem a
    habilitação (poda em `Instancia.elegivel`), o que a torna inviolável por
    construção no modo geração. No modo verificação ela existe — uma troca pode
    alocar alguém sem a habilitação.
    """
    inst = ctx.instancia
    dias = inst.dias
    termos = []
    pessoas = sorted(inst.pessoas, key=lambda p: p.id)

    # ---- H1: no máximo um plantão por pessoa por dia ----
    for pessoa in pessoas:
        for d in dias:
            vars_dia = [
                x[(pessoa.id, p.id)]
                for p in inst.plantoes_do_dia(d)
                if (pessoa.id, p.id) in x
            ]
            if len(vars_dia) > 1:
                modelo.AddAtMostOne(vars_dia)

    # ---- H2: cobertura mínima / S1: cobertura ótima ----
    for plantao in sorted(inst.plantoes, key=lambda p: p.id):
        vars_pl = [
            x[(pessoa.id, plantao.id)] for pessoa in pessoas if (pessoa.id, plantao.id) in x
        ]
        if not vars_pl:
            continue
        modelo.Add(sum(vars_pl) >= plantao.demanda_minima)
        if plantao.demanda_otima > plantao.demanda_minima:
            falta = modelo.NewIntVar(0, plantao.demanda_otima, f"S1_{plantao.id}")
            modelo.AddMaxEquality(falta, [plantao.demanda_otima - sum(vars_pl), 0])
            termos.append(PESO["S1"] * falta)
        # DIVERGÊNCIA DECLARADA em relação ao INRC-II (ver docstring do módulo):
        # a competição penaliza apenas a cobertura ABAIXO do ótimo, porque suas
        # instâncias são de demanda exata. Sem penalizar o excesso, qualquer
        # solução de custo zero serve e o solver superlota os plantões — alocando
        # gente onde não é necessária. Reutiliza o peso publicado de S1 (30);
        # nenhum número novo é inventado.
        excesso = modelo.NewIntVar(0, len(vars_pl), f"S1x_{plantao.id}")
        modelo.AddMaxEquality(excesso, [sum(vars_pl) - plantao.demanda_otima, 0])
        termos.append(PESO["S1"] * excesso)

    # ---- S2/S3: consecutividade (specs/technical/modelo-cpsat.md §11) ----
    for pessoa in pessoas:
        contrato = inst.contrato_de(pessoa)
        fr = ctx.fronteira_de(pessoa.id)
        trabalha = {}
        for d in dias:
            vd = [
                x[(pessoa.id, p.id)]
                for p in inst.plantoes_do_dia(d)
                if (pessoa.id, p.id) in x
            ]
            v = modelo.NewBoolVar(f"trab_{pessoa.id}_{d.isoformat()}")
            if vd:
                modelo.AddMaxEquality(v, vd)
            else:
                modelo.Add(v == 0)
            trabalha[d] = v

        mx = contrato.max_dias_consecutivos
        # §11.2 — toda janela de mx+1 dias contém ao menos uma folga
        for i in range(0, max(0, len(dias) - mx)):
            janela = [trabalha[d] for d in dias[i : i + mx + 1]]
            if len(janela) == mx + 1:
                modelo.Add(sum(janela) <= mx)
        # §11.3 — a sequência herdada encurta a primeira janela
        k = fr.dias_trabalhados_consecutivos
        if k > 0:
            restante = mx - k
            if restante <= 0:
                modelo.Add(trabalha[dias[0]] == 0)
            else:
                janela = [trabalha[d] for d in dias[: restante + 1]]
                modelo.Add(sum(janela) <= restante)

        # §11.4 — sequência mais curta que o mínimo é violação flexível de S2
        mn = contrato.min_dias_consecutivos
        for L in range(1, max(1, mn)):
            for i in range(1, len(dias) - L):
                viol = modelo.NewBoolVar(f"S2min_{pessoa.id}_{i}_{L}")
                literais = [trabalha[dias[i + j]] for j in range(L)]
                literais.append(trabalha[dias[i - 1]].Not())
                literais.append(trabalha[dias[i + L]].Not())
                modelo.AddBoolAnd(literais).OnlyEnforceIf(viol)
                termos.append(PESO["S2"] * viol)

        # S3 — folgas consecutivas abaixo do mínimo
        mnf = contrato.min_folgas_consecutivas
        for L in range(1, max(1, mnf)):
            for i in range(1, len(dias) - L):
                viol = modelo.NewBoolVar(f"S3min_{pessoa.id}_{i}_{L}")
                literais = [trabalha[dias[i + j]].Not() for j in range(L)]
                literais.append(trabalha[dias[i - 1]])
                literais.append(trabalha[dias[i + L]])
                modelo.AddBoolAnd(literais).OnlyEnforceIf(viol)
                termos.append(PESO["S3"] * viol)

        # ---- S4: preferências (peso 10) ----
        for pref in _indesejados(inst, pessoa.id):
            for plantao in inst.plantoes:
                if pref.cobre(plantao) and (pessoa.id, plantao.id) in x:
                    termos.append(PESO["S4"] * x[(pessoa.id, plantao.id)])

        # ---- S5: fim de semana completo ----
        if contrato.exige_fim_de_semana_completo:
            for d in dias:
                if d.weekday() == 5 and (d + timedelta(days=1)) in trabalha:
                    sab, dom = trabalha[d], trabalha[d + timedelta(days=1)]
                    incompleto = modelo.NewBoolVar(f"S5_{pessoa.id}_{d.isoformat()}")
                    modelo.Add(sab != dom).OnlyEnforceIf(incompleto)
                    modelo.Add(sab == dom).OnlyEnforceIf(incompleto.Not())
                    termos.append(PESO["S5"] * incompleto)

        # ---- S6: total de plantões no horizonte ----
        total_vars = [x[(pessoa.id, p.id)] for p in inst.plantoes if (pessoa.id, p.id) in x]
        if total_vars:
            total = sum(total_vars) + fr.total_plantoes
            acima = modelo.NewIntVar(0, len(inst.plantoes), f"S6a_{pessoa.id}")
            abaixo = modelo.NewIntVar(0, len(inst.plantoes), f"S6b_{pessoa.id}")
            modelo.AddMaxEquality(acima, [total - contrato.max_plantoes, 0])
            modelo.AddMaxEquality(abaixo, [contrato.min_plantoes - total, 0])
            termos.append(PESO["S6"] * acima)
            termos.append(PESO["S6"] * abaixo)

        # ---- S7: fins de semana trabalhados ----
        fds = sorted({d for d in dias if d.weekday() >= 5})
        if fds:
            marcas = []
            for d in fds:
                marcas.append(trabalha[d])
            excedente = modelo.NewIntVar(0, len(fds), f"S7_{pessoa.id}")
            modelo.AddMaxEquality(
                excedente,
                [
                    sum(marcas) + fr.fins_de_semana_trabalhados
                    - contrato.max_fins_de_semana,
                    0,
                ],
            )
            termos.append(PESO["S7"] * excedente)

        # ---- Regras internas ----
        for regra in inst.regras_internas:
            alvo = regra.parametros.get("tipo_de_turno_id")
            maximo = regra.parametros.get("max")
            if maximo is None:
                continue
            vars_regra = [
                x[(pessoa.id, p.id)]
                for p in inst.plantoes
                if (pessoa.id, p.id) in x
                and (alvo is None or p.tipo_de_turno_id == alvo)
            ]
            if not vars_regra:
                continue
            if regra.natureza is Natureza.RIGIDA:
                modelo.Add(sum(vars_regra) <= maximo)
            else:
                excesso = modelo.NewIntVar(0, len(vars_regra), f"{regra.id}_{pessoa.id}")
                modelo.AddMaxEquality(excesso, [sum(vars_regra) - maximo, 0])
                termos.append(regra.peso * excesso)

    return termos


# --------------------------------------------------------------------------
# Modo VERIFICAÇÃO
# --------------------------------------------------------------------------


def verificar(escala: Escala, ctx: Contexto) -> list[Violacao]:
    inst = ctx.instancia
    v: list[Violacao] = []

    # ---- H1 ----
    for pessoa in sorted(inst.pessoas, key=lambda p: p.id):
        por_dia: dict = {}
        for pid in escala.plantoes_de(pessoa.id):
            por_dia.setdefault(inst.plantao(pid).data, []).append(pid)
        for d, ps in sorted(por_dia.items()):
            if len(ps) > 1:
                v.append(
                    _viol(
                        "H1",
                        Natureza.RIGIDA,
                        "INRC-II H1",
                        f"{len(ps)} plantões no mesmo dia",
                        pessoa_id=pessoa.id,
                        data=d,
                    )
                )

    # ---- H2 / S1 ----
    for plantao in sorted(inst.plantoes, key=lambda p: p.id):
        n = len(escala.pessoas_em(plantao.id))
        if n < plantao.demanda_minima:
            v.append(
                _viol(
                    "H2",
                    Natureza.RIGIDA,
                    "INRC-II H2",
                    f"cobertura {n} abaixo do mínimo {plantao.demanda_minima}",
                    plantao_id=plantao.id,
                    data=plantao.data,
                )
            )
        elif n < plantao.demanda_otima:
            v.append(
                _viol(
                    "S1",
                    Natureza.FLEXIVEL,
                    "INRC-II S1",
                    f"cobertura {n} abaixo do ótimo {plantao.demanda_otima}",
                    peso=PESO["S1"] * (plantao.demanda_otima - n),
                    plantao_id=plantao.id,
                    data=plantao.data,
                )
            )
        elif n > plantao.demanda_otima:
            v.append(
                _viol(
                    "S1",
                    Natureza.FLEXIVEL,
                    "INRC-II S1 (extensão: excesso)",
                    f"cobertura {n} acima do ótimo {plantao.demanda_otima}",
                    peso=PESO["S1"] * (n - plantao.demanda_otima),
                    plantao_id=plantao.id,
                    data=plantao.data,
                )
            )

    # ---- H4: habilitação (existe na verificação; uma troca pode violá-la) ----
    for aloc in escala.alocacoes:
        pessoa = inst.pessoa(aloc.pessoa_id)
        plantao = inst.plantao(aloc.plantao_id)
        if plantao.habilitacao_id not in pessoa.habilitacoes:
            v.append(
                _viol(
                    "H4",
                    Natureza.RIGIDA,
                    "INRC-II H4",
                    f"não tem a habilitação '{plantao.habilitacao_id}' exigida",
                    pessoa_id=pessoa.id,
                    plantao_id=plantao.id,
                    data=plantao.data,
                )
            )
        # indisponibilidade declarada é rígida
        if not inst.elegivel(pessoa, plantao) and plantao.habilitacao_id in pessoa.habilitacoes:
            v.append(
                _viol(
                    "IND",
                    Natureza.RIGIDA,
                    "indisponibilidade declarada",
                    "alocado em data declarada como indisponível",
                    pessoa_id=pessoa.id,
                    plantao_id=plantao.id,
                    data=plantao.data,
                )
            )

    # ---- S4 ----
    for pessoa in sorted(inst.pessoas, key=lambda p: p.id):
        for pref in _indesejados(inst, pessoa.id):
            for pid in escala.plantoes_de(pessoa.id):
                if pref.cobre(inst.plantao(pid)):
                    v.append(
                        _viol(
                            "S4",
                            Natureza.FLEXIVEL,
                            "INRC-II S4",
                            "alocado em turno declarado indesejado",
                            peso=PESO["S4"],
                            pessoa_id=pessoa.id,
                            plantao_id=pid,
                            data=pref.data,
                        )
                    )

    # ---- S6 / S7 ----
    for pessoa in sorted(inst.pessoas, key=lambda p: p.id):
        contrato = inst.contrato_de(pessoa)
        fr = ctx.fronteira_de(pessoa.id)
        pids = escala.plantoes_de(pessoa.id)
        total = len(pids) + fr.total_plantoes
        if total > contrato.max_plantoes:
            v.append(
                _viol(
                    "S6",
                    Natureza.FLEXIVEL,
                    "INRC-II S6",
                    f"{total} plantões, acima do máximo {contrato.max_plantoes}",
                    peso=PESO["S6"] * (total - contrato.max_plantoes),
                    pessoa_id=pessoa.id,
                )
            )
        elif total < contrato.min_plantoes:
            v.append(
                _viol(
                    "S6",
                    Natureza.FLEXIVEL,
                    "INRC-II S6",
                    f"{total} plantões, abaixo do mínimo {contrato.min_plantoes}",
                    peso=PESO["S6"] * (contrato.min_plantoes - total),
                    pessoa_id=pessoa.id,
                )
            )
        fds = len({inst.plantao(p).data for p in pids if inst.plantao(p).fim_de_semana})
        fds += fr.fins_de_semana_trabalhados
        if fds > contrato.max_fins_de_semana:
            v.append(
                _viol(
                    "S7",
                    Natureza.FLEXIVEL,
                    "INRC-II S7",
                    f"{fds} fins de semana, acima do máximo "
                    f"{contrato.max_fins_de_semana}",
                    peso=PESO["S7"] * (fds - contrato.max_fins_de_semana),
                    pessoa_id=pessoa.id,
                )
            )

        # ---- Regras internas ----
        for regra in inst.regras_internas:
            alvo = regra.parametros.get("tipo_de_turno_id")
            maximo = regra.parametros.get("max")
            if maximo is None:
                continue
            n = sum(
                1
                for p in pids
                if alvo is None or inst.plantao(p).tipo_de_turno_id == alvo
            )
            if n > maximo:
                v.append(
                    _viol(
                        regra.id,
                        regra.natureza,
                        f"regra interna {regra.id}",
                        f"{regra.descricao}: {n} excede {maximo}",
                        origem=Origem.INTERNA,
                        peso=(regra.peso or 0) * (n - maximo),
                        pessoa_id=pessoa.id,
                    )
                )

    return v
