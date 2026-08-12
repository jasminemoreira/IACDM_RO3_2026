"""CA-3, CA-4, CA-7, CA-10, CA-11, CA-12, CA-17, CA-18, CA-19, CA-23 — validacao.

Cada teste exige que a mensagem NOMEIE o defeito. "Ha um ciclo" nao atende CA-3; e
precisa dizer QUAIS datasets formam o ciclo.
"""

from __future__ import annotations

import pytest

from t24.catalog import Catalog
from t24.cli import carregar
from t24.lineage_graph import LineageGraph
from t24.model import DatasetId, NomeInvalido
from t24.validation import CatalogInvalid, LoadedCatalog, Violation, ordenar


def violacoes_de(caminho):
    with pytest.raises(CatalogInvalid) as erro:
        carregar(caminho)
    return erro.value.violacoes


def texto(violacoes) -> str:
    return " | ".join(str(v) for v in violacoes)


def test_ciclo_nomeia_os_dois_datasets(fixtures):
    """CA-3: nomear o ciclo, nao apenas detecta-lo.

    E a razao pela qual Kahn (1962) sozinho nao bastaria: ele detecta QUE ha ciclo,
    pelas arestas remanescentes, mas nao QUAL e.
    """
    msg = texto(violacoes_de(fixtures / "ciclo"))
    assert "financeiro.receita" in msg
    assert "financeiro.previsao" in msg


def test_aresta_pendente_nomeia_referencia(fixtures):
    """CA-4: a mensagem contem a identidade quebrada."""
    msg = texto(violacoes_de(fixtures / "aresta-pendente"))
    assert "vendas.inexistente" in msg


def test_dominio_sem_dono_nomeia_dominio(fixtures):
    """CA-7 / INV-2."""
    msg = texto(violacoes_de(fixtures / "dominio-sem-dono"))
    assert "dono" in msg
    assert "financeiro.yaml" in msg


def test_nome_com_ponto_recusado(fixtures):
    """CA-10 / ASM-01: sem isso, 'vendas.br.pedidos' resolveria o dono errado."""
    msg = texto(violacoes_de(fixtures / "nome-com-ponto"))
    assert "vendas.br" in msg


def test_parse_recusa_identidade_com_dois_pontos():
    """CA-10 pelo outro lado: a leitura da identidade tambem recusa."""
    with pytest.raises(NomeInvalido):
        DatasetId.parse("vendas.br.pedidos")


def test_contato_ambiguo_exige_desambiguacao(fixtures):
    """CA-11 / GOV-04: duas pessoas com o mesmo contato NAO colapsam num dono.

    Este e o defeito inverso do GOV-03, e a resposta e recusar a ambiguidade.
    """
    msg = texto(violacoes_de(fixtures / "dono-ambiguo"))
    assert "dados@empresa.com" in msg
    assert "Maria Silva" in msg and "Ana Costa" in msg


def test_campo_desconhecido_nomeado(fixtures):
    """CA-12 / MEC-01: ignorar em silencio faria a aresta sumir sem aviso."""
    msg = texto(violacoes_de(fixtures / "campo-desconhecido"))
    assert "alimentado_pro" in msg


def test_loaded_catalog_recusa_construcao_com_violacao():
    """CA-17 / IMPL-06 — a garantia central do desenho, testada DIRETAMENTE.

    Nao pelo fluxo normal: chamando o construtor a mao, como qualquer codigo poderia.
    E isso que separa garantia de linguagem de convencao documentada.
    """
    vazio = Catalog(())
    grafo = LineageGraph.build((), ())
    with pytest.raises(CatalogInvalid):
        LoadedCatalog(vazio, grafo, [Violation("x.yaml", "defeito qualquer")])

    # E com a lista vazia, constroi normalmente.
    assert LoadedCatalog(vazio, grafo, []) is not None


def test_violacoes_semanticas_agregadas(fixtures):
    """CA-18 / A9, estagio SEMANTICO: 3 defeitos reportados de uma vez.

    Duas arestas pendentes em arquivos diferentes mais um contato ambiguo — todos
    reportados numa unica execucao, nao um por vez.
    """
    violacoes = violacoes_de(fixtures / "tres-defeitos")
    msg = texto(violacoes)
    assert len(violacoes) >= 3
    assert "beta.nao_existe" in msg
    assert "delta.tambem_nao_existe" in msg
    assert "alguem@empresa.com" in msg


def test_violacoes_de_forma_agregadas(fixtures):
    """CA-18 / A9, estagio de FORMA: defeitos em ARQUIVOS DIFERENTES de uma vez."""
    violacoes = violacoes_de(fixtures / "defeitos-de-forma")
    msg = texto(violacoes)
    assert len(violacoes) >= 2
    assert "a.yaml" in msg and "b.yaml" in msg
    assert "dono" in msg
    assert "campo_inventado" in msg


def test_forma_porteia_semantica_para_nao_gerar_falso_positivo(fixtures):
    """A agregacao de A9 e POR ESTAGIO, e isso e deliberado.

    Se um arquivo falha na forma, a validacao semantica NAO roda sobre o catalogo
    parcial: toda aresta apontando para dataset do arquivo rejeitado viraria 'aresta
    pendente', que e um defeito INEXISTENTE. Reportar defeito que nao existe e pior que
    exigir uma segunda rodada — e o usuario enfrenta no maximo duas, nunca N.
    """
    violacoes = violacoes_de(fixtures / "defeitos-de-forma")
    assert all("nao esta declarado em nenhum dominio" not in str(v) for v in violacoes)


def test_ordem_deterministica(fixtures):
    """CA-19 / IMPL-01: duas execucoes produzem a MESMA ordem."""
    primeira = [str(v) for v in violacoes_de(fixtures / "tres-defeitos")]
    segunda = [str(v) for v in violacoes_de(fixtures / "tres-defeitos")]
    assert primeira == segunda


def test_violacao_sem_dominio_vem_primeiro():
    """CA-19 / IMPL-08: violacao sem dominio (parse que nem chegou a ler o campo)
    precede as com dominio."""
    entrada = [
        Violation("z.yaml", "com dominio", dominio="zeta"),
        Violation("a.yaml", "sem dominio"),
        Violation("b.yaml", "outra com dominio", dominio="alfa"),
    ]
    resultado = ordenar(entrada)
    assert resultado[0].dominio is None
    assert [v.dominio for v in resultado[1:]] == ["alfa", "zeta"]


def test_safe_load_recusa_objeto_python(fixtures):
    """CA-23 / SEC-01: yaml.load sem SafeLoader instanciaria objeto Python arbitrario.

    Teste NEGATIVO de seguranca: carregar um catalogo de terceiro nao pode executar
    codigo. O safe_load recusa a tag, e o erro vira Violation em vez de execucao.
    """
    violacoes = violacoes_de(fixtures / "yaml-inseguro")
    msg = texto(violacoes)
    assert "python/object" in msg or "YAML invalido" in msg or "nome" in msg
