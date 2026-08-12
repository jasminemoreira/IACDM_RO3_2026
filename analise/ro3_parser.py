"""Parser da tabela de achados da Fase 2 (IACDM / Versus 0.12.4+).

Lê, por projeto:
  <ws>/specs/design/coverage-matrix.md   -> achados (id | módulo | lente | severidade | descrição)
  <ws>/specs/technical/architecture.md   -> módulos canônicos (M-01 | módulo | ...)
  <ws>/.versus/state.json                -> lentes condicionais declaradas ativas na Fase 2

Princípio: FALHA ALTO. Um achado malformado é erro, nunca linha ignorada em
silêncio. Ignorar em silêncio produziria uma análise de RO3 que parece
completa e não é — o modo de falha mais caro deste lote.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- vocabulário

class ErroDeFormato(Exception):
    """Formato do achado violado. Interrompe — nunca degrada para 'melhor esforço'."""



# Os nomes canônicos vêm do BUNDLE INSTALADO, não de cópia local — mesma razão do
# `predicao_cega.py`: uma lista escrita à mão diverge da extensão sem avisar, e aí o
# parser recusa lente legítima ou aceita nome que o gate já não aceita.
def _lentes_do_bundle() -> tuple[list[str], list[str]]:
    import json as _json, re as _re
    base = Path.home() / ".vscode-server" / "extensions"
    achadas = sorted(base.glob("jasminemoreira.versus-claude-*/out/bundle/server.js"))
    if len(achadas) != 1:
        raise ErroDeFormato(
            f"{len(achadas)} bundles versus-claude instalados; é preciso exatamente 1 para "
            f"o parser saber contra qual vocabulário validar.")
    txt = achadas[0].read_text(encoding="utf-8", errors="replace")
    defs = _re.findall(
        r'\{\s*name:\s*"([^"]+)",\s*question:\s*"(?:[^"\\]|\\.)*",'
        r'\s*failureClass:\s*"(?:[^"\\]|\\.)*"(?:,\s*trigger:\s*"((?:[^"\\]|\\.)*)")?\s*\}', txt)
    def lim(x):
        try: return _json.loads(f'"{x}"')
        except _json.JSONDecodeError: return x
    uni = [lim(n) for n, g in defs if not g]
    con = [lim(n) for n, g in defs if g]
    if len(uni) != 7 or len(con) != 12:
        raise ErroDeFormato(f"extraí {len(uni)} universais e {len(con)} condicionais do "
                            f"bundle; esperado 7 e 12. O formato de LensDef mudou.")
    return uni, con


UNIVERSAIS, CONDICIONAIS = _lentes_do_bundle()
LENTES = UNIVERSAIS + CONDICIONAIS

# Abreviações do BATCH-PROTOCOL §2 — só para relatório legível. NUNCA aceitas
# como entrada: aceitá-las reabriria o split "Segurança"/"SEG"/"Security" que a
# 0.12.1 fechou.
SIGLA = {
    "Assumptions": "PRE", "Architectural": "ARQ", "Implementability": "IMP",
    "Scientific": "CIE", "Security": "SEG", "Performance": "DES",
    "Regulatory": "REG", "Resilience": "RES", "UI/UX": "UX",
    "Migration / Coexistence": "MIG", "Sustainability / Proportionality": "SUS",
    "Ethical / Human Impact": "ETI", "Process / Workflow": "PRO",
    "Governance / Accountability": "GOV", "Observability / Operability": "OBS",
    "Control Engineering": "CTR", "Game Theory": "JOG",
    "Linguistics / Grammar": "LIN", "Mechanical Engineering": "MEC",
}

# Canal declarado para o Passo 5 do §4 (achado que não coube em nenhuma lente).
# Sem ele o Passo 5 é inrespondível: o formato não teria onde registrar o achado.
SEM_LENTE = "NENHUMA"

# As três severidades do método. Sem categorias novas (§5).
SEVERIDADES = {
    "🔴": "critico", "🟡": "importante", "🟢": "sugestao",
    "critical": "critico", "important": "importante", "suggestion": "sugestao",
    "critico": "critico", "importante": "importante", "sugestao": "sugestao",
}

# `M-` é reservado para módulos (architecture.md). A guidance 0.12.4 proíbe usá-lo
# como prefixo de achado; Eng. Mecânica usa `MEC-`. O gate da extensão já descarta
# essas linhas da contagem — aqui viram erro explícito, para não sumirem caladas.
PREFIXO_RESERVADO = "M"

RE_ID = re.compile(r"^([A-Za-z]{1,4})-(\d+)$")
RE_ID_MODULO = re.compile(r"^M-(\d+)$")
RE_DUPLICA = re.compile(r"duplica\s*:\s*([A-Za-z]{1,4}-\d+|none|nenhum[ao]?)", re.I)
RE_SEPARADOR = re.compile(r"^[\s|:-]+$")
RE_ITERACAO = re.compile(r"itera[cç][aã]o\s*(\d+)", re.I)
RE_ITERACAO_EN = re.compile(r"iteration\s*(\d+)", re.I)
RE_VERSAO = re.compile(r"^#+\s*V\s*\(?(\d+)\)?\b", re.I)
# A guidance é escrita em inglês, mas a sessão registra no idioma em que se conversa.
# Aceitar só "ACTIVATED LENSES" recusaria um projeto perfeitamente válido — foi o que
# aconteceu no T01, que gravou "LENTES ATIVADAS na Fase 2".
MARCAS_LENTES = ("ACTIVATED LENSES", "LENTES ATIVADAS")


@dataclass
class Achado:
    id: str
    modulo: str
    lente: str
    severidade: str
    descricao: str
    projeto: str
    duplica: str | None = None
    linha: int = 0
    iteracao: int = 1

    @property
    def sigla(self) -> str:
        return SIGLA.get(self.lente, self.lente)


@dataclass
class Projeto:
    task_id: str
    achados: list[Achado] = field(default_factory=list)
    modulos: list[str] = field(default_factory=list)
    lentes_ativas: list[str] = field(default_factory=list)  # universais + condicionais declaradas
    condicionais_ativas: list[str] = field(default_factory=list)   # união, p/ relatório
    condicionais_por_iteracao: dict = field(default_factory=dict)  # {iteração: [lentes]}
    # módulo -> ids, para achados de iterações anteriores cujo módulo a versão final
    # da arquitetura não tem mais. Informação, não erro: o artefato foi sobrescrito.
    modulos_de_versoes_antigas: dict = field(default_factory=dict)
    # união dos módulos de TODAS as versões da arquitetura (v0.12.5+)
    modulos_todas_versoes: list = field(default_factory=list)
    # {versão: quantos módulos a tabela daquela versão traz}. Existe para o relatório
    # poder mostrar que a última versão é um DELTA (T23-canario: 12, 12, 4) em vez de
    # imprimir "4 módulos" para um produto de 12.
    modulos_por_versao: dict = field(default_factory=dict)


# ------------------------------------------------------------------ utilidades

def _norm(s: str) -> str:
    """Normaliza para comparação: minúsculas, sem acento, sem espaço supérfluo."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"\s*/\s*", "/", s)
    return re.sub(r"\s+", " ", s)


