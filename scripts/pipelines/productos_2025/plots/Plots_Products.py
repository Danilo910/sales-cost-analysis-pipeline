#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plots_Products.py

Input:
  diccionario_ventas_costos_2025.json

Output:
  PDFs por línea con barras superpuestas:
    - Ventas (azul) vs Costo (rojo) por producto

Regla especial para líneas grandes:
  - Graficar TOP-K productos por utilidad (Ventas - Costo)
  - + una barra adicional "OTROS (n=...)" que agrupa el resto

Los demás gráficos quedan iguales (si la línea es pequeña, se grafica todo).

Requisitos:
  pip install --no-cache-dir matplotlib
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

KEY_TOTAL_COSTO = "TOTAL_COSTO"
KEY_TOTAL_VENTA = "TOTAL_VENTA"

# Líneas para las que aplicamos la regla TOP-K + OTROS
TOPK_PLUS_OTHERS_LINES = {"Linea_C": 15} # puedes añadir otras si quieres

# Si una línea NO está en TOPK_PLUS_OTHERS_LINES, se grafica TODO (asumiendo que es pequeña)


def safe_float(x):
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def fmt_intish(x: float) -> str:
    """12345 -> '12.345' """
    try:
        return f"{x:,.0f}".replace(",", ".")
    except Exception:
        return str(x)


def sanitize_filename(s: str) -> str:
    keep = []
    for ch in s.upper():
        if ch.isalnum():
            keep.append(ch)
        elif ch in [" ", "-", "_"]:
            keep.append("_")
    out = "".join(keep).strip("_")
    while "__" in out:
        out = out.replace("__", "_")
    return out or "LINEA"


def load_json(path: Path) -> dict:
    print("=== Verificación de ruta ===")
    print("Directorio actual:", Path(".").resolve())
    print("Archivo JSON esperado:", path.resolve())
    if not path.exists():
        raise FileNotFoundError(f"No encuentro {path}. ¿Estás en el directorio correcto?")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Formato inesperado: el JSON debería ser un dict en el nivel superior.")

    print("\n=== JSON cargado ===")
    print("Líneas detectadas:", list(data.keys()))
    for linea, productos in data.items():
        if isinstance(productos, dict):
            print(f"- {linea}: {len(productos)} productos")
        else:
            print(f"- {linea}: formato inesperado (no dict)")

    return data


def aggregate_products_for_line(productos: dict):
    """
    Retorna lista:
      [{"producto":..., "venta":..., "costo":..., "utilidad":...}, ...]
    """
    out = []
    for prod_name, prod_info in productos.items():
        if not isinstance(prod_info, dict):
            continue

        venta = 0.0
        costo = 0.0

        if KEY_TOTAL_VENTA in prod_info and isinstance(prod_info[KEY_TOTAL_VENTA], dict):
            venta = safe_float(prod_info[KEY_TOTAL_VENTA].get("valor", 0.0))

        if KEY_TOTAL_COSTO in prod_info and isinstance(prod_info[KEY_TOTAL_COSTO], dict):
            costo = safe_float(prod_info[KEY_TOTAL_COSTO].get("valor", 0.0))

        out.append({
            "producto": str(prod_name),
            "venta": venta,
            "costo": costo,
            "utilidad": venta - costo
        })

    return out


def topk_plus_others(rows: list, k: int):
    """
    Selecciona TOP-k por utilidad y agrega una fila "OTROS (n=...)" con el resto agregado.
    Si rows <= k, devuelve rows sin cambios.
    """
    if len(rows) <= k:
        return rows

    rows_sorted = sorted(rows, key=lambda r: r["utilidad"], reverse=True)
    top = rows_sorted[:k]
    rest = rows_sorted[k:]

    otros_venta = sum(r["venta"] for r in rest)
    otros_costo = sum(r["costo"] for r in rest)
    otros_util = sum(r["utilidad"] for r in rest)

    top.append({
        "producto": f"OTROS (n={len(rest)})",
        "venta": otros_venta,
        "costo": otros_costo,
        "utilidad": otros_util
    })
    return top


