"""Sonda lexical de "dano a pessoas" — REFUTADA em 2026-08-13. Preservada como artefato.

    python3 sonda_eti_refutada.py

NÃO USE ESTA SONDA COMO EVIDÊNCIA. Ela está aqui porque o caminho falso faz parte do
registro, e porque é um exemplo concreto e reproduzível de um proxy lexical que produz
separação aparente sem medir o que diz medir.

O QUE ELA TENTAVA ADJUDICAR
---------------------------
A lente Ética ativou em 5 de 12 projetos pela Fase 2 e em 9 de 12 sob o gatilho corrigido
Y2, nos dois leitores externos. Nos quatro projetos disputados — Y2 liga, Fase 2 não
ligou —, a classe de falha estava presente e foi capturada por lentes vizinhas, ou ETI
genuinamente não se aplicava?

A ideia era buscar vocabulário de dano a pessoas nas descrições dos achados de OUTRAS
lentes, e comparar o grupo disputado com o grupo de controle.

O QUE ELA PRODUZIU
------------------
Contagens absolutas com separação aparentemente limpa, sem sobreposição:

    disputados   T27 29 · T26 23 · T31 22 · T28 17
    controle     T29 14 · T24  9 · T23  6

Foi reportado, em 2026-08-12, que isso sustentava "a Fase 2 sub-ativava ETI".

POR QUE ESTÁ ERRADA — três defeitos, verificados em 2026-08-13
--------------------------------------------------------------
**1. O termo dominante mede outra coisa.** `operador` é o mais frequente (33 de ~155
ocorrências) e refere-se com frequência ao **operador da metodologia** — quem conduz as
fases IACDM —, não a alguém afetado pelo sistema: *"decisão do operador"*, *"dívida aceita
pelo operador"*, *"premissa A5 aceita explicitamente pelo operador"*.

**2. Homônimos.** `escala` casa *"escala fixa de 2 casas decimais"* e *"não declara escala
nem direção"*; `bloque` casa *"a chave está bloqueada"*. Nenhum é dano a pessoa.

**3. Os termos que realmente denotam dano quase não aparecem.** Em sete projetos:
`prejud` 0 · `penaliz` 0 · `injust` 0 · `privacidade` 0 · `consentimento` 0 · `discrimin` 1.

**E a separação não sobrevive à normalização.** Como fração dos achados do projeto, os
grupos se sobrepõem — 16%–31% nos disputados contra 8%–13% no controle, com T28 (16%) e
T29 (13%) a três pontos um do outro. A "separação sem sobreposição" era efeito de os
projetos disputados terem as maiores matrizes do lote.

Com vocabulário estrito — só termos de dano, sem papéis nem homônimos — o sinal desaparece:
3 achados nos quatro disputados, 3 nos três de controle.

O QUE SUBSTITUIU
----------------
A adjudicação por **leitura** dos próprios achados, com critério fixado antes, cegamento e
dois juízes: `CRITERIO-ADJUDICACAO-ETI.md` e `cego/ETI-adjudicacao-*`. Resultado: a
fronteira ética/governança **não reproduz entre juízes** (κ = 0,341), o que é achado sobre
o conceito, não sobre a redação do critério.

A LIÇÃO, que é por que este arquivo existe
------------------------------------------
A separação era real e o erro foi não testar **o que a produzia**. Um proxy lexical precisa
de duas verificações antes de virar evidência: **quais termos disparam** (aqui, papéis
genéricos e homônimos) e **se o efeito sobrevive à normalização** pelo tamanho do texto
(aqui, não sobrevive).

É a mesma classe que o lote catalogou cinco vezes sob outro nome — medida que parece
verificar e não verifica.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ro3_parser import carregar  # noqa: E402

RO3 = Path(__file__).resolve().parent.parent
ETI = "Ethical / Human Impact"

PROJ = ["T21-certificados", "T24-catalogo", "T22-plantoes", "T23-canario", "T25-orcamento",
        "T26-extratos", "T27-despesas", "T28-agenda", "T29-retencao", "T30-notifica",
        "T31-precos", "T32-triagem"]

# Y2 liga ETI nestes quatro; nos outros três do recorte, não liga
DISPUTADOS = {"T26-extratos", "T27-despesas", "T28-agenda", "T31-precos"}

# --- o vocabulário exatamente como foi usado, sem limpeza retroativa -------------------
TERMOS = ["pessoa", "usuári", "operador", "analista", "solicitante", "aprovador", "cliente",
          "funcionári", "colaborador", "paciente", "prejud", "penaliz", "injust", "discrimin",
          "exclu", "nega(r|do|ção)", "bloque", "puni", "sobrecarr", "plantão", "escala",
          "privacidade", "dado pessoal", "LGPD", "consentimento"]
AMPLO = re.compile(r"\b(" + "|".join(TERMOS) + r")", re.IGNORECASE)

# --- e o vocabulário estrito, que é o teste que a derruba ------------------------------
ESTRITO = re.compile(
    r"\b(prejud|penaliz|injust|discrimin|puni|sobrecarr|privacidade|dado pessoal|"
    r"dados pessoais|LGPD|consentimento|nega(r|do|ção) (o |a |ao )?(acesso|atendimento|serviço))",
    re.IGNORECASE)

# Regra de contagem, como usada: um achado conta UMA vez se a descrição casa >= 1 termo.
# Sem deduplicação por `duplica:`. Todas as iterações. Só a coluna de descrição.
# Todas as lentes EXCETO a própria ETI.


def main() -> int:
    print(f"{'projeto':<18}{'grupo':>8}{'achados':>9}{'amplo':>7}{'%':>6}{'estrito':>9}")
    for t in PROJ:
        p = carregar(RO3 / t)
        it1 = p.condicionais_por_iteracao[min(p.condicionais_por_iteracao)]
        if ETI in it1:
            continue                       # a Fase 2 já ativava: fora do recorte
        outros = [a for a in p.achados if a.lente != ETI]
        amplo = sum(1 for a in outros if AMPLO.search(a.descricao))
        estrito = sum(1 for a in outros if ESTRITO.search(a.descricao))
        grupo = "disputado" if t in DISPUTADOS else "controle"
        print(f"{t:<18}{grupo:>8}{len(outros):>9}{amplo:>7}"
              f"{100 * amplo / len(outros):>5.0f}%{estrito:>9}")

    print("\nA coluna 'amplo' reproduz os números reportados e depois retratados.")
    print("A coluna '%' mostra que a separação não sobrevive à normalização.")
    print("A coluna 'estrito' mostra que o sinal desaparece sem papéis nem homônimos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
