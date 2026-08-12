# Lições deste projeto — T25, ciclo v1.0

Sobre **este projeto**, não sobre a metodologia. Insumo do próximo ciclo.

---

## L1 · Dinheiro neste domínio não cabe em centavos — e o erro reaparece na tela

**Descoberta de domínio.** Uma requisição ao Opus 5 com mil tokens de entrada custa
meio centavo; no Haiku, um décimo de centavo. Armazenar em centavos truncaria
requisições inteiras para **zero** — o consumo sumiria da contabilidade e o teto
nunca seria atingido. Adotamos nano-unidades (10⁻⁹) com aritmética inteira, e
verificamos que todo preço e multiplicador vigente (0,1× · 1,25× · 2,0× · 0,5×)
resulta em inteiro exato nessa escala.

**O que não previmos:** o mesmo erro de escala voltou pela **apresentação**. A SPA
formatava com 2 casas decimais, e um teto de US$ 0,01 com consumo de US$ 0,0097
aparecia como `$0.01` e `$0.01`, saldo `$0.00`. O painel arredondava exatamente a
informação que existe para transmitir. Só o teste em navegador real pegou.

→ **Para o v2:** precisão é decisão de ponta a ponta — armazenamento **e** exibição.
Ao mudar de moeda ou de faixa de preço, revalidar as duas.

## L2 · A vida da reserva deve ser a vida da requisição, nunca um relógio

**Padrão que funcionou, depois de um que não funcionou.** O problema central é
manter um teto sobre uma soma enquanto a transação é longa — método Escrow
(O'Neil, 1986). A primeira solução para reservas órfãs foi um TTL de 15 minutos.
A crítica adversarial mostrou que ele **cria** dois defeitos críticos: expira a
reserva de uma requisição ainda viva (gerações longas passam de 15 min), e a
guarda de idempotência então descarta a reconciliação tardia — perdendo a
contabilidade, não só o saldo.

A solução foi **remover** o TTL: bloco `finally` cobre todos os caminhos de saída,
e queda de processo é tratada no arranque (num processo recém-iniciado nenhuma
requisição pode estar em voo). Sumiram o parâmetro, o estado `'expirada'`, a
varredura, a observabilidade da varredura e o laço de controle sem medição.

→ **Para o v2:** se houver múltiplas instâncias, esta solução **cai** — ela depende
da premissa de processo único. Um gateway distribuído precisa de outra resposta,
provavelmente com lease por instância.

## L3 · O clamp que garante o invariante também esconde a premissa falhando

**Premissa que se revelou perigosa.** `min(custo_real, reserva)` faz o invariante
do teto valer *por construção*. Consequência não óbvia: o critério de acerto
passaria **mesmo se a premissa A8 (`tokens ≤ bytes`) fosse falsa** — o excedente
simplesmente não seria contabilizado. Um teste verde não distinguiria "A8
verdadeira" de "A8 falsa mascarada".

Adicionamos um log `ERROR` que dispara quando o clamp atua. É o único sinal capaz
de denunciar A8 em produção.

→ **Para o v2:** A8 continua **não verificada** — exige comparar `count_tokens` real
com o tamanho em bytes numa amostra. É o primeiro item de qualquer próximo ciclo.

## L4 · Executar encontra o que ler não encontra — 8 defeitos, zero por leitura

**Fato medido neste ciclo.** Nenhum dos 8 defeitos apareceu revisando código:

| Como apareceu | Defeitos |
|---|---|
| Rodar o teste de integração | `check_same_thread`, clamp silencioso |
| Conferir o adapter contra a spec | TTL do cache 1h cobrado como 5m (1,6× a menos) |
| Um curl meu com escape errado | corpo não-JSON derrubava o login com 500 |
| Comparar painel e gateway lado a lado | painel dizia "ativa" enquanto o gateway dava 402 |
| Testar 100/40/20 tokens | o limite exibido ignorava o custo do prompt |
| Navegador real lendo a tela | 2 casas decimais escondendo teto, consumo e saldo |

Os 48 testes de API **não podiam** achar o último: verificam JSON com nano inteiro,
não texto renderizado.

→ **Para o v2:** cobertura de API não substitui cobertura de UI. Manter o smoke
test de navegador.

## L5 · Armadilhas concretas da stack

- **`sqlite3` + servidor ASGI:** exige `check_same_thread=False`, porque a app é
  construída numa thread e servida noutra. A segurança vem do desenho (processo
  único, event loop, `BEGIN IMMEDIATE`), não do guard da biblioteca.
- **`BEGIN IMMEDIATE`, não `BEGIN`:** adquire o lock de escrita na abertura. Sem
  isso, ler-decidir-escrever pode intercalar — a anomalia *lost update*, que é
  precisamente o modo de falha que o critério de acerto mede.
- **O `usage` não informa o TTL do cache.** Quem informa é a requisição
  (`cache_control.ttl`). Quem contabiliza a partir do `usage` sozinho subcontabiliza.
- **O hook de teste do motor precisa da saída não canalizada.** `pytest ... | tail`
  não é testemunhado; `pytest tests` é.

## L6 · O que ficou por fazer (dívida honesta deste ciclo)

1. **A8 nunca verificada** (CA-11) — sustenta o critério de acerto.
2. **Chave real do provedor nunca usada** — suíte e teste manual rodaram contra o
   upstream simulado. Erros de contrato só apareceriam em produção.
3. **`MEC-01` continua verdadeiro:** o preço promocional do Sonnet 5 expira em
   **2026-08-31**. Depois disso a linha de `rate_card.json` vencida faz o modelo
   ser negado — correto, mas exige manutenção da tabela nessa data.
4. **`GAM-03` mitigado, não resolvido:** o limite de reservas simultâneas encarece
   o ataque de negação por reserva; não o elimina.
