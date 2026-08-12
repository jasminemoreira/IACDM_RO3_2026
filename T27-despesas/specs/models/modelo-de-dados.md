# Modelo de dados — T27

Derivado da arquitetura V(1) (`specs/technical/architecture.md`) e das invariantes
(`specs/domain/glossario-e-invariantes.md`). SQLite, mapeamento manual, sem ORM.

## Tabelas

```sql
-- Matriz DoA: seed fixo, não editável em runtime (A3)
CREATE TABLE papel (
  id            TEXT PRIMARY KEY,          -- 'coordenador', 'gerente', 'diretor'
  nome          TEXT NOT NULL,
  nivel         INTEGER NOT NULL UNIQUE,   -- 1,2,3… linear e sem lacunas (A1)
  limite_centavos INTEGER NOT NULL         -- INV-12: inteiro, nunca REAL
);

CREATE TABLE usuario (
  id       TEXT PRIMARY KEY,
  nome     TEXT NOT NULL,
  papel_id TEXT NOT NULL REFERENCES papel(id)   -- exatamente um papel (A2)
);

CREATE TABLE despesa (
  id              TEXT PRIMARY KEY,
  solicitante_id  TEXT NOT NULL REFERENCES usuario(id),
  valor_centavos  INTEGER NOT NULL CHECK (valor_centavos > 0),
  descricao       TEXT NOT NULL,
  estado          TEXT NOT NULL CHECK (estado IN ('PENDENTE','APROVADA','REJEITADA')),
  nivel_corrente  INTEGER,                 -- NULL quando terminal
  criada_em       TEXT NOT NULL            -- ISO-8601 UTC (A6); ordena a bandeja FIFO
);

CREATE TABLE delegacao (
  id            TEXT PRIMARY KEY,
  delegante_id  TEXT NOT NULL REFERENCES usuario(id),
  delegado_id   TEXT NOT NULL REFERENCES usuario(id),
  inicio        TEXT NOT NULL,             -- ISO-8601 UTC
  fim           TEXT NOT NULL,
  estado        TEXT NOT NULL CHECK (estado IN ('ATIVA','REVOGADA')),
  revogada_em   TEXT,                      -- preenchido só quando REVOGADA
  revogada_por  TEXT REFERENCES usuario(id),
  criada_em     TEXT NOT NULL,
  CHECK (fim > inicio),
  CHECK (delegante_id <> delegado_id)
);

-- Trilha append-only (INV-8): sem UPDATE, sem DELETE. Só INSERT.
CREATE TABLE evento_trilha (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,  -- ordem total de escrita
  despesa_id      TEXT NOT NULL REFERENCES despesa(id),
  tipo            TEXT NOT NULL,   -- 'CRIADA','APROVADA_NIVEL','REJEITADA','DEVOLVIDA_AO_DELEGANTE'
  estado_anterior TEXT,
  estado_novo     TEXT NOT NULL,
  nivel           INTEGER,
  ator_id         TEXT REFERENCES usuario(id),        -- quem agiu (ator efetivo)
  em_nome_de_id   TEXT REFERENCES usuario(id),        -- NULL quando não há delegação (INV-7)
  limite_exercido_centavos INTEGER,                   -- autoridade exercida no instante (INV-7)
  motivo          TEXT,                               -- obrigatório em REJEITADA (INV-9)
  ocorrido_em     TEXT NOT NULL
);

CREATE TABLE evento_delegacao (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  delegacao_id TEXT NOT NULL REFERENCES delegacao(id),
  tipo         TEXT NOT NULL,   -- 'CRIADA','REVOGADA','EXPIRADA_OBSERVADA'
  ator_id      TEXT REFERENCES usuario(id),
  ocorrido_em  TEXT NOT NULL
);
```

## Notas de modelagem

- **`estado` da delegação não guarda `EXPIRADA`.** Expiração é função do relógio, não um
  fato gravado — o sistema não agenda nada (escopo negativo). `ativaEm(instante)` avalia
  `estado='ATIVA' AND inicio <= instante < fim`. Gravar `EXPIRADA` exigiria um agendador e
  criaria a possibilidade de o banco discordar do relógio.
- **`nivel_corrente` é o nível do papel que decide agora**, não a posição na cadeia. A
  cadeia é recalculada por M-02 a partir de (valor, papel do solicitante) — não é
  materializada, o que mantém A3 (matriz imutável) como única fonte de verdade.
- **`limite_exercido_centavos` é copiado no evento**, não referenciado. É o que faz INV-6
  (autoridade avaliada no instante do ato) sobreviver a qualquer mudança futura da matriz.
- **INV-8 é imposto por disciplina de acesso**, não por constraint SQL: o `TrilhaRepo` só
  expõe `anexar` e `porDespesa`. Não há caminho de UPDATE/DELETE no código.
- **INV-5** (vigências sobrepostas) não é expressável como constraint em SQLite; é checado
  em M-03 dentro da transação de criação, lendo as ativas do delegante.

## Seed (a produzir na Fase 5, depositar em `specs/datasets`)

Progressão de aproximadamente uma ordem de grandeza por nível, forma justificada em
`specs/references/dominio-aprovacao-despesas.md` (os números em si são arbitrários):

| papel | nível | limite |
|---|---|---|
| Coordenador | 1 | R$ 5.000,00 (500000 centavos) |
| Gerente | 2 | R$ 50.000,00 (5000000) |
| Diretor | 3 | R$ 500.000,00 (50000000) |

Usuários: ao menos 2 por papel — necessário para exercitar INV-4 (mesmo ator em dois
níveis) e delegação lateral sem violar INV-2.
