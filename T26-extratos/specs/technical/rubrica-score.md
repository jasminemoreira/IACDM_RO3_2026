# Rubrica de score e janelas de compensação — parâmetros faltantes de V(3)

Fecha os achados **ASM-12** e **SCI-07**, registrados na Fase 3 como pendência a cumprir
**antes** da Fase 5. Sem este arquivo, a Fase 5 implementaria pesos e janelas inventados — AP7.

---

## 1. Rubrica determinística de score (substitui a estimação m/u)

**Por que rubrica e não Fellegi-Sunter estimado.** SCI-06 mostrou que estimar `m` e `u` contra um
ground truth sintético desenhado pelo próprio projeto é validação circular: os pesos ficariam ótimos
para a distribuição que inventamos. Como VAL-2 exige **zero falso positivo** e a faixa intermediária
vai para revisão humana, uma rubrica **transparente e auditável** entrega mais que um modelo
probabilístico não calibrável. Fellegi-Sunter permanece em `specs/references/fontes-externas.md`
§2.1 como **fundamentação do desenho** — a intuição de que campos raros discriminam mais é dele —,
não como algoritmo implementado.

**Escala:** inteiro `0..100`, **crescente** (maior = mais provável ser o mesmo evento). Fixada aqui
para fechar LIN-03. Os cortes são P3/P4/P5 de `parametros-matching.md`.

### Perfil `dedup` (transação × transação)

**Duas regras têm precedência sobre a soma de pontos.** Ambas foram descobertas
executando a rubrica durante a Fase 5, e cada uma corrigia uma violação real de
critério de aceitação — não são ajustes de peso, são consequências de invariante:

| Regra | Condição | Efeito | Por quê |
|---|---|---|---|
| **Veto de mesma origem** (I6, VAL-2) | mesmo `(fonte, conta, arquivo)` e `ChaveNatural` distinta | **VETO** — nunca funde | Se a instituição imprimiu duas linhas, houve dois eventos. Os dois cafés de R$ 12,00 do mesmo dia são idênticos em todo campo comparável e pontuariam 100: **nenhuma rubrica sobre atributos os distingue**, porque a diferença não está nos atributos. Reimportação da mesma linha tem `ChaveNatural` idêntica e é capturada em L2, sem chegar ao score — logo este veto não mascara duplicata. |
| **Piso de evidência forte** (VAL-1) | valor idêntico **e** mesma data | score mínimo = **70** (corte de revisão) | Um par cross-source com valor e data exatos mas descrição divergente (premissa A6) pontuava 65 e era declarado distinto **sem ninguém olhar** — falso negativo. Vira pendência. Coerente com a precedência de V(3): corretude vence desempenho. |

| Campo | Condição | Pontos | Justificativa do peso |
|---|---|---:|---|
| valor | idêntico (`Decimal`, valor numérico) | **40** | Condição necessária: eventos financeiros distintos raramente coincidem em centavos exatos. É o campo de maior poder discriminante disponível. |
| valor | diferente | **−100** | Veto. Valor diferente ⇒ não é o mesmo evento. Garante que nenhum par com valor divergente alcance o corte de fusão. |
| sinal | mesmo sinal | 0 | Neutro (já implícito no valor com sinal). |
| sinal | sinais opostos | **−100** | **Veto — tratamento de A7 (estorno).** O bloco agrupa por `abs(valor)`; o veto de sinal impede que um estorno seja fundido com a transação original. Mitigação declarada, não comprovada: ver §3. |
| data | mesmo dia | **25** | Duplicata de reimportação preserva a data de postagem. |
| data | ≤ 3 dias de diferença | **12** | Cross-source com defasagem de postagem entre instituições. Janela de `P1`. |
| data | > 3 dias | **−40** | Fora da janela, a evidência conta contra. |
| contraparte | similaridade ≥ 90 (Jaro-Winkler) | **25** | Texto quase igual entre exports da mesma fonte. |
| contraparte | 70 ≤ similaridade < 90 | **10** | Compatível, insuficiente sozinho. |
| contraparte | similaridade < 70 | **0** | Sem evidência — **não penaliza**, porque A6 registra que fontes distintas escrevem a contraparte de formas legitimamente diferentes. |
| contraparte | ausente em um dos lados | **0** | Ausência não é evidência contra (tratamento de campo faltante exigido por IMP-02). |
| conta | mesma conta | **10** | Reimportação na mesma conta. |
| conta | contas distintas | **0** | Cross-source legítimo entre contas. |

Máximo alcançável: `40 + 25 + 25 + 10 = 100`. Um par sem contraparte comparável e com 3 dias de
defasagem chega a `40 + 12 + 0 + 0 = 52` — **abaixo do corte de fusão (95)** e dentro da faixa de
revisão humana. É o comportamento desejado: sob evidência parcial o sistema não decide (I5).

### Perfil `conciliacao` (transação × lançamento)

