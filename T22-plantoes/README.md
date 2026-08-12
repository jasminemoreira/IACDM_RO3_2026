# T22 — Distribuidor de plantões

Gera a escala mensal de plantões de uma unidade hospitalar respeitando a
legislação trabalhista brasileira, e gerencia trocas entre plantonistas com
revalidação automática.

Construído com a metodologia Versus (Fases 0-7). O raciocínio por trás de cada
decisão está em [`specs/`](specs/); a arquitetura, em
[`specs/technical/architecture.md`](specs/technical/architecture.md) (seção
V(3), a vigente).

## O que ele faz

- **Gera** a escala do mês por otimização com restrições (OR-Tools CP-SAT),
  respeitando limites legais e políticas internas da organização.
- **Fiscaliza** a lei: interjornada de 11 h (CLT art. 66), repouso semanal
  (art. 67), regime 12×36 (art. 59-A) e limite de jornada (art. 59). Cada
  parâmetro numérico do sistema cita o artigo ou o item do INRC-II de onde veio.
- **Media trocas** entre plantonistas: quem recebe consente, e o motor revalida.
  Uma troca que produziria escala ilegal é **rejeitada com o artigo citado**,
  mesmo com as duas partes de acordo.
- **Audita**: a escala publicada é imutável; as trocas efetivadas viram eventos
  registrados no próprio arquivo da escala.

## Instalação

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Uso — o fluxo inteiro em 7 comandos

```bash
V=./.venv/bin/python

# 1. uma instância de exemplo (30 pessoas, 30 dias, reprodutível pela semente)
$V -m plantoes.cli gerar-dados --saida dados/inst_set.json --pessoas 30 --dias 30

# 2. UC-1 — gerar a escala
$V -m plantoes.cli gerar --instancia dados/inst_set.json --id 2026-09

# 3. publicar (só escala publicada aceita troca)
$V -m plantoes.cli publicar --id 2026-09

# 4. UC-2 — consultar
$V -m plantoes.cli consultar --id 2026-09 --pessoa p00

# 5. UC-3 — solicitar troca
$V -m plantoes.cli trocar --id 2026-09 --pessoa p00 --com p03

# 6. tomada de ciência — o que está esperando você
$V -m plantoes.cli trocas --pessoa p03

# 7. UC-4 — responder
$V -m plantoes.cli responder --troca t001 --pessoa p03 --aceitar

# UC-5 — relatório de conformidade
$V -m plantoes.cli conformidade --id 2026-09
```

Meses seguintes herdam o estado de fronteira do anterior — sem isso, alguém que
fecha setembro no plantão noturno poderia abrir outubro no diurno seguinte,
violando o art. 66 exatamente na emenda:

```bash
$V -m plantoes.cli gerar --instancia dados/inst_out.json --id 2026-10 --anterior 2026-09
```

## Comandos

| Comando | O quê |
|---|---|
| `gerar` | UC-1: gera a escala do período (rascunho) |
| `publicar` | torna a escala publicada; a partir daí aceita trocas |
| `consultar` | UC-2: mostra a escala vigente, filtrável por pessoa |
| `trocar` | UC-3: solicita troca com um par identificado |
| `trocas` | lista pendentes recebidas **e** enviadas |
| `responder` | UC-4: aceita ou recusa; no aceite, revalida |
| `cancelar` | cancela uma troca que você mesmo solicitou |
| `conformidade` | UC-5: violações com artigo citado, custo e distribuição |
| `gerar-dados` | instância sintética reprodutível (`--inviavel` fabrica um conflito) |

Códigos de saída: `0` sucesso · `2` entrada inválida · `3` inviável ·
`4` escala já existe (use `--force`) · `5` fronteira inválida ·
`6` troca não efetivada · `7` escala com violação rígida.

**`--force` nunca destrói nada.** Re-gerar sobre uma escala existente cria uma
**nova versão** (`meu` → `meu-r1` → `meu-r2`), e a anterior fica intacta com
todos os seus eventos. É o que mantém a trilha de auditoria íntegra: uma troca
já efetivada continua apontando para a escala em que de fato aconteceu.

## Formato de entrada

Ver [`specs/models/modelo-dominio.md`](specs/models/modelo-dominio.md) §4.
Resumo: `periodo`, `habilitacoes`, `tipos_de_turno`, `contratos`, `pessoas`,
`plantoes` (com `demanda_minima` e `demanda_otima`), `preferencias` e
`regras_internas`.

Duas distinções que o formato faz de propósito:

- **`indesejado` × `indisponivel`** — o primeiro é preferência (flexível, peso
  10 do INRC-II); o segundo é rígido e a pessoa nem entra no modelo naquele dia.
- **regra legal × regra interna** — as legais são imutáveis, sempre rígidas e
  citam artigo; as internas são configuráveis, podem ser flexíveis, e seu peso
  é limitado ao maior peso publicado do INRC-II (30) para que uma política sem
  fonte não domine as restrições calibradas pela literatura.

## Arquitetura

Hexagonal, 11 módulos. Núcleo puro (não importa `ortools`, não toca disco):
`dominio`, `restricoes_legais`, `restricoes_modelo`, `avaliador`, `troca`.
Adaptadores: `solver_cpsat`, `repositorio_json`, `carregador`, `cli`.

A decisão central: **cada restrição é declarada uma única vez** e sabe se
aplicar (como restrição CP-SAT, quando as alocações são incógnitas) e se
verificar (sobre uma escala concreta, quando são fatos). Implementá-la duas
vezes seria implementar duas restrições — e o sintoma seria o gerador produzindo
escala que o relatório acusa de ilegal.

Três invariantes sustentam isso:

- **INV-1** — toda escala gerada com um conjunto de restrições aplicado deve
  ser verificada com zero violações rígidas desse mesmo conjunto.
- **INV-2** — restrição de origem legal é sempre rígida e nunca tem peso.
- **INV-3** — a escala vigente é função determinística de (snapshot, eventos)
  na ordem da lista.

## Limitações conscientes

Registradas, não esquecidas — cada uma foi decidida explicitamente:

- **Sem autenticação.** A identidade vem por parâmetro; qualquer pessoa pode
  responder por outra. Como o consentimento do par é a única aprovação do
  produto, isso é uma fronteira de segurança declarada, não um descuido.
- **Sem notificações.** Ninguém é avisado de uma troca pendente; o comando
  `trocas` existe para que a pessoa consulte.
- **Sem cálculo de remuneração.** Adicional noturno e hora extra classificam e
  restringem; não apuram valores.
- **Sem gestor.** Não há homologação em duplo estágio: aprovação é o
  consentimento do par mais o veredito do motor.
- **Uma unidade por instância.** Não há otimização entre setores.

## Divergência declarada em relação ao INRC-II

A competição penaliza apenas a cobertura *abaixo* do ótimo, porque suas
instâncias são de demanda exata. Sem penalizar o excesso, o solver superlota
plantões de graça — escalando gente que não era necessária. Este projeto
penaliza o excesso simetricamente, **reutilizando o peso publicado de S1 (30)**:
a extensão é de forma, não de calibração, e nenhum número novo foi inventado.
