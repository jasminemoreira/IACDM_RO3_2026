# Tabela número→comando

**Gerada, não transcrita.** Cada valor foi recomputado do corpus na execução que
produziu este arquivo:

```bash
python3 tools/tabela_numeros.py
```

Se um valor aqui divergir do manuscrito, um dos dois está errado.

---

## Corpus

*tab:corpus*

```
python3 analise/ro3_analise.py T*-*  ·  python3 tools/tabela_numeros.py
```

| valor | o que é |
|---|---|
| `12` | projetos válidos |
| `1100` | achados |
| `195` | críticos |
| `657` | importantes |
| `248` | sugestões |
| `1029` | defeitos distintos, clusterização do gerador |
| `130` | módulos |
| `36.8` | horas decorridas, pausas incluídas |
| `3.2` | mediana de horas por projeto |
| `28` | iterações do laço 2↔3 (9×2, 2×3, 1×4) |

## Cobertura de ativação

*tab:activation*

```
python3 tools/tabela_numeros.py
```

| valor | o que é |
|---|---|
| `12` | RES ativou em N de 12 projetos |
| `12` | UX ativou em N de 12 projetos |
| `12` | SUS ativou em N de 12 projetos |
| `12` | PRO ativou em N de 12 projetos |
| `12` | GOV ativou em N de 12 projetos |
| `12` | CTR ativou em N de 12 projetos |
| `12` | LIN ativou em N de 12 projetos |
| `10` | MEC ativou em N de 12 projetos |
| `9` | OBS ativou em N de 12 projetos |
| `7` | JOG ativou em N de 12 projetos |
| `5` | ETI ativou em N de 12 projetos |
| `4` | MIG ativou em N de 12 projetos |

## Distribuição de sobreposição

*tab:overlap*

```
python3 analise/ro3_analise.py T*-*  (Passos 3 e 4)  ·  python3 tools/tabela_numeros.py
```

| valor | o que é |
|---|---|
| `11%` | sobreposição média das 19 lentes |
| `2%` | menor — ARQ |
| `33%` | maior — SUS |
| `4` | lentes acima de 15% — SUS 33%, DES 20%, JOG 20%, ETI 17% |
| `41` | pares que compartilham ao menos um defeito, de 171 |
| `171` | pares possíveis de lentes |
| `24%` | idem, proporção |
| `0.10` | maior Jaccard par a par — DES × SUS |
| `9` | defeitos em comum nesse par |
| `0.01` | ARQ × PRE — o par que o §4 do protocolo suspeitava a priori |

## Contribuição exclusiva e concordância de marcação

*tab:robustness · tab:kappa*

```
python3 analise/figuras.py --conferir
```

