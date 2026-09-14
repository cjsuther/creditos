#!/usr/bin/env python3
"""Inventario funcional: extrae de cada .scx (form VFP) su título de ventana y
sus botones de acción, dereferenciando el memo .SCT (formato FPT).

Salida: inventario_funcional.md + inventario_funcional.json
"""
import os
import re
import sys
import json
import struct
import glob
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                "..", "capresca-nuevo", "backend"))
from app.etl.dbf import DbfReader  # noqa: E402

ROOT = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "."

# Familias de prefijo numérico -> módulo (inferido; el título confirma).
MODULO = {
    "000": "Sistema/Login", "001": "Sistema/Login", "010": "Sistema/Login",
    "105": "Despacho/Resoluciones", "120": "Despacho/Resoluciones",
    "130": "Despacho/Resoluciones",
    "220": "Caja", "225": "Caja", "230": "Caja (listados)",
    "305": "Créditos", "310": "Créditos", "315": "Créditos", "320": "Créditos",
    "321": "Créditos", "325": "Créditos", "330": "Créditos", "331": "Créditos",
    "335": "Créditos",
    "405": "Juegos/Quiniela", "410": "Juegos/Quiniela",
    "415": "Juegos/Quiniela", "420": "Juegos/Quiniela",
    "425": "Juegos/Quiniela", "430": "Juegos/Quiniela",
    "515": "Despacho/Notas", "520": "Despacho/Notas", "530": "Despacho/Notas",
    "605": "Mesa/Trámites", "625": "Mesa/Trámites",
    "705": "Seguros", "715": "Seguros", "720": "Seguros", "725": "Seguros",
    "730": "Seguros",
    "805": "Tesorería/Egresos", "815": "Tesorería/Egresos",
    "820": "Tesorería/Egresos", "825": "Tesorería/Egresos",
    "830": "Tesorería/Egresos", "835": "Tesorería/Egresos",
    "905": "Utilidades/Tablas", "910": "Utilidades/Tablas",
    "915": "Utilidades/Tablas", "920": "Utilidades/Tablas",
    "925": "Utilidades/Tablas", "930": "Utilidades/Tablas",
    "cb": "Contabilidad",
}


def fpt_reader(sct_path):
    """Devuelve función deref(block_no)->texto para un memo FPT (.SCT)."""
    data = open(sct_path, "rb").read()
    block_size = struct.unpack(">H", data[6:8])[0] or 64

    def deref(block_no):
        if not block_no:
            return ""
        off = block_no * block_size
        if off + 8 > len(data):
            return ""
        length = struct.unpack(">I", data[off + 4:off + 8])[0]
        return data[off + 8:off + 8 + length].decode("latin-1", "ignore")
    return deref


def block_no(raw):
    if isinstance(raw, bytes) and len(raw) == 4:
        return struct.unpack("<I", raw)[0]
    return 0


def caption_de(props):
    m = re.search(r'Caption\s*=\s*"([^"]{1,60})"', props, re.I)
    return m.group(1).strip() if m else ""


def analizar_form(scx):
    base = scx[:-1]
    sct = base + "T" if os.path.exists(base + "T") else base + "t"
    if not os.path.exists(sct):
        return None
    try:
        deref = fpt_reader(sct)
        r = DbfReader(scx)
    except Exception:
        return None

    titulo = ""
    botones = []
    titulo_fallback = ""
    for row in r.records(include_deleted=True):
        bc = deref(block_no(row.get("BASECLASS"))).strip().lower()
        props = deref(block_no(row.get("PROPERTIES")))
        cap = caption_de(props)
        if bc in ("form", "formset") and cap and not titulo:
            titulo = cap
        elif bc == "commandbutton" and cap:
            cap_limpio = cap.replace("\\<", "").replace("<", "").strip()
            if cap_limpio and cap_limpio.lower() not in ("salir", "cerrar", "cancelar"):
                botones.append(cap_limpio)
        elif bc in ("label", "container") and cap and len(cap) > len(titulo_fallback):
            titulo_fallback = cap
    r._f.close()
    return {"titulo": titulo or titulo_fallback, "botones": botones[:6]}


def familia(nombre):
    m = re.match(r"^(?:frm)?(\d{3})", nombre)
    return m.group(1) if m else ("cb" if nombre.startswith("cb-") else "otros")


def main():
    forms = sorted(glob.glob(os.path.join(ROOT, "Formularios", "*.scx")))
    inv = []
    for scx in forms:
        nombre = os.path.basename(scx)[:-4]
        info = analizar_form(scx) or {"titulo": "", "botones": []}
        fam = familia(nombre)
        inv.append({"form": nombre, "familia": fam,
                    "modulo": MODULO.get(fam, "Otros/Utilidades"),
                    "titulo": info["titulo"], "botones": info["botones"]})

    # reportes por familia
    reps = sorted({os.path.basename(p)[:-4]
                   for p in glob.glob(os.path.join(ROOT, "Reportes", "*.frx"))})

    json.dump({"forms": inv, "reportes": reps},
              open(os.path.join(OUT, "inventario_funcional.json"), "w"),
              ensure_ascii=False, indent=1)

    # markdown agrupado por módulo
    por_mod = defaultdict(list)
    for f in inv:
        por_mod[f["modulo"]].append(f)

    con_titulo = sum(1 for f in inv if f["titulo"])
    L = ["# Inventario funcional — Sistema CCyPP (Ca.Pre.S.Ca.)\n",
         f"> Extraído de los formularios VFP (.scx/.sct). **{len(inv)} pantallas**, "
         f"título recuperado en **{con_titulo}**. Reportes: **{len(reps)}**.\n",
         "> El título es el de la ventana del form; las acciones son sus botones.\n"]

    orden = ["Sistema/Login", "Créditos", "Caja", "Caja (listados)",
             "Contabilidad", "Contabilidad/Egresos", "Tesorería/Egresos",
             "Seguros", "Despacho/Resoluciones", "Despacho/Notas",
             "Mesa/Trámites", "Utilidades/Tablas", "Otros/Utilidades"]
    for mod in orden + [m for m in por_mod if m not in orden]:
        if mod not in por_mod:
            continue
        fs = sorted(por_mod[mod], key=lambda x: x["form"])
        L.append(f"\n## {mod}  ({len(fs)} pantallas)\n")
        for f in fs:
            t = f["titulo"] or "_(sin título)_"
            acc = f"  · acciones: {', '.join(f['botones'])}" if f["botones"] else ""
            L.append(f"- **{f['form']}** — {t}{acc}")

    L.append("\n\n## Reportes (.frx)\n")
    L.append(", ".join(f"`{r}`" for r in reps))

    open(os.path.join(OUT, "inventario_funcional.md"), "w").write("\n".join(L) + "\n")
    print(f"OK  forms={len(inv)}  con_titulo={con_titulo}  reportes={len(reps)}")
    print(f"  -> {OUT}/inventario_funcional.md , .json")
    # resumen por módulo
    for mod in sorted(por_mod, key=lambda m: -len(por_mod[m])):
        print(f"    {mod:26s} {len(por_mod[mod])}")


if __name__ == "__main__":
    main()
