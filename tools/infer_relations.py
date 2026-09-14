#!/usr/bin/env python3
"""
Infiere relaciones (claves foráneas candidatas) entre las tablas del catálogo
CCyPP, cruzando campos-clave compartidos. Genera:

  - relaciones.md         (lista de relaciones candidatas)
  - modelo_er.mmd         (diagrama ER en Mermaid, núcleo del modelo)

Heurística: un campo es "clave" si su nombre matchea patrones de identificador
(no_*, cod_*, cid*, id_*, cuil, dni, linea, norgano, corga, ...) y aparece en
>1 tabla. La tabla "dueña" del identificador se deduce por convención
(p.ej. `solicitud` posee `no_solicitud`).
"""
import re
import json
import sys
from collections import defaultdict

CAT = sys.argv[1] if len(sys.argv) > 1 else "salida/catalogo_datos.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "salida"

data = json.load(open(CAT, encoding="utf-8"))
tablas = data["tablas"]

# Patrones de campos que actúan como identificadores / claves de relación.
KEY_RE = re.compile(
    r"^(no_[a-z]+|cod_[a-z]+|cid[a-z]*|id_[a-z]+|ccuil|cuil|dni|edni|ndoc|"
    r"linea|no_agencia|no_subagencia|norgano|corga|cidcliente|ga_idcli|"
    r"no_credito|no_solicitud|no_liquida|no_recibo|no_op|no_resol|no_sorteo|"
    r"cod_agencia|cod_juego)$"
)

# Campo-clave -> tabla dueña preferida (dominio de esa entidad).
OWNER = {
    "no_solicitud": "solicitud",
    "no_credito": "crcliact",
    "no_liquida": "cajaliq",
    "no_recibo": "cajapagos",
    "no_op": "egresos",
    "no_resol": "resoluciones",
    "linea": "lineacred",
    "cidcliente": "maeclientes",
    "ga_idcli": "maeclientes",
    "ccuil": "maeclientes",
    "cuil": "maeclientes",
    "norgano": "organismos",
    "corga": "organismos",
    "no_agencia": "maeagencias",
    "cod_agencia": "maeagencias",
    "cod_juego": "maejuegos",
}

# índice campo -> {tablas que lo tienen}
field_tables = defaultdict(set)
table_fields = {}
for tbl, info in tablas.items():
    fs = {c["campo"] for c in info["campos"]}
    table_fields[tbl] = fs
    for f in fs:
        field_tables[f].add(tbl)

# Construir relaciones candidatas
relations = []          # (tabla_origen, campo, tabla_destino)
for field, owners in field_tables.items():
    if not KEY_RE.match(field):
        continue
    if len(owners) < 2 and field not in OWNER:
        continue
    dest = OWNER.get(field)
    if dest and dest in tablas:
        for t in owners:
            if t != dest:
                relations.append((t, field, dest))
    else:
        # sin dueño canónico: relacionar todas entre sí de forma informativa
        owners_l = sorted(owners)
        base = owners_l[0]
        for t in owners_l[1:]:
            relations.append((t, field, base))

# dedup
relations = sorted(set(relations))

# --- Markdown ---
md = ["# Relaciones inferidas entre tablas — CCyPP\n",
      "> Claves foráneas **candidatas**, deducidas por nombres de campo compartidos.\n",
      "> Confirmar cardinalidad e integridad contra los DBC reales.\n",
      f"\nTotal de relaciones candidatas: **{len(relations)}**\n"]

by_dest = defaultdict(list)
for src, fld, dst in relations:
    by_dest[dst].append((src, fld))

for dst in sorted(by_dest):
    md.append(f"\n### `{dst}`  ← referenciada por:")
    for src, fld in sorted(by_dest[dst]):
        md.append(f"- `{src}`.`{fld}`  →  `{dst}`")

open(f"{OUT}/relaciones.md", "w", encoding="utf-8").write("\n".join(md) + "\n")

# --- Mermaid ER (solo núcleo: tablas con DBC y con campos) ---
core = [t for t, i in tablas.items()
        if i["dbc"] and len(i["campos"]) >= 5]
core_set = set(core)

mer = ["erDiagram"]
# entidades con algunos campos representativos
for t in core:
    fields = tablas[t]["campos"][:14]
    mer.append(f"    {t} {{")
    for c in fields:
        typ = {"c": "string", "n": "number", "l": "bool", "d": "date",
               "f": "datetime", "t": "datetime", "i": "int", "y": "money",
               "e": "int", "m": "text", "b": "float", "g": "blob"}.get(
            c["campo"][0], "string")
        mer.append(f"        {typ} {c['campo']}")
    mer.append("    }")

seen = set()
for src, fld, dst in relations:
    if src in core_set and dst in core_set and src != dst:
        key = (src, dst)
        if key in seen:
            continue
        seen.add(key)
        mer.append(f'    {dst} ||--o{{ {src} : "{fld}"')

open(f"{OUT}/modelo_er.mmd", "w", encoding="utf-8").write("\n".join(mer) + "\n")

print(f"Relaciones candidatas: {len(relations)}")
print(f"Entidades núcleo en ER: {len(core)}")
print(f"OK -> {OUT}/relaciones.md , {OUT}/modelo_er.mmd")
