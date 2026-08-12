# Glossário de domínio — T30

Vocabulário canônico. Um termo, um significado. Sinônimos listados existem para
serem **evitados** no código e nos specs — a Fase 2 (lente Linguística) verifica
que o contrato não é ambíguo.

| Termo | Definição operacional | Sinônimos a EVITAR |
|-------|----------------------|--------------------|
| **Pessoa** (`Recipient`) | Destinatário identificado por id estável, com fuso horário, endereços por canal e preferências. | usuário, subscriber, contato |
| **Notificação** | Intenção lógica de comunicar um fato a uma pessoa. Existe antes e independentemente de qualquer canal. | mensagem, alerta, evento |
| **Mensagem** (`Delivery`) | Uma tentativa concreta de entregar uma notificação por um canal. Uma notificação gera 0..N mensagens. | envio, disparo |
| **Categoria** (`Topic`) | Classe semântica da notificação (ex.: `security`, `billing`, `marketing`). É a unidade sobre a qual a pessoa expressa preferência. | tipo, tag, assunto |
| **Canal** | Meio de entrega com contrato próprio: `email`, `webhook`. | provider, transporte |
| **Provedor** | Implementação concreta por trás de um canal (SMTP local, receptor HTTP). Trocável por configuração. | adaptador, driver |
| **Preferência** | Declaração da pessoa sobre se, por onde e quando quer receber uma categoria. | configuração, setting |
| **Supressão** | Decisão de NÃO entregar (ou de adiar) uma notificação, tomada antes da entrega, por uma regra explícita e nomeada. Nunca é silenciosa: toda supressão produz um registro com motivo. | filtro, bloqueio, mute |
| **Motivo de supressão** | Enum fechado: `opt_out`, `quiet_hours`, `rate_limited`, `duplicate`. | — |
| **Janela de silêncio** | Intervalo diário, no fuso da pessoa, em que a entrega é adiada. | quiet hours, DND, não perturbe |
| **Deduplicação** | Colapso de notificações com a mesma chave lógica dentro de uma janela temporal em uma única entrega. | dedup, idempotência (ver abaixo) |
| **Chave de deduplicação** | String fornecida pelo emissor que identifica a notificação *lógica*. Duas notificações com a mesma chave na mesma janela são a mesma coisa. | — |
| **Idempotência** | Propriedade da API de ingestão: reenviar a MESMA requisição não cria uma segunda notificação. Distinta de deduplicação — idempotência é sobre a requisição HTTP, deduplicação é sobre o conteúdo lógico. | — |
| **Teto de frequência** | Máximo de entregas a uma pessoa por janela de tempo. Excedente é suprimido com motivo `rate_limited`. | rate limit, throttle, capping |
| **Opt-out** | Desligamento durável de uma categoria ou canal pela pessoa, válido até reativação explícita. | unsubscribe, descadastro |
| **Transacional** | Notificação que ignora opt-out, janela de silêncio e teto de frequência por ser consequência direta de uma ação da pessoa ou requisito de segurança. Nunca ignora deduplicação. | crítica, urgente |
| **Entrega** | Ato de passar a mensagem ao provedor e obter um resultado. | envio |
| **Tentativa** | Uma execução de entrega. Falhas geram novas tentativas segundo PAR-01..PAR-04. | retry |

## Termos vagos do enunciado — como foram fixados

O enunciado congelado diz: *"Serviço de notificação com preferências por pessoa,
supressão e canais externos"*. Três termos vagos, todos resolvidos na Fase 0:

| Termo vago | Concretização | Onde foi decidido |
|---|---|---|
| "preferências por pessoa" | Por categoria × canal, mais fuso e janela de silêncio da pessoa | Nível 1 / Nível 3 |
| "supressão" | Quatro mecanismos distintos: opt-out, janela de silêncio, teto de frequência, deduplicação | decisão P0 `requirement` |
| "canais externos" | E-mail e webhook HTTP, via porta + adaptadores com provedor local | decisões P0 `requirement` / `technology` |

## Invariantes de domínio

1. Uma notificação nunca é descartada sem motivo registrado. Silêncio sem
   registro é defeito, não comportamento.
2. Transacional ignora opt-out, janela de silêncio e teto — **nunca** ignora
   deduplicação (duas cobranças idênticas continuam sendo uma).
3. Preferência ausente ≠ opt-out. A ausência resolve pelo padrão da categoria.
4. O fuso horário da avaliação de janela de silêncio é sempre o da pessoa, nunca
   o do servidor (R-09).
5. Entrega é *at-least-once*; a deduplicação e a chave de idempotência são o que
   torna o efeito observável *exactly-once* (R-06).
