# RETRABALHO — T32-triagem

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-12** |

CA-1 a CA-3, congelados na Fase 0 antes de codar, verificados na Fase 6: **68 testes
verdes** (51 de domínio + 13 de API, mais 4 de regressão), suíte em **550 ms com relógio
controlado, sem uma única espera real**, `tsc --noEmit` limpo.

**Poder de detecção medido por mutação em 3 pontos críticos** — 14, 4 e exatamente 1 falha
respectivamente. Quarta adoção espontânea da prática no lote.

Veredito da Fase 7: *"Atende — os critérios de acerto foram cumpridos"*.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### O melhor achado de teste manual do lote inteiro

**Confusão de autoria por troca de sessão entre abas.** Relato do operador:

> *"com um form aberto e preenchido em uma aba, ao trocar de usuário em outra aba e enviar
> o formulário da primeira, o chamado é registrado no usuário da segunda aba"*

Causa raiz: **o formulário não carregava vínculo algum com a identidade que o compôs.** O
cookie de sessão é do navegador, não da aba; ao enviar, o servidor atribui a autoria a quem
estiver logado *naquele momento*, não a quem escreveu.

Por que é o melhor do lote: é um defeito de **atribuição de autoria** — exatamente o que a
lente GOV existe para pegar — que **nenhum teste automatizado deste projeto encontraria**,
porque exige duas abas, dois usuários e uma ordem específica de ações. Os 64 testes estavam
verdes, incluindo 13 na borda HTTP.

E num sistema de triagem com trilha auditável, atribuir um chamado ao usuário errado é o
defeito que corrompe a própria evidência que o produto existe para produzir.

Corrigido; o envio sob outra identidade passa a ser recusado com explicação. Relato final
do operador: *"Corrigido — e o resto funcionou"*.

### Um segundo defeito de interface, também do operador, na Fase 5

*"Não consegui fechar o chamado, erro de triagem"*. A tela T-4 oferecia **Reconhecer** e
**Encerrar** em qualquer estado não-encerrado, inclusive `NAO_TRIADO`, enquanto a máquina de
estados da Fase 1 só admite encerrar a partir de `TRIADO` ou `RECONHECIDO`.

O domínio recusava **corretamente**. O defeito era a interface oferecer uma ação que o
modelo não permite — mesma classe do primeiro defeito do T31, onde o sistema se comportava
como projetado e o operador ainda assim não conseguia agir.

### Recusa explícita de uma fórmula, portada com a recusa junto

No Tier 2, `prioridade.derivar` foi portado literalmente de
`specs/examples/derivacao-prioridade.md` — *"incluindo a recusa explícita da fórmula
P = impacto + urgência − 1"*, por acoplar a escala ao número de níveis.

Portar a decisão negativa junto com a positiva é o que impede a fórmula rejeitada de voltar
por reimplementação distraída. É o oposto do §M6, onde a Fase 5 desfez o que a Fase 3
decidira — aqui a razão da recusa viajou com o código.

### Procedência do teste manual

O operador percorreu UC-1 a UC-6 na interface, na Fase 5 e de novo na Fase 6 após a
correção. **Oitavo dos doze projetos com human-AV pleno**, e o que rendeu o achado mais
difícil de obter por automação.
