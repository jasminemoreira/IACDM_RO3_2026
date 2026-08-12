# Rito de recurso — lógica depositada ANTES do código

⚠️ Este é o **único componente Tier 3** do projeto (não existe biblioteca; é
lógica de domínio própria). A Fase 0 registrou a obrigação: depositar a lógica
aqui antes de qualquer código da Fase 5. Regra S6, antídoto AP7.

Fundamento normativo: ISO 10002:2018 (F6) — níveis de escalonamento
declarados, critérios e prazos por nível, autoridade definida por nível.

## Máquina de estados do Recurso

```
                 abrir (admissível)
        ∅ ──────────────────────────▶ ABERTO
                                        │
                          ┌─────────────┴──────────────┐
                          │ julgar                     │ 24 h sem julgamento
                          ▼                            ▼
                ┌─── PROVIDO                 PRESCRITO_SEM_JULGAMENTO
                ├─── PARCIALMENTE_PROVIDO
                └─── IMPROVIDO
```

Estados terminais: PROVIDO, PARCIALMENTE_PROVIDO, IMPROVIDO,
PRESCRITO_SEM_JULGAMENTO. Não há retorno. Não há segunda instância
(escopo negativo).

**PRESCRITO_SEM_JULGAMENTO (V(3), MOV-11)** existe porque a guarda "não se
encerra chamado com recurso ABERTO" transformaria um recurso esquecido num
bloqueio permanente do chamado. Passadas 24 h sem julgamento, o recurso
prescreve, o encerramento é liberado e a trilha registra que **ninguém
julgou** — que é uma informação diferente de "foi improvido", e mentir sobre
isso reusando IMPROVIDO destruiria o valor de auditoria do rito.

## Admissibilidade — as 5 guardas, avaliadas nesta ordem

A ordem importa: o motivo devolvido ao usuário é o da **primeira** guarda que
falha, e os testes B-1..B-5 dependem de motivos distinguíveis.

| # | Guarda | Falha devolve | Caso de teste |
|---|---|---|---|
| G1 | O chamado existe e está TRIADO | `NAO_TRIADO` — não há classificação a contestar | B-1 |
| G2 | O chamado não está ENCERRADO | `CHAMADO_ENCERRADO` | B-11 |
| G3 | O autor é o solicitante **deste** chamado | `SEM_LEGITIMIDADE` | B-5 |
| G4 | Não existe recurso anterior para este chamado | `RECURSO_JA_EXISTE` | B-2 |
| G5 | `agora − ultimaMudancaClassificacao < prazoRecorrer` (48 h) | `PRESCRITO` | B-3, B-4 |

⚠️ **G5 mudou em V(3) (MOV-12):** o prazo conta da **última mudança de
classificação**, não da triagem. Motivo (SEG-05): o agente pode alterar a
urgência — o eixo do solicitante — numa reclassificação tardia, e com a
contagem a partir da triagem o solicitante perderia o eixo que é seu já
prescrito, sem instrumento. Na primeira classificação,
`ultimaMudancaClassificacao = triadoEm`, então o comportamento inicial é
idêntico ao de V(1).

Regras adicionais de entrada:
- Os eixos contestados são um subconjunto não vazio de `{URGENCIA, IMPACTO}`.
- A justificativa é obrigatória e não vazia.

## Julgamento — guardas

| # | Guarda | Falha devolve | Caso de teste |
|---|---|---|---|
| J1 | O julgador tem papel GESTOR | `SEM_AUTORIDADE` | B-6 |
| J2 | O recurso está ABERTO (não julgado) | `JA_JULGADO` | — |
| J3 | A fundamentação é não vazia | `FUNDAMENTACAO_OBRIGATORIA` | B-7 |
| J4 | Se desfecho ≠ IMPROVIDO, há ao menos um novo valor de eixo | `SEM_ALTERACAO` | — |

O prazo de julgamento (24 h) é meta de processo, **não guarda**: um recurso
julgado com atraso continua válido. Julgar fora do prazo não invalida a
decisão — invalidá-la puniria o solicitante pelo atraso do gestor.

## Efeito do desfecho

| Desfecho | Efeito nos eixos | Prioridade | Prazos | Trilha |
|---|---|---|---|---|
| **PROVIDO** | aplica todos os novos valores pedidos | recalculada | **recontados desde a abertura** | evento com antes/depois e a fundamentação como motivo |
| **PARCIALMENTE_PROVIDO** | aplica apenas os eixos que o gestor acolheu | recalculada | recontados desde a abertura | idem |
| **IMPROVIDO** | nenhum | inalterada | inalterados | evento registrando o julgamento (VAL-11) |

Observe que IMPROVIDO **também** grava trilha. O registro do que NÃO mudou, e
por quê, é metade do valor de auditoria do rito.

## Sequência de uma operação de provimento — V(3)

`recurso` **não modifica o chamado** (MOV-8). Ele devolve a intenção; quem
aplica é `chamado.reclassificar`, único dono do recálculo em todo o sistema.

```
casos-de-uso.julgarRecurso, dentro de UMA transação:
  1. autorizacao.pode(gestor, JULGAR, recurso)      → nega ⇒ devolve Motivo
  2. r = recurso.julgar(...)                        → {recurso, novosEixos?, eventos}
                                                       J1..J4 falham ⇒ devolve motivo
  3. se r.novosEixos:
       c = chamado.reclassificar(r.novosEixos, origem=RECURSO)
                                                    → {chamado, eventos}
       // dentro de reclassificar, e SÓ ali:
       //   p'      = prioridade.derivar(impacto', urgencia')
       //   prazos' = sla.prazos(p', chamado.abertoEm)   ← abertoEm, nunca agora
  4. repositorio.salvar({entidade: r.recurso, eventos: r.eventos})
  5. repositorio.salvar({entidade: c.chamado,  eventos: c.eventos})
commit
```

O passo 3 é a materialização do CA-2: `sla.prazos` recebe `chamado.abertoEm`.
Se recebesse `agora`, o sistema implementaria "reiniciar na reclassificação" —
a opção explicitamente descartada na Fase 0 — e GT-3 falharia. Como a
assinatura de `sla.prazos` não aceita `agora`, o erro é impossível de cometer.

`repositorio.salvar` recebe `{entidade, eventos}` juntos (MOV-9): **não existe
função que grave o estado sem a trilha**, de modo que CA-3 é garantido pelo
tipo e não pela disciplina de quem escreve o caso de uso.

## Prescrição — a fronteira exata

`prescrito(agora) ≡ (agora − triadoEm) >= prazoRecorrer`

Comparação **≥**, não `>`: exatamente 48 h após a triagem, já prescreveu.
B-4 testa 48 h − 1 min (admitido); B-3 testa 48 h + 1 min (prescrito). A
fronteira é decidida aqui, por escrito, e não no calor da implementação.

O prazo conta a partir de `triadoEm`, **não** de `abertoEm` — antes da triagem
não existe classificação a contestar (G1). Esta é a única contagem do sistema
que não parte da abertura, e a exceção é deliberada.
