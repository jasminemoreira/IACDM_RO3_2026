/**
 * Processo filho do teste AC-4 (durabilidade).
 *
 * Faz exatamente o que um worker de produção faz — reivindica uma entrega — e
 * então trava, para que o teste possa matá-lo com `kill -9` no pior momento
 * possível: depois de tomar a entrega e antes de registrar qualquer resultado.
 *
 * Fica fora de test/ de propósito: não é um teste, é o cúmplice de um.
 */
import { createApp } from '../src/app.ts';

const [dbPath, smtpPort, hookPort] = process.argv.slice(2);

const app = createApp({
  dbPath,
  smtpHost: '127.0.0.1',
  smtpPort: Number(smtpPort),
  allowPrivateWebhooks: true,
});

const claimed = app.outbox.claim(app.store.now());
process.stdout.write(`CLAIMED ${claimed.length}\n`);

// Fica vivo até levar SIGKILL — sem finally, sem cleanup, sem chance de gravar
// resultado. É o cenário que AC-4 exige provar.
//
// Com `await new Promise(() => {})` o Node detectaria "unsettled top-level await"
// e encerraria o processo com código 13 por conta própria: o filho morreria
// sozinho e o teste nunca chegaria a matá-lo. Um intervalo mantém o event loop
// ocupado de verdade.
setInterval(() => {}, 1000);