_LENTE_POR_NORM = {_norm(n): n for n in LENTES}
_SIGLA_POR_NORM = {_norm(v): k for k, v in SIGLA.items()}


def _celulas(linha: str) -> list[str]:
    bruto = linha.strip()
    if bruto.startswith("|"):
        bruto = bruto[1:]
    if bruto.endswith("|"):
        bruto = bruto[:-1]
    return [c.strip() for c in bruto.split("|")]


def _tabelas(texto: str):
    """Gera (n_linha, celulas) de toda linha que é linha de tabela markdown."""
    for n, linha in enumerate(texto.splitlines(), start=1):
        if linha.strip().startswith("|") and not RE_SEPARADOR.match(linha):
            yield n, _celulas(linha)


# ------------------------------------------------------------------- leitores

def ler_modulos(caminho: Path) -> tuple[list[str], list[str], dict[int, int]]:
    """Módulos canônicos da tabela da Fase 1 (M-01 | módulo | ...).

    A chave estável entre fases é o NOME (coluna 2); o id `M-` só torna a linha
    reconhecível por máquina (v0.12.2).
    """
    if not caminho.exists():
        raise ErroDeFormato(f"{caminho}: architecture.md ausente — sem lista canônica de módulos, "
                            f"o modo de falha 'módulo inexistente' fica indetectável.")
    # Desde a v0.12.5 a Fase 3 ACRESCENTA `## V(N+1)` em vez de sobrescrever, para que a
    # lista de módulos de cada iteração sobreviva. Logo o mesmo nome aparece em várias
    # seções — isso é o formato funcionando, não duplicata. Repetição DENTRO de uma
    # versão continua sendo erro.
    por_versao: dict[int, list[str]] = {}
    vistos_na_versao: dict[int, dict[str, int]] = {}
    versao = 1
    for n, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        if linha.lstrip().startswith("#"):
            if (m := RE_VERSAO.match(linha.strip())):
                versao = int(m.group(1))
            continue
        if not linha.strip().startswith("|") or RE_SEPARADOR.match(linha):
            continue
        cel = _celulas(linha)
        if not RE_ID_MODULO.match(cel[0]):
            continue
        if len(cel) < 2 or not cel[1]:
            raise ErroDeFormato(f"{caminho}:{n}: linha de módulo {cel[0]} sem nome na coluna 2.")
        nome = cel[1].strip().strip("`")
        chave = _norm(nome)
        vistos = vistos_na_versao.setdefault(versao, {})
        if chave in vistos:
            raise ErroDeFormato(f"{caminho}:{n}: módulo '{nome}' repetido dentro da versão V{versao} "
                                f"(já em {caminho.name}:{vistos[chave]}).")
        vistos[chave] = n
        por_versao.setdefault(versao, []).append(nome)

    # A versão corrente é a última seção; é contra ela que a última iteração é validada.
    #
    # CUIDADO — a última seção pode ser um DELTA. O T23-canario escreveu V(1) e V(2) com
    # os 12 módulos e V(3) com os 4 que mudaram; os outros oito continuam existindo, só não
    # foram reescritos. Ler a última seção crua dá "4 módulos" para um produto de 12.
    #
    # Delta e remoção são INDISTINGUÍVEIS pelo texto: nos dois casos o nome sumiu da última
    # tabela. Tentei resolver por carry-forward (a versão corrente é a acumulada) e estava
    # errado — os outros três projetos removem módulos de verdade, e o acumulado os
    # ressuscitava: T21 12→13, T24 9→11, T22 11→14.
    #
    # Como o número não entra em nenhuma medida da RO3 — os Passos 1 e 4 usam o módulo
    # ESCRITO em cada achado, não esta lista —, a saída certa é não escolher em silêncio.
    # `modulos` segue sendo a última versão (comportamento original, correto para quem
    # escreve a tabela inteira), e `por_versao` sobe junto para o relatório poder mostrar o
    # perfil e deixar o delta visível em vez de calado.
    modulos = por_versao[max(por_versao)] if por_versao else []
    todos = [m for v in sorted(por_versao) for m in por_versao[v]]
    perfil = {v: len(ms) for v, ms in sorted(por_versao.items())}
    if not modulos:
        raise ErroDeFormato(f"{caminho}: nenhuma linha de módulo (M-\\d+) — arquitetura em prosa. "
                            f"O gate architecture_doc da Fase 1 deveria ter recusado isto.")
    return modulos, todos, perfil


