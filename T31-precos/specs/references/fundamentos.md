# Fundamentos e referências

**Nota de procedência (registrada na Fase 0):** o operador **não autorizou
pesquisa web**. Este material vem de conhecimento consolidado e cita
obra/autor **sem URL**. Consequência assumida: a lente **Científica** da Fase 2
avaliará as referências sem link verificável. Isto é uma limitação conhecida, não
um descuido — o domínio é maduro e **não possui parâmetro numérico** que exija
validação contra literatura (não é DSP, ML ou ciência experimental). Todo número
deste projeto é de decisão do negócio (preços, faixas, prioridades), não de
literatura.

## 1. Motores de regras de negócio

- **Ross, Ronald G. — *Business Rule Concepts*.** Estabelece a regra de negócio
  como artefato declarativo de primeira classe, separado do código que a executa,
  e sob custódia do especialista de negócio — não do programador. É a
  justificativa direta do ator "analista de preços" e da separação
  rascunho/publicação: quem edita a regra não é quem faz deploy.
- **Fowler, Martin — *Patterns of Enterprise Application Architecture*,** e o
  artigo *"Rules Engine"*. Duas contribuições usadas aqui:
  - **Domain Model** vs. **Transaction Script**: com invariantes de domínio
    (I-1..I-7) e uma regra de precedência não trivial, Domain Model é o
    encaixe; Transaction Script espalharia a precedência por cada endpoint.
  - Advertência sobre motores de regras: o valor está na **separação e
    explicabilidade**, e o custo real é a perda de rastreabilidade quando o
    motor decide de forma opaca. Confirma que o trace é requisito, não enfeite.
- **Forgy, Charles L. — algoritmo RETE** (*"Rete: A Fast Algorithm for the Many
  Pattern/Many Object Pattern Match Problem"*, Artificial Intelligence, 1982).
  **Citado para ser descartado, com fundamento:** RETE amortiza o custo de
  reavaliar muitas regras contra fatos que mudam incrementalmente, trocando
  memória por tempo. Aqui os fatos não são incrementais (cada precificação é
  independente) e são ~10³ regras: avaliação linear é O(n) por chamada, com n
  ≈ 1.000 — três ordens de grandeza abaixo do orçamento de 100 ms. Adotar RETE
  seria AP2 (complexidade como falsa solução).
- **Decision tables** (formalismo clássico; base da norma **OMG DMN — Decision
  Model and Notation**, tabelas de decisão com *hit policy*). A contribuição
  importante é a **hit policy** explícita: DMN obriga a declarar o que acontece
  quando várias linhas casam — `UNIQUE`, `FIRST`, `PRIORITY`, `COLLECT`. O
  desenho deste projeto equivale a **hit policy `PRIORITY`** com desempate por
  especificidade, e trata empate residual como **erro de modelagem detectado na
  validação** — que é exatamente o tratamento de `UNIQUE` violado em DMN.
  Escolha registrada por analogia normativa, não por invenção.

## 2. Modelagem temporal (vigência)

- **Snodgrass, Richard T. — *Developing Time-Oriented Database Applications in
  SQL*.** Distingue **valid time** (quando o fato vale no mundo) de
  **transaction time** (quando o sistema soube dele); o uso de ambos é a
  **bitemporalidade**.
  - Adotado: **valid time apenas** — a regra carrega `[vigência_início,
    vigência_fim]` e a precificação recebe a data do pedido.
  - Descartado: bitemporal. Custo: cada consulta ganha um segundo eixo e o
    modelo mental dobra; benefício ("o que teríamos cobrado em D com o que
    sabíamos em D'") não é exigido por nenhum critério de sucesso.
  - **Consequência que a bitemporalidade teria coberto e que aqui é coberta de
    outra forma:** editar retroativamente uma regra faz o recálculo divergir da
    decisão registrada. Resolvido pelo **log imutável de decisões** (I-7) em vez
    de por um segundo eixo temporal — mais barato e suficiente para auditoria de
    "o que foi cobrado".
- **Fowler, Martin — *"Temporal Patterns"*** (*Audit Log*, *Effectivity*,
  *Snapshot*). `Effectivity` é o par de datas na regra; `Audit Log` é o registro
  de decisões; `Snapshot` é a versão publicada imutável. Os três padrões
  aparecem no desenho e vêm daqui.

## 3. Exatidão monetária

- **IEEE 754** — ponto flutuante binário não representa exatamente frações
  decimais como 0,10 ou 21,90. Em cálculo de dinheiro isso produz divergência de
  centavos, que aqui **falsifica o critério CS-1 (paridade)**.
- Prática consolidada (Goldberg, *"What Every Computer Scientist Should Know
  About Floating-Point Arithmetic"*; e a recomendação padrão de `BigDecimal` /
  `decimal.Decimal` / `decimal.js`): representar dinheiro como decimal exato ou
  como inteiro de centavos. → **Invariante I-5**.
- **Arredondamento:** meia-unidade para cima (*half-up*) a 2 casas é a
  convenção comercial brasileira e a que planilhas usam na exibição. O risco de
  paridade documentado na Fase 0 vem justamente daí: a planilha calcula em
  binário e arredonda só na exibição.

## 4. Explicabilidade

- A exigência de "por que **não**" (contrafactual) é reconhecida na literatura de
  explicação — **Miller, Tim — *"Explanation in Artificial Intelligence:
  Insights from the Social Sciences"*** (Artificial Intelligence, 2019):
  explicações humanas são **contrastivas** ("por que P e não Q?") e
  **selecionadas**, não exaustivas.
  - Consequência de desenho: o trace guarda **todas** as candidatas e as
    derrotadas com motivo (a base contrastiva completa), mas a **frase**
    apresentada é seletiva — a regra vencedora e a razão da derrota da rival mais
    próxima. Guardar tudo e mostrar pouco é a resposta correta, e é por isso que
    trace e frase são artefatos distintos e não um só.

## 5. Como cada referência entra no desenho

| Referência | Onde aparece |
|---|---|
| Ross, *Business Rule Concepts* | ator analista; rascunho/publicação separados do deploy |
| Fowler, *PoEAA* / *Rules Engine* | Domain Model; trace obrigatório |
| Forgy, RETE (1982) | **descartado** com justificativa quantitativa (n≈10³, O(n) ≪ 100 ms) |
| OMG DMN — *hit policy* | precedência = `PRIORITY` + especificidade; empate residual = erro de validação |
| Snodgrass, *Time-Oriented* | valid time único; bitemporal descartado |
| Fowler, *Temporal Patterns* | Effectivity, Audit Log, Snapshot |
| IEEE 754 / Goldberg | I-5, decimal exato; risco de paridade |
| Miller (2019) | trace exaustivo + frase contrastiva seletiva |
