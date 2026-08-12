# Lições deste projeto — T22 distribuidor de plantões

Ciclo v1.0, sessão única. Lições sobre ESTE projeto (domínio, stack, padrões,
premissas erradas), não sobre a metodologia. É o que um ciclo v2 ou um
post-mortem deve ler antes de qualquer coisa.

---

## L1 — Domínio: o regime 12×36 desliga menos regras do que eu afirmei

Registrei na Fase 0 e reafirmei na Fase 3 que aplicar L1, L2, L4, L6 e L7
cumulativamente sobre um contrato 12×36 rejeitaria escalas legais — "a mesma
armadilha em quatro lugares". **Está errado, e o teste de mutação mostrou onde.**

Sob 12×36, L3 proíbe dias consecutivos, o que torna o descanso mínimo entre
plantões de 36 h. Logo:

- **L1** (interjornada 11 h) nunca dispara — L3 é estritamente mais forte.
- **L2** (repouso semanal) nunca dispara — com dias alternados, toda janela de
  7 dias tem folga.
- **L4** (limite de jornada) é o **único** perigoso: aplicá-lo rejeitaria todo
  turno de 12 h, ou seja, toda escala de plantão hospitalar. E o sintoma
  pareceria "configuração inválida", não "regra errada".

A afirmação original era plausível, foi escrita com fonte legal correta e
**passou por duas rodadas de crítica adversarial sem ser questionada**. Quem a
derrubou foi mutar o código, não reler o texto.

## L2 — Domínio × referência: o silêncio de um benchmark é uma decisão do contexto dele

O INRC-II penaliza cobertura *abaixo* do ótimo e não diz nada sobre cobertura
*acima*. Portado ao pé da letra, o gerador entregou **183 alocações para 150
vagas ótimas**: com custo zero alcançável e nada penalizando o excesso,
superlotar plantões era grátis. Num hospital, isso é escalar gente que não era
necessária.

O benchmark não está errado — as instâncias dele são de demanda exata, então a
situação não existe no contexto dele. **O que uma implementação de referência
não diz é tão específico do contexto dela quanto o que ela diz.** A extensão
(penalizar o excesso reutilizando o peso publicado de S1) precisou ser declarada
como divergência, não absorvida em silêncio.

## L3 — Stack: o risco de desempenho era imaginário; o risco semântico era real

Duas lentes (Performance, Sustainability) e duas premissas (PR-2, A4) se
preocuparam com o tempo do solver. Medido: **0,3 s** no porte de referência,
contra um orçamento de 60 s — três ordens de grandeza de folga. CP-SAT nunca foi
o problema.

O único momento em que o tempo estourou (60,0 s, custo 1830) **não foi
desempenho**: era a fronteira carregando `total_plantoes` de setembro para
dentro da avaliação de S6 de outubro, fazendo cada pessoa "começar" o mês já no
teto contratual. Sintoma de performance, causa semântica. Corrigido separando o
que a fronteira carrega: estado de **borda** vem sempre da última escala;
contadores **acumulados** só somam dentro do mesmo horizonte contratual.

## L4 — Padrão: "a mesma preocupação em dois lugares" é a forma recorrente de defeito deste sistema

A decisão central da arquitetura foi impedir que uma restrição fosse
implementada duas vezes (`aplicar` no solver, `verificar` na escala). Funcionou —
INV-1 como teste de propriedade nunca falhou.

Mas o **mesmo formato de defeito reapareceu disfarçado**, e passou por tudo:

| Onde | Metade implementada | Metade esquecida |
|---|---|---|
| Tratamento de JSON inválido | `carregador` (instância de entrada) | `repositorio-json` (arquivos que o sistema grava) → **D-01, traceback bruto** |
| Imutabilidade da escala | fluxo normal de trocas | caminho `--force` → **B-01, auditoria inconsistente** |

Os dois são achados 🔴 da Fase 2 (RES-03 e GOV-01) que a Fase 3 marcou como
resolvidos — e estavam, **no desenho**. Num v2, a regra é: quando uma decisão
diz "o sistema sempre faz X", listar explicitamente TODOS os caminhos que
precisam fazer X, e testar cada um.

## L5 — Premissa errada: "decisão de design registrada" ≠ "comportamento implementado"

A premissa mais cara deste ciclo não estava na lista A1-A9. Era implícita: que
um achado crítico endereçado na Fase 3 estaria, por consequência, correto no
código.

Dos 14 críticos, **dois chegaram à Fase 6 apenas meio implementados** — e
nenhuma quantidade de crítica adversarial sobre o *desenho* os pegaria, porque o
desenho estava certo. Só rodar o programa pegou. O corolário prático: o teste
exploratório de bordas não é formalidade de fim de ciclo, é onde se descobre a
distância entre o documento e o binário.

## L6 — Processo: corrigir por adição cria a própria família de falhas

V(2) respondeu à crítica acrescentando um módulo (`diario`) e dois estados
(ORFA, CANCELADA). A rodada seguinte de lentes achou **3 críticos, todos no
módulo novo** — ordem de eventos indefinida, append não atômico sobre a única
fonte de verdade, e dois tipos idênticos com significados diferentes.

V(3) corrigiu por **remoção**: eliminou o módulo, voltou a 5 estados, e os 3
críticos caíram juntos. Descobriu-se que ORFA era redundante com uma regra que
já existia desde V(1) — a revalidação no aceite. Trajetória: **11 → 12 → 11
módulos, 5 → 7 → 5 estados, 11 → 3 → 0 críticos abertos**.

---

## Para um ciclo v2, nesta ordem

1. **Validação humana das mensagens.** O único item que ficou explicitamente
   não verificado: se a rejeição de uma troca é compreensível para um
   plantonista não-técnico. Nenhum teste automatizado alcança isso.
2. **Autenticação** (SEC-01). Hoje o consentimento do par — a única aprovação do
   produto — é falsificável por um argumento de linha de comando. Está declarado
   como fronteira de segurança, não escondido, mas é o maior buraco do produto.
3. **Notificação** de troca pendente. Sem ela, `trocas` depende de a pessoa
   lembrar de consultar.
4. **Equidade como critério**, se o produto for julgado por ela. Hoje é termo
   flexível com peso 10 (o menor do INRC-II): sacrificar preferência é sempre a
   saída mais barata, e tende a recair sistematicamente sobre as mesmas pessoas
   (ETI-02). O relatório de distribuição torna isso mensurável, mas nada age
   sobre ele.
