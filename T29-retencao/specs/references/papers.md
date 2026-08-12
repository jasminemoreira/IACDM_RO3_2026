# Referências — T29 Compactador de séries temporais

Bibliografia levantada na Fase 0 (pesquisa autorizada pelo operador em 2026-08-11).
Regra vinculante do projeto: **nenhum parâmetro numérico entra no código sem uma
linha desta tabela como fonte** (antídoto a AP7).

## Tier 1 — Fonte primária (peer-reviewed)

| id | Referência | Onde usamos |
|----|-----------|-------------|
| R1 | Pelkonen, T.; Franklin, S.; Teller, J.; Cavallaro, P.; Huang, Q.; Meza, J.; Veeraraghavan, K. **Gorilla: A Fast, Scalable, In-Memory Time Series Database.** *PVLDB* 8(12):1816-1827, 2015. <https://www.vldb.org/pvldb/vol8/p1816-teller.pdf> — DOI <https://dl.acm.org/doi/10.14778/2824032.2824078> | Codec principal (delta-of-delta + XOR). §4.1.1 e §4.1.2 dão a especificação bit a bit. Ver `specs/technical/codec-gorilla.md` |
| R2 | Liakos, P.; Papakonstantinopoulou, K.; Kotidis, Y. **Chimp: Efficient Lossless Floating Point Compression for Time Series Databases.** *PVLDB* 15(11):3058-3070, 2022. <https://www.vldb.org/pvldb/vol15/p3058-liakos.pdf> | Alternativa ao XOR do Gorilla; §4.1.5 tem o esquema completo. Ver `specs/technical/codec-alternativas.md` |
| R3 | Li, R.; Li, Z.; Wu, Y.; Chen, C.; Zheng, Y. **Elf: Erasing-Based Lossless Floating-Point Compression.** *PVLDB* 16(7):1763-1776, 2023. <https://www.vldb.org/pvldb/vol16/p1763-li.pdf> | Estado da arte em razão de compressão. Documentado como **não escolhido** — justificativa em `codec-alternativas.md` |
| R4 | Hishida, T. et al. **Beyond Compression: A Comprehensive Evaluation of Lossless [Floating-Point Compressors].** *PVLDB* 18. <https://www.vldb.org/pvldb/vol18/p4396-hishida.pdf> | Benchmark independente — usar para calibrar expectativa de razão de compressão, não para escolher algoritmo |
| R5 | Ratanaworabhan, P.; Ke, J.; Burtscher, M. **Fast lossless compression of scientific floating-point data** (FPC), DCC 2006 — citado como [17]/[25] em R1 §4.1.2 | Origem do esquema de predição que o Gorilla simplificou. Contexto histórico |

## Tier 2 — Especificação de formato / implementação de referência

| id | Referência | Onde usamos |
|----|-----------|-------------|
| R6 | **The Whisper Database** — Graphite docs. <https://graphite.readthedocs.io/en/latest/whisper.html> | Layout de arquivo com slot fixo e arquivos de retenção múltipla. Bytes exatos em `specs/technical/formatos-armazenamento.md` |
| R7 | **RRDtool** — RRA / consolidation functions / `xff`. <https://oss.oetiker.ch/rrdtool/doc/rrdcreate.en.html> | Origem do conceito de round-robin archive e do `xFilesFactor` |
| R8 | **Prometheus TSDB** — chunk XOR, head block 2h, `DefaultSamplesPerChunk`=120. <https://pkg.go.dev/github.com/prometheus/prometheus/tsdb> e <https://ganeshvernekar.com/blog/prometheus-tsdb-compaction-and-retention/> | Implementação de referência do codec do Gorilla em produção; parâmetros de bloco e compactação |
| R9 | **Thanos Compact** — downsampling 5m / 1h, retenção por resolução. <https://thanos.io/tip/components/compact.md/> | Política de retenção multi-resolução com números reais (40h, 10 dias) |
| R10 | **Apache Parquet — Encodings.** <https://parquet.apache.org/docs/file-format/data-pages/encodings/> | `DELTA_BINARY_PACKED`, `BYTE_STREAM_SPLIT`, RLE/bit-packing — candidato a formato alvo da troca |
| R11 | **Apache Arrow — Columnar Format / IPC.** <https://arrow.apache.org/docs/format/Columnar.html> | Formato in-memory e IPC; distinção in-memory vs on-disk |
| R12 | Vernekar, G. **Prometheus TSDB (Part 6): Compaction and Retention.** <https://ganeshvernekar.com/blog/prometheus-tsdb-compaction-and-retention/> | Como retenção por tempo e por tamanho interagem com compactação |

## Tier 3 — Contexto secundário (não citar como fonte de parâmetro)

| id | Referência | Nota |
|----|-----------|------|
| R13 | TigerData (Timescale). **Time-series compression algorithms, explained.** <https://www.tigerdata.com/blog/time-series-compression-algorithms-explained> | Bom panorama (simple-8b, RLE, dicionário, LZ). Números do Gorilla aqui estão **arredondados** — usar R1 |
| R14 | Acolyer, A. **Gorilla — the morning paper.** <https://blog.acolyer.org/2016/05/03/gorilla-a-fast-scalable-in-memory-time-series-database/> | Resumo. ⚠️ As faixas de bucket do delta-of-delta neste resumo **divergem** de R1 §4.1.1 — vale R1 |

## Descoberto durante a implementação (Fase 7)

Nenhuma referência nova foi necessária — o material da Fase 0 bastou para os 12 módulos, o que
é em si um resultado: as lacunas que apareceram não eram de *literatura ausente*, eram de
**codificação de campo que a literatura deixa implícita** (ver `lessons.md` §L4).

O que se aprendeu sobre as fontes já listadas:

| Ref | Aprendizado |
|---|---|
| R1 (Gorilla) | Especifica a semântica bit a bit e **cala sobre a codificação de três campos**: a faixa assimétrica em 7 bits, o comprimento significativo quando é 64, e o `prev_delta` inicial. Todas as três geraram defeito real |
| R6 (Whisper) | A doc dá `struct` **e** um tamanho em bytes, e o tamanho estava errado no resumo que consultei (16, não 20). Também: a **validade-por-timestamp** — que faz o round-robin *ser* a expiração — é a chave do formato e não está em destaque na doc |
| R9 (Thanos) | Guardar min/max/sum/count existe para permitir **re-agregação sem erro**. Entendida a razão, a contradição aparente com R6 se resolve por aritmética: quatro dos cinco métodos de R6 são associativos, só `average` não é |
| R14 (resumo do Gorilla) | Confirmado como não-confiável para parâmetros: as faixas de bucket divergem do paper. Serviu de aviso e virou a regra de L5 |

**Regra derivada e agora escrita:** quando a fonte fornece a **fórmula** e o **resultado**, a
fórmula é a autoridade. Foi violada duas vezes neste ciclo, com dias — e um ciclo inteiro — de
diferença.

## Nota de rastreabilidade

R1 e R2 foram lidos no PDF original (texto extraído), não em resumo de terceiros.
As faixas de bucket em `codec-gorilla.md` são transcrição literal de R1 §4.1.1, itens
(b)-(f). Divergência conhecida: R14 lista faixas diferentes — é erro do resumo.
