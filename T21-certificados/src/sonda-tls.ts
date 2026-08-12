/**
 * M-08 sonda-tls — adaptador de saida. Unico modulo que conhece rede.
 *
 * Handshake TLS e devolucao da CADEIA COMPLETA servida, em DER.
 *
 * `rejectUnauthorized: false` e deliberado e essencial: um monitor de vencimento
 * precisa inspecionar justamente os certificados invalidos, expirados e
 * autoassinados. Verificado empiricamente na Fase 0.
 *
 * Limitacao declarada (ASS-02, arbitrada pelo operador): exige TLS DIRETO na porta.
 * STARTTLS (SMTP 587, IMAP 143, PostgreSQL 5432) esta fora de escopo, e o alvo
 * declara isso — a limitacao e visivel, nao silenciosa.
 *
 * Parametros com fonte em specs/technical/parameters.md:
 * timeout 10 s (net/http.DefaultTransport do Go); cadeia maxima 10 (defensivo,
 * SEC-06, sem fonte normativa e declarado como tal).
 */

import tls from 'node:tls';
import { ok, erro, type Resultado } from './tipos.ts';

export const TIMEOUT_MS = 10_000;
export const MAX_CADEIA = 10;

export type TipoErroSonda = 'timeout' | 'recusado' | 'dns' | 'tls' | 'cadeia-grande';

/** OBS-03: a mensagem original e preservada — diagnosticar nao pode exigir
 *  alterar o codigo. */
export type ErroSonda = { readonly tipo: TipoErroSonda; readonly detalhe: string };

export type Sonda = {
  sondar(host: string, porta: number): Promise<Resultado<Buffer[], ErroSonda>>;
};

function classificarErro(e: NodeJS.ErrnoException): TipoErroSonda {
  switch (e.code) {
    case 'ENOTFOUND':
    case 'EAI_AGAIN':
      return 'dns';
    case 'ECONNREFUSED':
    case 'EHOSTUNREACH':
    case 'ENETUNREACH':
    case 'ECONNRESET':
      return 'recusado';
    case 'ETIMEDOUT':
      return 'timeout';
    default:
      return 'tls';
  }
}

/** Percorre a cadeia por issuerCertificate ate a raiz (que se auto-referencia). */
function coletarCadeia(socket: tls.TLSSocket): Resultado<Buffer[], ErroSonda> {
  const ders: Buffer[] = [];
  let atual = socket.getPeerCertificate(true) as tls.DetailedPeerCertificate | null;
  const vistos = new Set<string>();

  while (atual && atual.raw) {
    const impressao = atual.fingerprint256 ?? atual.raw.toString('base64');
    if (vistos.has(impressao)) break; // raiz auto-assinada fecha o ciclo
    vistos.add(impressao);
    ders.push(Buffer.from(atual.raw));
    if (ders.length > MAX_CADEIA) {
      return erro({ tipo: 'cadeia-grande', detalhe: `cadeia excede ${MAX_CADEIA} certificados` });
    }
    atual = atual.issuerCertificate ?? null;
  }

  if (ders.length === 0) {
    return erro({ tipo: 'tls', detalhe: 'handshake concluido sem certificado apresentado' });
  }
  return ok(ders);
}

function tentar(host: string, porta: number): Promise<Resultado<Buffer[], ErroSonda>> {
  return new Promise((resolve) => {
    let resolvido = false;
    const encerrar = (r: Resultado<Buffer[], ErroSonda>) => {
      if (resolvido) return;
      resolvido = true;
      socket.destroy();
      resolve(r);
    };

    const socket = tls.connect(
      { host, port: porta, servername: host, rejectUnauthorized: false, timeout: TIMEOUT_MS },
      () => encerrar(coletarCadeia(socket)),
    );

    socket.on('timeout', () =>
      encerrar(erro({ tipo: 'timeout', detalhe: `sem resposta em ${TIMEOUT_MS} ms` })),
    );
    socket.on('error', (e) =>
      encerrar(erro({ tipo: classificarErro(e as NodeJS.ErrnoException), detalhe: e.message })),
    );
  });
}

export function criarSonda(): Sonda {
  return {
    /** PER-05: a retentativa vale SO para `timeout`. `recusado` e `dns` sao
     *  deterministicos — repeti-los apenas dobraria o pior caso da varredura. */
    async sondar(host, porta) {
      const primeira = await tentar(host, porta);
      if (primeira.ok || primeira.erro.tipo !== 'timeout') return primeira;
      return tentar(host, porta);
    },
  };
}
