#!/usr/bin/env python3
"""Extrae el esquema REAL de los DBF del backup, por módulo.
Salida: catalogo_real.json + catalogo_real.md
"""
import os
import sys
import json
import glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                "..", "capresca-nuevo", "backend"))
from app.etl.dbf import DbfReader  # noqa: E402

BASES = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "salida"
# Juegos tiene 1247 tablas (per-sorteo/agencia): sólo muestreo las maestras.
LIMIT_JUEGOS = 40

catalogo = {}
for modulo in sorted(os.listdir(BASES)):
    mdir = os.path.join(BASES, modulo)
    if not os.path.isdir(mdir):
        continue
    dbfs = sorted(glob.glob(os.path.join(mdir, "*.dbf")) +
                  glob.glob(os.path.join(mdir, "*.DBF")))
    if modulo.lower() == "juegos":
        dbfs = dbfs[:LIMIT_JUEGOS]
    tablas = {}
    for path in dbfs:
        nombre = os.path.basename(path)
        base = os.path.splitext(nombre)[0].lower()
        try:
            r = DbfReader(path)
            tablas[base] = {
                "registros": r.record_count,
                "campos": [{"n": f.name.lower(), "t": f.type,
                            "len": f.length, "dec": f.decimals} for f in r.fields],
            }
            r._f.close()
        except Exception as e:
            tablas[base] = {"error": str(e)[:80]}
    catalogo[modulo] = tablas

json.dump(catalogo, open(os.path.join(OUT, "catalogo_real.json"), "w"),
          ensure_ascii=False, indent=1)

# Markdown
L = ["# Catálogo de datos REAL — backup CCyPP\n",
     "> Esquema extraído de los DBF reales del backup (por módulo).\n"]
tot_tab = tot_reg = 0
for modulo, tablas in catalogo.items():
    reg = sum(t.get("registros", 0) for t in tablas.values())
    tot_tab += len(tablas)
    tot_reg += reg
    L.append(f"\n## {modulo} — {len(tablas)} tablas · {reg:,} registros\n")
    for base, info in sorted(tablas.items(), key=lambda x: -x[1].get("registros", 0)):
        if "error" in info:
            L.append(f"- `{base}` — ERROR: {info['error']}")
            continue
        campos = ", ".join(f"{c['n']}" for c in info["campos"][:22])
        L.append(f"- **`{base}`** ({info['registros']:,} reg, {len(info['campos'])} campos): {campos}")

L.insert(2, f"\n**Totales analizados:** {tot_tab} tablas · {tot_reg:,} registros.\n")
open(os.path.join(OUT, "catalogo_real.md"), "w").write("\n".join(L) + "\n")
print(f"OK  módulos={len(catalogo)}  tablas={tot_tab}  registros={tot_reg:,}")
for m, t in catalogo.items():
    reg = sum(x.get("registros", 0) for x in t.values())
    print(f"  {m:16s} {len(t):4d} tablas · {reg:,} reg")
