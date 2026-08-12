"""M-07 coordenador — máquina de estados e laço de execução.

CINCO estados. `aquecendo` existe porque nos primeiros julgamentos não há
amostra e o sistema não pode progredir — em V(1) ele ficava nominalmente em
`progredindo` sem poder progredir (achado PRO-02). `pausado` existe porque
falhar DETÉM o avanço sem reverter (R-07): sem ele, um único ponto ruim
reverteria.

Emite eventos TIPADOS (achado OBS-01); não imprime nada — quem imprime é a CLI.
É o dono ÚNICO do avanço do relógio (premissa A9, achado LIN-02).

Expirar por duração máxima mapeia para `revertido` com motivo `expirou`, e não
para um sexto estado: um mecanismo de segurança que não conseguiu concluir deve
terminar do lado seguro (achado PRO-05).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from . import guarda_absoluta
from .alvo_de_implantacao import AlvoSimulado, Papel
from .configuracao import Configuracao
from .contadores import Contadores
from .fonte_de_metricas import Amostra, FonteDeMetricas
from .janela import Janela
from .julgamento import METRICAS, Metrica, Veredito, julgar
from .relogio import Relogio
from .score import Score, aprova, pontuar


class Estado(str, Enum):
    AQUECENDO = "aquecendo"
    PROGREDINDO = "progredindo"
    PAUSADO = "pausado"
    REVERTIDO = "revertido"
    PROMOVIDO = "promovido"


TERMINAIS = (Estado.REVERTIDO, Estado.PROMOVIDO)


# --- Eventos tipados ---------------------------------------------------------

@dataclass(frozen=True)
class PesoAplicado:
    instante: int
    peso_canario: int
    distribuicao: dict[Papel, int]


@dataclass(frozen=True)
class Aquecendo:
    instante: int
    metrica: str
    coletadas: int
    faltam: int


@dataclass(frozen=True)
class JulgamentoConcluido:
    instante: int
    peso_canario: int
    score: Score
    aprovado: bool


@dataclass(frozen=True)
class ErroDeColeta:
    instante: int
    metrica: str
    consecutivos: int
    motivo: str


@dataclass(frozen=True)
class MudouEstado:
    instante: int
    de: Estado
    para: Estado
    motivo: str


@dataclass(frozen=True)
class Concluido:
    instante: int
    estado: Estado
    motivo: str


Evento = (
    PesoAplicado | Aquecendo | JulgamentoConcluido | ErroDeColeta | MudouEstado | Concluido
)
Observador = Callable[[Evento], None]


@dataclass
class Desfecho:
    estado: Estado
    motivo: str
    instante_final: int
    julgamentos: int = 0
    falhas: int = 0

    @property
    def promovido(self) -> bool:
        return self.estado is Estado.PROMOVIDO

    @property
    def revertido(self) -> bool:
        return self.estado is Estado.REVERTIDO


class Coordenador:
    def __init__(
        self,
        cfg: Configuracao,
        relogio: Relogio,
        fonte: FonteDeMetricas,
        alvo: AlvoSimulado,
    ) -> None:
        self._cfg = cfg
        self._relogio = relogio
        self._fonte = fonte
        self._alvo = alvo
        self._janela = Janela(cfg)
        self._contadores = Contadores(cfg)
        self._observadores: list[Observador] = []
        self._estado = Estado.AQUECENDO
        self._peso: int | None = None
        self._abortar = False
        self._julgamentos = 0
        self._motivo_final = "laço encerrado"

    # --- Superfície do operador ---------------------------------------------

    def assinar(self, observador: Observador) -> None:
        self._observadores.append(observador)

    def abortar(self) -> None:
        """Assíncrono em relação ao laço: apenas marca a flag.

        O laço a verifica no início de cada iteração. É isso que torna o aborto
        atendível num laço monothread — em V(1) `abortar()` existia sem
        mecanismo, e VAL-12 era inatendível (achado UX-02).
        """
        self._abortar = True

    # --- Laço ----------------------------------------------------------------

    def executar(self) -> Desfecho:
        self._peso = self._cfg.proximo_peso(None)
        self._alvo.aplicar(self._peso)
        self._emitir(
            PesoAplicado(self._relogio.agora(), self._peso, self._alvo.distribuicao())
        )

        while self._estado not in TERMINAIS:
            if self._abortar:
                return self._terminar(Estado.REVERTIDO, "aborto solicitado pelo operador")

            if self._relogio.agora() >= self._cfg.duracao_maxima:
                return self._terminar(
                    Estado.REVERTIDO,
                    f"expirou: duração máxima de {self._cfg.duracao_maxima} tiques "
                    f"atingida em {self._estado.value}",
                )

            self._relogio.avancar(self._cfg.intervalo)
            houve_erro = self._coletar_intervalo()

            if self._contadores.estourou_erros():
                metrica = self._contadores.metrica_estourada()
                return self._terminar(
                    Estado.REVERTIDO,
                    f"coleta de '{metrica}' falhou "
                    f"{self._cfg.limite_erros_consecutivos} vezes seguidas",
                )

            # A guarda é consultada ANTES da checagem de amostra: é exatamente
            # essa a sua razão de existir.
            motivo = guarda_absoluta.dispara(self._janela, self._cfg)
            if motivo is not None:
                return self._terminar(Estado.REVERTIDO, motivo)

            if houve_erro:
                # A janela NÃO foi renovada neste intervalo. Julgar agora seria
                # re-julgar exatamente as mesmas amostras, e o contador de
                # falhas pressupõe julgamentos independentes — três repetições
                # do mesmo veredito virariam rollback por uma falha que não
                # existe. O erro já está contado onde deve, no contador de erro
                # consecutivo. Ver decisão de diagnóstico da Fase 5.
                continue

            if not self._pronto_para_julgar():
                self._reportar_aquecimento()
                continue

            self._julgar_e_decidir()

        return self._terminar(self._estado, self._motivo_final)

    # --- Passos do laço ------------------------------------------------------

    def _coletar_intervalo(self) -> bool:
        """Uma chamada por amostra (A8), para os três papéis e as três métricas.

        Devolve True se ALGUMA métrica teve erro de coleta neste intervalo —
        sinal de que a janela não foi renovada e o julgamento deve ser pulado.
        """
        quantas = self._cfg.intervalo * self._cfg.taxa_de_amostragem
        houve_erro: dict[str, bool] = {m.nome: False for m in METRICAS}

        for metrica in METRICAS:
            for papel in (Papel.ESTAVEL, Papel.BASELINE, Papel.CANARIO):
                for _ in range(quantas):
                    resultado = self._fonte.coletar(papel.value, metrica.nome)
                    if isinstance(resultado, Amostra):
                        self._janela.adicionar(papel, metrica.nome, resultado.valor)
                    else:
                        houve_erro[metrica.nome] = True

        for nome, com_erro in houve_erro.items():
            if com_erro:
                self._contadores.registrar_erro(nome)
                self._emitir(
                    ErroDeColeta(
                        self._relogio.agora(),
                        nome,
                        self._contadores.erros_consecutivos(nome),
                        "coleta não produziu amostras neste intervalo",
                    )
                )
            else:
                self._contadores.registrar_coleta_ok(nome)

        return any(houve_erro.values())

    def _pronto_para_julgar(self) -> bool:
        return all(
            self._janela.pronta(m.nome) and self._janela.volumes_comparaveis(m.nome)
            for m in METRICAS
        )

    def _reportar_aquecimento(self) -> None:
        for metrica in METRICAS:
            n = self._janela.contagem(Papel.CANARIO, metrica.nome)
            if n < self._cfg.amostra_minima:
                self._emitir(
                    Aquecendo(
                        self._relogio.agora(),
                        metrica.nome,
                        n,
                        self._cfg.amostra_minima - n,
                    )
                )
                return

    def _julgar_e_decidir(self) -> None:
        vereditos: dict[Metrica, Veredito] = {}
        for metrica in METRICAS:
            vereditos[metrica] = julgar(
                self._janela.series(Papel.CANARIO, metrica.nome),
                self._janela.series(Papel.BASELINE, metrica.nome),
                metrica,
                self._cfg.alfa,
                self._cfg.amostra_minima,
            )

        score = pontuar(vereditos)
        self._julgamentos += 1

        if score.indefinido:
            # Nem aprova nem reprova: o passo aguarda amostra. A duração máxima
            # garante que isso não vire laço infinito (achados SCI-09, PRO-05).
            return

        aprovado = aprova(score, self._cfg.limiar_score)
        self._emitir(
            JulgamentoConcluido(self._relogio.agora(), self._peso, score, aprovado)
        )

        if aprovado:
            self._contadores.registrar_aprovacao()
            self._apos_aprovacao()
        else:
            self._contadores.registrar_falha()
            self._apos_falha(score)

    def _apos_aprovacao(self) -> None:
        if self._estado is Estado.PAUSADO and not self._contadores.recuperou():
            return  # histerese: ainda faltam sucessos consecutivos
        if self._estado in (Estado.AQUECENDO, Estado.PAUSADO):
            self._transitar(Estado.PROGREDINDO, "julgamento aprovado")

        proximo = self._cfg.proximo_peso(self._peso)
        if proximo is None:
            self._alvo.promover()
            self._transitar(Estado.PROMOVIDO, "todos os passos aprovados")
            return

        self._peso = proximo
        self._alvo.aplicar(proximo)
        # O passo anterior tinha outro regime de carga: começar limpo evita
        # julgar o passo N+1 com amostras do passo N (achado ASM-03).
        self._janela.limpar()
        self._emitir(
            PesoAplicado(self._relogio.agora(), proximo, self._alvo.distribuicao())
        )

    def _apos_falha(self, score: Score) -> None:
        reprovadas = ", ".join(score.reprovadas) or "nenhuma"
        if self._contadores.estourou_falhas():
            self._alvo.reverter()
            self._transitar(
                Estado.REVERTIDO,
                f"{self._contadores.falhas} julgamentos reprovados "
                f"(limite {self._cfg.limite_falhas}); pior sinal em: {reprovadas}",
            )
            return
        if self._estado is not Estado.PAUSADO:
            self._transitar(
                Estado.PAUSADO,
                f"julgamento reprovado em: {reprovadas} "
                f"({self._contadores.falhas}/{self._cfg.limite_falhas})",
            )

    # --- Transições e eventos ------------------------------------------------

    def _transitar(self, novo: Estado, motivo: str) -> None:
        anterior = self._estado
        self._estado = novo
        if novo in TERMINAIS:
            # O operador precisa saber POR QUE o sistema decidiu, e a transição
            # terminal é onde o motivo real existe (achado VAL-11).
            self._motivo_final = motivo
        self._emitir(MudouEstado(self._relogio.agora(), anterior, novo, motivo))

    def _terminar(self, estado: Estado, motivo: str) -> Desfecho:
        if estado is Estado.REVERTIDO:
            self._alvo.reverter()
        if self._estado is not estado:
            self._transitar(estado, motivo)
        self._emitir(Concluido(self._relogio.agora(), estado, motivo))
        return Desfecho(
            estado=estado,
            motivo=motivo,
            instante_final=self._relogio.agora(),
            julgamentos=self._julgamentos,
            falhas=self._contadores.falhas,
        )

    def _emitir(self, evento: Evento) -> None:
        for observador in self._observadores:
            observador(evento)
