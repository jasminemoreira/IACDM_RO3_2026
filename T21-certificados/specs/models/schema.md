# Esquema de persistência — V(2)

Resposta a `IMP-02` (🔴 — `repositorio` não era implementável sem DDL) e a
`RES-03`, `SEC-07`, `PER-03`, `ASS-07`, `GOV-02`.

Alvo: `node:sqlite`. Todo acesso passa por statements **preparados com parâmetros**
(`SEC-07`) — nenhuma string de SQL é montada por concatenação.

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Ator: quem opera. GOV-03: a criação de ator é registrada na trilha.
CREATE TABLE ator (
  id           TEXT PRIMARY KEY,
  nome         TEXT NOT NULL UNIQUE,
  papel        TEXT NOT NULL CHECK (papel IN ('solicitante','aprovador','auditor')),
  senha_hash   TEXT NOT NULL,          -- scrypt, ver specs/technical/parameters.md
  senha_salt   TEXT NOT NULL,          -- 16 bytes, hex
  ativo        INTEGER NOT NULL DEFAULT 1,   -- ETH-03: desativação sem apagar histórico
  criado_em    TEXT NOT NULL           -- ISO-8601 UTC
);

-- Alvo: host:porta sob monitoramento. GOV-02: dono declarado.
CREATE TABLE alvo (
  id             TEXT PRIMARY KEY,
  host           TEXT NOT NULL,
  porta          INTEGER NOT NULL,
  dono           TEXT NOT NULL,        -- GOV-02: quem responde por este certificado
  limiar_aviso   INTEGER NOT NULL DEFAULT 90,
  limiar_atencao INTEGER NOT NULL DEFAULT 60,
  limiar_critico INTEGER NOT NULL DEFAULT 30,
  criado_em      TEXT NOT NULL,
  UNIQUE (host, porta)
);

-- Observação: o que a varredura viu. PER-04/SUS-02: só grava quando o
-- fingerprint muda; visto_ultima_vez marca a revisita sem duplicar a linha.
CREATE TABLE observacao (
  id                 TEXT PRIMARY KEY,
  alvo_id            TEXT NOT NULL REFERENCES alvo(id),
  fingerprint256     TEXT NOT NULL,
  issuer             TEXT NOT NULL,
  subject            TEXT NOT NULL,
  serial             TEXT NOT NULL,
  san                TEXT NOT NULL,     -- JSON array
  not_before         TEXT NOT NULL,     -- ISO-8601 UTC
  not_after_folha    TEXT NOT NULL,
  not_after_efetivo  TEXT NOT NULL,     -- ASS-01: menor notAfter da cadeia inteira
  profundidade       INTEGER NOT NULL,  -- nº de certificados servidos
  visto_primeiro_em  TEXT NOT NULL,
  visto_ultima_vez   TEXT NOT NULL      -- OBS-02: idade do dado vem daqui
);
CREATE INDEX idx_obs_alvo ON observacao (alvo_id, visto_ultima_vez DESC);

-- Varredura: OBS-01 — o sistema passa a saber quando rodou e o que falhou.
CREATE TABLE varredura (
  id             TEXT PRIMARY KEY,
  iniciada_em    TEXT NOT NULL,
  concluida_em   TEXT,
  alvos_total    INTEGER NOT NULL,
  alvos_ok       INTEGER NOT NULL,
  alvos_falha    INTEGER NOT NULL
);

-- Falha de sonda: RES-01/OBS-03 — o erro vira fato registrado, não silêncio.
CREATE TABLE falha_sonda (
  id           TEXT PRIMARY KEY,
  varredura_id TEXT NOT NULL REFERENCES varredura(id),
  alvo_id      TEXT NOT NULL REFERENCES alvo(id),
  tipo         TEXT NOT NULL CHECK (tipo IN ('timeout','recusado','dns','tls','cadeia-grande')),
  detalhe      TEXT NOT NULL,          -- OBS-03: mensagem original preservada
  ocorrida_em  TEXT NOT NULL
);

-- Pedido: PRO-01/PRO-02 — os estados órfãos ganharam saída.
CREATE TABLE pedido (
  id             TEXT PRIMARY KEY,
  alvo_id        TEXT NOT NULL REFERENCES alvo(id),
  estado         TEXT NOT NULL CHECK (estado IN
                   ('pendente','aprovado','fechado','rejeitado','cancelado','expirado-sem-emissao')),
  solicitante_id TEXT NOT NULL REFERENCES ator(id),
  aprovador_id   TEXT REFERENCES ator(id),
  motivo         TEXT,                  -- obrigatório quando estado = 'rejeitado'
  evidencia_id   TEXT REFERENCES observacao(id),  -- CA-3: o certificado novo
  aberto_em      TEXT NOT NULL,
  decidido_em    TEXT,
  fechado_em     TEXT
);
CREATE INDEX idx_pedido_alvo_estado ON pedido (alvo_id, estado);

-- Trilha: append-only encadeada. Nenhum UPDATE ou DELETE nesta tabela.
CREATE TABLE trilha (
  i             INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo          TEXT NOT NULL,
  ator_id       TEXT REFERENCES ator(id),   -- NULL quando o autor é o sistema
  alvo_id       TEXT REFERENCES alvo(id),
  pedido_id     TEXT REFERENCES pedido(id),
  payload       TEXT NOT NULL,   -- JSON canônico: chaves ordenadas, datas ISO UTC
  registrado_em TEXT NOT NULL,
  hash_anterior TEXT NOT NULL,
  hash          TEXT NOT NULL    -- sha256 hex de (hash_anterior + payload canônico)
);
CREATE INDEX idx_trilha_alvo ON trilha (alvo_id, i);
```

## Tipos de evento da trilha (enumeração fechada)

`ator-criado` · `alvo-cadastrado` · `alvo-removido` · `limiar-alterado` ·
`varredura-iniciada` · `varredura-concluida` · `pedido-aberto` · `pedido-aprovado` ·
`pedido-rejeitado` · `pedido-cancelado` · `pedido-fechado` ·
`troca-nao-autorizada` · `troca-justificada` · `relogio-retrocedeu`

Os quatro primeiros e `limiar-alterado` são a resposta a `GOV-01` (🔴): alterar a
política e mexer no inventário passam a ter autor. `relogio-retrocedeu` é a resposta a
`ASS-08`/`REG-04` — a primeira mitigação real da premissa A2.

## Transação (RES-03)

`varrer()` e cada ação de governança executam dentro de **uma** transação que envolve
gravar o fato e anexar a entrada na trilha. Se a transação falha, nem o estado nem a
trilha mudam — nunca um sem o outro. `repositorio.emTransacao(fn)` é a única forma de
escrita exposta.

## Concorrência (ASS-07)

Uma trava exclusiva de escrita no arquivo do banco na abertura da aplicação: uma
segunda instância recebe erro claro em vez de intercalar escritas na cadeia de hash.
