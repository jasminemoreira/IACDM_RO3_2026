# Referências — aprovação de despesas, alçadas e delegação

Pesquisa da Fase 0 (2026-08-11), depositada por decisão do operador (N5/Pesquisa =
"Pesquisar e depositar"). Toda afirmação abaixo tem URL. O que **não** vier daqui é
decisão do operador, marcada como tal.

---

## 1. Matriz de Delegação de Autoridade (DoA)

Documento formal que fixa quais papéis podem aprovar em cada faixa de valor e qual é o
caminho de escalonamento quando o valor excede a faixa. É a fonte do conceito de "alçada
por valor" do enunciado.

- Definição e construção da matriz, com foco em contas a pagar:
  <https://www.stampli.com/resources/delegation-of-authority-matrix-ap/>
- Guia de níveis de aprovação e caminhos de escalonamento:
  <https://www.auravms.com/blogs/procurement-delegation-authority-matrix-approval-guide>
- "Quem aprova o quê e quando" — modelo de matriz:
  <https://tallyfy.com/delegation-of-authority-matrix-template/>
- Enquadramento em governança e prestação de contas:
  <https://umbrex.com/resources/frameworks/organization-frameworks/delegation-of-authority-doa-framework/>
- Exemplo de política real, publicada, com tabela de limites (GGGI, 2017):
  <https://gggi.org/wp-content/uploads/2017/11/GGGI-DELEGATION-OF-AUTHORITY-_-APPROVED-VERSION-Effective-1-September-2017-_-Updated-4-September-2017.pdf>
- Implantação de política de DoA na prática:
  <https://blog.approvalmax.com/how-to-establish-a-delegation-of-authority-policy-and-stick-to-it-effortlessly>

**Achados aplicáveis ao seed (`specs/datasets`):**
- Limites sobem aproximadamente **uma ordem de grandeza por nível**; estrutura típica de
  mercado médio: gerente até dezenas de milhares, diretor até centenas de milhares, CFO
  até um teto fixado pelo conselho, conselho acima disso.
  Fonte: Stampli / AuraVMS (acima).
- A separação de responsabilidades é a tríade **matriz** (as regras) + **workflow** (a
  aplicação) + **SoD** (a impossibilidade de contornar). Precisa das três.
  Fonte: Stampli (acima).

⚠️ Os valores concretos do seed deste projeto são **arbitrários por natureza** (dados de
configuração de uma empresa fictícia), não parâmetros científicos. A referência acima
justifica a **forma** (progressão por ordem de grandeza), não os números.

---

## 2. Segregação de funções (SoD) e princípio dos quatro olhos

Base das invariantes INV-2 e INV-4 do glossário.

- Ninguém aprova a própria despesa — exemplo canônico de conflito de interesse que SoD
  previne: <https://www.sikich.com/insight/why-segregation-of-duties-is-a-key-internal-control-and-how-to-implement-it/>
- Princípio dos quatro olhos: toda transação crítica passa por pelo menos duas pessoas:
  <https://www.tenfold-security.com/en/wiki/segregation-of-duties/>
- *Maker-checker* — formalização do mesmo princípio em instituições financeiras:
  <https://en.wikipedia.org/wiki/Maker-checker>
- SoD em contas a pagar, com os pares de funções incompatíveis:
  <https://ramp.com/blog/accounts-payable/segregation-of-duties-in-accounts-payable>
- SoD como controle exigido por SOX (documentação e certificação dos controles):
  <https://www.securends.com/blog/segregation-of-duties-for-sox-compliance/>
- Quatro olhos como controle antifraude em tesouraria (ACT):
  <https://www.treasurers.org/ACTmedia/May15TTtreasuryessentialsp48.pdf>

**Achado que confirma INV-4:** se, por delegação, o mesmo ator ocupasse dois níveis da
mesma cadeia, a "cadeia de dois níveis" degeneraria em uma aprovação única disfarçada —
exatamente o que o princípio dos quatro olhos existe para impedir.

---

## 3. Delegação com semântica "em nome de" e trilha de auditoria

Base das invariantes INV-6 e INV-7.

- Delegação ≠ acesso por procuração (*proxy*): delegação cede **autoridade de aprovação**
  por um tipo de processo, tipicamente durante ausência; proxy é acesso administrativo
  amplo em nome de outro. O enunciado descreve delegação, não proxy:
  <https://www.cloudapper.ai/workday-help/workday-delegate-proxy-access-manager-self-service-scale/>
- Aprovação delegada é registrada **do mesmo modo** que a direta e aparece na mesma
  trilha, mostrando **quem delegou e quem agiu**:
  <https://www.openiam.com/blog/workflow-approval-delegation-options-in-openiam>
- Delegação de worklist com vigência definida (implementação real, Oracle/Stanford):
  <https://fingate.stanford.edu/authority/delegate-or-share-oracle-approval-worklist>
- Metadados de delegação carregados como par **`act` (ator) / `obo` (on-behalf-of)** —
  a mesma dupla que INV-7 exige na Decisão:
  <https://www.scalekit.com/blog/delegated-agent-access>
- Lacuna de auditoria em delegação, e por que registrar só o ator efetivo é insuficiente:
  <https://auth0.com/blog/closing-audit-gap-human-to-agent-delegation/>
- Caso de uso "delegação temporária de aprovação por ausência" como requisito recorrente
  de produto: <https://github.com/documenso/documenso/issues/3087>

---

## 4. Modelos formais de delegação (RBAC) — fundamento de INV-3, INV-5 e INV-6

- **DW-RBAC** — modelo formal de segurança para delegação e revogação em sistemas de
  workflow; define formalmente asserção, aceitação, execução e revogação de uma delegação,
  com provas de propriedades. É a referência acadêmica mais próxima deste projeto:
  <https://www.ic.unicamp.br/~wainer/papers/is07.pdf> (PDF aberto; versão editorial:
  <https://www.sciencedirect.com/science/article/abs/pii/S0306437905001122>)
- Panorama de gestão de delegação em modelos de controle de acesso, incluindo delegação
  **multi-passo** (o que INV-3 deliberadamente **proíbe** aqui) e delegação temporária que
  expira automaticamente: <https://arxiv.org/pdf/1012.2720>
- Dimensões de revogação (propagação, dominância, dependência, revogação automática vs.
  por usuário): mesmo survey acima.

**Como isto se aplica:** a literatura trata delegação transitiva/multi-passo como caso
suportável porém caro em auditoria e sujeito a ciclos. A decisão do operador (INV-3:
**não transitiva**) é uma restrição deliberada e conservadora dentro do espaço de desenho
que a literatura descreve — não uma omissão.

---

## 5. Lacunas conhecidas

- Nenhuma fonte encontrada fixa a **fronteira inclusiva vs. exclusiva** do limite
  (`valor ≤ limite` ou `valor < limite`). É ambiguidade real do domínio, resolvida por
  decisão explícita do operador (INV-1, inclusiva) e coberta por teste (CA-2).
- Nenhuma fonte encontrada define o destino de itens pendentes **no instante da
  expiração**. Resolvido por decisão do operador (INV-6, retorno ao delegante com
  preservação dos atos já praticados).
