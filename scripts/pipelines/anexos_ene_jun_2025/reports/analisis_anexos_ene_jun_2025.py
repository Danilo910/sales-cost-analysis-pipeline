#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
analisis_anexos_ene_jun_2025.py

Genera un PDF ejecutivo en español para gerencia usando el pipeline correcto:
    ANEXOS.pdf
        -> anexos_ene_jun_2025_extraido_desde_xlsx.json
        -> este script
        -> Reporte_Graficas_Anexos_Ene-Jun_2025.pdf

Diferencias respecto al script viejo
------------------------------------
- YA NO usa datos hardcodeados.
- Lee el JSON extraído desde el XLSX.
- Guarda las gráficas usadas por el reporte en:
      outputs/anexos_ene_jun_2025/plots/
- Guarda el PDF final en:
      docs/Informes_Analisis_Graficas/

Requisitos:
    pip install numpy pandas matplotlib reportlab
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

def find_project_root(start_path: Path) -> Path:
    """
    Busca hacia arriba una raíz de proyecto razonable.
    Criterio: presencia simultánea de README.md y requirements.txt.
    """
    candidate = start_path.parent
    for _ in range(10):
        if (candidate / "README.md").exists() and (candidate / "requirements.txt").exists():
            return candidate
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    raise RuntimeError(
        f"No se pudo localizar la raíz del proyecto desde: {start_path}"
    )



# ============================================================
# PATHS DEL PROYECTO
# ============================================================
PROJECT_ROOT = find_project_root(Path(__file__).resolve())

INPUTS_RAW = PROJECT_ROOT / "inputs" / "raw" / "anexos_ene_jun_2025"

REPORTS_COMPILED = PROJECT_ROOT / "reports" / "compiled_pdf" / "anexos"
OUTPUTS_ANEXOS = PROJECT_ROOT / "outputs" / "anexos_ene_jun_2025"

OUTPUTS_PLOTS = OUTPUTS_ANEXOS / "plots"

INPUT_JSON = INPUTS_RAW / "anexos_ene_jun_2025_extraido_desde_xlsx.json"
OUTPUT_PDF = REPORTS_COMPILED / "Reporte_Graficas_Anexos_Ene-Jun_2025.pdf"


# ============================================================
# UTILIDADES BÁSICAS
# ============================================================
def ensure_dirs() -> None:
    REPORTS_COMPILED.mkdir(parents=True, exist_ok=True)
    OUTPUTS_PLOTS.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el JSON de entrada: {path.resolve()}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_input_schema(data: Dict[str, Any]) -> None:
    required_top = ["totales", "lineas", "zonas"]
    for key in required_top:
        if key not in data:
            raise KeyError(f"Falta la clave requerida en el JSON: '{key}'")

    if "facturacion_usd" not in data["totales"] or "margen_usd" not in data["totales"]:
        raise KeyError("La clave 'totales' debe contener 'facturacion_usd' y 'margen_usd'.")

    if not isinstance(data["lineas"], list) or not data["lineas"]:
        raise ValueError("'lineas' debe ser una lista no vacía.")
    if not isinstance(data["zonas"], list) or not data["zonas"]:
        raise ValueError("'zonas' debe ser una lista no vacía.")


def money_usd(x: float) -> str:
    return f"US$ {x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x: float) -> str:
    return f"{x:.1f}%"


# ============================================================
# CARGA Y CONSTRUCCIÓN DE TABLAS
# ============================================================
def get_report_comments(data: Dict[str, Any]) -> List[str]:
    """
    Para el PDF ejecutivo conviene usar primero comentarios_interpretados.
    Si no existen, se cae a comentarios_extraidos_pdf.
    """
    comments_interpreted = data.get("comentarios_interpretados", [])
    if isinstance(comments_interpreted, list) and len(comments_interpreted) > 0:
        return comments_interpreted

    comments_extracted = data.get("comentarios_extraidos_pdf", [])
    if isinstance(comments_extracted, list):
        return comments_extracted

    return []


