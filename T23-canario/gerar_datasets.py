"""Gera o ground truth de specs/datasets a partir do simulador.

Prometido no Production Capacity Check da Fase 0: quatro cenários
determinísticos com séries sintéticas de >=50 pontos por métrica e por
participante. É o insumo dos testes da Fase 6 — testar contra ele é testar
contra dado depositado, não contra o simulador rodando junto do teste.
"""

from __future__ import annotations

import json
from pathlib import Path

from canario.alvo_de_implantacao import AlvoSimulado, Papel
from canario.configuracao import Configuracao
from canario.fonte_de_metricas import Amostra
from canario.julgamento import METRICAS
from canario.relogio import RelogioVirtual
from canario.simulador_de_cenario import CENARIOS, SimuladorDeCenario

DESTINO = Path(__file__).parent / "specs" / "datasets"
PONTOS = 50


def gerar(chave: str) -> dict:
    cenario = CENARIOS[chave]
    cfg = Configuracao(guarda_taxa_erro=0.10, guarda_latencia_p99=400.0)
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    alvo.aplicar(cfg.pesos[0])
    fonte = SimuladorDeCenario(cenario, relogio, alvo)

    relogio.avancar(cfg.intervalo)
    series: dict[str, dict[str, list[float]]] = {}
    indisponiveis = 0

    for metrica in METRICAS:
        series[metrica.nome] = {}
        for papel in (Papel.ESTAVEL, Papel.BASELINE, Papel.CANARIO):
            valores: list[float] = []
            for _ in range(PONTOS):
                r = fonte.coletar(papel.value, metrica.nome)
                if isinstance(r, Amostra):
                    valores.append(round(r.valor, 6))
                else:
                    indisponiveis += 1
            series[metrica.nome][papel.value] = valores

    return {
        "cenario": cenario.nome,
        "chave": chave,
        "semente": cenario.semente,
        "instante": relogio.agora(),
        "pontos_por_serie": PONTOS,
        "coletas_indisponiveis": indisponiveis,
        "series": series,
    }


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    indice = []
    for chave in sorted(CENARIOS):
        dados = gerar(chave)
        caminho = DESTINO / f"{chave}.json"
        caminho.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        resumo = {
            "arquivo": caminho.name,
            "cenario": dados["cenario"],
            "semente": dados["semente"],
            "indisponiveis": dados["coletas_indisponiveis"],
        }
        for m in METRICAS:
            s = dados["series"][m.nome]
            if s[Papel.CANARIO.value] and s[Papel.BASELINE.value]:
                mc = sum(s[Papel.CANARIO.value]) / len(s[Papel.CANARIO.value])
                mb = sum(s[Papel.BASELINE.value]) / len(s[Papel.BASELINE.value])
                resumo[f"{m.nome}_canario/baseline"] = round(mc / mb, 4)
        indice.append(resumo)
        print(f"{caminho.name}: {resumo}")

    (DESTINO / "indice.json").write_text(
        json.dumps(indice, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
