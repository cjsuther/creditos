#!/usr/bin/env python3
"""Análisis de brechas: cruza el inventario funcional (377 forms) contra lo
efectivamente construido en el sistema nuevo. Deja registro completo, sin omitir
ninguna pantalla.

Salida: analisis-brechas.md + analisis-brechas.json
"""
import os
import json
from collections import defaultdict

HERE = os.path.dirname(__file__)
INV = os.path.join(HERE, "..", "salida", "inventario_funcional.json")
OUT = os.path.join(HERE, "..", "salida")

# Conjunto de formularios cuya funcionalidad YA fue implementada (aunque sea
# parcialmente). Curado a mano a partir de estado-migracion.md.
CONSTRUIDO = {
    # Créditos
    "frm305050000lineas", "consulta_solicitudes", "frm315050000consoli",
    "frm320100000solcre", "frm320050001pagacred", "320050001pagacred",
    "frm315650000hiscre", "frm315400000sitmar", "frm315350000estadvar",
    "frm315300000consenvios", "frm315250000organismos",
    # Créditos — informes/consultas (iteración 5)
    "frm315451500solactivas", "frm330350000liscre", "frm330500000crepag",
    "frm330301000tdc_cre_can", "frm330851000infosaldos", "frm330600000ctasmora1",
    "frm330550000crepart", "frm330650000creditoslinea", "frm310100000lineas",
    "frm330850500infoestado",
    "frm305150000requisitos", "frm305250000gasistas", "frm305300000montosperiodos",
    "frm330750000ctactejub", "frm330400000lisrecupera",
    # Utilidades/Tablas — usuarios/perfiles + Despacho por oficina
    "frm905050000abmusu-1", "frm90505abmusu", "frm9050501camcla",
    "frm90510admperfil", "frm91010lisusu", "frm910050000lisper",
    "frm905250000abmorg", "frm905200000abmpar", "frm905450000admofi",
    "frm530100000lista_tram_pend_ofi", "frm515100000historial",
    "frm515050000trampend", "frm520100003cons_exptes", "frm520100003constram",
    "rpt106auditoria", "frm920050000audit001",
    # Jubilados / Ley 5094
    "frm320250500soljub", "frm320251000soljubpro", "frm320251500solpagjub",
    "frm320550000subjub", "frm330250500soljub", "frm330251000soljubdpto",
    "frm330251500cli5094", "frm315150000consjub",
    # Caja
    "frm225050000aplicativodeCaja", "frm225050000aplicaj", "frm225150001pagcsj",
    "frm225350000cierrec", "frm225300000ctrlcaj", "frm230050000rptpend",
    "frm230100000rptreci", "frm230100000rptrecihis", "frm225250000anupago",
    # Contabilidad
    "cb-crasientootorga", "cb-crasientodevenga", "cb-iva-a-pagar-periodo",
    "cb-cjcreditoscobrados",
    # Tesorería / Egresos
    "frm805100000altaop", "frm820150000cargachetra", "frm820100000recibos",
    "frm815050000buscaegresos", "frm805050000altachequeras",
    "frm825050000depurapendientes", "frm825100000opcero", "frm815050001buscamuestra",
    # Seguros
    "frm720100000altatitular-1", "frm720100000altatitular-2",
    "frm730100000informededeudapororganismos", "frm720050000cobrasegu",
    "frm705050000maetit", "frm720200000excombatientes", "frm725150000cuotasdesubsidio",
    # Seguros — informes (cerrados en iteración Seguros)
    "frm730050000rptcobseg", "frm715100000cons_primas", "frm720150000pagosseguros",
    # Despacho
    "120050000reso_disp", "105050000modelos", "520100000pasegral",
    "520100003paseinicial", "520100003paseinicial1",
    # Mesa
    "frm315600000consturno", "frm315620000consturno",
    # Juegos/Quiniela (agencias, liquidaciones, resumen, cobro)
    "frm405050001maeagencias", "frm410050000rptagencias",
    "frm425050002altaage", "frm425050003revliq", "frm425050003revliq1",
    # Contabilidad — informes (iteración 2)
    "cb-op-dev-periodo", "cb-crevicredborra", "cb-egreviegresos",
    # Informes desbloqueados por extensión de modelo con datos reales (H-011)
    "cb-egivaegresos", "cb-iva-gsoq-periodo", "cb-prepag-linea", "cb-prepag-linea-1",
}

