# Análise de concorrentes — escala de plantões médicos

> Depositado na Fase 0 (Nível 1 — Domínio). Fonte da metade "troca + aprovação"
> do enunciado, que a literatura de rostering (INRC-II) não cobre.

## Quadro comparativo

| Produto | Gera escala? | Troca entre pessoas | Aprovação | Observação |
|---|---|---|---|---|
| **QGenda** | Sim (regras → escala) | Sim, pedido de troca entre profissionais | Sim, workflow configurável em 1 ou 2 níveis | Referência do fluxo de troca/aprovação |
| **Amion** | **Não** — só publica | Limitado | — | "is not a schedule generator and doesn't take rules and produce a call schedule" |
| **Sanishift** | Sim, com foco declarado em *fairness* | Sim | Sim | Posiciona equidade como diferencial |
| **PagerDuty / Opsgenie** | Rotação por regra (não otimização) | Override / swap | Leve | Domínio TI; útil como contraste, não como modelo |

Fontes:
- QGenda — fluxo de troca e aprovação (tip sheets institucionais, Northwestern Medicine):
  - https://physicianforum.nm.org/uploads/1/1/9/4/119404942/swap_or_request_shifts_and_approve_-_tip_sheet_qgenda.pdf
  - https://physicianforum.nm.org/uploads/1/1/9/4/119404942/schedule_view__providers__swap_request_approval.pdf
  - https://healthsciencesit.yale.edu/news/introducing-qgenda-new-enterprise-provider-scheduling-application
- Amion (não é gerador de escala) e panorama de ferramentas:
  - https://www.trythrawn.com/blog/physician-call-scheduling-software
  - https://www.trythrawn.com/blog/staff-scheduling-software-physicians
  - https://www.kimedics.com/blog/best-physician-scheduling-software-for-healthcare
- Sanishift (fairness como eixo): https://www.sanishift.com/en/physician-scheduling-software

## Padrão de troca + aprovação observado no QGenda (o mais próximo do enunciado)

Fluxo, verbatim das fontes:

1. Profissional submete **swap** (troca com par identificado) ou **request**
   (pedido de folga/turno) — os dois são fluxos distintos, não o mesmo.
2. "QGenda sends email notifications asking staff to login and approve or deny
   swaps after a swap is submitted."
3. "Swaps or Requests remain pending until the approval is made." →
   **estado PENDENTE é de primeira classe**, com duração indeterminada.
4. Aprovação é feita pelo par envolvido (web ou app), em lista de pendentes,
   com ação Aprovar / Rejeitar.
5. "Once approved, changes will either automatically appear on the schedule or
   be sent to the Schedule Owner for final approval, then the schedule will
   update." → **duplo estágio configurável**: consentimento do par + aprovação
   do gestor.

### O que este padrão implica para o design (registrar como achado, não como decisão)

- A troca tem **dois consentimentos distintos** (o par aceita; o gestor
  homologa) e o segundo é *configurável* — logo é uma máquina de estados com
  caminho longo e caminho curto, não um booleano `aprovado`.
- Uma troca aprovada **pode produzir uma escala que viola restrição**. Nenhuma
  das fontes descreve o que acontece nesse caso. Essa é a **lacuna central** do
  produto: revalidar a escala no momento da aprovação (e quem arbitra se a
  troca é legal mas piora o custo soft) é decisão de projeto, sem precedente
  claro nos concorrentes.
- Enquanto uma troca está pendente, a escala publicada **já pode ter mudado**
  por outra troca aprovada antes — pedidos concorrentes sobre o mesmo plantão
  são o caso de borda que nenhuma fonte documenta.

## Gap explorável (posicionamento)

- Amion domina por inércia institucional **sem gerar escala**.
- QGenda gera e tem bom fluxo de troca, mas o material público não descreve
  **revalidação normativa no ato da troca**.
- Nenhum dos produtos analisados expõe **rastreabilidade de qual regra legal
  cada restrição implementa** — que é exatamente o que o regime CLT + regras
  internas exige (ver `specs/references/clt-jornada.md`).
