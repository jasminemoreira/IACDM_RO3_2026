# As chaves privadas deste diretório são sintéticas

Os cinco arquivos `key-*.pem` são **chaves de teste geradas localmente com `openssl`** em
2026-08-09, durante a Fase 6 do T21-certificados. Não protegem nada, não correspondem a
nenhum serviço, e nunca foram usadas fora da suíte de testes deste projeto.

Verificável sem confiar nesta nota:

```bash
openssl x509 -in cert-45d.pem    -noout -subject -issuer -dates
openssl x509 -in cert-ca-30d.pem -noout -subject -issuer -dates
```

Os certificados são **autoassinados**, com nomes obviamente fictícios — `CN=curto.exemplo`,
`CN=CA Intermediaria Curta` — e validade curta a partir de 2026-08-09.

## Por que estão no repositório

O T21 é um monitor de vencimento de certificados TLS. A suíte precisa de certificados
reais em formato real para exercitar os critérios de aceitação: `CA-1` cobre cinco faixas
de vencimento com o relógio fixado, `CA-3` faz um handshake TLS de verdade contra um
servidor local, e `cert-xss.pem` carrega um payload de XSS no campo *subject* para exercitar
`SEC-02`.

Substituir por fixtures falsos descaracterizaria os testes. Removê-los quebraria a suíte —
este projeto não tem script de geração, ao contrário do T23 e do T29.

## Se o secret scanning alertar

O alerta é esperado e correto do ponto de vista da ferramenta: são chaves privadas em
formato PEM. O que a ferramenta não sabe é que não protegem nada. Esta nota existe para
que a verificação seja possível em segundos, por qualquer pessoa, sem depender da palavra
de quem publicou.
