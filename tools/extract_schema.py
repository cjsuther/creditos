#!/usr/bin/env python3
"""
Ingeniería inversa del esquema de datos del sistema CCyPP (Visual FoxPro).

Trabaja SOLO con el código fuente (no hay acceso a los DBC/DBF reales).
Escanea .prg (texto) y .scx/.sct/.frx/.frt/.vcx/.vct (binarios DBF: se extraen
cadenas imprimibles) para inferir:

  - Tablas de negocio referenciadas (USE / FROM / INTO / dbc!tabla / SET DATABASE)
  - Mapeo tabla -> DBC (cuando aparece la sintaxis  dbc!tabla)
  - Campos por tabla (referencias  alias.campo  con convención de tipos VFP)

Salidas:
  - catalogo_datos.json   (estructurado)
  - catalogo_datos.md     (legible)

Uso:  python3 extract_schema.py <ruta_codigo_CCyPP-Desarrollo> [--out <dir>]
"""
import os
import re
import sys
import json
import argparse
from collections import defaultdict, Counter

# --- Contenedores de base de datos conocidos (DBC) ---
DBCS = {
    "agjsgeneral", "agjscreditos", "agjscaja", "agjscontable", "agjsegresos",
    "agjsdespacho", "agjsmesa", "agjsseguros", "agjsjuegos", "symdesec",
    "symdeperf",  # (tabla, pero aparece como db en algunos lugares)
}

# Alias que son objetos/propiedades VFP, NO tablas ni campos de base de datos.
OBJECT_ALIASES = {
    "thisform", "this", "_screen", "_vfp", "_app", "sys", "screen", "form",
    "parent", "thisformset", "loform", "loformset", "goapp", "application",
    "os", "sets", "osets", "odb", "ousuario", "oca", "ole", "oexcel", "oword",
    "ooutlook", "server", "connection", "rs", "cn", "cmd", "xml", "http",
    "lohttp", "ojson", "controls", "columns", "column", "grid", "pageframe",
    "page", "container", "toolbar", "combo", "list", "text", "label", "shape",
    "line", "image", "timer", "spinner", "check", "option", "editbox", "header",
    "activepage", "activecontrol", "value", "caption", "name", "parentclass",
}

# Prefijos de objeto por nomenclatura húngara habitual (o..., l...form, etc.)
OBJECT_PREFIX_RE = re.compile(r"^(o[A-Z]|lo[A-Z]|go[A-Z]|_)", re.ASCII)

# Un campo de base de datos VFP suele empezar por letra de tipo + minúsculas.
# c=char n=num l=logic d=date f/t=datetime e=? i=int y=currency b=double
# m=memo g=general. Es heurística, no perfecta.
FIELD_TYPE_RE = re.compile(r"^[cnldfeimytbg][a-z0-9_]{2,}$")

# Palabras reservadas / propiedades comunes que NO son campos aunque matcheen.
NOT_FIELDS = {
    "caption", "name", "value", "enabled", "visible", "left", "top", "width",
    "height", "forecolor", "backcolor", "fontname", "fontsize", "fontbold",
    "controlsource", "recordsource", "rowsource", "rowsourcetype", "listindex",
    "listcount", "displayvalue", "keyboardhighvalue", "tabindex", "tabstop",
    "borderstyle", "specialeffect", "picture", "readonly", "alignment",
    "inputmask", "format", "comment", "tag", "class", "baseclass", "count",
    "controlcount", "pagecount", "columncount", "activecolumn", "recordsourcetype",
    "clock", "interval", "closable", "movable", "titlebar", "windowstate",
    "colorsource", "gridlines", "deletemark", "highlight", "scrollbars",
    "buttoncount", "cols", "rows", "text1", "text2", "cmd", "cboxes",
}


def read_text_prg(path):
    with open(path, "rb") as f:
        return f.read().decode("latin-1", errors="ignore")


def read_binary_strings(path, minlen=3):
    """Extrae runs de caracteres imprimibles de un binario DBF (scx/frx/vcx...)."""
    data = open(path, "rb").read().decode("latin-1", errors="ignore")
    # separa por caracteres de control en tokens legibles
    return re.findall(r"[ -~áéíóúñÁÉÍÓÚÑ]{%d,}" % minlen, data)


def strip_comments(text):
    out = []
    for line in text.splitlines():
        s = line.lstrip()
        if s.startswith("*"):
            continue
        # comentario inline con &&
        amp = line.find("&&")
        if amp >= 0:
            line = line[:amp]
        out.append(line)
    return "\n".join(out)