| Campo | Condição | Pontos | Justificativa |
|---|---|---:|---|
| valor | idêntico | **50** | Peso maior que em `dedup`: o livro registra o valor esperado, e conciliação com valor divergente é exceção contábil, não casamento. |
| valor | dentro da tolerância configurada (default 0) | **30** | Só quando o operador liga a tolerância. Resultado é `casado-com-divergencia`. |
| valor | fora da tolerância | **−100** | Veto. |
| data | ≤ janela do instrumento (§2) | **30** | Diferença de tempo é esperada, não erro. |
| data | fora da janela | **−40** | Vira órfão anômalo. |
| contraparte | similaridade ≥ 70 | **20** | Limiar mais baixo que em `dedup`: A6 é mais severa aqui — o ERP escreve "Fornecedor João da Silva ME" e o extrato "PIX ENVIADO JOAO". |
| contraparte | < 70 ou ausente | **0** | Não penaliza. |

**Versionamento (MEC-05):** cada perfil carrega `versao` no arquivo. A versão vigente é gravada pelo
`audit-log` em cada execução e impressa no cabeçalho do relatório. Dois perfis com conteúdo
diferente não podem circular com o mesmo par `(nome, versao)`.

---

## 2. Janelas de compensação por instrumento (fecha SCI-03, SCI-04, SCI-07)

Substituem o `±3 dias` genérico de `P1`, que vinha de um exemplo que a própria fonte declarava
"ilustrativo, não normativo". Usadas em duas funções distintas: janela de casamento no
`reconcile-engine` e corte entre **órfão esperado** e **órfão anômalo** no `reporter`.

| Instrumento | Janela | Base |
|---|---:|---|
| PIX | **D+0** | Crédito em até 10 segundos, 24×7, inclusive fins de semana e feriados. Um órfão PIX com mais de um dia é anômalo, não diferença de tempo. |
| TED | **D+0 / D+1** | Crédito no mesmo dia útil se enviada até 17h (horário de Brasília); depois disso, no dia útil seguinte. |
| Boleto | **D+1** | Regra Febraban: boleto pago até 13h30 compensa no mesmo dia; após esse horário, no dia útil seguinte. |
| Cartão de crédito | **D+32** | Compensação em D+32, contando D como o dia do pagamento. |
| Desconhecido / não classificado | **D+3** | Default conservador, mantendo o valor de `P1`. Aplica-se quando o `TRNTYPE` do OFX ou o perfil CSV não permitem inferir o instrumento. |

Fontes: [Compensação de pagamento de boleto, cartão e Pix — Asaas](https://blog.asaas.com/compensacao-de-pagamento/) ·
[Compensação de Boleto: novos prazos — Efí](https://sejaefi.com.br/blog/compensacao-de-boleto) ·
[Compensação bancária — InvestNews](https://investnews.com.br/guias/compensacao-bancaria/) ·
[Pix, TED ou boleto — Mercado Pago](https://www.mercadopago.com.br/blog/pix-ted-boleto-melhor-opcao) ·
Sistema de Pagamentos Brasileiro, supervisão do [Banco Central](https://www.bcb.gov.br/).

**Ressalva de qualidade de fonte, registrada honestamente:** estes prazos vêm de documentação de
provedores de pagamento e não de norma do BCB citada diretamente. São suficientes para default
configurável e **não** para uso normativo. Como `P3`-`P5`, entram como parâmetro com valor padrão
documentado, jamais como constante mágica no código.

**Inferência do instrumento:** a partir de `TRNTYPE` no OFX (`XFER`, `PAYMENT`, `CHECK`, `POS`,
`DIRECTDEBIT`) e de campo declarado no perfil CSV. Quando não inferível, cai no default D+3 — e o
relatório marca o item como "instrumento não identificado", para o analista não confundir o
conservadorismo do default com um resultado.

---

## 3. Limitação conhecida: A7 (estorno)

A premissa A7 segue **aberta desde a Fase 0**. O bloco agrupa por `abs(valor)`, então um estorno de
R$ 1.250,00 cai no mesmo bloco da transação original de R$ 1.250,00. A mitigação em V(3) é o **veto
de sinal oposto** na rubrica `dedup` (−100), que impede a fusão.

O que a mitigação **não** cobre e precisa ser verificado na Fase 6 contra o dataset:

1. Estorno **parcial** (valor diferente) não é atingido pelo veto de sinal — mas também não passa no
   veto de valor, logo não funde. Consequência real: vira órfão, não pendência.
2. Estorno lançado como **crédito de mesma natureza** por alguns bancos (sem sinal oposto claro na
   descrição) pode não ser distinguível de um recebimento legítimo.
3. O bloco continua **inchado** por estornos, o que consome orçamento de comparação sem produzir
   casamento — efeito de desempenho, não de corretude.

O `fixture-generator` **deve plantar estornos** no dataset para que estes três casos sejam medidos e
não presumidos.
