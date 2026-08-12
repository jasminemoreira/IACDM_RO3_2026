/**
 * Convencao canonica de resultado — V(3), resolve LIN-02.
 *
 * Erro de dominio e VALOR DE RETORNO, nunca excecao. Excecao fica reservada a
 * falha programatica (bug). Onze modulos implementam este contrato de forma
 * independente; sem forma canonica declarada eles nao compoem.
 */

export type Ok<T> = { readonly ok: true; readonly valor: T };
export type Erro<E> = { readonly ok: false; readonly erro: E };
export type Resultado<T, E> = Ok<T> | Erro<E>;

export const ok = <T>(valor: T): Ok<T> => ({ ok: true, valor });
export const erro = <E>(e: E): Erro<E> => ({ ok: false, erro: e });

/** Token de transacao — repositorio (V(3), SEC-11).
 *  As portas de escrita exigem este token como parametro, o que torna escrever
 *  fora de `emTransacao` impossivel pelo tipo, e nao apenas proibido por convencao. */
export type Transacao = { readonly __transacao: unique symbol };
