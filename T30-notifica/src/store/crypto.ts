/**
 * M-12 store — cifra de segredos em repouso.
 *
 * Achado SEC-04: `webhook_secret` precisa ser LEGÍVEL para assinar (ao contrário
 * de uma senha, que só precisa ser comparável), logo hash não serve. Cifra com
 * chave de ambiente.
 *
 * Achado SEC-09: ciphertext VERSIONADO e leitura pela chave anterior durante a
 * rotação — sem isso, trocar a chave torna todos os segredos ilegíveis sem
 * caminho de migração.
 *
 * Formato: v1:<nonce b64>:<ciphertext b64>:<tag b64>
 */
import { createCipheriv, createDecipheriv, randomBytes, scryptSync } from 'node:crypto';

const VERSION = 'v1';
const ALGO = 'aes-256-gcm';
const NONCE_BYTES = 12;

function deriveKey(passphrase: string): Buffer {
  // Sal fixo: a chave vem do ambiente e é única por instalação; o sal aqui só
  // estica a passphrase para 32 bytes, não protege contra dicionário — quem
  // tem o ambiente já tem a chave.
  return scryptSync(passphrase, 't30-secret-key-v1', 32);
}

export interface SecretBox {
  encrypt(plaintext: string): string;
  decrypt(stored: string): string;
}

export function createSecretBox(current: string, previous?: string): SecretBox {
  const currentKey = deriveKey(current);
  const previousKey = previous ? deriveKey(previous) : null;

  function tryDecrypt(key: Buffer, nonce: Buffer, ct: Buffer, tag: Buffer): string {
    const decipher = createDecipheriv(ALGO, key, nonce);
    decipher.setAuthTag(tag);
    return decipher.update(ct, undefined, 'utf8') + decipher.final('utf8');
  }

  return {
    encrypt(plaintext) {
      const nonce = randomBytes(NONCE_BYTES);
      const cipher = createCipheriv(ALGO, currentKey, nonce);
      const ct = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
      const tag = cipher.getAuthTag();
      return [VERSION, nonce.toString('base64'), ct.toString('base64'), tag.toString('base64')].join(':');
    },

    decrypt(stored) {
      const [version, nonceB64, ctB64, tagB64] = stored.split(':');
      if (version !== VERSION) throw new Error(`versão de ciphertext desconhecida: ${version}`);
      const nonce = Buffer.from(nonceB64, 'base64');
      const ct = Buffer.from(ctB64, 'base64');
      const tag = Buffer.from(tagB64, 'base64');
      try {
        return tryDecrypt(currentKey, nonce, ct, tag);
      } catch (err) {
        // Rotação em andamento: o segredo ainda está cifrado com a chave anterior.
        if (previousKey) return tryDecrypt(previousKey, nonce, ct, tag);
        throw err;
      }
    },
  };
}
