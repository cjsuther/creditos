"""Generación de documentos Word (.docx) — resoluciones/disposiciones.

Reemplaza la generación vía Word del VFP (owordclass.vcx, 105050000modelos).
El documento sigue la estructura formal de un acto administrativo.
"""
from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

TIPO_NOMBRE = {"RES": "RESOLUCIÓN", "DIS": "DISPOSICIÓN"}


def resolucion_docx(resolucion) -> bytes:
    """Genera el .docx de una resolución/disposición. Devuelve los bytes."""
    doc = Document()

    # Encabezado institucional
    enc = doc.add_paragraph()
    enc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = enc.add_run("Caja de Crédito y Previsión Popular — Ca.Pre.S.Ca.")
    run.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = RGBColor(0x14, 0x42, 0x8A)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run("Provincia de Catamarca").italic = True

    doc.add_paragraph()

    # Título del acto
    tipo = TIPO_NOMBRE.get(resolucion.tipo, "RESOLUCIÓN")
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = titulo.add_run(f"{tipo} N° {resolucion.numero}/{resolucion.anio}")
    r.bold = True
    r.font.size = Pt(14)

    # Lugar y fecha
    lugar = doc.add_paragraph()
    lugar.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    lugar.add_run(f"San Fernando del Valle de Catamarca, {resolucion.fecha:%d/%m/%Y}")

    if resolucion.organo:
        org = doc.add_paragraph()
        org.add_run("Órgano emisor: ").bold = True
        org.add_run(resolucion.organo)

    # Asunto
    asunto = doc.add_paragraph()
    asunto.add_run("ASUNTO: ").bold = True
    asunto.add_run(resolucion.asunto)

    doc.add_paragraph()

    # Cuerpo (VISTO / CONSIDERANDO / RESUELVE a partir del texto)
    texto = (resolucion.texto or "").strip()
    if texto:
        for parrafo in texto.split("\n"):
            p = parrafo.strip()
            if not p:
                continue
            par = doc.add_paragraph(p)
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    else:
        doc.add_paragraph("VISTO:").runs[0].bold = True
        doc.add_paragraph(f"El expediente relativo a: {resolucion.asunto};")
        doc.add_paragraph("CONSIDERANDO:").runs[0].bold = True
        doc.add_paragraph("Que corresponde dictar el presente acto administrativo;")
        p = doc.add_paragraph()
        p.add_run("Por ello, EL DIRECTORIO de la Ca.Pre.S.Ca.").bold = True
        p.add_run(" RESUELVE:")
        doc.add_paragraph(
            "ARTÍCULO 1°.- Aprobar lo actuado conforme a los considerandos precedentes.")
        doc.add_paragraph(
            "ARTÍCULO 2°.- Regístrese, comuníquese y archívese.")

    # Estado
    doc.add_paragraph()
    estado = doc.add_paragraph()
    estado.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    txt = "— FIRMADA —" if resolucion.estado == "F" else "— BORRADOR (sin firma) —"
    estado.add_run(txt).italic = True

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def anexo_docx(anexo, resolucion) -> bytes:
    """Genera el .docx de un anexo de resolución/disposición."""
    doc = Document()
    tipo = TIPO_NOMBRE.get(resolucion.tipo, "RESOLUCIÓN")

    enc = doc.add_paragraph()
    enc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = enc.add_run("Caja de Crédito y Previsión Popular — Ca.Pre.S.Ca.")
    run.bold = True; run.font.size = Pt(13); run.font.color.rgb = RGBColor(0x14, 0x42, 0x8A)

    doc.add_paragraph()
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = titulo.add_run(f"ANEXO N° {anexo.numero} — {tipo} N° {resolucion.numero}/{resolucion.anio}")
    r.bold = True; r.font.size = Pt(13)

    if anexo.titulo:
        st = doc.add_paragraph(); st.alignment = WD_ALIGN_PARAGRAPH.CENTER
        st.add_run(anexo.titulo).bold = True

    doc.add_paragraph()
    for linea in (anexo.texto or "").split("\n"):
        doc.add_paragraph(linea)

    doc.add_paragraph()
    estado = doc.add_paragraph(); estado.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    estado.add_run("— CONFIRMADO —" if anexo.estado == "C" else "— BORRADOR —").italic = True

    buf = BytesIO()
    doc.save(buf); buf.seek(0)
    return buf.read()
