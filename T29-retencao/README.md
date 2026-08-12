# tsz — compactador de séries temporais

Codec Gorilla, retenção multi-tier por downsampling e migração entre formatos de
armazenamento. **Python 3.12, só stdlib** — zero dependência externa.

```bash
export PYTHONPATH=/caminho/para/T29-retencao
python3 -m tsz.cli --help
```

## Os três eixos

| Eixo | O que faz |
|---|---|
| **Comprimir** | delta-of-delta nos timestamps + XOR nos valores, conforme Pelkonen et al., *Gorilla*, PVLDB 8(12), 2015, §4.1. Sem perda: o round-trip é exato bit a bit |
| **Reter** | tiers de resolução com janela própria, função de agregação e `xFilesFactor` (Whisper/RRDtool), com downsampling entre tiers |
| **Trocar de formato** | migração do acervo entre **F1** (slot fixo, layout Whisper) e **F2** (bitstream Gorilla em chunks), com verificação ponto a ponto |

## Uso

```bash
# criar (default: cru 60s/15d + 5m/90d)
python3 -m tsz.cli create cpu.load --format f2

# ingerir CSV "ts,valor" (ou - para stdin)
python3 -m tsz.cli ingest cpu.load --input pontos.csv

# ler um intervalo SEMIABERTO [from, to)
python3 -m tsz.cli read cpu.load --from 1786464000 --to 1786464060

# ver o que a retenção FARIA, antes de fazer
python3 -m tsz.cli retain cpu.load --dry-run

# aplicar (derivar → gravar → verificar → expirar, nessa ordem)
python3 -m tsz.cli retain cpu.load

# migrar de formato; a origem NUNCA é removida
python3 -m tsz.cli migrate cpu.load --to-format f1

# estado do acervo: tiers, pontos, bytes por tier, integridade
python3 -m tsz.cli info cpu.load --history

# razão de compressão medida por perfil de série
python3 -m tsz.cli report
```

Configuração de tiers: `resolução:retenção[:agregação[:xff[:idade_mínima]]]`, separados por
vírgula. Durações aceitam `s`, `m`, `h`, `d`.

```bash
python3 -m tsz.cli validate-config --tiers "60:15d:average,300:90d:average:0.5:40h"
```

## ⚠️ O que você precisa saber antes de usar

**`retain` é um comando, não um processo.** Nada envelhece sozinho: se você não agendar
`retain` externamente (cron, systemd timer), o acervo cresce sem limite — o oposto do
propósito da ferramenta. Isso é uma decisão consciente: embutir um agendador seria outro
produto.

**A retenção efetiva excede a nominal.** Em F2 a granularidade de descarte é o **chunk**
(2 h), então um chunk só sai quando *todo* o seu intervalo caiu fora da janela.
`info` e o relatório de `retain` mostram o `effective_before_ts` real.

**Downsampling é irreversível.** O dado cru é descartado. Para recomputar um tier derivado
depois de corrigir a configuração, apague os arquivos daquele tier — a marca d'água é
derivada do dado, então ele é refeito na próxima execução.

**O journal (`journal.jsonl`) é evidência contra erro operacional, não contra alteração
deliberada.** É um arquivo de texto editável, sem encadeamento de hash. Rotação é sua, como
em qualquer log.

**O `crc32` de cada chunk detecta corrupção acidental — não autentica.** Quem tem permissão
de escrita recalcula o checksum.

**F1 tem timestamp de 4 bytes: estoura em 2106.** É a limitação do formato Whisper original,
preservada de propósito para fidelidade ao layout. `migrate` aborta antes de escrever se o
dado não couber no destino.

**F1 pré-aloca o arquivo inteiro na criação.** Um tier cru de 1 s com 15 dias de retenção
ocupa ~15 MB por série mesmo vazio. É o preço do tamanho previsível e da escrita O(1) por
slot; `info` mostra os bytes por tier para a comparação ser feita antes da escolha.

**Escritor único.** Não há trava de arquivo: dois processos escrevendo o mesmo acervo ao
mesmo tempo o corrompem.

## Formatos

**F1 — slot fixo (layout Whisper, byte-exato)**

```
Metadata     '>2LfL'  16 B : aggregationType, maxRetention, xFilesFactor, archiveCount
ArchiveInfo  '>3L'    12 B : offset, secondsPerPoint, points
Point        '>Ld'    12 B : timestamp (4 B), value (8 B)
```

Um slot é válido apenas se o timestamp gravado nele for igual ao esperado daquela posição —
é assim que o round-robin expira o dado antigo, sem mecanismo separado.

**F2 — bitstream Gorilla, um arquivo por chunk**

```
acervo-cpu.load/
├── meta.json        # tiers, format_version, block_seconds
├── journal.jsonl
└── tier-0/
    ├── 1786464000.chunk
    └── 1786471200.chunk
```

O nome do arquivo é o índice: uma leitura de intervalo descarta chunks sem decodificá-los.
Cada chunk carrega `n_points` e `crc32`.

## Razão de compressão

**A razão depende do perfil da série, não do algoritmo.** Medido com `--n 7200 --seed 7`:

| Perfil | B/ponto | Razão vs 16 B |
|---|---|---|
| gauge inteiro estável | 0,33 | 48,5× |
| pontos faltando | 0,40 | 40,1× |
| jitter de timestamp | 0,64 | 24,9× |
| contador monotônico | 2,67 | 6,0× |
| temperatura, 1 decimal | 6,41 | 2,5× |
| float de alta precisão | 6,63 | 2,4× |

Os 1,37 B/ponto publicados no paper do Gorilla são propriedade do dataset de monitoração do
Facebook — não do algoritmo. Por isso esta ferramenta **mede e reporta** a razão em vez de
prometer um limiar. Rode `report` no seu perfil.

## Documentação de projeto

`specs/` guarda o material que sustenta cada decisão: `references/papers.md` (14 referências
citadas), `technical/codec-gorilla.md` (a especificação bit a bit), `technical/architecture.md`
(as três versões da arquitetura), `design/coverage-matrix.md` (109 achados da crítica
adversarial) e `validation/criterios-aceitacao.md` (os critérios de aceitação).