| valor | o que é |
|---|---|
| `51565` | pares avaliáveis, soma intra-projeto |
| `1029` | clusters sob a marcação — gerador |
| `960` | clusters sob a marcação — qwen full |
| `788` | clusters sob a marcação — gpt-5.4 |
| `668` | clusters sob a marcação — união das quatro |
| `82` | pares marcados — Generator (Opus 5) |
| `87` | pares marcados — Qwen Q4 (local) |
| `153` | pares marcados — Qwen full |
| `340` | pares marcados — GPT-5.4 |
| `84` | co-marcações observadas — Qwen full × GPT-5.4 |
| `1.01` | esperado ao acaso — Qwen full × GPT-5.4 |
| `0.338` | κ de Cohen — Qwen full × GPT-5.4 |
| `33` | co-marcações observadas — Generator (Opus 5) × Qwen full |
| `0.24` | esperado ao acaso — Generator (Opus 5) × Qwen full |
| `0.279` | κ de Cohen — Generator (Opus 5) × Qwen full |
| `48` | co-marcações observadas — Generator (Opus 5) × GPT-5.4 |
| `0.54` | esperado ao acaso — Generator (Opus 5) × GPT-5.4 |
| `0.226` | κ de Cohen — Generator (Opus 5) × GPT-5.4 |
| `13` | co-marcações observadas — Generator (Opus 5) × Qwen Q4 (local) |
| `0.14` | esperado ao acaso — Generator (Opus 5) × Qwen Q4 (local) |
| `0.152` | κ de Cohen — Generator (Opus 5) × Qwen Q4 (local) |
| `17` | co-marcações observadas — Qwen Q4 (local) × Qwen full |
| `0.26` | esperado ao acaso — Qwen Q4 (local) × Qwen full |
| `0.140` | κ de Cohen — Qwen Q4 (local) × Qwen full |
| `24` | co-marcações observadas — Qwen Q4 (local) × GPT-5.4 |
| `0.57` | esperado ao acaso — Qwen Q4 (local) × GPT-5.4 |
| `0.110` | κ de Cohen — Qwen Q4 (local) × GPT-5.4 |
| `35%` | redução de clusters da marcação do gerador para a união |
| `40%` | recuperação das marcações do gerador — Qwen full |
| `59%` | recuperação das marcações do gerador — GPT-5.4 |
| `16%` | recuperação das marcações do gerador — Qwen Q4 (local) |
| `98` | contribuição exclusiva — PRE sob Generator, Opus 5 |
| `88` | contribuição exclusiva — ARQ sob Generator, Opus 5 |
| `73` | contribuição exclusiva — UX sob Generator, Opus 5 |
| `74` | contribuição exclusiva — SEG sob Generator, Opus 5 |
| `55` | contribuição exclusiva — CIE sob Generator, Opus 5 |
| `60` | contribuição exclusiva — PRO sob Generator, Opus 5 |
| `76` | contribuição exclusiva — LIN sob Generator, Opus 5 |
| `52` | contribuição exclusiva — GOV sob Generator, Opus 5 |
| `47` | contribuição exclusiva — DES sob Generator, Opus 5 |
| `36` | contribuição exclusiva — OBS sob Generator, Opus 5 |
| `70` | contribuição exclusiva — IMP sob Generator, Opus 5 |
| `42` | contribuição exclusiva — MEC sob Generator, Opus 5 |
| `42` | contribuição exclusiva — CTR sob Generator, Opus 5 |
| `34` | contribuição exclusiva — REG sob Generator, Opus 5 |
| `20` | contribuição exclusiva — JOG sob Generator, Opus 5 |
| `56` | contribuição exclusiva — RES sob Generator, Opus 5 |
| `26` | contribuição exclusiva — SUS sob Generator, Opus 5 |
| `15` | contribuição exclusiva — ETI sob Generator, Opus 5 |
| `14` | contribuição exclusiva — MIG sob Generator, Opus 5 |
| `85` | contribuição exclusiva — PRE sob Qwen full |
| `75` | contribuição exclusiva — ARQ sob Qwen full |
| `68` | contribuição exclusiva — UX sob Qwen full |
| `65` | contribuição exclusiva — SEG sob Qwen full |
| `48` | contribuição exclusiva — CIE sob Qwen full |
| `60` | contribuição exclusiva — PRO sob Qwen full |
| `57` | contribuição exclusiva — LIN sob Qwen full |
| `48` | contribuição exclusiva — GOV sob Qwen full |
| `44` | contribuição exclusiva — DES sob Qwen full |
| `34` | contribuição exclusiva — OBS sob Qwen full |
| `53` | contribuição exclusiva — IMP sob Qwen full |
| `36` | contribuição exclusiva — MEC sob Qwen full |
| `37` | contribuição exclusiva — CTR sob Qwen full |
| `36` | contribuição exclusiva — REG sob Qwen full |
| `25` | contribuição exclusiva — JOG sob Qwen full |
| `52` | contribuição exclusiva — RES sob Qwen full |
| `28` | contribuição exclusiva — SUS sob Qwen full |
| `18` | contribuição exclusiva — ETI sob Qwen full |
| `9` | contribuição exclusiva — MIG sob Qwen full |
| `62` | contribuição exclusiva — PRE sob GPT-5.4 |
| `57` | contribuição exclusiva — ARQ sob GPT-5.4 |
| `44` | contribuição exclusiva — UX sob GPT-5.4 |
| `46` | contribuição exclusiva — SEG sob GPT-5.4 |
| `45` | contribuição exclusiva — CIE sob GPT-5.4 |
| `38` | contribuição exclusiva — PRO sob GPT-5.4 |
| `42` | contribuição exclusiva — LIN sob GPT-5.4 |
| `34` | contribuição exclusiva — GOV sob GPT-5.4 |
| `29` | contribuição exclusiva — DES sob GPT-5.4 |
| `23` | contribuição exclusiva — OBS sob GPT-5.4 |
| `32` | contribuição exclusiva — IMP sob GPT-5.4 |
| `30` | contribuição exclusiva — MEC sob GPT-5.4 |
| `27` | contribuição exclusiva — CTR sob GPT-5.4 |
| `27` | contribuição exclusiva — REG sob GPT-5.4 |
| `24` | contribuição exclusiva — JOG sob GPT-5.4 |
| `28` | contribuição exclusiva — RES sob GPT-5.4 |
| `16` | contribuição exclusiva — SUS sob GPT-5.4 |
| `13` | contribuição exclusiva — ETI sob GPT-5.4 |
| `7` | contribuição exclusiva — MIG sob GPT-5.4 |
| `53` | contribuição exclusiva — PRE sob Union of 4 |
| `47` | contribuição exclusiva — ARQ sob Union of 4 |
| `39` | contribuição exclusiva — UX sob Union of 4 |
| `38` | contribuição exclusiva — SEG sob Union of 4 |
| `37` | contribuição exclusiva — CIE sob Union of 4 |
| `31` | contribuição exclusiva — PRO sob Union of 4 |
| `27` | contribuição exclusiva — LIN sob Union of 4 |
| `25` | contribuição exclusiva — GOV sob Union of 4 |
| `24` | contribuição exclusiva — DES sob Union of 4 |
| `23` | contribuição exclusiva — OBS sob Union of 4 |
| `22` | contribuição exclusiva — IMP sob Union of 4 |
| `22` | contribuição exclusiva — MEC sob Union of 4 |
| `18` | contribuição exclusiva — CTR sob Union of 4 |
| `18` | contribuição exclusiva — REG sob Union of 4 |
| `17` | contribuição exclusiva — JOG sob Union of 4 |
| `16` | contribuição exclusiva — RES sob Union of 4 |
| `13` | contribuição exclusiva — SUS sob Union of 4 |
| `11` | contribuição exclusiva — ETI sob Union of 4 |
| `3` | contribuição exclusiva — MIG sob Union of 4 |

