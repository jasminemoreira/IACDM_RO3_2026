# Por que este arquivo existe

`EVIDENCIA-corrupcao-terminal-T23.txt` é a saída **crua e não tratada** do
`ollama run qwen3.6:27b --format json` para o pacote cego do T23-canario, em
2026-08-10.

Ela contém três sequências `cursor-left` (`ESC[nD`) seguidas de `erase-line`
(`ESC[K`): o CLI redesenha a linha enquanto escreve, e as sequências entram no
arquivo **mesmo com stdout redirecionado**. O efeito não é cosmético — caracteres
foram **sobrescritos**, e o JSON saiu truncado no meio de um id:

    ["F-24", "F-3<ESC>[4D<ESC>[K
    "F-37", "F-47"]

Falhou alto: o JSON não parseou. Verificação nos demais projetos: T22 e T24 não têm
nenhum `cursor-left`, e o `comparar` valida cada id contra o pacote, então o T21
também está limpo. **Só o T23 foi atingido, e nada foi analisado corrompido.**

Motivou a troca do CLI pela **API do Ollama com schema** (subcomando
`cegar_duplicatas.py julgar`), registrada no `LOG-OPERACAO.md` em 2026-08-10. A razão
de trocar em vez de tratar: depender de duas redes de proteção contra um defeito de
transporte é frágil — bastaria a sobrescrita produzir um id **válido** para a
corrupção passar calada.

Guardado porque é o único artefato que sustenta essa decisão.