def build_tables(data: Dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, int, int, List[str]]:
    total_facturacion_usd = int(data["totales"]["facturacion_usd"])
    total_margen_usd = int(data["totales"]["margen_usd"])

    df_lines = pd.DataFrame(data["lineas"]).copy()
    df_zones = pd.DataFrame(data["zonas"]).copy()
    comments = get_report_comments(data)

    # Shares por línea
    dfL = df_lines.copy()
    dfL["share_fact"] = dfL["facturacion_pct"] / 100.0
    dfL["share_margen"] = dfL["margen_pct"] / 100.0

    # Montos aproximados
    dfL["facturacion_usd_aprox"] = dfL["share_fact"] * total_facturacion_usd
    dfL["margen_usd_aprox"] = dfL["share_margen"] * total_margen_usd

    # Señal gerencial simple
    dfL["senal_margen_vs_ventas"] = dfL["share_margen"] / dfL["share_fact"]

    dfL = dfL.sort_values("facturacion_pct", ascending=False).reset_index(drop=True)
    dfZ = df_zones.copy().sort_values("ventas_usd", ascending=False).reset_index(drop=True)

    return dfL, dfZ, total_facturacion_usd, total_margen_usd, comments


# ============================================================
# GRÁFICAS
# ============================================================
def save_charts(data: Dict[str, Any], outdir: Path) -> List[Path]:
    outdir.mkdir(parents=True, exist_ok=True)

    dfL, dfZ, total_facturacion_usd, total_margen_usd, comments = build_tables(data)

    path1 = outdir / "01_mix_linea_facturacion.png"
    path2 = outdir / "02_mix_linea_margen.png"
    path3 = outdir / "03_ventas_zona_usd.png"
    path4 = outdir / "04_ventas_zona_pct.png"

    # 1) Mix por línea (% facturación)
    plt.figure(figsize=(10, 5))
    plt.bar(dfL["linea"], dfL["facturacion_pct"])
    plt.title("Mix por línea - Porcentaje de facturación (Ene-Jun 2025)")
    plt.xlabel("Línea")
    plt.ylabel("% de facturación")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path1, dpi=200, bbox_inches="tight")
    plt.close()

    # 2) Mix por línea (% margen)
    plt.figure(figsize=(10, 5))
    plt.bar(dfL["linea"], dfL["margen_pct"])
    plt.title("Mix por línea - Participación en el margen total (Ene-Jun 2025)")
    plt.xlabel("Línea")
    plt.ylabel("% de margen")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path2, dpi=200, bbox_inches="tight")
    plt.close()

    # 3) Ventas por zona (US$)
    plt.figure(figsize=(10, 5))
    plt.bar(dfZ["zona"], dfZ["ventas_usd"])
    plt.title("Ventas por zona - Monto (US$) (Ene-Jun 2025)")
    plt.xlabel("Zona")
    plt.ylabel("Ventas (US$)")
    plt.xticks(rotation=20, ha="right")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path3, dpi=200, bbox_inches="tight")
    plt.close()

    # 4) Ventas por zona (%)
    plt.figure(figsize=(10, 5))
    plt.bar(dfZ["zona"], dfZ["ventas_pct"])
    plt.title("Ventas por zona - Porcentaje del total (Ene-Jun 2025)")
    plt.xlabel("Zona")
    plt.ylabel("% del total")
    plt.xticks(rotation=20, ha="right")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path4, dpi=200, bbox_inches="tight")
    plt.close()

    return [path1, path2, path3, path4]


# ============================================================
# PDF HELPERS
# ============================================================
def draw_wrapped_text(c, text, x, y, max_width, leading=14, font_name="Helvetica", font_size=11):
    c.setFont(font_name, font_size)
    words = text.split()
    line = ""
    lines = []

    for w in words:
        trial = (line + " " + w).strip()
        if c.stringWidth(trial, font_name, font_size) <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = w

    if line:
        lines.append(line)

    for ln in lines:
        c.drawString(x, y, ln)
        y -= leading

    return y


def add_header_footer(c, title, page_num):
    W, H = A4
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, H - 1.2 * cm, title)

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawRightString(W - 2 * cm, 1.0 * cm, f"Página {page_num}")
    c.setFillColor(colors.black)