## Estimadores cegos de ativação

*tab:estimators*

```
python3 tools/tabela_numeros.py
```

| valor | o que é |
|---|---|
| `7.5` | Qwen Q4 (local) — lentes ativas por rodada |
| `29` | Qwen Q4 (local) — oscilações |
| `81%` | Qwen Q4 (local) — concordância com a Fase 2 |
| `6.5` | Qwen full — lentes ativas por rodada |
| `26` | Qwen full — oscilações |
| `74%` | Qwen full — concordância com a Fase 2 |
| `8.6` | Kimi K2 — lentes ativas por rodada |
| `17` | Kimi K2 — oscilações |
| `89%` | Kimi K2 — concordância com a Fase 2 |
| `9.7` | GPT-5.4 — lentes ativas por rodada |
| `7` | GPT-5.4 — oscilações |
| `91%` | GPT-5.4 — concordância com a Fase 2 |
| `78%` | concordância entre estimadores — Qwen full × GPT-5.4 |
| `87%` | concordância entre estimadores — Qwen Q4 (local) × GPT-5.4 |
| `88%` | concordância entre estimadores — Qwen full × Kimi K2 |
| `92%` | concordância entre estimadores — Qwen Q4 (local) × Qwen full |
| `93%` | concordância entre estimadores — Qwen Q4 (local) × Kimi K2 |
| `94%` | concordância entre estimadores — Kimi K2 × GPT-5.4 |

## Divergências por lente, com denominador

*tab:divergences*

```
python3 analise/divergencias.py
```