# --- Regex de extracción ---
RE_DBC_TABLE = re.compile(r"\b([a-z][a-z0-9_]+)\s*!\s*([a-z][a-z0-9_]+)", re.I)
RE_USE = re.compile(r"\bUSE\s+(?:[a-z]:\\|\\\\|[\w\\.]*[\\/])?([a-z][a-z0-9_]+)", re.I)
RE_FROM = re.compile(r"\bFROM\s+([a-z][a-z0-9_]+)", re.I)
RE_JOIN = re.compile(r"\bJOIN\s+([a-z][a-z0-9_]+)", re.I)
RE_INTO_TABLE = re.compile(r"\bINTO\s+(?:TABLE|DBF)\s+([a-z][a-z0-9_]+)", re.I)
RE_SETDB = re.compile(r"\bSET\s+DATABASE\s+TO\s+([a-z][a-z0-9_]+)", re.I)
RE_DOTTED = re.compile(r"\b([a-z][a-z0-9_]{1,})\.([a-z][a-z0-9_]{1,})\b", re.I)

# Cursores temporales / alias que no son tablas persistentes
TEMP_NAMES = re.compile(r"^(vfp|tmp|cur|tmp\w|c_|qtmp|_?temp|csr|crs|aux|vfptmp|"
                        r"vfp\d|cursor|array|xx|yy|zz|ta_|la_)", re.I)


# Funciones y palabras reservadas de VFP que se cuelan detrás de USE/FROM/dotted.
VFP_BUILTINS = {
    "empty", "found", "deleted", "seek", "eof", "bof", "used", "inlist", "this",
    "general", "estado", "feof", "recno", "reccount", "alltrim", "upper", "lower",
    "substr", "left", "right", "iif", "vartype", "isnull", "between", "str",
    "val", "date", "datetime", "year", "month", "day", "space", "trim", "len",
    "at", "occurs", "chr", "asc", "padl", "padr", "transform", "evaluate",
    "type", "fieldname", "fcount", "dbf", "alias", "select", "curval", "oldval",
    "getfldstate", "cursorgetprop", "cursorsetprop", "reccount", "message",
    "program", "sys", "os", "gomonth", "ctod", "dtoc", "dtos", "ttoc", "ctot",
    "nvl", "isdigit", "isalpha", "proper", "strtran", "chrtran", "createobject",
    "newobject", "file", "fopen", "fread", "fclose", "adir", "afields", "atc",
    "rat", "like", "getwordcount", "getwordnum", "min", "max", "abs", "round",
    "int", "mod", "sqrt", "rand", "seconds", "datetime", "this", "que", "este",
    "esta", "para", "con", "los", "las", "una", "por", "del", "field", "data",
    "name", "shared", "exclusive", "again", "order", "the", "where", "group",
    "most", "old", "array", "cursor", "serversql", "agjs", "win32_networkadapterconfiguration",
    "formset", "toolbar", "container", "recordsource", "recordsourcetype",
}


