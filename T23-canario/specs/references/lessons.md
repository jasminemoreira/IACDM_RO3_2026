# Lições do ciclo v1.0 — T23 coordenador canário

Escrito na Fase 7. É o que um ciclo v2 (ou um post-mortem) lê no lugar do chat.
Lições sobre **este projeto**, não sobre a metodologia.

---

## L1 — Domínio: o baseline pareado não é preciosismo, é o mecanismo

A literatura (R-03, R-04, R-05) insiste que não se compara o canário contra a
produção de vida longa, e é fácil ler isso como rigor acadêmico. Não é.

`test_val1_julga_contra_baseline_nao_contra_estavel` mede a diferença sobre o
ground truth depositado: o **mesmo** canário sadio recebe veredito `Pass` contra
o baseline pareado e `High` contra a estável quente. O viés de aquecimento
sozinho é suficiente para reprovar uma versão boa. Quem implementar comparando
contra a estável terá um sistema que reverte versões corretas e não saberá por quê.

Corolário operacional: **o simulador precisa modelar idade de instância**, senão
a decisão mais cara do projeto vira código não demonstrável. Isso atravessou o
projeto como premissa A2 e só virou contrato verificável em V(3).

## L2 — Domínio: "falha" e "erro" são espécies diferentes, e confundi-las é o modo de falha mais provável

R-06 separa contagem total (falha) de contagem consecutiva com reset (erro)
porque *"errors tend to happen ephemerally and may recover on its own"*.

Na prática isso apareceu **duas vezes**, por caminhos independentes:
1. No desenho — UC-4 existe justamente para provar a distinção.
2. Na implementação — o coordenador julgava sobre janela **não renovada**
   durante a queda do coletor, repetindo o mesmo veredito e revertendo por uma
   falha inexistente. O contador de falhas estava correto; o que estava errado
   era deixar o julgamento rodar sem dado novo.

Lição transferível: **não basta separar os contadores, é preciso impedir que o
julgamento aconteça sem insumo novo.** Um julgamento repetido sobre os mesmos
dados vira N falhas para qualquer contador.

## L3 — Estatística: parâmetro emprestado carrega semântica, não só valor

Dois erros do mesmo tipo, ambos pegos pela lente Científica:

- Os limiares 75/95 de R-03 foram importados junto com uma faixa `Marginal`
  **inalcançável com 3 métricas** — o score só assume {0; 33,3; 66,7; 100}.
- Ao migrar de teste bicaudal (o do Kayenta) para unicaudal, manter alfa 0,02
  **dobraria** a taxa de falso positivo na cauda testada. O valor que preserva a
  semântica da fonte é 0,01.

Lição: ao citar um número, cite também o *teste* a que ele pertence. Um alfa sem
a lateralidade é meio parâmetro.

## L4 — Estatística: tolerância zero + comparações múltiplas = falso positivo garantido

Exigir score 100 (3 de 3 `Pass`) parece rigor. Com alfa 0,01 e 3 métricas por
julgamento, a chance de ao menos um falso positivo em *n* julgamentos é
`1 − 0,99^(3n)`. Isso se manifestou de verdade: no UC-1 saudável, a saturação
deu `High` em t=20.

O que salvou o canário sadio não foi a estatística — foi a **tolerância a falhas**
(R-07) somada à **histerese** (R-06). Argo e Flagger resolvem assim, e agora
sabemos por quê.

## L5 — Arquitetura: a correção de um defeito é a fonte mais provável do próximo

O achado mais caro do ciclo. Na segunda passada do laço 2↔3, **três dos quatro
críticos eram iatrogênicos** — criados pelas correções da primeira passada:

| Correção de V(2) | Defeito que ela criou |
|---|---|
| Espelhar `baseline == canário` (consertou ASM-02) | A estável ia a **zero** no último passo — 100% dos usuários em instâncias frias, a negação da segurança do canário |
| Janela deslizante (consertou 4 achados) | Julgamentos consecutivos compartilhavam amostras, invalidando o pressuposto de independência do limite de falhas |
| Objeto `configuracao` (consertou IMP-03) | Misturava limiares com semente/cenário, e "a mesma configuração" voltava a ser inverificável |

Nenhum dos três foi resolvido acrescentando componente. Os três foram resolvidos
por **regra de validação** ou **realocação de responsabilidade** — e V(3) tem os
mesmos 12 módulos de V(1).

## L6 — Teste: ler o próprio código não encontra falsa cobertura

`test_reg01_canario_sem_trafego_nao_promove` passava com a defesa **desligada**.
Com `tamanho_janela == amostra_minima` e `deque(maxlen=50)`, `pronta()` já
implica contagens iguais, então `volumes_comparaveis` nunca discriminava —
quem prestava a garantia era outro mecanismo.

Só o **teste de mutação** encontrou isso. Nenhuma quantidade de releitura teria.
Lição: depois de escrever a suíte, quebre o mecanismo de propósito e conte
quantos testes caem. Se cair um só, provavelmente ele está medindo outra coisa.

## L7 — Stack: a verificação Tier 1 decidiu a linguagem, e a evidência estava num concorrente

`scipy.stats.mannwhitneyu` é a única implementação madura de Mann-Whitney entre
as candidatas — gonum não tem (issue #320 aberta), `golang.org/x/perf` tem em
pacote `internal` não importável, TypeScript não tem e ainda carece de RNG
semeável nativo.

A confirmação mais forte não veio da documentação: o **PipeCD**, coordenador de
entrega progressiva real escrito em Go, precisou vendorizar sua própria
implementação. Quando um projeto sério da área reescreveu algo do zero, isso é
dado sobre a maturidade do ecossistema.

## L8 — Premissa que se revelou errada

**A6: "exigir score 100 não é rigoroso demais".** Errada, e demonstrada errada
por aritmética antes de virar código. Retirada em V(2).

**A7: "o laço monothread representa adequadamente o aborto manual".** Errada:
`abortar()` existia sem nenhum mecanismo que o acionasse num laço bloqueante.
VAL-12 era inatendível. Retirada em V(2), substituída por tratador de sinal com
flag verificada por iteração.

Ambas eram premissas que eu teria mantido se não as tivesse **escrito e
numerado**. O custo de listá-las foi baixo; o de não listá-las teria aparecido
na Fase 6.

## Dívida conhecida, para um eventual v2

| Item | Por quê |
|---|---|
| **VAL-6** — latência de sucesso separada da de falha | Cumprido só no nome: o substrato simulado não modela requisições individuais. R-01 avisa que *"a slow error is even worse than a fast error"*, e esse caso segue descoberto |
| Latência p99 de falha como quarta métrica | Fora de escopo por decisão da Fase 0; reinstalá-la também tornaria alcançável a faixa `Marginal` de R-03 |
| Trilha de julgamentos persistida (GOV-01) | Sem persistência não há auditoria pós-execução; a decisão de não persistir foi consciente |
| Requisições em voo na troca de peso (MIG-01) | Não observável em substrato simulado |
| Limiares da guarda absoluta sem fonte (SCI-01) | Único parâmetro do sistema sem fundamentação bibliográfica; hoje é decisão obrigatória e impressa do operador |
