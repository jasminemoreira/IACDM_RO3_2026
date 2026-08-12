# Parâmetros normativos — jornada de trabalho (CLT)

> Depositado na Fase 0 (Nível 1 — Domínio). Fonte canônica: Decreto-Lei nº
> 5.452/1943 (CLT), com redação da Lei nº 13.467/2017 (Reforma Trabalhista).
> URL canônica: https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm
>
> **Nota de procedência — VERIFICADO NA FONTE CANÔNICA (Fase 0, iteração 1).**
> As duas primeiras tentativas via WebFetch deram `ECONNRESET`; a terceira, via
> `curl`, obteve HTTP 200 (3.531.201 bytes) e os oito parâmetros foram
> conferidos contra o texto oficial, com transcrição literal abaixo. A premissa
> PR-1 está **fechada**: estes números não são mais "corroborados por fontes
> secundárias", são citação direta.

## Parâmetros com efeito direto no motor de restrições

| id | Parâmetro | Valor | Base legal | Natureza |
|----|-----------|-------|-----------|----------|
| L1 | Intervalo interjornada mínimo | **11 horas consecutivas** entre duas jornadas | CLT art. 66 | **HARD** |
| L2 | Repouso semanal remunerado | **24 horas consecutivas**, preferencialmente aos domingos | CLT art. 67 | **HARD** |
| L3 | Escala 12×36 | 12h de trabalho seguidas de **36h ininterruptas** de descanso; facultada por acordo individual escrito, convenção ou acordo coletivo | CLT art. 59-A (incluído pela Lei 13.467/2017) | HARD quando o contrato é 12×36 |
| L4 | Prorrogação de jornada (hora extra) | máx. **2 horas** diárias, com adicional de no mínimo **50%** sobre a hora normal | CLT art. 59 | HARD (limite) |
| L5 | Trabalho noturno — faixa | **22h às 5h** (urbano) | CLT art. 73, §2º | classificação |
| L6 | Adicional noturno | **20%** sobre a hora diurna | CLT art. 73 | remuneração |
| L7 | Hora noturna reduzida ("hora ficta") | **52 minutos e 30 segundos** | CLT art. 73, §1º | cômputo |
| L8 | Exceção 12×36 | no regime do art. 59-A, prorrogação da hora noturna e adicional noturno são considerados **compensados** (contratos vigentes após 11/11/2017) | CLT art. 59-A, parágrafo único | exceção a L6/L7 |

## Transcrição literal (planalto.gov.br, verificada nesta sessão)

- **Art. 59** (redação da Lei nº 13.467/2017): "A duração diária do trabalho
  poderá ser acrescida de horas extras, em número não excedente de duas, por
  acordo individual, convenção coletiva ou acordo coletivo de trabalho."
  **§1º:** "A remuneração da hora extra será, pelo menos, 50% (cinquenta por
  cento) superior à da hora normal."
  *(Atenção: o texto do Planalto exibe também a redação REVOGADA do §1º, com
  20%. O valor vigente é 50%. Ler a página inteira sem atentar para o marcador
  "(Redação dada pela Lei nº 13.467, de 2017)" leva ao número errado.)*

- **Art. 59-A** (incluído pela Lei nº 13.467/2017): "Em exceção ao disposto no
  art. 59 desta Consolidação, é facultado às partes, mediante acordo individual
  escrito, convenção coletiva ou acordo coletivo de trabalho, estabelecer
  horário de trabalho de doze horas seguidas por trinta e seis horas
  ininterruptas de descanso, observados ou indenizados os intervalos para
  repouso e alimentação."
  **Parágrafo único:** "A remuneração mensal pactuada pelo horário previsto no
  caput deste artigo abrange os pagamentos devidos pelo descanso semanal
  remunerado e pelo descanso em feriados, e serão considerados compensados os
  feriados e as prorrogações de trabalho noturno […]"

- **Art. 66:** "Entre 2 (duas) jornadas de trabalho haverá um período mínimo de
  11 (onze) horas consecutivas para descanso."

- **Art. 67:** "É assegurado a todo empregado um repouso semanal remunerado de
  vinte e quatro horas consecutivas […]" (redação anterior: "descanso semanal de
  24 (vinte e quatro) horas consecutivas, o qual […] deverá coincidir com o
  domingo, no todo ou em parte"). **Parágrafo único:** "Nos serviços que exijam
  trabalho aos domingos […] será estabelecida escala de revezamento, mensalmente
  organizada e constando de quadro sujeito à fiscalização."

- **Art. 73:** "Salvo nos casos de revezamento semanal ou quinzenal, o trabalho
  noturno terá remuneração superior à do diurno e, para esse efeito, sua
  remuneração terá um acréscimo de 20% (vinte por cento), pelo menos, sobre a
  hora diurna."
  **§1º:** "A hora do trabalho noturno será computada como de 52 minutos e 30
  segundos."
  **§2º:** "Considera-se noturno, para os efeitos deste artigo, o trabalho
  executado entre as 22 horas de um dia e as 5 horas do dia seguinte."
  **§3º:** "Nos horários mistos, assim entendidos os que abrangem períodos
  diurnos e noturnos, aplica-se às horas de trabalho noturno o disposto neste
  artigo."

