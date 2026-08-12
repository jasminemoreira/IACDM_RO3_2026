# Análise competitiva — quem já resolve isto e o que deixam de fora

Fase 0. Objetivo: saber o que **não** precisamos inventar, e onde está a lacuna que
justifica o projeto existir.

---

## Panorama

| Produto | Compressão | Retenção | Troca de formato | Lacuna |
|---|---|---|---|---|
| **RRDtool** (R7) | nenhuma (slot fixo) | downsampling multi-RRA com CF + xff | não | formato único, imutável desde os anos 1990 |
| **Graphite/Whisper** (R6) | nenhuma (12 B/ponto) | multi-archive, 5 métodos de agregação, regra de divisibilidade | não — `whisper-resize` reescreve, não troca formato | sem compressão; timestamp de 4 B (limite 2106) |
| **Prometheus TSDB** (R8, R12) | XOR do Gorilla, ~1,37 B/amostra | **expiração** por tempo e por tamanho, granularidade de bloco | não | **não faz downsampling** — é a lacuna declarada que o Thanos existe para preencher |
| **Thanos Compact** (R9) | herda a do Prometheus | downsampling cru→5m→1h + retenção por resolução | não (blocos TSDB sempre) | acoplado ao ecossistema Prometheus/object storage |
| **InfluxDB / VictoriaMetrics / TimescaleDB** | codecs próprios (Gorilla-like, simple-8b, RLE) | retention policy + agregações contínuas | não exposto ao usuário | banco completo — ordens de magnitude acima do porte deste projeto |
| **Parquet + engine** (R10) | encodings colunares, 5–10× | nenhuma (é formato, não sistema) | é o formato, não troca | nenhuma noção de retenção ou de série temporal |

## Achados que orientam o escopo

1. **Ninguém da lista trata "troca de formato de armazenamento" como capacidade de
   primeira classe.** Prometheus faz *compactação* (bloco pequeno → bloco grande, mesmo
   formato). Whisper tem `whisper-resize` (mesma família de formato, retenção diferente).
   Migrar entre **famílias** de formato é sempre uma ferramenta externa e ad-hoc.
   → Esta é a lacuna real. O terceiro eixo do enunciado é o que não existe pronto.

2. **A separação compressão × retenção é universal e ninguém a mistura.** Em todos os
   sistemas, o codec não sabe da política e a política não sabe do codec — a fronteira é o
   bloco/arquivo. Isto é evidência empírica forte a favor de uma decomposição em módulos
   com essa mesma fronteira (insumo para a Fase 1, questão 1: decomposição).

3. **Downsampling preserva agregados, não médias** (R9: min/max/sum/count). Um projeto que
   guardar `average` no tier reduzido não é comparável a nenhum destes e não permite
   re-agregar. Decisão a tomar explicitamente.

4. **Retenção destrutiva e downsampling coexistem** (Thanos: retenção *por resolução*). São
   políticas ortogonais compostas, não alternativas. Se o projeto implementar só uma,
   precisa dizer qual e por quê.

5. **A regra de divisibilidade do Whisper** (R6) é a única invariante de configuração
   formalizada que encontrei no domínio. É de graça implementar e é o teste negativo mais
   óbvio do projeto.

## O que NÃO copiar

- **Escala.** R1 opera 2 bilhões de séries em 20 máquinas; R9 opera object storage de TBs. O
  porte deste projeto é 8–12 módulos em sessão única. Copiar a *arquitetura* desses
  sistemas (WAL distribuído, sharding, replicação) é AP2 (complexidade como falsa solução).
  Copiar o *codec* e a *semântica de retenção* é Tier 2 legítimo.
- **Cardinalidade.** Todos os sistemas acima gastam a maior parte da complexidade em índice
  de séries e cardinalidade de labels. Se o nosso modelo de série for simples, esse custo
  não se transfere — e não deve ser importado "por completude".
