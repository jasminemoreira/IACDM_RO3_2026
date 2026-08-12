"""M-11 cli — casos de uso nomeados + casca fina de argumentos.

ARC-01 — cada caso de uso é uma FUNÇÃO com contrato próprio (`importar`,
`conciliar`, `revisar`, `relatar`), e o parser de argumentos é casca sobre elas.
A versão anterior tinha o fluxo do UC-1 existindo apenas dentro do parser, o que
o tornava inexecutável e intestável fora da CLI.

OBS-03 — código de saída por CLASSE de falha, não 0/1. Sem isso, "rodou e não
achou nada" e "falhou" são indistinguíveis, para script e para o analista.

PRC-04 — pré-condição de ordem verificada: `conciliar` sem livro importado
produziria 100% de órfão-no-extrato, resultado indistinguível de falha real.

SEC-04 — caminhos validados e base criada com permissão restrita (no store).
OBS-05 — as métricas de bloco devolvidas pelo matcher são PERSISTIDAS aqui; sem
consumidor declarado, a métrica que revela bloco degenerado seria descartada.

FORA DE ESCOPO por decisão do operador na Fase 3: `--dry-run` (UX-02) e
`fechar_periodo` (PRC-03). Registrados como dívida, não esquecidos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from t26.adapters import csv_fonte, ofx
from t26.adapters.perfil import Alvo, carregar_perfil
from t26.domain.model import (
    Estado5,
    Resultado,
    Situacao,
    construir_lancamentos,
    construir_transacoes,
    estado_val5,
)
from t26.engines.dedup import DedupEngine, Escopo
from t26.engines.reconcile import ConfigConciliacao, ReconcileEngine
from t26.matching import matcher as M
from t26.persistence.auditoria import AuditLog
from t26.persistence.store import (
    Store,
    linha_para_lancamento,
    linha_para_transacao,
)
from t26.report import reporter
from t26.review.fila import ConfirmacaoAusente, ErroRevisao, ReviewQueue


class Saida:
    """OBS-03 — códigos de saída por classe de falha."""

    OK = 0
    ERRO_ENTRADA = 2  # arquivo/perfil inválido
    ERRO_ESTADO = 3  # pré-condição de ordem não satisfeita
    ERRO_BASE = 4  # persistência: lock, esquema incompatível
    ERRO_USO = 5  # argumento inválido, ação inexistente


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _execucao_id(comando: str, arquivos: list[Path]) -> str:
    """Identificador da execução — metadado de proveniência, não estado.

    Usa microssegundos e o pid porque duas execuções do mesmo comando sobre o
    mesmo arquivo no mesmo segundo colidiriam. Isso NÃO afeta o determinismo que
    VAL-5 mede: `digest_estado` exclui a coluna de execução exatamente porque ela
    muda a cada rodada por construção.
    """
    instante = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    material = (
        comando
        + "|" + "|".join(sorted(str(a) for a in arquivos))
        + "|" + instante
        + "|" + str(os.getpid())
    )
    return "X" + hashlib.sha256(material.encode()).hexdigest()[:16]


def _hash_arquivo(caminho: Path) -> str:
    return "sha256:" + hashlib.sha256(caminho.read_bytes()).hexdigest()[:32]


def _validar_caminho(bruto: str) -> Path:
    """SEC-04 — recusa caminho inexistente ou que não seja arquivo comum."""
    p = Path(bruto).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"não é um arquivo legível: {p}")
    return p


def _parametros_efetivos() -> dict:
    """REG-03/CTL-02 — o que estava valendo nesta execução."""
    return {
        "corte_fusao": M.CORTE_FUSAO,
        "corte_revisao": M.CORTE_REVISAO,
        "teto_bloco": M.TETO_BLOCO,
        "sim_alta": M.SIM_ALTA,
        "sim_media": M.SIM_MEDIA,
        "janelas_instrumento": M.JANELA_POR_INSTRUMENTO,
    }


def _versoes(perfis: dict[str, str] | None = None) -> dict:
    v = {
        "software": reporter.VERSAO_SOFTWARE,
        "perfil_dedup": M.PERFIL_DEDUP.versao,
        "perfil_conciliacao": M.PERFIL_CONCILIACAO.versao,
    }
    v.update(perfis or {})
    return v


# --------------------------------------------------------------------------- #
# Casos de uso — funções com contrato próprio (ARC-01)
# --------------------------------------------------------------------------- #


def importar(base: str, arquivo: str, fonte: str | None, perfil: str | None) -> int:
    """UC-1 e UC-2 — importa extrato ou livro, deduplica, reporta por classe."""
    caminho = _validar_caminho(arquivo)
    store = Store(base)
    log = AuditLog(store)
    dedup = DedupEngine(store, log)

    if perfil:
        p = carregar_perfil(perfil)
        registros = csv_fonte.ler(caminho, p)
        alvo = p.alvo
        versoes_perfil = {f"perfil_csv_{p.nome}": p.versao}
    else:
        if not fonte:
            raise ValueError("informe --fonte para arquivos OFX")
        registros = ofx.ler(caminho, fonte)
        alvo = Alvo.EXTRATO
        versoes_perfil = {}

    execucao = _execucao_id("importar", [caminho])
    with store.unidade_de_trabalho(execucao) as uow:
        log.registrar_execucao(
            uow, _parametros_efetivos() | {"arquivo": caminho.name},
            {caminho.name: _hash_arquivo(caminho)},
        )

        if alvo is Alvo.LIVRO:
            lancamentos = construir_lancamentos(list(registros))
            res = store.gravar_lancamentos(
                uow, [(l, M.chave_bloco(l)) for l in lancamentos]
            )
            print(
                f"livro: {res.novas} lançamentos novos, "
                f"{res.ja_presentes_por_chave} já presentes"
            )
            return Saida.OK

        transacoes = construir_transacoes(list(registros))
        # PRF-02 — uma consulta por FATIA de blocos, não uma por bloco. Iterar
        # os blocos chamando carregar_bloco reintroduzia o N+1 no composition
        # root, uma camada acima de onde a arquitetura o havia eliminado.
        existentes = [
            linha_para_transacao(l)
            for l in store.carregar_blocos([M.chave_bloco(t) for t in transacoes])
        ]
        res = store.gravar_lote(uow, [(t, M.chave_bloco(t)) for t in transacoes])
        # O conjunto é construído UMA vez. Dentro da compreensão, `set(...)` seria
        # reconstruído por item — O(n²) e o gargalo real que fez VAL-4 estourar.
        chaves_novas = set(res.chaves_novas)
        novas = [t for t in transacoes if t.chave in chaves_novas]
        dedup_res = dedup.classificar_lote(uow, novas, existentes, Escopo())
        res.ja_presentes_por_dedup = len(dedup_res.duplicatas)

        # OBS-05 — a métrica não é descartada.
        uow.executar(
            """INSERT INTO auditoria (execucao, tipo, chave, conteudo, instante)
               VALUES (?,?,?,?,?)""",
            (
                execucao, "metricas-bloco", None,
                json.dumps(
                    {
                        "blocos": dedup_res.metricas.blocos,
                        "maior_bloco": dedup_res.metricas.maior_bloco,
                        "pares_avaliados": dedup_res.metricas.pares_avaliados,
                        "excedentes": dedup_res.metricas.excedentes,
                        "blocos_degenerados": dedup_res.metricas.blocos_degenerados,
                    }
                ),
                _agora(),
            ),
        )

    print(
        f"{res.total()} linhas lidas de {caminho.name}\n"
        f"  novas                      {res.novas}\n"
        f"  já presentes (mesma linha) {res.ja_presentes_por_chave}\n"
        f"  duplicatas (dedup)         {res.ja_presentes_por_dedup}\n"
        f"  pendências de revisão      {len(dedup_res.pendencias)}\n"
        f"  maior bloco / teto         {dedup_res.metricas.maior_bloco} / {M.TETO_BLOCO}"
    )
    return Saida.OK


def conciliar(base: str, tolerancia: str = "0") -> int:
    """UC-4 — casa extrato × livro e classifica todo item em um dos 5 estados."""
    store = Store(base)
    log = AuditLog(store)
    engine = ReconcileEngine(store, log)

    # PRC-04 — pré-condição de ordem, verificada e explicada.
    if store.contar("lancamento") == 0:
        print(
            "nenhum lançamento no livro: `conciliar` agora produziria 100% de "
            "órfão-no-extrato, indistinguível de falha real.\n"
            "Importe o livro primeiro: t26 importar --perfil perfis/livro.json <arquivo>",
            file=sys.stderr,
        )
        return Saida.ERRO_ESTADO
    if store.contar("transacao") == 0:
        print("nenhuma transação importada — nada a conciliar.", file=sys.stderr)
        return Saida.ERRO_ESTADO

    transacoes = [
        linha_para_transacao(dict(l))
        for l in store.conexao.execute(
            "SELECT * FROM transacao WHERE duplicata_de IS NULL ORDER BY chave"
        )
    ]
    lancamentos = [
        linha_para_lancamento(dict(l))
        for l in store.conexao.execute("SELECT * FROM lancamento ORDER BY chave")
    ]

    execucao = _execucao_id("conciliar", [])
    config = ConfigConciliacao(tolerancia_valor=Decimal(tolerancia))
    with store.unidade_de_trabalho(execucao) as uow:
        log.registrar_execucao(
            uow, _parametros_efetivos() | {"tolerancia": tolerancia}, {}
        )
        res = engine.conciliar(uow, transacoes, lancamentos, config)

    total = (
        len(res.casamentos) * 2
        + len(res.orfaos_extrato)
        + len(res.orfaos_livro)
        + len(res.pendencias)
    )
    print(
        f"casados                {len(res.casamentos)}\n"
        f"órfãos no extrato      {len(res.orfaos_extrato)}\n"
        f"órfãos no livro        {len(res.orfaos_livro)}\n"
        f"pendentes de revisão   {len(res.pendencias)}\n"
        f"VAL-3: {total} de {len(transacoes) + len(lancamentos)} itens classificados"
    )
    return Saida.OK


def revisar(base: str, acao: str | None, pendencia: str | None, autor: str) -> int:
    """UC-5 — lista a fila ou resolve uma pendência, e a decisão persiste."""
    store = Store(base)
    fila = ReviewQueue(store, AuditLog(store))

    if not acao:
        itens = fila.listar()
        if not itens:
            print("fila vazia — nada pendente de revisão.")
            return Saida.OK
        print(f"{len(itens)} pendências, por impacto financeiro:\n")
        for i in itens:
            cands = ", ".join(c.texto()[:34] for c in i.candidatos) or "—"
            print(
                f"  {i.id}  R$ {i.impacto:>10}  score={i.melhor_score():3d}  [{i.familia}]\n"
                f"      {i.motivo[:88]}\n"
                f"      candidatos: {cands}"
            )
        return Saida.OK

    if not pendencia:
        print("informe --pendencia <id> para resolver", file=sys.stderr)
        return Saida.ERRO_USO

    execucao = _execucao_id("revisar", [])
    itens = {i.id: i for i in fila.listar()}
    alvo = None
    if pendencia in itens and itens[pendencia].candidatos:
        alvo = itens[pendencia].candidatos[0]
    try:
        with store.unidade_de_trabalho(execucao) as uow:
            res = fila.resolver(uow, pendencia, acao, autor, alvo=alvo)
    except (ErroRevisao, ConfirmacaoAusente) as erro:
        print(str(erro), file=sys.stderr)
        return Saida.ERRO_USO
    print(f"resolvida {pendencia} como '{acao}' por {autor} (registro {res.id})")
    return Saida.OK


def relatar(base: str, formato: str = "texto", saida: str | None = None) -> int:
    """Relatório com cabeçalho reexecutável e órfãos separados por natureza."""
    store = Store(base)
    itens: list[reporter.ItemRelatorio] = []

    casados = {
        l["transacao"]: dict(l) for l in store.conexao.execute("SELECT * FROM casamento")
    }
    casados_l = {v["lancamento"] for v in casados.values()}
    pendentes = {
        l["esquerda"]
        for l in store.conexao.execute("SELECT esquerda FROM pendencia WHERE aberta = 1")
    }

    for linha in store.conexao.execute(
        "SELECT * FROM transacao WHERE duplicata_de IS NULL"
    ):
        d = dict(linha)
        if d["chave"] in pendentes:
            estado = estado_val5(None, Situacao.PENDENTE)
            detalhe = "aguarda revisão humana"
        elif d["chave"] in casados:
            c = casados[d["chave"]]
            estado = estado_val5(Resultado(c["resultado"]), Situacao(c["situacao"]))
            detalhe = f"score={c['score']} delta={c['delta_valor']} dias={c['delta_dias']}"
        else:
            estado = Estado5.ORFAO_NO_EXTRATO
            detalhe = ""
        itens.append(
            reporter.ItemRelatorio(
                chave=d["chave"], estado=estado, valor=Decimal(d["valor"]),
                data=date.fromisoformat(d["data"]), descricao=d["descricao"],
                instrumento=d["instrumento"], detalhe=detalhe,
            )
        )

    for linha in store.conexao.execute("SELECT * FROM lancamento"):
        d = dict(linha)
        if d["chave"] in casados_l:
            continue
        itens.append(
            reporter.ItemRelatorio(
                chave=d["chave"], estado=Estado5.ORFAO_NO_LIVRO,
                valor=Decimal(d["valor"]), data=date.fromisoformat(d["data"]),
                descricao=d["descricao"], instrumento=d["instrumento"],
            )
        )

    rel = reporter.resumo(
        itens, _parametros_efetivos(), _versoes(), date.today(),
        titulo="Conciliação", gerado_em=_agora(),
    )
    texto = reporter.render(rel, formato)
    if saida:
        Path(saida).write_text(texto, encoding="utf-8")
        print(f"relatório escrito em {saida} ({formato})")
    else:
        print(texto)
    return Saida.OK


# --------------------------------------------------------------------------- #
# Casca de argumentos
# --------------------------------------------------------------------------- #


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="t26",
        description="Importador de extratos com deduplicação e conciliação.",
    )
    p.add_argument("--base", default="t26.db", help="arquivo SQLite (default: t26.db)")
    sub = p.add_subparsers(dest="comando", required=True)

    imp = sub.add_parser("importar", help="importa um extrato OFX/CSV ou o livro")
    imp.add_argument("arquivo")
    imp.add_argument("--fonte", help="identificador da fonte (obrigatório para OFX)")
    imp.add_argument("--perfil", help="perfil CSV (JSON); ausente = arquivo OFX")

    con = sub.add_parser("conciliar", help="casa extrato × livro interno")
    con.add_argument(
        "--tolerancia", default="0",
        help="tolerância de valor em Decimal (default 0 = casamento exato)",
    )

    rev = sub.add_parser("revisar", help="lista ou resolve pendências")
    rev.add_argument("--acao", help="e-a-mesma | sao-distintas | casar-com | nao-casa")
    rev.add_argument("--pendencia", help="id da pendência a resolver")
    rev.add_argument("--autor", default="operador")

    rel = sub.add_parser("relatar", help="relatório de conciliação")
    rel.add_argument("--formato", default="texto", choices=("texto", "csv", "json"))
    rel.add_argument("--saida", help="arquivo de destino (default: stdout)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        if args.comando == "importar":
            return importar(args.base, args.arquivo, args.fonte, args.perfil)
        if args.comando == "conciliar":
            return conciliar(args.base, args.tolerancia)
        if args.comando == "revisar":
            return revisar(args.base, args.acao, args.pendencia, args.autor)
        if args.comando == "relatar":
            return relatar(args.base, args.formato, args.saida)
    except FileNotFoundError as erro:
        print(erro, file=sys.stderr)
        return Saida.ERRO_ENTRADA
    except (ofx.ErroLeituraOFX, csv_fonte.ErroLeituraCSV, ValueError) as erro:
        print(erro, file=sys.stderr)
        return Saida.ERRO_ENTRADA
    except Exception as erro:  # persistência e o resto
        print(f"{type(erro).__name__}: {erro}", file=sys.stderr)
        return Saida.ERRO_BASE
    return Saida.ERRO_USO


if __name__ == "__main__":
    raise SystemExit(main())