def is_probable_table(name):
    n = name.lower()
    if n in DBCS:
        return False
    if len(n) < 3:
        return False
    if TEMP_NAMES.match(n):
        return False
    if n in VFP_BUILTINS:
        return False
    if n in OBJECT_ALIASES:
        return False
    if OBJECT_PREFIX_RE.match(name):   # o..., lo..., go..., _...
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    root = args.root
    os.makedirs(args.out, exist_ok=True)

    tables = Counter()                      # tabla -> nº de referencias
    table_files = defaultdict(set)          # tabla -> archivos donde aparece
    table_dbc = defaultdict(Counter)        # tabla -> {dbc: n}
    fields_by_alias = defaultdict(Counter)  # alias -> {campo: n}

    n_prg = n_bin = 0

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)

            if ext == ".prg":
                try:
                    text = strip_comments(read_text_prg(path))
                except Exception:
                    continue
                n_prg += 1
                blob = text
            elif ext in (".scx", ".sct", ".frx", ".frt", ".vcx", ".vct", ".mnx"):
                try:
                    blob = "\n".join(read_binary_strings(path))
                except Exception:
                    continue
                n_bin += 1
            else:
                continue

            # dbc!tabla
            for dbc, tbl in RE_DBC_TABLE.findall(blob):
                if is_probable_table(tbl):
                    tables[tbl.lower()] += 1
                    table_files[tbl.lower()].add(rel)
                    if dbc.lower() in DBCS:
                        table_dbc[tbl.lower()][dbc.lower()] += 1

            # USE / FROM / JOIN / INTO TABLE
            for rex in (RE_USE, RE_FROM, RE_JOIN, RE_INTO_TABLE):
                for m in rex.findall(blob):
                    if is_probable_table(m):
                        tables[m.lower()] += 1
                        table_files[m.lower()].add(rel)

            # campos: alias.campo
            for alias, field in RE_DOTTED.findall(blob):
                a, f = alias.lower(), field.lower()
                if a in OBJECT_ALIASES or OBJECT_PREFIX_RE.match(alias):
                    continue
                if f in NOT_FIELDS:
                    continue
                if not FIELD_TYPE_RE.match(f):
                    continue
                if a in DBCS or TEMP_NAMES.match(a):
                    continue
                fields_by_alias[a][f] += 1

    # --- Consolidación: campos por tabla (alias que coincide con tabla) ---
    catalog = {}
    for tbl, n in tables.most_common():
        dbc = None
        if table_dbc[tbl]:
            dbc = table_dbc[tbl].most_common(1)[0][0]
        flds = fields_by_alias.get(tbl, Counter())
        # Filtro de confianza: mantener si tiene DBC, si se observaron campos,
        # o si se referencia muchas veces (tabla real muy usada).
        if not dbc and len(flds) < 2 and n < 20:
            continue
        catalog[tbl] = {
            "referencias": n,
            "dbc": dbc,
            "archivos": sorted(table_files[tbl])[:8],
            "n_archivos": len(table_files[tbl]),
            "campos": [{"campo": c, "usos": u} for c, u in flds.most_common()],
        }

    # aliases con campos pero que no quedaron como tabla (posibles vistas/alias)
    huerfanos = {
        a: [{"campo": c, "usos": u} for c, u in fl.most_common()]
        for a, fl in fields_by_alias.items()
        if a not in catalog and sum(fl.values()) >= 3
    }

    out_json = os.path.join(args.out, "catalogo_datos.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"tablas": catalog, "alias_con_campos_sin_tabla": huerfanos},
                  f, ensure_ascii=False, indent=2)

    # --- Markdown ---
    lines = []
    lines.append("# Catálogo de datos preliminar — CCyPP (inferido del código)\n")
    lines.append(f"> Generado por ingeniería inversa. Archivos analizados: "
                 f"{n_prg} `.prg` + {n_bin} binarios (scx/frx/vcx).\n")
    lines.append(f"> Tablas candidatas: **{len(catalog)}** · "
                 f"Alias con campos sin tabla resuelta: **{len(huerfanos)}**.\n")
    lines.append("> ⚠️ Tipos de campo inferidos por convención VFP (prefijo). "
                 "Confirmar contra los DBC reales cuando haya backup.\n")

    # agrupar por DBC
    by_dbc = defaultdict(list)
    for tbl, info in catalog.items():
        by_dbc[info["dbc"] or "(sin DBC identificado)"].append((tbl, info))

    for dbc in sorted(by_dbc, key=lambda d: (d.startswith("("), d)):
        lines.append(f"\n## Base: `{dbc}`\n")
        for tbl, info in sorted(by_dbc[dbc], key=lambda x: -x[1]["referencias"]):
            lines.append(f"### `{tbl}`  ·  {info['referencias']} refs  ·  "
                         f"{info['n_archivos']} archivos")
            if info["campos"]:
                cs = ", ".join(f"`{c['campo']}`" for c in info["campos"][:40])
                lines.append(f"- Campos observados ({len(info['campos'])}): {cs}")
            else:
                lines.append("- Campos: (no se observaron referencias `alias.campo`)")
            lines.append("")

    if huerfanos:
        lines.append("\n## Alias con campos pero sin tabla resuelta "
                     "(posibles vistas, cursores persistentes o alias renombrados)\n")
        for a, flds in sorted(huerfanos.items(), key=lambda x: -sum(f['usos'] for f in x[1]))[:40]:
            cs = ", ".join(f"`{c['campo']}`" for c in flds[:25])
            lines.append(f"- **`{a}`**: {cs}")

    out_md = os.path.join(args.out, "catalogo_datos.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"OK  ->  {out_json}")
    print(f"OK  ->  {out_md}")
    print(f"Tablas candidatas: {len(catalog)}  |  alias huérfanos: {len(huerfanos)}")
    print(f"Archivos: {n_prg} prg + {n_bin} binarios")


if __name__ == "__main__":
    main()