### Consequência de descumprimento de L1
"A não concessão regular do intervalo mínimo entre uma jornada e outra importa o
pagamento de horas extras correspondente ao lapso temporal de descanso suprimido."
→ ou seja, **violar L1 não é uma preferência degradada, é passivo trabalhista**.
Confirma L1 como restrição HARD, não soft.

### Interação do regime 12×36 com as demais regras (armadilha DUPLA)

O art. 59-A é declaradamente uma **exceção** ao art. 59 ("Em exceção ao disposto
no art. 59 desta Consolidação"). Sobre um contrato 12×36:

| Regra | Como se comporta sob 12×36 | Base |
|---|---|---|
| **L1** interjornada 11h | satisfeita **por construção** — as 36h de descanso contêm as 11h | art. 66 lido com art. 59-A |
| **L2** repouso semanal 24h | **absorvida** pela remuneração mensal pactuada | art. 59-A, parágrafo único (verbatim: "abrange os pagamentos devidos pelo descanso semanal remunerado e pelo descanso em feriados") |
| **L4** limite de 2h extras | o regime é exceção expressa ao art. 59 | art. 59-A, caput |
| **L6/L7** adicional e hora noturna reduzida | prorrogações do noturno "serão consideradas compensadas" | art. 59-A, parágrafo único |

**Consequência de implementação:** a natureza de cada restrição depende do
REGIME DO CONTRATO da pessoa; não é propriedade global do sistema. `Contrato`
carrega o regime e o catálogo de restrições o consulta.

**Correção por evidência (Fase 6).** As Fases 0 e 3 registraram que aplicar
L1, L2, L4, L6 e L7 cumulativamente sobre 12×36 rejeitaria escalas legais — "a
mesma armadilha em quatro lugares". Um teste de mutação mostrou que isso é
**forte demais**, e onde:

| Regra | Aplicá-la cumulativamente sob 12×36 é… | Por quê |
|---|---|---|
| L1 interjornada 11h | **inócuo** | L3 proíbe dias consecutivos, logo o descanso mínimo entre plantões já é de 36h — L1 nunca dispara |
| L2 repouso semanal | **inócuo** | idem: com dias alternados, toda janela de 7 dias tem folga |
| **L4 limite de jornada** | **DANOSO** | rejeitaria todo turno de 12h — ou seja, toda escala de plantão hospitalar. O sintoma pareceria "configuração inválida", não "regra errada" |
| L6/L7 noturno | fora de escopo | remuneração não é calculada (REG-02) |

Ou seja: L3 é **estritamente mais forte** que L1 e L2, e a redundância entre
elas é inofensiva. O risco real estava concentrado em L4 — e só nele. Fixado
por `test_l4_nao_se_aplica_ao_regime_12x36`.

Vale registrar o método: a afirmação original era plausível e passou por duas
rodadas de crítica adversarial sem ser questionada. Quem a derrubou foi a
mutação, não a leitura.

*(Registrado na Fase 0 como PR-3. A extensão a L2 só apareceu na reconferência
contra o texto oficial — as fontes secundárias mencionavam apenas a interação
com o art. 66.)*

## Fontes secundárias consultadas

- Art. 66 / intervalo interjornada e sua verificação no 12×36:
  - https://solides.com.br/blog/artigo-66-da-clt/
  - https://www.contabeis.com.br/noticias/64182/artigo-66-da-clt-tudo-sobre-o-intervalo-interjornada/
  - https://ambitojuridico.com.br/intervalo-de-descanso-entre-jornadas/
- Art. 67 (RSR de 24h consecutivas, escala de revezamento aos domingos):
  - https://www.jusbrasil.com.br/topicos/10758983/artigo-67-do-decreto-lei-n-5452-de-01-de-maio-de-1943
  - https://www.legjur.com/legislacao/art/dcl_00054521943-67
- Art. 59-A (12×36) e parágrafo único (compensação do noturno):
  - https://www.guiatrabalhista.com.br/tematicas/Jornada-12-x-36-reforma-trabalhista.htm
  - https://seval.com.br/jornada-12x36-e-a-prorrogacao-da-hora-noturna-a-luz-da-reforma-trabalhista/
  - Constitucionalidade (STF): https://buscadordizerodireito.com.br/jurisprudencia/11928/
  - Análise TST: https://juslaboris.tst.jus.br/bitstream/handle/20.500.12178/181570/2020_rocha_fabio_aspectos_polemicos.pdf
- Art. 59 (adicional mínimo de 50% da hora suplementar):
  - http://www.sato.adm.br/guiadp/bcoclt/banco_de_dados_clt_art_059.htm

## Fronteira legal × política interna

O operador decidiu (Fase 0, Nível 1) que o sistema convive com **dois regimes
simultâneos**: restrições legais (esta tabela, imutáveis, HARD, rastreáveis a
artigo) e **regras internas da organização** (configuráveis, podendo ser hard ou
soft por escolha do gestor). O modelo de domínio precisa distinguir as duas
origens — uma restrição legal violada é ilegalidade; uma interna violada é
política. Misturá-las num mesmo saco de "regras" apaga essa diferença e é,
previsivelmente, onde a rastreabilidade normativa quebra.