def ler_lentes_ativas(caminho: Path) -> dict[int, list[str]]:
    """Condicionais declaradas ativas, POR ITERAÇÃO da Fase 2.

    Desde a v0.14.0 a declaração é ESTADO ESTRUTURADO: `state.activatedLenses` é um
    array de `LensActivation` com `conditional`, `iteration` e `againstVersion`. Ler o
    campo em vez de parsear prosa elimina a classe inteira de erro que já custou dois
    projetos — a decisão gravada em português, o marcador ausente, o nome abreviado.

    O parse da prosa fica só para projetos anteriores à v0.14.0, identificados pela
    AUSÊNCIA de `stateVersion` — o mesmo critério que a extensão usa para decidir se
    aceita o formato antigo. Projeto novo com prosa e sem campo é erro, não fallback:
    seria a garantia estrutural virando opcional.
    """
    if not caminho.exists():
        raise ErroDeFormato(f"{caminho}: state.json ausente — sem ele não dá para saber quais "
                            f"condicionais foram declaradas ativas.")
    estado = json.loads(caminho.read_text(encoding="utf-8"))

    ativ = estado.get("activatedLenses")
    if ativ:
        por_iteracao: dict[int, list[str]] = {}
        for e in ativ:
            it = e.get("iteration", 1)
            cond = [c for c in e.get("conditional", []) if _norm(c) in _LENTE_POR_NORM]
            desconhecidas = [c for c in e.get("conditional", []) if _norm(c) not in _LENTE_POR_NORM]
            if desconhecidas:
                raise ErroDeFormato(
                    f"{caminho}: iteração {it} declara lente(s) fora do conjunto canônico: "
                    f"{', '.join(desconhecidas)}. O enum de record_activated_lenses deveria "
                    f"ter barrado — estado gravado por caminho que não passou pela ferramenta.")
            por_iteracao[it] = [_LENTE_POR_NORM[_norm(c)] for c in cond]
        return por_iteracao

    if estado.get("stateVersion") is not None:
        raise ErroDeFormato(
            f"{caminho}: projeto criado sob a v0.14.0+ (stateVersion presente) mas sem "
            f"`activatedLenses`. A declaração estruturada é obrigatória; prosa não é "
            f"aceita como substituto em projeto novo.")

    # --- projeto anterior à v0.14.0: prosa, com os dois marcadores de idioma ---
    por_iteracao = {}
    for d in estado.get("decisions", []):
        conteudo = d.get("content", "")
        alto = conteudo.upper()
        marca = next((m for m in MARCAS_LENTES if m in alto), None)
        if marca is None:
            continue
        ini_m = alto.index(marca)
        corte = min((c for c in (alto.find("NOT ACTIVATED", ini_m + 1),
                                 alto.find("NÃO ATIVADAS", ini_m + 1),
                                 alto.find("NAO ATIVADAS", ini_m + 1)) if c != -1), default=-1)
        trecho = _norm(conteudo[ini_m:corte if corte != -1 else len(conteudo)])
        m = RE_ITERACAO.search(conteudo[:ini_m + 200]) or RE_ITERACAO_EN.search(conteudo[:ini_m + 200])
        por_iteracao[int(m.group(1)) if m else 1] = [n for n in CONDICIONAIS if _norm(n) in trecho]
    if not por_iteracao:
        raise ErroDeFormato(f"{caminho}: nenhuma declaração de lentes — nem campo estruturado "
                            f"nem decisão em prosa.")
    return por_iteracao


