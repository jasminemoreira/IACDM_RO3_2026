"""M-05 contadores — falha e erro são coisas diferentes.

R-06, comentário do código-fonte do Argo Rollouts: 'A consecutive count is used
instead of a total count, because unlike failures, errors tend to happen
ephemerally and may recover on its own.'

    falha  = o julgamento REPROVOU o canário   -> total acumulado, nunca reseta
    erro   = não foi possível MEDIR            -> sucessão, reseta ao recuperar

Se caíssem no mesmo contador, a queda do coletor de métricas derrubaria um
canário saudável — que é justamente o caso de uso UC-4.

Contadores são POR MÉTRICA e não globais (achado RES-02): uma única métrica com
coleta quebrada não deve derrubar a execução inteira. A regra de agregação
— o que dispara o rollback — está declarada em `estourou` (achado RES-04).
"""

from __future__ import annotations

from collections import defaultdict

from .configuracao import Configuracao


class Contadores:
    def __init__(self, cfg: Configuracao) -> None:
        self._cfg = cfg
        self._falhas = 0
        self._erros_consecutivos: dict[str, int] = defaultdict(int)
        self._sucessos_consecutivos = 0

    # --- Falha: propriedade do julgamento, contada no total ------------------

    def registrar_falha(self) -> None:
        self._falhas += 1
        self._sucessos_consecutivos = 0

    def registrar_aprovacao(self) -> None:
        self._sucessos_consecutivos += 1

    @property
    def falhas(self) -> int:
        return self._falhas

    def estourou_falhas(self) -> bool:
        return self._falhas >= self._cfg.limite_falhas

    def recuperou(self) -> bool:
        """Histerese: K aprovações CONSECUTIVAS para sair de `pausado`.

        Fonte: R-06, `consecutiveSuccessLimit` — 'the number of consecutive
        times the measurement must succeed'. Sem isso, um canário limítrofe
        oscila entre pausado e progredindo a cada julgamento (achado CTL-01).

        A histerese é assimétrica de propósito: entrar em `pausado` basta uma
        falha, sair exige K sucessos. Pausar não altera tráfego e é barato;
        promover não é. O viés é deliberado e a favor da segurança (achado
        CTL-04, aceito com justificativa).
        """
        return self._sucessos_consecutivos >= self._cfg.histerese_k

    # --- Erro: propriedade da coleta, contado em sucessão --------------------

    def registrar_erro(self, metrica: str) -> None:
        self._erros_consecutivos[metrica] += 1

    def registrar_coleta_ok(self, metrica: str) -> None:
        self._erros_consecutivos[metrica] = 0

    def erros_consecutivos(self, metrica: str) -> int:
        return self._erros_consecutivos[metrica]

    def estourou_erros(self) -> bool:
        """Regra de agregação declarada: basta UMA métrica estourar.

        Se a coleta de uma das três métricas está permanentemente quebrada, o
        score passa a ser calculado sobre um denominador menor sem que ninguém
        tenha decidido isso — julgar com dois terços das evidências e chamar de
        aprovação seria pior que parar.
        """
        limite = self._cfg.limite_erros_consecutivos
        return any(n >= limite for n in self._erros_consecutivos.values())

    def metrica_estourada(self) -> str | None:
        limite = self._cfg.limite_erros_consecutivos
        for nome, n in self._erros_consecutivos.items():
            if n >= limite:
                return nome
        return None
