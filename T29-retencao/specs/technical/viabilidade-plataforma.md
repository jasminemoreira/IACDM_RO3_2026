# Tech Feasibility — Python 3 (VERIFICADO, não assumido)

Fase 0, Nível 4. Regra do método: *"a viabilidade técnica da plataforma alvo deve ser
VERIFICADA, não assumida"*. Executado em **Python 3.12.1**, 2026-08-11.

---

## Capacidades ESSENCIAIS

| # | Capacidade | Verificação executada | Resultado |
|---|---|---|---|
| E1 | Round-trip `double ↔ uint64` bit a bit exato | `struct.pack('>d')` → `unpack('>Q')` → `pack('>Q')` → comparar bytes, em 14 valores incluindo `0.0`, `-0.0`, `±inf`, `NaN`, `5e-324` (subnormal), `1e308`, `2⁵³+1`, `1/3` | ✅ **OK — exato em todos** |
| E2 | `0.0` e `-0.0` distinguíveis a nível de bits | comparação de bytes | ✅ diferem (necessário: `0.0 == -0.0` em aritmética, mas o codec é *lossless* e tem de preservar o bit de sinal) |
| E3 | Payload de `NaN` preservado | `0x7ff8000000000001` round-trip | ✅ preservado (um `float('nan')` genérico **perderia** o payload) |
| E4 | Contagem de zeros à esquerda/direita em 64 bits | `64 - x.bit_length()` e `(x & -x).bit_length() - 1` | ✅ `XOR(42.5, 42.6) = 0x00000ccccccccccd` → lead=20, trail=0, signif=44 |
| E5 | Framework de teste para a Fase 6 | `import pytest` | ✅ **pytest 9.0.2** presente |

## Capacidades DESEJÁVEIS

| # | Capacidade | Estado | Consequência |
|---|---|---|---|
| D1 | `numpy` | ✅ **2.1.3** presente | disponível para geração de dataset; **não** usar no codec (o codec é bit a bit, e numpy esconderia o comportamento) |
| D2 | `pyarrow` (Parquet/Arrow) | ❌ **AUSENTE** | Parquet como formato alvo cairia de **Tier 1 para Tier 3** sem instalar dependência. Ver decisão abaixo |
| D3 | `bitarray` | ❌ AUSENTE | irrelevante — `int` de precisão arbitrária + deslocamento da stdlib bastam para o bitstream |

## Nenhuma capacidade essencial ausente ⇒ **SEM BLOQUEADOR**

## Achado com efeito no escopo (D2)

`pyarrow` não está instalado. Isso não bloqueia o projeto, mas **desqualifica Parquet como
formato alvo "de graça"**: seria uma dependência nova a instalar, e o método manda não cortar
escopo para caber na tecnologia — mas também não manda importar dependência sem necessidade.

Os dois formatos do achado central (F1 slot-fixo tipo Whisper × F2 bitstream comprimido tipo
Gorilla) são **ambos implementáveis com a stdlib** e são justamente os que têm **modelos de
acesso incompatíveis** — o que torna a migração do eixo V3 tecnicamente interessante.
Parquet, por ser um terceiro modelo de acesso (colunar por row-group), **acrescentaria custo
sem acrescentar a tensão de projeto que o enunciado explora**.

→ Proposta a confirmar no Nível 5 / Fase 1: **formatos = F1 e F2, stdlib apenas.** Parquet
como escopo negativo explícito com esta justificativa (não como omissão).

## Armadilhas de plataforma registradas antes de codar

| # | Armadilha | Por quê | Mitigação |
|---|---|---|---|
| P1 | `int` do Python é de precisão arbitrária | um deslocamento à esquerda **não trunca em 64 bits** — o bug não aparece, o número só cresce | mascarar com `& 0xFFFFFFFFFFFFFFFF` em toda escrita; testar com valor cujo bit 63 esteja setado |
| P2 | `float('nan') != float('nan')` | um teste de round-trip escrito com `==` **passa falsamente** ou falha por motivo errado | comparar sempre `struct.pack('>d', a) == struct.pack('>d', b)`, nunca `a == b` (é assim que E2/E3 foram verificados) |
| P3 | `(x & -x).bit_length() - 1` com `x == 0` | dá `-1`, não erro | o caso `x == 0` é tratado antes (é o ramo de 1 bit); garantir a ordem |
| P4 | `>d` vs `<d` no `struct` | big/little-endian muda os bytes gravados | fixar **big-endian (`>`)** no formato de arquivo e documentar; não usar ordem nativa (`=`/`@`) |
| P5 | Faixas assimétricas de R1 (`[-63, 64]`) | 7 bits em complemento de dois dão `[-64, 63]`, não `[-63, 64]` | teste explícito para `D = 64` (cabe) e `D = -64` (não cabe) |
