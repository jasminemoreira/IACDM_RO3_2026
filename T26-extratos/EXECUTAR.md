# Como executar o T26 — roteiro de verificação do UC-1 ao UC-5

Requisitos: Python 3.10+ (testado em 3.12) e as duas dependências aprovadas.

```bash
cd /home/jasmine/INDT/RO3/T26-extratos
python3 -m pip install ofxtools rapidfuzz
```

## 1. Gerar o dataset sintético (com ground truth rotulado)

```bash
python3 -c "from t26.fixtures.gerador import gerar; \
  gerar(42, 200, 'dados', 'perfis/bancox.json', 'perfis/livro.json')"
```

## 2. UC-1 — importar um extrato OFX

```bash
python3 -W ignore -m t26.cli --base minha.db importar --fonte bancox dados/extrato-jul.ofx
```

## 3. UC-2 — reimportar janela SOBREPOSTA (idempotência)

```bash
python3 -W ignore -m t26.cli --base minha.db importar --fonte bancox dados/extrato-julago.ofx
# espere ver "já presentes (mesma linha)" > 0 e "novas" só para o período novo
python3 -W ignore -m t26.cli --base minha.db importar --fonte bancox dados/extrato-jul.ofx
# rodar de novo NÃO deve alterar nada
```

## 4. UC-3 — duplicata cross-source

```bash
python3 -W ignore -m t26.cli --base minha.db importar --perfil perfis/bancox.json dados/extrato-outrafonte.csv
# o mesmo evento por outra fonte: parte funde, parte vira pendência — nunca é descartado
```

## 5. UC-4 — conciliar contra o livro interno

```bash
python3 -W ignore -m t26.cli --base minha.db importar --perfil perfis/livro.json dados/livro.csv
python3 -W ignore -m t26.cli --base minha.db conciliar
# "VAL-3: N de N itens classificados" deve fechar
```

## 6. UC-5 — revisar e resolver uma pendência

```bash
python3 -W ignore -m t26.cli --base minha.db revisar            # lista por impacto financeiro
python3 -W ignore -m t26.cli --base minha.db revisar --acao sao-distintas --pendencia <ID> --autor seunome
python3 -W ignore -m t26.cli --base minha.db revisar            # o item resolvido saiu da fila
```

## 7. Relatório

```bash
python3 -W ignore -m t26.cli --base minha.db relatar
python3 -W ignore -m t26.cli --base minha.db relatar --formato json --saida rel.json
```

## Ordem errada de propósito (verificação de pré-condição)

```bash
rm -f vazia.db && python3 -W ignore -m t26.cli --base vazia.db conciliar; echo "código: $?"
# deve recusar com código 3 e explicar por quê, em vez de devolver 100% de órfãos
```
