# Referências de implementação (S6 Tier 1/2) — consultar ANTES de codar cada módulo

O objetivo é evitar AP7 (codar sem referência). Nada aqui é inventado: são os padrões de
uso documentados das libs aprovadas na Fase 1.

## Transação leitura-para-atualização (M-09, better-sqlite3)

better-sqlite3 é **síncrono**, o que torna a transação trivial de raciocinar em Node
mono-thread: nada intercala entre as instruções de dentro do bloco.

```ts
const decidir = db.transaction((cmd) => {
  const despesa = lerDespesa.get(cmd.despesaId);        // leitura DENTRO da transação
  if (despesa.estado !== 'PENDENTE') throw new ErroConflito(despesa.estado);
  if (despesa.nivel_corrente !== cmd.nivelEsperado) throw new ErroConflito('nivel');
  gravarDecisao.run(...);                                // INSERT na trilha
  atualizarDespesa.run(...);                             // UPDATE do estado
});
```

Pontos que a Fase 2 vai cobrar:
- A leitura precisa estar **dentro** do bloco; ler antes e decidir depois reabre a janela
  de corrida que a transação existia para fechar.
- `nivelEsperado` vem do cliente e é conferido contra o banco: é o que transforma "dois
  aprovadores no mesmo item" em erro determinístico em vez de dupla aprovação.
- Docs: <https://github.com/WiseLibs/better-sqlite3/blob/master/docs/api.md#transactionfunction---function>

## Relógio como porta (M-07)

```ts
export interface Clock { agora(): string /* ISO-8601 UTC */ }
export const relogioReal: Clock = { agora: () => new Date().toISOString() };
export function relogioControlavel(inicial: string) {
  let t = Date.parse(inicial);
  return { agora: () => new Date(t).toISOString(), avancar: (ms: number) => { t += ms; } };
}
```

Nenhum módulo de domínio chama `Date.now()` diretamente — é o que torna CA-5 (expiração)
testável de forma determinística.

## Fastify: rota + tratamento de erro de domínio (M-11)

Erro de domínio nomeado → status HTTP, em um único ponto, para que as 4 mensagens do CA-6
cheguem intactas ao usuário:

```ts
app.setErrorHandler((err, _req, reply) => {
  if (err instanceof ErroSoD)      return reply.code(409).send({ codigo: err.codigo, mensagem: err.mensagem });
  if (err instanceof ErroValidacao) return reply.code(400).send({ codigo: err.codigo, mensagem: err.mensagem });
  if (err instanceof ErroConflito)  return reply.code(409).send({ codigo: 'CONFLITO', mensagem: err.mensagem });
  reply.code(500).send({ codigo: 'INTERNO' });
});
```

Docs: <https://fastify.dev/docs/latest/Reference/Errors/>

## UI server-rendered sem build (M-12)

Páginas montadas por template de string e servidas com `reply.type('text/html')`;
formulários HTML nativos com `method="POST"`. Sem framework de front, sem bundler — o que
sustenta a estimativa de LOC da Fase 0 e o argumento contra a opção SPA.

## Aritmética monetária (M-01)

Valores sempre em **inteiro de centavos**. Entrada da UI em reais é convertida uma única
vez na borda (M-11), por parsing de string, nunca por `parseFloat(x) * 100` — que produz
erro de arredondamento em valores como `19.99`. Comparação de alçada é comparação de
inteiros (INV-12, CA-2).