# ============================================================
# PDF PRINCIPAL
# ============================================================
def make_pdf(pdf_path: Path, chart_paths: List[Path], data: Dict[str, Any]) -> None:
    dfL, dfZ, total_facturacion_usd, total_margen_usd, comments = build_tables(data)

    W, H = A4
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    page = 1
    doc_title = "Reporte de Gráficas - Input Ene-Jun 2025"

    # -------------------------
    # Página 1: portada / resumen
    # -------------------------
    add_header_footer(c, doc_title, page)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, H - 3.0 * cm, "Reporte de gráficas (Enero - Junio 2025)")

    c.setFont("Helvetica", 12)
    c.drawString(2 * cm, H - 3.8 * cm, "Escenario: demostración sintética")
    c.drawString(2 * cm, H - 4.5 * cm, f"Fecha de generación: {dt.date.today().isoformat()}")

    c.setStrokeColor(colors.lightgrey)
    c.line(2 * cm, H - 5.0 * cm, W - 2 * cm, H - 5.0 * cm)
    c.setStrokeColor(colors.black)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, H - 6.1 * cm, "Totales del periodo (según anexo):")

    c.setFont("Helvetica", 12)
    c.drawString(2 * cm, H - 6.9 * cm, f"- Facturación total: {money_usd(total_facturacion_usd)}")
    c.drawString(2 * cm, H - 7.6 * cm, f"- Margen total: {money_usd(total_margen_usd)}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, H - 8.8 * cm, "Comentarios del periodo:")

    y = H - 9.6 * cm
    c.setFont("Helvetica", 11)
    for s in comments:
        y = draw_wrapped_text(
            c, f"- {s}", 2 * cm, y, max_width=(W - 4 * cm), leading=14, font_size=11
        )

    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Nota:")
    y -= 16
    c.setFont("Helvetica", 11)
    y = draw_wrapped_text(
        c,
        "Los porcentajes de 'margen' se interpretan como participación del margen total del periodo "
        "(según el anexo). No necesariamente significan 'margen porcentual' por producto. "
        "Para cálculo de margen por producto se requiere costo por producto o margen bruto por ítem.",
        2 * cm, y, max_width=(W - 4 * cm), leading=14, font_size=11
    )

    c.showPage()
    page += 1

    # -------------------------
    # Página 2: mix por línea - facturación
    # -------------------------
    add_header_footer(c, doc_title, page)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, H - 2.2 * cm, "1) Mix por línea: porcentaje de facturación")

    y = H - 3.0 * cm
    y = draw_wrapped_text(
        c,
        "Esta gráfica muestra qué líneas aportaron más a las ventas totales del semestre. "
        "Si una línea sube mucho, puede ser por mayor venta o porque otras líneas tuvieron faltantes.",
        2 * cm, y, max_width=(W - 4 * cm), leading=14, font_size=11
    )

    img = ImageReader(str(chart_paths[0]))
    c.drawImage(img, 2 * cm, 7.2 * cm, width=W - 4 * cm, height=9.0 * cm,
                preserveAspectRatio=True, anchor="c")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, 6.6 * cm, "Resumen (aproximado) por línea:")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, 5.9 * cm, "Línea")
    c.drawString(7 * cm, 5.9 * cm, "% fact.")
    c.drawString(11 * cm, 5.9 * cm, "Facturación aprox.")

    c.setFont("Helvetica", 10)
    yy = 5.4 * cm
    df_small = dfL[["linea", "facturacion_pct", "facturacion_usd_aprox"]].copy()
    for _, r in df_small.iterrows():
        c.drawString(2 * cm, yy, str(r["linea"]))
        c.drawString(7 * cm, yy, pct(r["facturacion_pct"]))
        c.drawString(11 * cm, yy, money_usd(r["facturacion_usd_aprox"]))
        yy -= 0.55 * cm

    c.showPage()
    page += 1

    # -------------------------
    # Página 3: mix por línea - margen
    # -------------------------
    add_header_footer(c, doc_title, page)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, H - 2.2 * cm, "2) Mix por línea: participación en el margen total")

    y = H - 3.0 * cm
    y = draw_wrapped_text(
        c,
        "Esta gráfica muestra qué líneas aportaron más al margen total del semestre. "
        "Si una línea tiene más margen que ventas, es una buena señal, pero conviene confirmarlo con costos.",
        2 * cm, y, max_width=(W - 4 * cm), leading=14, font_size=11
    )

    img = ImageReader(str(chart_paths[1]))
    c.drawImage(img, 2 * cm, 7.2 * cm, width=W - 4 * cm, height=9.0 * cm,
                preserveAspectRatio=True, anchor="c")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, 6.6 * cm, "Resumen (aproximado) por línea:")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, 5.9 * cm, "Línea")
    c.drawString(6.2 * cm, 5.9 * cm, "% margen")
    c.drawString(10.0 * cm, 5.9 * cm, "Margen aprox.")
    c.drawString(14.0 * cm, 5.9 * cm, "Señal")

    c.setFont("Helvetica", 10)
    yy = 5.4 * cm
    df_small = dfL[["linea", "margen_pct", "margen_usd_aprox", "senal_margen_vs_ventas"]].copy()
    for _, r in df_small.iterrows():
        c.drawString(2 * cm, yy, str(r["linea"]))
        c.drawString(6.2 * cm, yy, pct(r["margen_pct"]))
        c.drawString(10.0 * cm, yy, money_usd(r["margen_usd_aprox"]))

        sig = r["senal_margen_vs_ventas"]
        if np.isfinite(sig):
            label = "Buena" if sig > 1.0 else "A revisar"
        else:
            label = "-"

        c.drawString(14.0 * cm, yy, label)
        yy -= 0.55 * cm

    c.showPage()
    page += 1

    # -------------------------
    # Página 4: ventas por zona (US$)
    # -------------------------
    add_header_footer(c, doc_title, page)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, H - 2.2 * cm, "3) Ventas por zona: montos en US$")

    y = H - 3.0 * cm
    y = draw_wrapped_text(
        c,
        "Aquí se ve dónde está el volumen de ventas. Sirve para decidir prioridad comercial, "
        "rutas y esfuerzo de cobranza.",
        2 * cm, y, max_width=(W - 4 * cm), leading=14, font_size=11
    )

    img = ImageReader(str(chart_paths[2]))
    c.drawImage(img, 2 * cm, 7.2 * cm, width=W - 4 * cm, height=9.0 * cm,
                preserveAspectRatio=True, anchor="c")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, 6.6 * cm, "Resumen por zona:")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, 5.9 * cm, "Zona")
    c.drawString(12.2 * cm, 5.9 * cm, "Ventas")
    c.drawString(15.0 * cm, 5.9 * cm, "%")

    c.setFont("Helvetica", 10)
    yy = 5.4 * cm
    for _, r in dfZ.iterrows():
        c.drawString(2 * cm, yy, str(r["zona"]))
        c.drawString(12.2 * cm, yy, money_usd(r["ventas_usd"]))
        c.drawString(15.0 * cm, yy, pct(r["ventas_pct"]))
        yy -= 0.55 * cm

    c.showPage()
    page += 1

    # -------------------------
    # Página 5: ventas por zona (%) + cierre
    # -------------------------
    add_header_footer(c, doc_title, page)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, H - 2.2 * cm, "4) Ventas por zona: porcentaje del total")

    y = H - 3.0 * cm
    y = draw_wrapped_text(
        c,
        "Esta versión en porcentaje ayuda a comparar zonas sin distraerse por montos. "
        "Si el orden de zonas se mantiene en el tiempo, la empresa ya tiene un mapa comercial estable.",
        2 * cm, y, max_width=(W - 4 * cm), leading=14, font_size=11
    )

    img = ImageReader(str(chart_paths[3]))
    c.drawImage(img, 2 * cm, 9.0 * cm, width=W - 4 * cm, height=9.0 * cm,
                preserveAspectRatio=True, anchor="c")

    y = 8.2 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Conclusiones rápidas (del semestre):")
    y -= 0.8 * cm

    c.setFont("Helvetica", 11)
    bullets = [
    "La categoría con mayor participación concentra una parte importante de las ventas y del margen del periodo.",
    "Las diferencias entre categorías deben interpretarse como un resumen agregado y no como evidencia causal.",
    "Las zonas líderes concentran la mayor parte de las ventas del periodo analizado.",
    "Este reporte sirve como resumen visual del escenario sintético cargado desde el archivo XLSX.",
    ]
    for b in bullets:
        y = draw_wrapped_text(
            c, f"- {b}", 2 * cm, y, max_width=(W - 4 * cm), leading=14, font_size=11
        )

    c.save()


# ============================================================
# MAIN
# ============================================================
def main() -> None:
    ensure_dirs()

    print("=" * 90)
    print("GENERACIÓN DE REPORTE PDF - ANEXOS ENE-JUN 2025")
    print("=" * 90)
    print(f"JSON de entrada : {INPUT_JSON.resolve()}")


    print(f"Plots de salida : {OUTPUTS_PLOTS.resolve()}")
    print(f"PDF de salida   : {OUTPUT_PDF.resolve()}")

    data = load_json(INPUT_JSON)
    validate_input_schema(data)

    chart_paths = save_charts(data, OUTPUTS_PLOTS)
    make_pdf(OUTPUT_PDF, chart_paths, data)




    print("\n[OK] PDF generado correctamente.")
    print(f"[OK] Reporte final: {OUTPUT_PDF.resolve()}")
    print("[OK] Gráficas registradas en:")
    for p in chart_paths:
        print(f"     - {p.resolve()}")


if __name__ == "__main__":
    main()