def _resolver_lente(bruto: str, caminho: Path, n: int) -> str:
    chave = _norm(bruto.strip().strip("`*"))
    if chave == _norm(SEM_LENTE):
        return SEM_LENTE
    if chave in _LENTE_POR_NORM:
        return _LENTE_POR_NORM[chave]
    if chave in _SIGLA_POR_NORM:
        canonico = _SIGLA_POR_NORM[chave]
        raise ErroDeFormato(
            f"{caminho}:{n}: coluna `lente` traz a sigla '{bruto}'. Use o nome canônico "
            f"'{canonico}'. Siglas e traduções quebram a agregação entre projetos.")
    raise ErroDeFormato(
        f"{caminho}:{n}: lente desconhecida '{bruto}'. Use um dos 19 nomes canônicos "
        f"ou '{SEM_LENTE}' para achado que não coube em nenhuma lente (Passo 5).")


def ler_achados(caminho: Path, projeto: str) -> list[Achado]:
    """Tabela de achados da Fase 2. Valida forma; não julga conteúdo."""
    if not caminho.exists():
        raise ErroDeFormato(f"{caminho}: coverage-matrix.md ausente.")

    linhas = caminho.read_text(encoding="utf-8").splitlines()

    # A Fase 2 faz LOOP com a Fase 3: cada iteração critica uma versão diferente da
    # arquitetura e escreve sua própria tabela sob um cabeçalho `## Iteração N`. Uma
    # varredura que parasse na primeira tabela engoliria as demais em silêncio — que
    # é exatamente o modo de falha que este parser existe para impedir. Varre o
    # arquivo INTEIRO e mantém a iteração de cada achado.
    achados: list[Achado] = []
    iteracao, dentro_da_tabela, achou_tabela = 1, False, False

    for n, linha in enumerate(linhas, start=1):
        crua = linha.strip()

        if crua.startswith("#"):
            if (m := RE_ITERACAO.search(crua)):
                iteracao = int(m.group(1))
            dentro_da_tabela = False
            continue

        if not crua.startswith("|"):
            dentro_da_tabela = False
            continue

        if RE_SEPARADOR.match(linha):
            continue

        cel = _celulas(linha)

        if not dentro_da_tabela:
            cabecalho = {_norm(c) for c in cel}
            if "id" in cabecalho and ({"lens", "lente"} & cabecalho):
                dentro_da_tabela, achou_tabela = True, True
            continue          # linha de cabeçalho, ou tabela que não é de achados

        if len(cel) < 5:
            raise ErroDeFormato(
                f"{caminho}:{n}: linha de achado com {len(cel)} campo(s); "
                f"o formato exige 5 (id | módulo | lente | severidade | descrição). Linha: {linha.strip()}")

        bruto_id = cel[0].strip().strip("`*")
        casado = RE_ID.match(bruto_id)
        if not casado:
            raise ErroDeFormato(
                f"{caminho}:{n}: achado sem id na primeira coluna (encontrado '{cel[0]}'). "
                f"Sem id não dá para distinguir sobreposição de ortogonalidade.")
        if casado.group(1).upper() == PREFIXO_RESERVADO:
            raise ErroDeFormato(
                f"{caminho}:{n}: achado usa o prefixo reservado 'M-' ({bruto_id}), que identifica "
                f"MÓDULO. Eng. Mecânica usa 'MEC-'. O gate da extensão descarta estas linhas "
                f"da contagem — se passassem aqui, sumiriam da análise sem aviso.")

        severidade = _norm(cel[3].strip().strip("`*"))
        severidade = severidade.split()[0] if severidade else ""
        if severidade not in SEVERIDADES:
            raise ErroDeFormato(
                f"{caminho}:{n}: severidade '{cel[3]}' fora das três do método "
                f"(🔴 crítico | 🟡 importante | 🟢 sugestão).")

        descricao = " | ".join(cel[4:]).strip()
        dup = None
        if (m := RE_DUPLICA.search(descricao)):
            alvo = m.group(1)
            if not alvo.lower().startswith(("none", "nenhum")):
                dup = alvo

        achados.append(Achado(
            id=bruto_id, modulo=cel[1].strip().strip("`"),
            lente=_resolver_lente(cel[2], caminho, n),
            severidade=SEVERIDADES[severidade], descricao=descricao,
            projeto=projeto, duplica=dup, linha=n, iteracao=iteracao,
        ))

    if not achou_tabela:
        raise ErroDeFormato(
            f"{caminho}: nenhuma tabela de achados encontrada (esperado um cabeçalho com "
            f"colunas 'id' e 'lente'/'lens'). Uma grade só-severidade não é analisável.")
    if not achados:
        raise ErroDeFormato(f"{caminho}: tabela de achados vazia. Uma passada adversarial por "
                            f"19 lentes que não achou nada não foi adversarial.")
    return achados


