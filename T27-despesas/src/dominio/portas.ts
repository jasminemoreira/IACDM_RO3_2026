/**
 * M-08 portas-repositorio — contratos de persistência por agregado + contrato de transação.
 *
 * V(2)/R7: `pendentesDe(nivel)` foi substituído por `pendentes()` — o parâmetro era ambíguo
 * entre "no nível k" e "até k" e não recebia usuário, logo não servia à bandeja, seu único
 * consumidor (achado LING-03). Sob A7 (~1.000 despesas) a filtragem é em memória.
 * V(2)/R5: toda implementação DEVE usar prepared statements (achado SEC-05).
 */
import type { Despesa } from "./despesa.js";
import type { Delegacao } from "./delegacao.js";
import type { Evento } from "./trilha.js";
import type { Papel } from "./matriz-doa.js";
import type { Instante } from "./resultado.js";

export type Usuario = {
  readonly id: string;
  readonly nome: string;
  readonly papelId: string;
};

export interface DespesaRepo {
  salvar(despesa: Despesa): void;
  porId(id: string): Despesa | undefined;
  pendentes(): readonly Despesa[];
  todas(): readonly Despesa[];
}

export interface DelegacaoRepo {
  salvar(delegacao: Delegacao): void;
  porId(id: string): Delegacao | undefined;
  todas(): readonly Delegacao[];
  porDelegante(deleganteId: string): readonly Delegacao[];
}

export interface UsuarioRepo {
  porId(id: string): Usuario | undefined;
  todos(): readonly Usuario[];
}

export interface PapelRepo {
  todos(): readonly Papel[];
}

/** Só `anexar` e `porDespesa`: não existe caminho de UPDATE/DELETE (INV-8). */
export interface TrilhaRepo {
  anexar(evento: Evento): void;
  porDespesa(despesaId: string): readonly Evento[];
}

export interface Repositorios {
  readonly despesas: DespesaRepo;
  readonly delegacoes: DelegacaoRepo;
  readonly usuarios: UsuarioRepo;
  readonly papeis: PapelRepo;
  readonly trilha: TrilhaRepo;
  /**
   * Transação leitura-para-atualização. A decisão inteira (ler estado, checar invariantes,
   * gravar decisão + trilha + novo estado) roda aqui dentro; uma exceção reverte tudo.
   */
  emTransacao<T>(fn: () => T): T;
  fechar(): void;
}

export type { Instante };
