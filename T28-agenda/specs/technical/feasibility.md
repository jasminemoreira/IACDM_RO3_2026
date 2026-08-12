# Verificação de viabilidade técnica (HSA Nível 4)

> Regra da metodologia: viabilidade da plataforma é **verificada, não assumida**.
> Executado em 2026-08-11 na máquina alvo.

## Ambiente verificado empiricamente

| Capacidade | Necessária para | Verificação executada | Resultado |
|---|---|---|---|
| Python | runtime | `python3 --version` | **3.12.1** ✅ |
| `sqlite3` (stdlib) | persistência transacional do ancestral e da fila de conflitos | `import sqlite3` | ✅ **3.41.2** |
| `zoneinfo` (stdlib) + base tz | fusos IANA, DST correto | `ZoneInfo('America/Sao_Paulo')` | ✅ resolve |
| `python-dateutil` | expansão de RRULE (REF-9) — Tier 1, evita expansor próprio | `import dateutil` | ✅ **2.9.0.post0** |
| `icalendar` | parse/serialize RFC 5545 | não vinha instalado → `pip install icalendar` | ✅ **7.2.2** instalado |
| `pytest` | verificação automatizada (Fase 6) | `import pytest` | ✅ **9.0.2** |
| Instalação de pacotes | dependências | `pip3 install icalendar` | ✅ funciona (rede disponível) |

## Capacidades ESSENCIAIS vs DESEJÁVEIS

| Capacidade | Classe | Ausente? |
|---|---|---|
| Expansão de RRULE conforme RFC 5545 | **ESSENCIAL** (escopo temporal completo) | não — `dateutil.rrule` |
| Aritmética de fuso com DST | **ESSENCIAL** | não — `zoneinfo` |
| Persistência transacional (ancestral + eco na mesma transação) | **ESSENCIAL** | não — `sqlite3` |
| Parse/serialize iCalendar | **ESSENCIAL** se as fixtures forem `.ics` | não — `icalendar` |
| Execução determinística de teste (sem rede/OAuth) | **ESSENCIAL** | não — provedores simulados |
| Rede / OAuth2 | DESEJÁVEL (ciclo futuro, adaptador real) | irrelevante neste ciclo |

**Conclusão: nenhuma capacidade essencial ausente. Sem BLOCKER técnico.**

## Risco residual declarado (não é blocker, é orçamento)

O escopo temporal completo (recorrência + exceções + fusos + all-day) somado a
sync bidirecional com merge por campo e fila de conflitos é o fator de pressão
sobre a janela de 2-4h do enunciado. Não há impedimento técnico — há risco de
prazo. Mitigação: a expansão de recorrência e a aritmética de fuso são 100% Tier 1
(biblioteca madura), então o código próprio se concentra na reconciliação, que é
onde o valor do projeto está.