| valor | o que é |
|---|---|
| `7/33 (21%)` | RES — Fase 2 ativou, estimador recusou |
| `0/36 (0%)` | UX — Fase 2 ativou, estimador recusou |
| `0/9 (0%)` | MIG — Fase 2 ativou, estimador recusou |
| `0/26` | MIG — Fase 2 recusou, estimador ativou |
| `11/25 (44%)` | SUS — Fase 2 ativou, estimador recusou |
| `5/13 (38%)` | ETI — Fase 2 ativou, estimador recusou |
| `0/19` | ETI — Fase 2 recusou, estimador ativou |
| `2/34 (6%)` | PRO — Fase 2 ativou, estimador recusou |
| `0/33 (0%)` | GOV — Fase 2 ativou, estimador recusou |
| `6/21 (29%)` | OBS — Fase 2 ativou, estimador recusou |
| `4/11` | OBS — Fase 2 recusou, estimador ativou |
| `8/28 (29%)` | CTR — Fase 2 ativou, estimador recusou |
| `1/2` | CTR — Fase 2 recusou, estimador ativou |
| `2/17 (12%)` | JOG — Fase 2 ativou, estimador recusou |
| `1/12` | JOG — Fase 2 recusou, estimador ativou |
| `4/31 (13%)` | LIN — Fase 2 ativou, estimador recusou |
| `1/27 (4%)` | MEC — Fase 2 ativou, estimador recusou |
| `5/5` | MEC — Fase 2 recusou, estimador ativou |

## Redeclaração entre iterações

*§5.3*

```
python3 analise/redeclaracao.py
```

| valor | o que é |
|---|---|
| `36` | comparações lente a lente entre iterações consecutivas |
| `0` | justificativas idênticas |
| `0.41` | Jaccard no conjunto |
| `0.23` | menor Jaccard médio por projeto |
| `0.59` | maior Jaccard médio por projeto |

## Adjudicação da lente Ética

*§5.5*

```
python3 tools/tabela_numeros.py
```

| valor | o que é |
|---|---|
| `60` | achados cegados julgados |
| `40` | do grupo disputado |
| `20` | do grupo de controle |
| `6` | Claude — SIM entre os 40 disputados (15%) |
| `3` | Claude — SIM entre os 20 de controle (15%) |
| `1.000` | Claude — Fisher bicaudal p |
| `5` | gpt-5.4 — SIM entre os 40 disputados (12%) |
| `0` | gpt-5.4 — SIM entre os 20 de controle (0%) |
| `0.159` | gpt-5.4 — Fisher bicaudal p |
| `4` | consenso — SIM entre os 40 disputados (10%) |
| `0` | consenso — SIM entre os 20 de controle (0%) |
| `0.291` | consenso — Fisher bicaudal p |
| `82%` | concordância bruta entre juízes |
| `0.341` | κ de Cohen entre juízes |

## Critérios de saída

*§5.4*

```
python3 tools/tabela_numeros.py
```

| valor | o que é |
|---|---|
| `468` | registros de critério de saída |
| `801` | caracteres em média por registro |
| `0` | registros vazios |

---

## Registrados, não computados

Fatos operacionais que não vivem no corpus — verificáveis por leitura, não por execução.

| valor | o que é | onde |
|---|---|---|
| `7` | projetos descartados, cada um com motivo | `LOG-OPERACAO.md` |
| `claude-opus-5` | agente gerador nos doze | `LOG-OPERACAO.md` — verificado em 5.328 mensagens |
| `0.14.2` | instrumento, única versão instalada | `instrumento/server.js`, md5 `9dfee8beb881…` |
| `-0.001` | κ que motivou a regra de rotulagem em esparsidade | § desvios — medida **eliminada**; valor histórico, não resultado |

## Citados de terceiros

**Não são medida deste experimento e não têm comando.** `90,3%` e `1.900` são de
Hao et al. (2026); `921`, `5.800` e `63%` de De Santana et al. (2026). Atribuí-los
ao corpus seria o pior erro que esta tabela poderia cometer.
