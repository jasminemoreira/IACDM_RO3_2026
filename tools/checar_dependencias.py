#!/usr/bin/env python3
"""Verifica a afirmação do requirements.txt: o pipeline é stdlib puro.

    python3 tools/checar_dependencias.py

Percorre todo módulo em analise/ e tools/, coleta os imports de topo, e reporta qualquer
um que não seja da biblioteca padrão nem local ao repositório. Sai com código 1 se achar.
"""
import ast, pathlib, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
if sys.version_info < (3, 10):
    sys.exit(f"ERRO: requer Python 3.10+; este é {sys.version.split()[0]}")

alvos = sorted(RAIZ.glob("analise/*.py")) + sorted(RAIZ.glob("tools/*.py"))
locais = {p.stem for p in alvos}
std = set(sys.stdlib_module_names)
externos = {}
for f in alvos:
    for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        nomes = ([a.name for a in n.names] if isinstance(n, ast.Import)
                 else [n.module] if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module
                 else [])
        for nome in nomes:
            topo = nome.split(".")[0]
            if topo not in std and topo not in locais:
                externos.setdefault(topo, set()).add(f.name)

print(f"python {sys.version.split()[0]} · {len(alvos)} módulos verificados")
if externos:
    for mod, onde in sorted(externos.items()):
        print(f"  DEPENDÊNCIA EXTERNA: {mod}  ({', '.join(sorted(onde))})")
    sys.exit(1)
print("stdlib puro — nenhuma dependência de terceiros, como o requirements.txt declara")
