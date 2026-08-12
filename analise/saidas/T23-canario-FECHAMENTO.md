# Fechamento — T23-canario

Quarto projeto válido do ciclo 2. Concluído 2026-08-10, 1,9 h, 8 fases, instrumento
**versus-claude 0.14.2**.

72 achados · 12 módulos · 2 iterações do laço 2↔3 · 67 defeitos distintos · 33 decisões.

Passos 1–5 em `T23-canario-passos.md`. Agregado dos quatro em `AGREGADO-4.md`.

---

## 1. Formato: limpo, com uma ressalva de artefato

Validação sem recusas. Mas a **V(3) é um _delta_**: 12 módulos em V(1), 12 em V(2), **4**
em V(3) — só os que mudaram. Os outros três projetos escreveram a tabela inteira a cada
versão.

Nada disso afeta a medida: as duas iterações foram criticadas contra V(1) e V(2), que são
completas, e os Passos 1 e 4 usam o módulo escrito em **cada achado**, não a lista da
arquitetura. O que quebrou foi meu relatório, que imprimia "Módulos: 4" para um produto de
12.

Corrigido mostrando o perfil por versão em vez de escolher em silêncio — **delta e remoção
são indistinguíveis pelo texto**, e uma tentativa de resolver por carry-forward
ressuscitava módulos legitimamente removidos nos outros três (T21 12→13, T24 9→11, T22
11→14). Detalhe em `ACHADOS-METODO.md` §M3.

## 2. Ativação: 10 de 12 — **MIG ativou pela primeira vez**

Ativaram, sem mudança entre as iterações: RES · UX · **MIG** · SUS · PRO · GOV · OBS ·
CTR · LIN · MEC. Fora: ETI e JOG.

| projeto | condicionais ativas |
|---|---|
| T21-certificados | 11 |
| T24-catalogo | 9 |
| T22-plantoes | 9 |
| T23-canario | 10 |

MIG saiu de 0/3 para 1/4, e o desenho ainda tem T26, T29 e T31 mirando-a. O risco de
repetir o caso GOV/SUS do ciclo 1 — lente que nunca dispara e produz silêncio — recuou.

**ETI e JOG fora pela segunda vez.** ETI em 2 de 4, JOG em 3 de 4. São as duas cujo
descompasso pergunta × gatilho está documentado.

## 3. Estimativa cega sobre a V(1)

| | qwen3.6:27b | kimicode |
|---|---|---|
| coincidem | 8 | **11** |
| divergem | 3 (SUS, GOV, LIN) | **0** |
| oscilaram | 1 (MEC) | 1 (SUS) |

O Kimi acertou 11 de 11 decisões estáveis — o melhor resultado do lote. **Os dois
estimadores acertaram MIG**, que é a novidade do projeto.

Com quatro projetos, a concordância acumulada:

| par | total |
|---|---|
| estimador × estimador | 29/34 = **85%** |
| kimi × Fase 2 | 34/40 = **85%** |
| qwen × Fase 2 | 30/41 = **73%** |

**Isso desmonta a leitura que escrevi no T22.** Lá eu disse que os externos concordam
entre si (88%) mais do que com a Fase 2 (73–79%); com o T23 o kimi × Fase 2 subiu a 85% e
empatou. É a **quarta** vez que esta entrada é reescrita, e a quarta redação é
deliberadamente descritiva — registrei em `ACHADOS-TAXONOMIA.md` a regra de que **nada
direcional entra no relatório antes dos doze**.

O único número estável em quatro projetos é o qwen × Fase 2 em 73%, sempre o mais baixo
dos três pares.

## 4. Remarcação cega

| | todos os pares | mesmo módulo |
|---|---|---|
| κ de Cohen | **0,115** | **0,183** |
| ambos: duplicata | 1 | 1 |
| só o modelo gerador | 4 | 3 |
| só o juiz cego | **11** | 5 |

