"""M-01 dominio — entidades, objetos de valor e Contexto.

Núcleo puro: não importa ortools, não toca disco.

Decisões de arquitetura materializadas aqui:
- `Contexto` só existe completo (E3/ASS-01): o construtor exige a fronteira,
  então nenhum módulo consegue verificar restrições sem ela.
- `Escala` é entidade de dados; o cálculo de custo mora em `avaliador`
  (resolução explícita de ARQ-04).
- A escala vigente é função determinística de (snapshot, eventos) na ordem da
  lista — INV-3. Ver `Escala.vigente()`.
- `TipoDeTurno.vira_o_dia` é explícito, não deduzido de `fim < inicio` (LIN-03).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, time, timedelta
from enum import Enum
from typing import Iterable

# --------------------------------------------------------------------------
# Enumerações
# --------------------------------------------------------------------------


class Regime(str, Enum):
    """Regime do contrato. Altera a NATUREZA das restrições legais (art. 59-A)."""

    COMUM = "comum"
    DOZE_TRINTA_SEIS = "12x36"


class Origem(str, Enum):
    LEGAL = "legal"
    MODELO = "modelo"
    INTERNA = "interna"


class Natureza(str, Enum):
    RIGIDA = "rigida"
    FLEXIVEL = "flexivel"


class EstadoEscala(str, Enum):
    RASCUNHO = "rascunho"
    PUBLICADA = "publicada"


class EstadoTroca(str, Enum):
    """5 estados (V(3)). ORFA e CANCELADA foram removidos em E2.

    ORFA era redundante com a revalidação no aceite; cancelar termina em
    RECUSADA, com o evento registrando quem encerrou.
    """

    PENDENTE = "pendente"
    EFETIVADA = "efetivada"
    REJEITADA = "rejeitada"  # veredito da máquina: violaria restrição rígida
    RECUSADA = "recusada"  # decisão humana (o par recusou, ou o autor cancelou)
    EXPIRADA = "expirada"


class TipoEvento(str, Enum):
    TROCA_EFETIVADA = "troca_efetivada"
    EXPIRACAO = "expiracao"
    HISTORICO_ACEITO = "historico_aceito"


class TipoPreferencia(str, Enum):
    INDESEJADO = "indesejado"  # soft, S4 (peso 10)
    INDISPONIVEL = "indisponivel"  # rígido: a variável nem é criada


# --------------------------------------------------------------------------
# Objetos de valor e entidades
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Habilitacao:
    id: str
    nome: str


@dataclass(frozen=True)
class TipoDeTurno:
    """Turno com horário FIXO (premissa A1) — é o que permite compilar L1 em
    sucessões proibidas sem aritmética temporal dentro do solver."""

    id: str
    nome: str
    inicio: time
    fim: time
    vira_o_dia: bool  # explícito, não deduzido (LIN-03)

    @property
    def duracao_horas(self) -> float:
        i = self.inicio.hour + self.inicio.minute / 60
        f = self.fim.hour + self.fim.minute / 60
        if self.vira_o_dia:
            f += 24
        return round(f - i, 4)

    @property
    def noturno(self) -> bool:
        """Intersecta a faixa 22h-5h (CLT art. 73, §2º)."""
        inicio_h = self.inicio.hour + self.inicio.minute / 60
        fim_h = inicio_h + self.duracao_horas
        # faixa noturna repetida por dia, para cobrir turnos que viram o dia
        for base in (0, 24):
            noite_ini, noite_fim = 22 + base - 24, 5 + base
            if inicio_h < noite_fim and fim_h > noite_ini:
                return True
        return False

    def intervalo_ate(self, seguinte: "TipoDeTurno") -> float:
        """Horas de descanso entre este turno num dia e `seguinte` no dia
        posterior. Base da compilação de L1 (CLT art. 66)."""
        fim_h = self.inicio.hour + self.inicio.minute / 60 + self.duracao_horas
        inicio_seguinte = seguinte.inicio.hour + seguinte.inicio.minute / 60 + 24
        return round(inicio_seguinte - fim_h, 4)


@dataclass(frozen=True)
class Contrato:
    id: str
    regime: Regime
    min_plantoes: int
    max_plantoes: int
    max_dias_consecutivos: int
    min_dias_consecutivos: int
    min_folgas_consecutivas: int
    max_fins_de_semana: int
    exige_fim_de_semana_completo: bool
    horizonte_meses: int = 1  # janela de realimentação (CTL-03): vem do dado


@dataclass(frozen=True)
class Pessoa:
    id: str
    nome: str
    contrato_id: str
    habilitacoes: tuple[str, ...]


@dataclass(frozen=True)
class Plantao:
    id: str
    data: date
    tipo_de_turno_id: str
    habilitacao_id: str
    demanda_minima: int  # H2, rígida
    demanda_otima: int  # S1, peso 30

    @property
    def fim_de_semana(self) -> bool:
        return self.data.weekday() >= 5


@dataclass(frozen=True)
class Preferencia:
    """Uma única gramática (LIN-02): sempre `data`; `tipo_de_turno_id` opcional
    significa "todos os turnos daquele dia"."""

    pessoa_id: str
    data: date
    tipo: TipoPreferencia
    tipo_de_turno_id: str | None = None

    def cobre(self, plantao: Plantao) -> bool:
        if plantao.data != self.data:
            return False
        return self.tipo_de_turno_id in (None, plantao.tipo_de_turno_id)


@dataclass(frozen=True)
class RegraInterna:
    """Política da organização. Distinta das legais pelo campo `origem` do
    catálogo; peso limitado a 30 pela guarda de `restricoes_modelo` (REG-04)."""

    id: str
    descricao: str
    natureza: Natureza
    parametros: dict
    peso: int | None = None


@dataclass(frozen=True)
class Alocacao:
    pessoa_id: str
    plantao_id: str


@dataclass(frozen=True)
class Violacao:
    restricao_id: str
    origem: Origem
    natureza: Natureza  # rígida bloqueia troca; flexível apenas soma custo
    fonte: str  # 'CLT art. 66' | 'INRC-II S4' | id da regra interna
    descricao: str
    peso: int = 0
    pessoa_id: str | None = None
    plantao_id: str | None = None
    data: date | None = None

    def __str__(self) -> str:  # mensagem legível ao plantonista (UX-02)
        onde = f" [{self.pessoa_id}" if self.pessoa_id else " ["
        if self.data:
            onde += f" em {self.data.isoformat()}"
        onde += "]"
        return f"{self.descricao} ({self.fonte}){onde}"


@dataclass(frozen=True)
class Evento:
    """Registro append-only dentro do arquivo da escala (E1).

    A ordem é a POSIÇÃO na lista, nunca o carimbo de tempo (INV-3/LIN-05):
    `quando` é informativo, não ordenador.
    """

    tipo: TipoEvento
    quem: str  # identidade auto-declarada — fronteira de segurança A5/GOV-04
    quando: str  # ISO-8601, informativo
    dados: dict


@dataclass(frozen=True)
class Fronteira:
    """Estado herdado do período anterior, por pessoa."""

    ultimo_tipo_de_turno_id: str | None = None
    dias_trabalhados_consecutivos: int = 0
    folgas_consecutivas: int = 0
    total_plantoes: int = 0
    fins_de_semana_trabalhados: int = 0


@dataclass(frozen=True)
class Instancia:
    """Entrada validada de um período."""

    inicio: date
    fim: date
    habilitacoes: tuple[Habilitacao, ...]
    tipos_de_turno: tuple[TipoDeTurno, ...]
    contratos: tuple[Contrato, ...]
    pessoas: tuple[Pessoa, ...]
    plantoes: tuple[Plantao, ...]
    preferencias: tuple[Preferencia, ...] = ()
    regras_internas: tuple[RegraInterna, ...] = ()

    def turno(self, tid: str) -> TipoDeTurno:
        return next(t for t in self.tipos_de_turno if t.id == tid)

    def contrato_de(self, pessoa: Pessoa) -> Contrato:
        return next(c for c in self.contratos if c.id == pessoa.contrato_id)

    def plantao(self, pid: str) -> Plantao:
        return next(p for p in self.plantoes if p.id == pid)

    def pessoa(self, pid: str) -> Pessoa:
        return next(p for p in self.pessoas if p.id == pid)

    @property
    def dias(self) -> list[date]:
        n = (self.fim - self.inicio).days + 1
        return [self.inicio + timedelta(days=i) for i in range(n)]

    def plantoes_do_dia(self, d: date) -> list[Plantao]:
        return [p for p in self.plantoes if p.data == d]

    def elegivel(self, pessoa: Pessoa, plantao: Plantao) -> bool:
        """H4 + indisponibilidade rígida. Usada tanto pela poda de variáveis do
        solver quanto pela verificação (a troca pode alocar um inelegível)."""
        if plantao.habilitacao_id not in pessoa.habilitacoes:
            return False
        for pref in self.preferencias:
            if (
                pref.pessoa_id == pessoa.id
                and pref.tipo is TipoPreferencia.INDISPONIVEL
                and pref.cobre(plantao)
            ):
                return False
        return True


@dataclass(frozen=True)
class Escala:
    """snapshot publicado + eventos; a vigente é derivada (E1, INV-3)."""

    id: str
    inicio: date
    fim: date
    estado_escala: EstadoEscala
    alocacoes: tuple[Alocacao, ...]
    eventos: tuple[Evento, ...] = ()
    status_solver: str = ""
    otimalidade_provada: bool = False
    custo: int = 0
    custo_por_restricao: dict = field(default_factory=dict)

    def vigente(self) -> "Escala":
        """Aplica os eventos NA ORDEM DA LISTA (INV-3). Determinístico:
        mesma dupla (snapshot, eventos) → mesma escala, em qualquer
        implementação que respeite a ordem posicional."""
        alocacoes = list(self.alocacoes)
        for ev in self.eventos:
            if ev.tipo is TipoEvento.TROCA_EFETIVADA:
                a = Alocacao(ev.dados["pessoa_a"], ev.dados["plantao_a"])
                b = Alocacao(ev.dados["pessoa_b"], ev.dados["plantao_b"])
                if a in alocacoes and b in alocacoes:
                    alocacoes.remove(a)
                    alocacoes.remove(b)
                    alocacoes.append(Alocacao(a.pessoa_id, b.plantao_id))
                    alocacoes.append(Alocacao(b.pessoa_id, a.plantao_id))
        return replace(self, alocacoes=tuple(alocacoes))

    def plantoes_de(self, pessoa_id: str) -> list[str]:
        return [a.plantao_id for a in self.alocacoes if a.pessoa_id == pessoa_id]

    def pessoas_em(self, plantao_id: str) -> list[str]:
        return [a.pessoa_id for a in self.alocacoes if a.plantao_id == plantao_id]


@dataclass(frozen=True)
class Contexto:
    """Contexto de avaliação — SEMPRE completo (E3, resolve ASS-01).

    Não existe caminho para verificar restrições sem fronteira: ela é
    parâmetro obrigatório do construtor. Ausência de período anterior é
    representada por fronteiras vazias explícitas, não por omissão.
    """

    instancia: Instancia
    fronteira: dict[str, Fronteira]

    def __post_init__(self) -> None:
        faltando = [
            p.id for p in self.instancia.pessoas if p.id not in self.fronteira
        ]
        if faltando:
            raise ValueError(
                "Contexto incompleto: sem fronteira para "
                + ", ".join(sorted(faltando))
                + ". Use Contexto.sem_historico(instancia) quando não houver "
                "período anterior."
            )

    @classmethod
    def sem_historico(cls, instancia: Instancia) -> "Contexto":
        """Primeiro período: fronteira vazia EXPLÍCITA (distingue de erro,
        ASS-02)."""
        return cls(instancia, {p.id: Fronteira() for p in instancia.pessoas})

    def fronteira_de(self, pessoa_id: str) -> Fronteira:
        return self.fronteira[pessoa_id]


@dataclass(frozen=True)
class Avaliacao:
    violacoes: tuple[Violacao, ...]
    custo: int
    custo_por_restricao: dict[str, int]
    distribuicao: dict

    @property
    def rigidas(self) -> tuple[Violacao, ...]:
        return tuple(v for v in self.violacoes if v.natureza is Natureza.RIGIDA)

    @property
    def flexiveis(self) -> tuple[Violacao, ...]:
        return tuple(v for v in self.violacoes if v.natureza is Natureza.FLEXIVEL)


def ordenar(itens: Iterable) -> list:
    """Ordem determinística por id — o determinismo não pode depender da ordem
    de leitura do arquivo (§8 de specs/technical/modelo-cpsat.md)."""
    return sorted(itens, key=lambda x: x.id)
