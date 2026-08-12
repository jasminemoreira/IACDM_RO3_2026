/**
 * Convenção única de contrato do núcleo (V(3)/R7, mantida em V(4)).
 *
 * Todo o núcleo (M-01..M-08) RETORNA `Resultado<T, E>` e NUNCA lança. Exceção existe
 * apenas na borda de infraestrutura. Nasceu do achado LING-01: `resolver(...) -> X | Erro`
 * não dizia se o erro era lançado ou retornado, e duas implementações corretas do mesmo
 * contrato seriam incompatíveis com o mesmo consumidor.
 */
export type Resultado<T, E> = { ok: true; valor: T } | { ok: false; erro: E };

export const ok = <T>(valor: T): Resultado<T, never> => ({ ok: true, valor });
export const falha = <E>(erro: E): Resultado<never, E> => ({ ok: false, erro });

/** Erro de domínio: `codigo` para o teste, `mensagem` para a pessoa (achado UX-02). */
export type ErroDominio = { codigo: string; mensagem: string };

export const erro = (codigo: string, mensagem: string): ErroDominio => ({ codigo, mensagem });

/**
 * Instante é `string` ISO-8601 UTC — um tipo só, sem conversão (achado LING-04).
 * Nenhum módulo de domínio chama `Date.now()`: o tempo entra pela porta `Clock` (M-07).
 */
export type Instante = string;
