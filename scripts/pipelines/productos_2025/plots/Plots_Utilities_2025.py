#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plots_Utilities_2025.py

Genera 2 PDFs distintos:

(1) PDF A (SIN CAMBIOS respecto al anterior):
    - Barras superpuestas por línea: Ventas (azul) vs Costo (rojo)
    - Con etiquetas numéricas arriba

(2) PDF B (NUEVO):
    - Mismo overlay Ventas (azul) vs Costo (rojo)
    - + barra morada de Utilidad (Ventas - Costo) desplazada a la derecha por cada línea
    - Con etiquetas numéricas arriba de cada barra

Requisitos:
  pip install --no-cache-dir matplotlib

Ejecutar:
  python3 Plots_Utilities_2025.py
"""

import json
from pathlib import Path

# -------------------------------------------------
# PROJECT PATHS
# -------------------------------------------------
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

PROJECT_ROOT = find_project_root(Path(__file__).resolve())
INPUTS_RAW_SHARED = PROJECT_ROOT / "inputs" / "raw" / "shared"
OUTPUTS_PRODUCTOS_PDF = PROJECT_ROOT / "outputs" / "productos_2025" / "pdf"

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


JSON_FILE = INPUTS_RAW_SHARED / "diccionario_ventas_costos_2025.json"

OUTPUT_PDF_OVERLAY = OUTPUTS_PRODUCTOS_PDF / "Costo_vs_Ventas_por_Linea_2025.pdf"
OUTPUT_PDF_OVERLAY_PLUS_PROFIT = OUTPUTS_PRODUCTOS_PDF / "Costo_Ventas_y_Utilidad_por_Linea_2025.pdf"

KEY_TOTAL_COSTO = "TOTAL_COSTO"
KEY_TOTAL_VENTA = "TOTAL_VENTA"


def safe_float(x):
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def fmt_intish(x: float) -> str:
    """12345 -> '12.345' (punto como separador de miles)"""
    try:
        s = f"{x:,.0f}"
        return s.replace(",", ".")
    except Exception:
        return str(x)


def load_json(path: Path) -> dict:
    print("=== Verificación de ruta ===")
    print("Directorio actual:", Path(".").resolve())
    print("Archivo JSON esperado:", path.resolve())

    if not path.exists():
        raise FileNotFoundError(f"No encuentro {path}. Asegúrate de estar en el directorio correcto.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n=== JSON cargado correctamente ===")
    print("Número de líneas (nivel 1):", len(data))
    print("Líneas detectadas:", list(data.keys()))
    return data


def aggregate_totals_by_line(data: dict) -> dict:
    """
    totals[linea] = {
      "venta": suma TOTAL_VENTA.valor por producto,
      "costo": suma TOTAL_COSTO.valor por producto,
      "utilidad": venta - costo,
      "n_prod": n productos,
      "faltan_venta": cuántos productos sin TOTAL_VENTA,
      "faltan_costo": cuántos productos sin TOTAL_COSTO
    }
    """
    totals = {}

    for linea, productos in data.items():
        venta_total = 0.0
        costo_total = 0.0
        faltan_venta = 0
        faltan_costo = 0
        n_prod = 0

        if not isinstance(productos, dict):
            print(f"[ADVERTENCIA] La línea {linea} no contiene un dict de productos. Se omite.")
            continue

        for _, prod_info in productos.items():
            n_prod += 1
            if not isinstance(prod_info, dict):
                continue

            if KEY_TOTAL_VENTA in prod_info and isinstance(prod_info[KEY_TOTAL_VENTA], dict):
                venta_total += safe_float(prod_info[KEY_TOTAL_VENTA].get("valor", 0.0))
            else:
                faltan_venta += 1

            if KEY_TOTAL_COSTO in prod_info and isinstance(prod_info[KEY_TOTAL_COSTO], dict):
                costo_total += safe_float(prod_info[KEY_TOTAL_COSTO].get("valor", 0.0))
            else:
                faltan_costo += 1

        totals[linea] = {
            "venta": venta_total,
            "costo": costo_total,
            "utilidad": venta_total - costo_total,
            "n_prod": n_prod,
            "faltan_venta": faltan_venta,
            "faltan_costo": faltan_costo,
        }

    print("\n=== Agregación por línea (totales anuales) ===")
    for linea, t in totals.items():
        print(f"- {linea}: venta={t['venta']:.2f}, costo={t['costo']:.2f}, utilidad={t['utilidad']:.2f}, "
              f"productos={t['n_prod']}, faltan TOTAL_VENTA={t['faltan_venta']}, faltan TOTAL_COSTO={t['faltan_costo']}")

    return totals


def add_value_labels(ax, x_positions, values, y_offset_frac=0.01, fontsize=9):
    ymin, ymax = ax.get_ylim()
    yrange = (ymax - ymin) if ymax > ymin else 1.0
    offset = y_offset_frac * yrange
    for x, v in zip(x_positions, values):
        ax.text(x, v + offset, fmt_intish(v), ha="center", va="bottom", fontsize=fontsize)


# =========================
# PDF A: overlay original (sin cambios)
# =========================

def plot_overlay_original(lineas, ventas, costos, output_pdf):
    x = list(range(len(lineas)))

    fig = plt.figure(figsize=(11, 6))
    ax = fig.add_subplot(111)

    ax.bar(x, ventas, color="blue", alpha=0.70, label="Ventas (US$)", edgecolor="black", linewidth=0.6, zorder=2)
    ax.bar(x, costos, color="red",  alpha=0.45, label="Costo (US$)",  edgecolor="black", linewidth=0.6, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(lineas)
    ax.set_ylabel("Monto (US$)")
    ax.set_title("Costo vs Ventas por línea (Totales 2025)")
    ax.grid(True, axis="y", alpha=0.25, zorder=1)
    ax.legend()

    # Etiquetas numéricas (como antes)
    add_value_labels(ax, x, ventas, y_offset_frac=0.012, fontsize=9)
    add_value_labels(ax, x, costos, y_offset_frac=0.002, fontsize=9)

    fig.tight_layout()
    with PdfPages(output_pdf) as pdf:
        pdf.savefig(fig)
    plt.close(fig)

    print(f"\nPDF generado (overlay original): {output_pdf}")


# =========================
# PDF B: overlay + utilidad a la derecha (morado)
# =========================

def plot_overlay_plus_profit(lineas, ventas, costos, utilidades, output_pdf):
    """
    Por cada línea i:
      - Ventas (azul) y Costo (rojo) superpuestos en el "slot" central (x_center)
      - Utilidad (morado) en un "slot" independiente a la derecha (x_profit)
    De esta forma NO se superponen físicamente (no colisionan).
    """
    base = list(range(len(lineas)))

    # Control geométrico del layout
    w_overlay = 0.35   # ancho de barra para el overlay (azul/rojo)
    w_profit  = 0.25   # ancho de la barra de utilidad
    gap       = 0.18   # separación entre overlay y utilidad
    shift     = (w_overlay/2) + gap + (w_profit/2)  # distancia del centro al centro de utilidad

    x_center = base
    x_profit = [b + shift for b in base]

    fig = plt.figure(figsize=(11, 6))
    ax = fig.add_subplot(111)

    # Overlay (mismo x_center, pero con ancho controlado para que NO invada el slot de utilidad)
    ax.bar(x_center, ventas, width=w_overlay, color="blue", alpha=0.70,
           label="Ventas (US$)", edgecolor="black", linewidth=0.6, zorder=2)
    ax.bar(x_center, costos, width=w_overlay, color="red", alpha=0.45,
           label="Costo (US$)", edgecolor="black", linewidth=0.6, zorder=3)

    # Utilidad a la derecha (slot separado)
    ax.bar(x_profit, utilidades, width=w_profit, color="purple", alpha=0.65,
           label="Utilidad (Ventas - Costo)", edgecolor="black", linewidth=0.6, zorder=4)

    # Ticks: mantenemos el nombre centrado en el overlay (x_center)
    ax.set_xticks(x_center)
    ax.set_xticklabels(lineas)
    ax.set_ylabel("Monto (US$)")
    ax.set_title("Costo vs Ventas (superpuestos) + Utilidad (a la derecha) por línea (Totales 2025)")
    ax.grid(True, axis="y", alpha=0.25, zorder=1)
    ax.legend()

    # Línea 0 para utilidades negativas si aparecieran
    ax.axhline(0, linewidth=0.8, zorder=5)

    # Etiquetas numéricas
    add_value_labels(ax, x_center, ventas, y_offset_frac=0.012, fontsize=9)
    add_value_labels(ax, x_center, costos, y_offset_frac=0.002, fontsize=9)
    add_value_labels(ax, x_profit, utilidades, y_offset_frac=0.012, fontsize=9)

    # Ajuste de límites x para que entre el "slot" derecho
    ax.set_xlim(-0.6, len(lineas) - 1 + shift + 0.6)

    fig.tight_layout()
    with PdfPages(output_pdf) as pdf:
        pdf.savefig(fig)
    plt.close(fig)

    print(f"\nPDF generado (overlay + utilidad): {output_pdf}")


def main():
    OUTPUTS_PRODUCTOS_PDF.mkdir(parents=True, exist_ok=True)
    data = load_json(Path(JSON_FILE))

    print("\n=== Chequeo de claves en una muestra ===")
    for linea, productos in data.items():
        if isinstance(productos, dict) and len(productos) > 0:
            prod_name = next(iter(productos))
            prod_info = productos[prod_name]
            print("Línea muestra:", linea)
            print("Producto muestra:", prod_name)
            if isinstance(prod_info, dict):
                keys = list(prod_info.keys())
                print("Keys del producto (primeras 15):", keys[:15])
                print(f"¿Existe {KEY_TOTAL_VENTA}? ->", KEY_TOTAL_VENTA in prod_info)
                print(f"¿Existe {KEY_TOTAL_COSTO}? ->", KEY_TOTAL_COSTO in prod_info)
            break

    totals = aggregate_totals_by_line(data)
    if not totals:
        raise RuntimeError("No se agregaron totales. Revisa el JSON y las claves TOTAL_VENTA/TOTAL_COSTO.")

    # Orden por ventas desc (para lectura)
    items = sorted(totals.items(), key=lambda kv: kv[1]["venta"], reverse=True)
    lineas = [k for k, _ in items]
    ventas = [v["venta"] for _, v in items]
    costos = [v["costo"] for _, v in items]
    utilidades = [v["utilidad"] for _, v in items]

    print("\n=== Orden de líneas para gráficos ===")
    print(lineas)

    # PDF A: NO CAMBIA
    plot_overlay_original(lineas, ventas, costos, OUTPUT_PDF_OVERLAY)

    # PDF B: overlay + utilidad
    plot_overlay_plus_profit(lineas, ventas, costos, utilidades, OUTPUT_PDF_OVERLAY_PLUS_PROFIT)


if __name__ == "__main__":
    main()