# Formularios que necesitan datos/conceptos que NO están en el modelo actual.
NECESITA_DATOS = set()

# Formularios que son variantes/duplicados de otro ya construido (no cuentan como
# brecha real). Heurística: mismo prefijo + sufijo de variante.
VARIANTE_MARCAS = ("-a medias", "_s_interes", "-1", "_1", "-2", "_2", "_anterior",
                   "reimp", "_esp", "_h", "hist", "_andres", "_gustavo")


def es_variante(nombre: str, construidos: set) -> bool:
    base = nombre
    for m in VARIANTE_MARCAS:
        if base.endswith(m):
            base = base[: -len(m)]
            if base in construidos:
                return True
    return False


def main():
    data = json.load(open(INV, encoding="utf-8"))
    forms = data["forms"]

    por_mod = defaultdict(lambda: {"total": 0, "construido": 0, "variante": 0,
                                   "datos": 0, "pendiente": 0, "items": []})
    for f in forms:
        mod = f["modulo"]
        estado = "pendiente"
        if f["form"] in CONSTRUIDO:
            estado = "construido"
        elif f["form"] in NECESITA_DATOS:
            estado = "datos"
        elif es_variante(f["form"], CONSTRUIDO):
            estado = "variante"
        d = por_mod[mod]
        d["total"] += 1
        d[estado] += 1
        d["items"].append({"form": f["form"], "titulo": f["titulo"],
                           "estado": estado, "botones": f["botones"]})

    total = len(forms)
    construido = sum(d["construido"] for d in por_mod.values())
    variante = sum(d["variante"] for d in por_mod.values())
    datos = sum(d["datos"] for d in por_mod.values())
    pendiente = sum(d["pendiente"] for d in por_mod.values())

    json.dump({"por_modulo": por_mod, "totales": {
        "total": total, "construido": construido, "variante": variante,
        "datos": datos, "pendiente": pendiente}},
        open(os.path.join(OUT, "analisis-brechas.json"), "w"),
        ensure_ascii=False, indent=1)

    L = ["# Análisis de brechas — CCyPP",
         "### Inventario completo (377 forms) vs. sistema nuevo\n",
         "> Registro exhaustivo, sin omitir pantallas. **✅ construido** (funcionalidad "
         "implementada aunque sea parcial) · **≈ variante** (duplicado de una ya "
         "construida) · **⏳ pendiente**.\n",
         f"\n## Totales\n",
         f"| | Cantidad | % |",
         f"|---|---:|---:|",
         f"| Formularios totales | {total} | 100% |",
         f"| ✅ Construido | {construido} | {construido*100//total}% |",
         f"| ≈ Variante de uno construido | {variante} | {variante*100//total}% |",
         f"| 🔷 Requiere datos reales/modelo | {datos} | {datos*100//total}% |",
         f"| ⏳ **Pendiente** | {pendiente} | {pendiente*100//total}% |\n"]

    orden = sorted(por_mod, key=lambda m: -por_mod[m]["pendiente"])
    L.append("\n## Brecha por módulo (ordenado por pendientes)\n")
    L.append("| Módulo | Total | ✅ | ≈ | 🔷 | ⏳ Pendiente |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for mod in orden:
        d = por_mod[mod]
        L.append(f"| {mod} | {d['total']} | {d['construido']} | {d['variante']} | "
                 f"{d['datos']} | **{d['pendiente']}** |")

    # detalle por módulo
    for mod in orden:
        d = por_mod[mod]
        L.append(f"\n## {mod} — {d['pendiente']} pendientes de {d['total']}\n")
        icon = {"construido": "✅", "variante": "≈", "datos": "🔷", "pendiente": "⏳"}
        for it in sorted(d["items"], key=lambda x: (x["estado"] != "pendiente", x["form"])):
            t = it["titulo"] or "_(sin título)_"
            acc = f" · [{', '.join(it['botones'])}]" if it["botones"] else ""
            L.append(f"- {icon[it['estado']]} **{it['form']}** — {t}{acc}")

    open(os.path.join(OUT, "analisis-brechas.md"), "w").write("\n".join(L) + "\n")
    print(f"forms={total}  construido={construido}  variante={variante}  pendiente={pendiente}")
    print("Pendientes por módulo:")
    for mod in orden:
        print(f"  {mod:26s} {por_mod[mod]['pendiente']:3d} / {por_mod[mod]['total']}")


if __name__ == "__main__":
    main()
