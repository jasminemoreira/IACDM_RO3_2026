# Pedido de correção — `test-outcome.js`

Contra a **v0.14.2** (bundle instalado em `T21-certificados/.versus/test-outcome.js`).
Motivado pelo achado **M1** do `ACHADOS-METODO.md`: no T21-certificados o gate
`tests_passing` recusou `advance_phase` **cinco vezes** com a suíte em 68/68 verde e
`tsc --noEmit` limpo.

São **dois defeitos independentes**. O primeiro é trivial; o segundo é o que transforma
um marcador faltando em projeto travado, e vale sozinho o pedido.

---

## Defeito 1 — `unknown` não escreve estado, e o veredito anterior fica congelado

`main()`, na altura da linha 1193 do bundle:

```js
const outcome = detectOutcome(output);
if (outcome === "unknown") {
  emit();       // <- sai sem chamar recordTestOutcome
  return;
}
```

E `isPhaseTestPassing()` lê o estado, não a execução:

```js
const t = this.state?.lastTestOutcome;
return !!t && t.outcome === "pass" && t.phase === phase;
```

**A composição é falha fechada e permanente.** Uma vez gravado um `fail`, qualquer
execução posterior cuja saída o `detectOutcome` não classifique deixa o `fail` no lugar.
Não há caminho de recuperação pela ferramenta: rodar os testes de novo, corretamente e em
verde, **não muda nada**. Foi exatamente isto que se observou — `lastTestOutcome=fail`
carimbado às 00:00:34 e nunca reescrito.

O agente não tem como diagnosticar isso de dentro. O que ele vê é `advance_phase`
recusando com a suíte verde, sem nenhuma indicação de que o problema está no hook e não
nos testes. Cinco tentativas depois, a única saída disponível é contornar o gate — que é o
que aconteceu, e foi divulgado.

**Correção pedida:**

1. `unknown` **deve** escrever estado, com o valor `unknown` — distinto de `pass` e de
   `fail`. "Não consegui ler o resultado" não pode continuar parecendo "o resultado
   anterior segue valendo".
2. `isPhaseTestPassing()` recusa `unknown` como recusa `fail` — o gate continua fechado, o
   que está certo —, mas a **mensagem de recusa passa a distinguir os dois casos**. Com
   `unknown`, dizer que a saída da última execução de teste não foi reconhecida, e citar
   o comando. Isso é o que faltou: o agente teria lido a causa em vez de tentar cinco
   vezes.
3. `unknown` **não** conta para o `loopCounter` do S6. Saída ilegível não é teste
   falhando, e somar as duas coisas dispara o bloqueio do S6 por motivo errado.

O `catch { emit() }` no fim de `main()` tem a mesma forma — JSON de entrada malformado
some sem deixar rastro. Vale ao menos escrever `unknown` ali também.

---

## Defeito 2 — os marcadores não cobrem o repórter padrão do `node:test`

O repórter `spec` do Node imprime o resumo assim:

```
ℹ tests 68
ℹ pass 68
ℹ fail 0
```

Nenhum dos conjuntos casa, e vale conferir um a um porque a razão é sempre a mesma —
**ordem das palavras**:

| conjunto | padrão relevante | por que não casa |
|---|---|---|
| `CLEAN_MARKERS[0]` | `\b0\s+(tests?\s+)?fail(ed\|ures?\|ing)?\b` | espera `0 fail`; a saída traz `fail 0` |
| `CLEAN_MARKERS[1]` | `fail(ed\|ures?)\s*[:=]\s*0` | exige sufixo (`failed`/`failures`) e separador `:`/`=`; a saída não tem nenhum dos dois |
| `PASS_MARKERS[0]` | `\d+\s+(tests?\s+)?pass(ed\|ing)\b` | espera `68 passed`; a saída traz `pass 68` |
| `PASS_MARKERS[2]` | `\d+\s+passed\b` | idem |

Resultado: `detectOutcome` devolve `unknown`, e cai no defeito 1.

**Correção pedida:** dois padrões, na forma `palavra número`:

```js
// node:test spec reporter — "pass 68" / "fail 0"
/^\s*(?:ℹ\s*)?fail\s+0\b/im,      // -> CLEAN_MARKERS
/^\s*(?:ℹ\s*)?pass\s+[1-9]\d*\b/im, // -> PASS_MARKERS
```

Ancorados em início de linha e com o `ℹ` opcional, para não casarem por acidente com
prosa que contenha "fail 0" no meio de uma frase. O mesmo formato aparece na cauda do
repórter TAP (`# pass 68`, `# fail 0`), então cobrir os dois de uma vez pede tolerar
`#` além de `ℹ`.

---

## Observação sobre o item (d) do registro

O agente reportou que, **mesmo após trocar para `--test-reporter=tap`** — cuja saída casa
`CLEAN_MARKERS[4]` (`/^ok\s|^PASS\b/im`) e nenhum `FAIL_MARKER` —, o hook continuou não
registrando. A hipótese registrada é que o `PostToolUse` não estava entregando o
`tool_response` do Bash ao hook naquela sessão.

**Não consigo confirmar isso pelo bundle**, e pode ser condição da sessão e não defeito do
código. Registro como observação, não como pedido. Se for reproduzível, é mais sério que
os dois acima, porque nenhuma correção de marcador ajuda. Um jeito barato de instrumentar:
com `unknown` passando a escrever estado (defeito 1), guardar junto o tamanho da saída
recebida — `0` distingue "não entregaram nada ao hook" de "entregaram e não reconheci".

---

## Efeito sobre o lote

**Nenhum descarte.** O gate atrasou a Fase 6; a matriz de cobertura, que é o que a RO3
mede, fecha na Fase 4. Nenhuma variável medida foi afetada, e o contorno está registrado
no `RETRABALHO.md` do projeto.

A correção pode entrar a qualquer momento sem quebrar homogeneidade do instrumento, pelo
mesmo motivo: ela não toca em nada que a RO3 mede. É o primeiro item do lote de que isso é
verdade — vale decidir explicitamente se entra já ou espera o fim, e registrar a escolha
no `LOG-OPERACAO.md` de qualquer forma.
