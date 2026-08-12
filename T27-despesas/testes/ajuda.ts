/**
 * Montagem de ambiente para os testes. O banco é `:memory:`, o relógio é o controlável, e o
 * seed pode ser trocado por variantes — os cenários D-20 e D-21 (nível pulado, nenhum
 * decisor) exigem uma empresa sem gerentes / só com coordenadores, e specs/datasets manda
 * montá-la em memória sem tocar no seed principal.
 */
import { abrir, SEED_PAPEIS, SEED_USUARIOS, type Adaptador } from "../src/adaptadores/sqlite.js";
import { validar, type MatrizValida, type Papel } from "../src/dominio/matriz-doa.js";
import { relogioControlavel } from "../src/dominio/relogio.js";
import type { Usuario } from "../src/dominio/portas.js";
import type { Ambiente } from "../src/app/casos-de-uso.js";

export const T0 = "2026-08-11T09:00:00.000Z";

export type Bancada = {
  amb: Ambiente;
  relogio: ReturnType<typeof relogioControlavel>;
  repos: Adaptador;
  matriz: MatrizValida;
};

export function montar(opcoes?: {
  papeis?: readonly Papel[];
  usuarios?: readonly Usuario[];
  inicio?: string;
}): Bancada {
  const repos = abrir(":memory:");
  repos.semear(opcoes?.papeis ?? SEED_PAPEIS, opcoes?.usuarios ?? SEED_USUARIOS);

  const v = validar(repos.papeis.todos(), repos.usuarios.todos());
  if (!v.ok) throw new Error(`seed de teste inválido: ${v.erro.mensagem}`);

  const relogio = relogioControlavel(opcoes?.inicio ?? T0);
  let n = 0;
  const amb: Ambiente = {
    repos,
    matriz: v.valor,
    relogio,
    novoId: () => `id-${++n}`,
  };
  return { amb, relogio, repos, matriz: v.valor };
}

/** Empresa sem nenhum Gerente — exercita CA-1b (nível intermediário pulado). */
export const USUARIOS_SEM_GERENTE: readonly Usuario[] = SEED_USUARIOS.filter(
  (u) => u.papelId !== "gerente",
);

/** Empresa só de Coordenadores — exercita CA-1c (nenhum nível com decisor). */
export const USUARIOS_SO_COORDENADORES: readonly Usuario[] = SEED_USUARIOS.filter(
  (u) => u.papelId === "coordenador",
);

export const dias = (n: number) => n * 86_400_000;

export function precisa<T, E>(r: { ok: true; valor: T } | { ok: false; erro: E }): T {
  if (!r.ok) throw new Error(`esperava sucesso, veio erro: ${JSON.stringify(r.erro)}`);
  return r.valor;
}

export function erroDe<T, E>(r: { ok: true; valor: T } | { ok: false; erro: E }): E {
  if (r.ok) throw new Error(`esperava erro, veio sucesso: ${JSON.stringify(r.valor)}`);
  return r.erro;
}
