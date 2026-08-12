# Estado da arte — ferramentas de gestão de ciclo de vida de certificados (CLM)

Fase 0, HSA Nível 1. Coleta em 2026-08-09.

## Panorama

| Produto | Natureza | O que cobre | Aprovação humana da emissão |
|---|---|---|---|
| Venafi / CyberArk Certificate Manager | comercial, enterprise | descoberta, inventário, automação de ciclo de vida em escala; definiu a categoria "machine identity" | sim, com políticas e workflow |
| Keyfactor (+ EJBCA) | comercial + CA open source | CLM e a própria CA no mesmo fornecedor | sim |
| DigiCert / Sectigo / Entrust / AppViewX | comerciais, ligados a CAs públicas | emissão e gestão dentro do ecossistema da CA | sim |
| cert-manager | open source | automação de certificados **dentro de Kubernetes** | não — automação total, sem gate humano |
| Smallstep (step-ca) | open source | CA + emissão/renovação automatizada, mTLS, certificados de vida curta | não é o foco |
| certbot e clientes ACME | open source | renovação automática de um host | não |

Fontes:
- https://infisical.com/blog/best-certificate-management-tools
- https://guptadeepak.com/tools/top-5-pki-certificate-lifecycle-management-tools-2026/
- https://axelspire.com/business/building-pki-clm-comparison/
- https://monofor.com/compare/best-certificate-lifecycle-management

## Leitura para este projeto

1. **O eixo automação↔governança é onde os produtos se dividem.** As ferramentas
   open source (cert-manager, certbot, step-ca) otimizam para *remover* o humano do
   caminho: renovação totalmente automática. As comerciais caras reintroduzem o
   humano via política e workflow. Este projeto pede explicitamente
   "registro de quem aprovou cada emissão" — ou seja, fica do lado da **governança**,
   que é justamente o lado sem opção open source óbvia.

2. **Consequência para o S6 (Tier 1/2/3) da Fase 5:** parsing de X.509 e checagem de
   validade são Tier 1 (biblioteca madura, nunca implementar à mão). O *workflow de
   aprovação com trilha auditável* não tem lib de prateleira — é o Tier 3 legítimo do
   projeto e é onde o esforço de design deve se concentrar.

3. **Gap identificado:** nenhuma ferramenta gratuita do levantamento acopla
   "monitorar vencimento" + "exigir aprovação nomeada antes de emitir" +
   "trilha imutável de quem aprovou". Essa é a razão de existir deste produto —
   e é o que deve aparecer nos critérios de aceitação, não a parte de monitoramento
   (que é commodity).
