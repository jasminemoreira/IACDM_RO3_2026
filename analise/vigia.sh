#!/usr/bin/env bash
# Vigia os 12 projetos do lote e emite um evento por marco.
#
# Existe para a operadora não ter que avisar nada no meio do caminho: ela inicializa
# pelo Versus, opera, e este laço detecta os dois momentos que importam.
#
#   FASE-4  — a matriz está fechada (o laço 2↔3 terminou). É quando o formato precisa
#             ser validado com a sessão ainda aberta: nome de lente por sigla,
#             severidade fora das três e `duplica` apontando id inexistente são coisas
#             que os gates da extensão não pegam, e corrigir depois é caro.
#   FIM     — fase 7 com os TRÊS critérios de saída registrados (`specs_updated`,
#             `lessons_documented`, `human_feedback`). Dispara o fechamento: estimativa
#             sobre a V(1), análise, remarcação cega, RETRABALHO.
#   PARADO  — fase 7, 10 min sem escrita, e critérios de saída FALTANDO. O projeto está
#             estacionado esperando alguém, quase sempre o `human_feedback`.
#
# POR QUE NÃO É MAIS SÓ SILÊNCIO
# ------------------------------
# A regra anterior era "fase 7 e parado há 10 min", e errou nos dois sentidos em
# projetos reais:
#
#   T24-catalogo — tudo pronto, os três critérios `met`, e o FIM atrasou 10 min porque
#                  o cronômetro ainda contava.
#   T22-plantoes — o cronômetro estourou com a fase 7 INTOCADA (nenhum critério
#                  registrado, última decisão de fase 6) e o FIM disparou cedo. Rodar o
#                  fechamento ali teria analisado um projeto inacabado.
#
# Silêncio na fase 7 significa "acabou" ou "está esperando você", e os dois casos pedem
# avisos diferentes. O estado tem a resposta; o relógio não.
#
# O guard de 60 s no FIM não é o critério — é só para não ler o `state.json` no meio de
# uma escrita.
#
# Cada marco é emitido UMA vez por projeto (registro em .vigia-estado). Silêncio
# significa "nada mudou", não "nada quebrou" — por isso ERRO também é evento.
set -uo pipefail
RO3="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MARCAS="$RO3/analise/.vigia-estado"
touch "$MARCAS"
PARADO=600   # segundos sem alteração no state.json para considerar concluído

ja() { grep -qxF "$1" "$MARCAS"; }
marca() { echo "$1" >> "$MARCAS"; }

while true; do
  for d in "$RO3"/T*/; do
    p="${d%/}"; nome="$(basename "$p")"
    st="$p/.versus/state.json"
    [ -f "$st" ] || continue

    fase=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['currentPhase'])" "$st" 2>/dev/null) || {
      ja "ERRO-$nome" || { echo "ERRO $nome: state.json ilegível"; marca "ERRO-$nome"; }
      continue; }

    if [ "$fase" -ge 4 ] && ! ja "FASE4-$nome"; then
      echo "FASE-4 $nome"; marca "FASE4-$nome"
    fi

    if [ "$fase" -ge 7 ] && ! ja "FIM-$nome"; then
      idade=$(( $(date +%s) - $(stat -c %Y "$st") ))
      faltam=$(python3 -c "
import json,sys
s=json.load(open(sys.argv[1]))
tem={c['criterion'] for c in s.get('exitCriteria',[]) if c['phase']==7 and c.get('met')}
print(','.join(sorted({'specs_updated','lessons_documented','human_feedback'} - tem)))" "$st" 2>/dev/null) || faltam="ilegivel"

      if [ -z "$faltam" ] && [ "$idade" -ge 60 ]; then
        echo "FIM $nome"; marca "FIM-$nome"
      elif [ -n "$faltam" ] && [ "$idade" -ge "$PARADO" ] && ! ja "PARADO-$nome"; then
        echo "PARADO $nome na fase 7 há $((idade/60)) min — falta: $faltam"
        marca "PARADO-$nome"
      fi
    fi
  done
  sleep 60
done
