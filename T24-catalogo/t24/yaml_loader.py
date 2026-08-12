"""M-06 yaml_loader — leitura do diretorio e validacao da FORMA.

Nao conhece regra de dominio: verifica campos obrigatorios, tipos e campos desconhecidos.

SEC-01 — `yaml.safe_load` OBRIGATORIO. `yaml.load` sem SafeLoader instancia objetos
Python arbitrarios, e carregar um catalogo de terceiro executaria codigo.
ASM-02 — le apenas `*.yaml` e `*.yml`; qualquer outro arquivo no diretorio e ignorado.
MEC-01 — campo desconhecido e VIOLACAO, nao e ignorado: silenciar `alimentado_pro:` faria
a aresta desaparecer sem aviso, o que e pior do que quebrar a evolucao do formato.
RES-01 / RES-04 — erro de parse e arquivo ilegivel viram Violation com arquivo e, quando
existe, linha. A excecao do PyYAML nunca vaza para o usuario.
LING-05 — se houver qualquer violacao, os docs parciais NAO devem ser usados: o contrato
e explicito e quem chama aborta.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .model import RawDomainDoc
from .validation import Violation

EXTENSOES = (".yaml", ".yml")

CAMPOS_RAIZ = {"dominio", "dono", "datasets"}
CAMPOS_DONO = {"nome", "contato"}
CAMPOS_DATASET = {"nome", "descricao", "dono", "alimentado_por"}


class DiretorioInvalido(Exception):
    """Diretorio de catalogo inexistente ou ilegivel (RES-02)."""


@dataclass(frozen=True)
class LoadResult:
    docs: tuple[RawDomainDoc, ...]
    violacoes: tuple[Violation, ...]

    @property
    def ok(self) -> bool:
        return not self.violacoes


def _linha_do_erro(erro: yaml.YAMLError) -> int | None:
    marca = getattr(erro, "problem_mark", None)
    return None if marca is None else marca.line + 1


def _checa_dono(valor: Any, arquivo: str, dominio: str | None, onde: str) -> list[Violation]:
    if not isinstance(valor, dict):
        return [Violation(arquivo, f"{onde}: 'dono' deve ser um objeto com nome e contato", dominio)]
    achados = []
    desconhecidos = set(valor) - CAMPOS_DONO
    if desconhecidos:
        achados.append(
            Violation(arquivo, f"{onde}: campo desconhecido em 'dono': {sorted(desconhecidos)}", dominio)
        )
    # ASM-03: a sobrescrita e total — nome e contato sao ambos obrigatorios.
    for campo in sorted(CAMPOS_DONO):
        if not isinstance(valor.get(campo), str) or not valor.get(campo, "").strip():
            achados.append(
                Violation(arquivo, f"{onde}: 'dono.{campo}' ausente ou vazio", dominio)
            )
    return achados


def _checa_doc(conteudo: Any, arquivo: str) -> list[Violation]:
    if not isinstance(conteudo, dict):
        return [Violation(arquivo, "o arquivo deve conter um objeto YAML na raiz")]

    dominio = conteudo.get("dominio") if isinstance(conteudo.get("dominio"), str) else None
    achados: list[Violation] = []

    desconhecidos = set(conteudo) - CAMPOS_RAIZ
    if desconhecidos:
        achados.append(
            Violation(arquivo, f"campo desconhecido na raiz: {sorted(desconhecidos)}", dominio)
        )

    if not isinstance(conteudo.get("dominio"), str) or not conteudo.get("dominio", "").strip():
        achados.append(Violation(arquivo, "'dominio' ausente ou vazio", dominio))

    if "dono" not in conteudo:
        achados.append(Violation(arquivo, "'dono' ausente: todo dominio precisa de dono (INV-2)", dominio))
    else:
        achados += _checa_dono(conteudo["dono"], arquivo, dominio, "dominio")

    datasets = conteudo.get("datasets")
    if datasets is None:
        achados.append(Violation(arquivo, "'datasets' ausente (use lista vazia se nao houver)", dominio))
        return achados
    if not isinstance(datasets, list):
        achados.append(Violation(arquivo, "'datasets' deve ser uma lista", dominio))
        return achados

    for indice, ds in enumerate(datasets):
        onde = f"datasets[{indice}]"
        if not isinstance(ds, dict):
            achados.append(Violation(arquivo, f"{onde}: deve ser um objeto", dominio))
            continue
        desconhecidos = set(ds) - CAMPOS_DATASET
        if desconhecidos:
            achados.append(
                Violation(arquivo, f"{onde}: campo desconhecido: {sorted(desconhecidos)}", dominio)
            )
        if not isinstance(ds.get("nome"), str) or not ds.get("nome", "").strip():
            achados.append(Violation(arquivo, f"{onde}: 'nome' ausente ou vazio", dominio))
        if "descricao" in ds and not isinstance(ds["descricao"], str):
            achados.append(Violation(arquivo, f"{onde}: 'descricao' deve ser texto", dominio))
        if "dono" in ds:
            achados += _checa_dono(ds["dono"], arquivo, dominio, onde)
        alimentado = ds.get("alimentado_por")
        if alimentado is not None:
            if not isinstance(alimentado, list):
                achados.append(Violation(arquivo, f"{onde}: 'alimentado_por' deve ser uma lista", dominio))
            else:
                for item in alimentado:
                    if not isinstance(item, str) or not item.strip():
                        achados.append(
                            Violation(arquivo, f"{onde}: item de 'alimentado_por' deve ser texto", dominio)
                        )
    return achados


def load_files(diretorio: Path) -> LoadResult:
    """Le todos os `*.yaml`/`*.yml` do diretorio e valida a forma de cada um."""
    if not diretorio.exists():
        raise DiretorioInvalido(f"diretorio de catalogo nao encontrado: {diretorio}")
    if not diretorio.is_dir():
        raise DiretorioInvalido(f"nao e um diretorio: {diretorio}")

    caminhos = sorted(p for p in diretorio.iterdir() if p.suffix.lower() in EXTENSOES)
    docs: list[RawDomainDoc] = []
    violacoes: list[Violation] = []

    for caminho in caminhos:
        arquivo = caminho.name
        try:
            texto = caminho.read_text(encoding="utf-8")
        except OSError as erro:
            # RES-04: sem linha a apontar — a Violation aceita linha ausente.
            violacoes.append(Violation(arquivo, f"arquivo ilegivel: {erro.strerror}"))
            continue
        try:
            conteudo = yaml.safe_load(texto)
        except yaml.YAMLError as erro:
            violacoes.append(
                Violation(arquivo, f"YAML invalido: {getattr(erro, 'problem', erro)}", None, _linha_do_erro(erro))
            )
            continue
        achados = _checa_doc(conteudo, arquivo)
        if achados:
            violacoes.extend(achados)
        else:
            docs.append(RawDomainDoc(arquivo=arquivo, conteudo=conteudo))

    return LoadResult(docs=tuple(docs), violacoes=tuple(violacoes))