# ---------------------------------------------------------------- consistência

def validar(proj: Projeto, caminho_matriz: Path) -> None:
    """Checagens que dependem do projeto inteiro, não de uma linha só."""
    por_id: dict[str, Achado] = {}
    for a in proj.achados:
        if a.id in por_id:
            raise ErroDeFormato(
                f"{caminho_matriz}:{a.linha}: id '{a.id}' repetido "
                f"(já usado na linha {por_id[a.id].linha}). Ids são únicos no projeto.")
        por_id[a.id] = a

    ultima_iteracao = max((a.iteracao for a in proj.achados), default=1)
    modulos_norm = {_norm(m): m for m in proj.modulos}
    antigos_norm = {_norm(m) for m in proj.modulos_todas_versoes}
    # Cada achado é validado contra o conjunto vigente NA ITERAÇÃO DELE, não contra a
    # união: um achado da iteração 1 usando lente que só foi declarada na 2 é erro real.
    ativas_por_it = {
        it: {_norm(l) for l in UNIVERSAIS + lentes}
        for it, lentes in proj.condicionais_por_iteracao.items()
    }

    for a in proj.achados:
        if a.duplica:
            if a.duplica == a.id:
                raise ErroDeFormato(f"{caminho_matriz}:{a.linha}: achado '{a.id}' marcado como "
                                    f"duplicata de si mesmo.")
            if a.duplica not in por_id:
                raise ErroDeFormato(
                    f"{caminho_matriz}:{a.linha}: achado '{a.id}' marca 'duplica: {a.duplica}', "
                    f"mas '{a.duplica}' não existe neste projeto.")

        if _norm(a.modulo) not in modulos_norm:
            # A Fase 2 faz loop com a Fase 3 e `architecture.md` é SOBRESCRITO a cada
            # iteração: só a última versão sobrevive. Um achado da iteração 1 pode
            # apontar um módulo que a V(2) eliminou — isso é evolução do desenho, não
            # deriva de nome. Só a ÚLTIMA iteração tem verdade de referência viva, e é
            # a única em que a ausência é erro.
            if a.iteracao == ultima_iteracao and _norm(a.modulo) not in antigos_norm:
                raise ErroDeFormato(
                    f"{caminho_matriz}:{a.linha}: achado '{a.id}' aponta o módulo '{a.modulo}', "
                    f"ausente da tabela de módulos da Fase 1 ({', '.join(proj.modulos)}). "
                    f"Deriva de nome quebra a rastreabilidade por módulo.")
            proj.modulos_de_versoes_antigas.setdefault(a.modulo, []).append(a.id)

        if a.lente != SEM_LENTE:
            vigentes = ativas_por_it.get(a.iteracao)
            if vigentes is None:
                raise ErroDeFormato(
                    f"{caminho_matriz}:{a.linha}: achado '{a.id}' está na iteração {a.iteracao}, "
                    f"mas não há declaração de lentes para essa iteração "
                    f"(declaradas: {sorted(ativas_por_it)}). A v0.12.6 exige uma por rodada.")
            if _norm(a.lente) not in vigentes:
                declaradas = proj.condicionais_por_iteracao.get(a.iteracao, [])
                raise ErroDeFormato(
                    f"{caminho_matriz}:{a.linha}: achado '{a.id}' usa a lente '{a.lente}', que não é "
                    f"universal nem foi declarada ativa na iteração {a.iteracao} "
                    f"(ativas nessa rodada: {', '.join(declaradas) or 'nenhuma'}).")


def carregar(workspace: Path) -> Projeto:
    """Carrega e valida um workspace de projeto. Levanta ErroDeFormato ao primeiro problema."""
    ws = Path(workspace)
    task_id = ws.name
    matriz = ws / "specs" / "design" / "coverage-matrix.md"

    proj = Projeto(task_id=task_id)
    proj.modulos, proj.modulos_todas_versoes, proj.modulos_por_versao = ler_modulos(
        ws / "specs" / "technical" / "architecture.md")
    proj.condicionais_por_iteracao = ler_lentes_ativas(ws / ".versus" / "state.json")
    uniao: list[str] = []
    for it in sorted(proj.condicionais_por_iteracao):
        for l in proj.condicionais_por_iteracao[it]:
            if l not in uniao:
                uniao.append(l)
    proj.condicionais_ativas = uniao
    proj.lentes_ativas = UNIVERSAIS + uniao
    proj.achados = ler_achados(matriz, task_id)
    validar(proj, matriz)
    return proj