Série completa: **0,000 · 0,000 · 0,362 · 0,115**. Um único valor acima de 0,2 em quatro.
A leitura de que a marcação de duplicatas não é reprodutível entre juízes se firma.

O juiz cego viu **11 agrupamentos que o gerador não viu**, contra 4 no sentido oposto —
mesma direção dos outros três projetos. Autoavaliação enxergando menos sobreposição do que
um leitor externo enxerga nos mesmos achados.

**Defeito de transporte encontrado e corrigido.** A saída do `ollama run` veio corrompida
por sequências de terminal — três `cursor-left` seguidos de `erase-line` sobrescreveram
caracteres e truncaram um id no meio (`"F-24", "F-3` seguido de `"F-37"`). Falhou alto: o
JSON não parseou. Verifiquei os outros: T22 e T24 não têm nenhum cursor-left, e o
`comparar` valida cada id contra o pacote, então o T21 também está limpo. Substituí a
chamada pelo **subcomando `julgar`, que usa a API do Ollama com schema** — sem TUI, sem
redesenho. Mesmo modelo e mesmos parâmetros do Modelfile.

## 5. Ortogonalidade — o agregado dos quatro

**328 achados · 308 defeitos distintos · nenhuma lente com contribuição exclusiva zero.**

Sobreposição média **9%**. Seis lentes seguem em **0%** — não dividem nenhum defeito com
ninguém: RES, ETI, OBS, **LIN**, MEC e MIG.

O par a vigiar segue sendo **DES × SUS**, único acima de 0,2 em Jaccard de defeitos (0,23)
e presente nos quatro projetos. É o candidato natural a "duas lentes perguntando a mesma
coisa sobre custo".

`ARQ × PRE`, o único par que o §4 nomeia *a priori* como suspeito, aparece com **1 defeito
em comum e Jaccard 0,02** — praticamente disjunto. A suspeita do protocolo não se
confirma.

## 6. Método e instrumento

Detalhe em `T23-canario/RETRABALHO.md`. Zero defeitos pós-entrega.

**O achado mais forte do projeto, e vai para `ACHADOS-METODO.md`:** o teste de mutação
revelou que a defesa contra REG-01 **nunca discriminou nada**. Com
`tamanho_janela == amostra_minima == 50` e `deque(maxlen=50)`, `pronta()` só é verdadeira
quando as duas séries têm exatamente 50 pontos — e aí a razão min/max é sempre 1,0. A
correção existia, o teste existia, o teste passava, e a condição era inalcançável. **62
testes verdes não notaram; a mutação notou.**

Também: UC-4 revertia por falha em vez de tolerar o coletor fora, e o registro identifica
como *"o achado CTL-03 ressurgindo por outra porta"*. Mesma classe do D-01 do T22 —
**correção que cobre parte do que o achado implica** —, agora em dois projetos. Candidato a
padrão.

**Procedência do teste manual: a mais forte dos quatro.** Executado pelo operador, e
rendeu — fechou VAL-12, que estava marcada como não exercida.

---

## Estado do lote

4 de 12. Nenhuma lente candidata a remoção em nenhum projeto nem no agregado.

Cobertura das condicionais: MIG **1/4** · ETI 2/4 · OBS e JOG 3/4 · as outras oito em 4/4.
Três ainda abaixo do piso de 3 do §2 — só MIG e ETI seguem realmente escassas.

## Pendências

1. **Rótulo de κ para valores nulos-por-baixo** — corrigir uniformemente após os doze.
2. **`duplica` intra-lente** — a guidance tem a frase desde o C1 e o gerador segue sem
   marcar.
3. **Patch M1 do `test-outcome.js`** — decidir se entra já ou espera o fim do lote.
4. **Tabela de módulos completa por versão** — o T23 escreveu delta. Candidato pós-lote;
   não afeta medida.
5. **ARQ × LIN** — reincidiu no T21 e no T22 na marcação cega, **não** no T23. Seguir.
