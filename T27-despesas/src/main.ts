/**
 * Ponto de entrada. Sobe com um comando (`npm start`), sem infra externa.
 *
 * V(2)/R1 + V(4)/T5: a matriz é validada UMA vez na carga e o processo NÃO sobe se falhar
 * (INV-14). V(3)/S3: o relógio é o real deslocado por `T27_RELOGIO_OFFSET_MS`, lido aqui;
 * offset mal formado também impede a subida (achado RES-04).
 */
import { randomUUID } from "node:crypto";
import { abrir } from "./adaptadores/sqlite.js";
import { validar } from "./dominio/matriz-doa.js";
import { lerOffsetDoAmbiente, relogioReal } from "./dominio/relogio.js";
import { criarServidor } from "./api/http.js";
import type { Ambiente } from "./app/casos-de-uso.js";

const CAMINHO_BANCO = process.env["T27_BANCO"] ?? "t27.db";
const PORTA = Number(process.env["PORT"] ?? 3000);

async function principal() {
  const offset = lerOffsetDoAmbiente(process.env["T27_RELOGIO_OFFSET_MS"]);
  const repos = abrir(CAMINHO_BANCO);
  const semeou = repos.semear();

  const validacao = validar(repos.papeis.todos(), repos.usuarios.todos());
  if (!validacao.ok) {
    console.error(`[T27] Matriz DoA inválida (${validacao.erro.codigo}): ${validacao.erro.mensagem}`);
    console.error("[T27] O processo não sobe com matriz inválida — INV-14.");
    process.exit(1);
  }

  const amb: Ambiente = {
    repos,
    matriz: validacao.valor,
    relogio: relogioReal(offset),
    novoId: () => randomUUID(),
  };

  const app = criarServidor(amb);
  await app.listen({ port: PORTA, host: "127.0.0.1" });

  console.log(`[T27] banco: ${CAMINHO_BANCO}${semeou ? " (semeado agora)" : ""}`);
  console.log(`[T27] offset de relógio: ${offset} ms — agora() = ${amb.relogio.agora()}`);
  console.log(`[T27] http://127.0.0.1:${PORTA}`);
}

principal().catch((e) => {
  console.error(`[T27] falha na inicialização: ${e instanceof Error ? e.message : String(e)}`);
  process.exit(1);
});