def add_value_labels(ax, x_positions, values, y_offset_frac=0.01, fontsize=8):
    ymin, ymax = ax.get_ylim()
    yrange = (ymax - ymin) if ymax > ymin else 1.0
    offset = y_offset_frac * yrange

    for x, v in zip(x_positions, values):
        ax.text(x, v + offset, fmt_intish(v), ha="center", va="bottom", fontsize=fontsize)


def plot_overlay_by_product(linea: str, rows: list, pdf_path: str):
    """
    Ventas (azul) vs Costo (rojo) superpuestos por producto.
    Mantenemos estilo igual al anterior.
    """
    # Orden visual por ventas desc para que el gráfico "cuente la historia" de volumen
    rows_sorted = sorted(rows, key=lambda r: r["venta"], reverse=True)

    productos = [r["producto"] for r in rows_sorted]
    ventas = [r["venta"] for r in rows_sorted]
    costos = [r["costo"] for r in rows_sorted]
    utilidades = [r["utilidad"] for r in rows_sorted]

    x = list(range(len(productos)))

    fig_w = max(11, 0.6 * len(productos))
    fig_h = 6
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_subplot(111)

    ax.bar(x, ventas, color="blue", alpha=0.70, label="Ventas (US$)", edgecolor="black", linewidth=0.6, zorder=2)
    ax.bar(x, costos, color="red",  alpha=0.45, label="Costo (US$)",  edgecolor="black", linewidth=0.6, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(productos, rotation=35, ha="right")
    ax.set_ylabel("Monto (US$)")
    ax.set_title(f"{linea}: Ventas vs Costo por producto (Totales 2025)")
    ax.grid(True, axis="y", alpha=0.25, zorder=1)
    ax.legend()

    # Etiquetas numéricas: solo ventas (para no saturar)
    add_value_labels(ax, x, ventas, y_offset_frac=0.012, fontsize=8)

    # Utilidad total de lo mostrado (incluye 'OTROS' si aplica)
    utilidad_total = sum(utilidades)
    ax.text(0.01, 0.95,
            f"Utilidad total (mostrado): {fmt_intish(utilidad_total)} US$",
            transform=ax.transAxes, va="top", fontsize=10)

    fig.tight_layout()
    with PdfPages(pdf_path) as pdf:
        pdf.savefig(fig)
    plt.close(fig)

    print(f"PDF generado: {pdf_path}")


def main():
    OUTPUTS_PRODUCTOS_PDF.mkdir(parents=True, exist_ok=True)
    data = load_json(Path(JSON_FILE))

    print("\n=== Procesando líneas ===")
    for linea, productos in data.items():
        if not isinstance(productos, dict) or len(productos) == 0:
            print(f"[ADVERTENCIA] Línea '{linea}' vacía o formato raro. Se omite.")
            continue

        rows = aggregate_products_for_line(productos)

        # (Opcional) filtrar filas completamente vacías (0,0)
        # rows = [r for r in rows if (r["venta"] != 0 or r["costo"] != 0)]

        if linea in TOPK_PLUS_OTHERS_LINES:
            k = TOPK_PLUS_OTHERS_LINES[linea]
            print(f"\n[{linea}] regla especial: TOP-{k} por utilidad + barra OTROS")
            rows_use = topk_plus_others(rows, k)

            # Prints de control
            rows_rank = sorted(rows, key=lambda r: r["utilidad"], reverse=True)
            print(f"  Total productos: {len(rows)}")
            print(f"  Top-{k} utilidad (antes de agregar OTROS):")
            for r in rows_rank[:k]:
                print(f"    - {r['producto']}: venta={r['venta']:.2f}, costo={r['costo']:.2f}, utilidad={r['utilidad']:.2f}")
            print(f"  Se agruparon {max(0, len(rows)-k)} productos en 'OTROS'.")

        else:
            print(f"\n[{linea}] graficando TODOS ({len(rows)} productos).")
            rows_use = rows

        out_pdf = OUTPUTS_PRODUCTOS_PDF / f"Productos_{sanitize_filename(linea)}_Costo_vs_Ventas_2025.pdf"
        plot_overlay_by_product(linea, rows_use, out_pdf)

    print("\nListo. Se generaron PDFs por línea en este directorio.")


if __name__ == "__main__":
    main()
