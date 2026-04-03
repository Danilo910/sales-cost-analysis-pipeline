#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Matriz_Ventas_Utilidad_2025_Multipanel.py

Versión multipanel para resolver colapso visual:
- Página 1: matriz general
- Página 2: zoom de "Fuerte del portafolio"
- Página 3: zoom de "Nicho rentable"

Escalas:
- eje X: log
- eje Y: symlog

Clasificación:
    - Alta venta / Alta utilidad   -> Fuerte del portafolio
    - Alta venta / Baja utilidad   -> Tractor de volumen
    - Baja venta / Alta utilidad   -> Nicho rentable
    - Baja venta / Baja utilidad   -> Debil / revisar
"""

import json
import re
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
OUTPUTS_MATRIZ_CSV = PROJECT_ROOT / "outputs" / "matriz_ventas_2025" / "csv"
OUTPUTS_MATRIZ_PDF = PROJECT_ROOT / "outputs" / "matriz_ventas_2025" / "pdf"

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D

JSON_FILE = INPUTS_RAW_SHARED / "diccionario_ventas_costos_2025.json"
OUTPUT_CSV = OUTPUTS_MATRIZ_CSV / "matriz_ventas_utilidad_productos_2025_multipanel.csv"
OUTPUT_PDF = OUTPUTS_MATRIZ_PDF / "matriz_ventas_utilidad_productos_2025_multipanel.pdf"

KEY_TOTAL_COSTO = "TOTAL_COSTO"
KEY_TOTAL_VENTA = "TOTAL_VENTA"


def safe_float(x):
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def normalize_sku_name(name: str) -> str:
    if name is None:
        return ""
    s = str(name).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def load_json(path: Path) -> dict:
    print("=" * 90)
    print("MATRIZ VENTAS–UTILIDAD 2025 | VERSIÓN MULTIPANEL")
    print("=" * 90)
    print(f"Directorio actual     : {Path('.').resolve()}")
    print(f"Archivo JSON esperado : {path.resolve()}")

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el JSON: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("[OK] JSON cargado correctamente.")
    print(f"Líneas detectadas     : {list(data.keys())}")
    return data


def build_product_df(data: dict) -> pd.DataFrame:
    rows = []

    for linea, productos in data.items():
        if not isinstance(productos, dict):
            continue

        for producto, prod_info in productos.items():
            if not isinstance(prod_info, dict):
                continue

            tiene_venta = False
            tiene_costo = False
            venta = None
            costo = None

            if KEY_TOTAL_VENTA in prod_info and isinstance(prod_info[KEY_TOTAL_VENTA], dict):
                venta = safe_float(prod_info[KEY_TOTAL_VENTA].get("valor", 0.0))
                tiene_venta = True

            if KEY_TOTAL_COSTO in prod_info and isinstance(prod_info[KEY_TOTAL_COSTO], dict):
                costo = safe_float(prod_info[KEY_TOTAL_COSTO].get("valor", 0.0))
                tiene_costo = True

            utilidad = None
            margen = None
            if tiene_venta and tiene_costo:
                utilidad = venta - costo
                margen = (utilidad / venta) if venta not in (None, 0) else None

            rows.append({
                "linea": linea,
                "producto_original": producto,
                "producto": normalize_sku_name(producto),
                "tiene_venta": tiene_venta,
                "tiene_costo": tiene_costo,
                "venta": venta,
                "costo": costo,
                "utilidad": utilidad,
                "margen": margen,
            })

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No se pudo construir la tabla de productos.")
    print(f"[OK] Tabla construida con {len(df)} registros.")
    return df


def validate_df(df: pd.DataFrame) -> pd.DataFrame:
    df_valid = df[(df["tiene_venta"]) & (df["tiene_costo"])].copy()
    df_valid = df_valid[df_valid["venta"] > 0].copy()

    print("\n" + "=" * 90)
    print("VALIDACIÓN")
    print("=" * 90)
    print(f"Productos válidos para la matriz : {len(df_valid)}")
    print(f"Con utilidad negativa            : {int((df_valid['utilidad'] < 0).sum())}")

    if df_valid.empty:
        raise RuntimeError("No hay productos válidos para graficar.")
    return df_valid


def classify_quadrants(df: pd.DataFrame) -> pd.DataFrame:
    med_venta = df["venta"].median()
    med_utilidad = df["utilidad"].median()

    def classify(row):
        alta_venta = row["venta"] >= med_venta
        alta_utilidad = row["utilidad"] >= med_utilidad

        if alta_venta and alta_utilidad:
            return "Fuerte del portafolio"
        elif alta_venta and not alta_utilidad:
            return "Tractor de volumen"
        elif not alta_venta and alta_utilidad:
            return "Nicho rentable"
        else:
            return "Debil / revisar"

    df = df.copy()
    df["cuadrante"] = df.apply(classify, axis=1)
    df["mediana_venta"] = med_venta
    df["mediana_utilidad"] = med_utilidad

    print("\n" + "=" * 90)
    print("CLASIFICACIÓN")
    print("=" * 90)
    print(f"Mediana de ventas   : {med_venta:.2f}")
    print(f"Mediana de utilidad : {med_utilidad:.2f}")
    print("\nConteo por cuadrante:")
    print(df["cuadrante"].value_counts().to_string())

    return df


def color_map_for_lines(df: pd.DataFrame):
    lineas = sorted(df["linea"].unique())
    return {linea: f"C{i}" for i, linea in enumerate(lineas)}


def legend_handles(df: pd.DataFrame, color_map: dict):
    lineas = sorted(df["linea"].unique())

    point_handles = [
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor=color_map[linea], markeredgecolor='black',
               markeredgewidth=0.4, markersize=7, label=linea)
        for linea in lineas
    ]

    ref_handles = [
        Line2D([0], [0], color="tab:blue", linestyle="--", linewidth=1.3,
               label="Mediana de ventas / utilidad"),
        Line2D([0], [0], color="tab:blue", linestyle="-", linewidth=1.3,
               label="Utilidad = 0"),
    ]
    return point_handles, ref_handles


def choose_labels_general(df: pd.DataFrame) -> pd.DataFrame:
    parts = [
        df.sort_values("venta", ascending=False).head(8),
        df.sort_values("utilidad", ascending=False).head(8),
        df[df["utilidad"] < 0],
        df[df["cuadrante"] == "Nicho rentable"].sort_values("utilidad", ascending=False).head(8),
    ]
    return pd.concat(parts).drop_duplicates(subset=["linea", "producto"])


def choose_labels_zoom(df: pd.DataFrame, quadrant_name: str) -> pd.DataFrame:
    sub = df[df["cuadrante"] == quadrant_name].copy()

    if quadrant_name == "Fuerte del portafolio":
        return sub.sort_values(["utilidad", "venta"], ascending=[False, False]).copy()

    if quadrant_name == "Nicho rentable":
        return sub.sort_values(["utilidad", "venta"], ascending=[False, False]).copy()

    return sub.copy()


def assign_offsets_by_rank(labels_df: pd.DataFrame) -> pd.DataFrame:
    labels_df = labels_df.copy()

    offset_cycle = [
        (8, 8),
        (10, 14),
        (12, -10),
        (-12, 10),
        (-10, -10),
        (15, 2),
        (3, 16),
        (16, -5),
        (-16, 2),
        (5, -16),
        (-8, 16),
        (18, 10),
    ]

    dxs, dys = [], []
    for i in range(len(labels_df)):
        dx, dy = offset_cycle[i % len(offset_cycle)]
        dxs.append(dx)
        dys.append(dy)

    labels_df["dx"] = dxs
    labels_df["dy"] = dys
    return labels_df


def scatter_by_line(ax, df, color_map):
    for linea in sorted(df["linea"].unique()):
        sub = df[df["linea"] == linea]
        ax.scatter(
            sub["venta"],
            sub["utilidad"],
            s=45,
            alpha=0.88,
            edgecolors="black",
            linewidths=0.4,
            color=color_map[linea],
            zorder=3
        )


def draw_reference_lines(ax, med_venta, med_utilidad):
    ax.axvline(med_venta, linestyle="--", linewidth=1.3, color="tab:blue", zorder=2)
    ax.axhline(med_utilidad, linestyle="--", linewidth=1.3, color="tab:blue", zorder=2)
    ax.axhline(0, linestyle="-", linewidth=1.3, color="tab:blue", zorder=2)


def annotate_points(ax, labels_df):
    for _, row in labels_df.iterrows():
        ax.annotate(
            row["producto"],
            xy=(row["venta"], row["utilidad"]),
            xytext=(row["dx"], row["dy"]),
            textcoords="offset points",
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.78),
            arrowprops=dict(arrowstyle="-", lw=0.6, alpha=0.55),
            zorder=4
        )


def set_axes_style(ax, title):
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=300)
    ax.set_xlabel("Ventas anuales (US$) [escala log]")
    ax.set_ylabel("Utilidad anual (US$) [escala symlog]")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.22, zorder=1)


def add_quadrant_labels_general(ax, med_venta, med_utilidad):
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    x_left = (xmin * med_venta) ** 0.5 if xmin > 0 else med_venta / 2
    x_right = (med_venta * xmax) ** 0.5
    y_top = med_utilidad + 0.28 * (ymax - med_utilidad)
    y_bottom = med_utilidad - 0.28 * (med_utilidad - ymin)

    quad_bbox = dict(boxstyle="round,pad=0.25", fc="white", ec="gray", alpha=0.80)

    ax.text(x_right, y_top, "Fuerte del portafolio", ha="center", va="center", fontsize=10, bbox=quad_bbox)
    ax.text(x_right, y_bottom, "Tractor de volumen", ha="center", va="center", fontsize=10, bbox=quad_bbox)
    ax.text(x_left, y_top, "Nicho rentable", ha="center", va="center", fontsize=10, bbox=quad_bbox)
    ax.text(x_left, y_bottom, "Debil / revisar", ha="center", va="center", fontsize=10, bbox=quad_bbox)


def make_general_page(pdf, df, color_map, point_handles, ref_handles):
    med_venta = df["mediana_venta"].iloc[0]
    med_utilidad = df["mediana_utilidad"].iloc[0]

    fig = plt.figure(figsize=(14, 9))
    ax = fig.add_subplot(111)

    scatter_by_line(ax, df, color_map)
    draw_reference_lines(ax, med_venta, med_utilidad)
    set_axes_style(ax, "Matriz descriptiva por producto: Ventas vs Utilidad (2025)")

    labels_df = choose_labels_general(df)
    labels_df = assign_offsets_by_rank(labels_df)
    annotate_points(ax, labels_df)
    add_quadrant_labels_general(ax, med_venta, med_utilidad)

    legend1 = ax.legend(
        handles=point_handles,
        title="Línea comercial",
        loc="upper left",
        bbox_to_anchor=(1.02, 1.00),
        borderaxespad=0.0
    )
    ax.add_artist(legend1)

    ax.legend(
        handles=ref_handles,
        title="Líneas de referencia",
        loc="upper left",
        bbox_to_anchor=(1.02, 0.72),
        borderaxespad=0.0
    )

    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def make_zoom_page(pdf, df, color_map, point_handles, ref_handles, quadrant_name):
    med_venta = df["mediana_venta"].iloc[0]
    med_utilidad = df["mediana_utilidad"].iloc[0]

    sub = df[df["cuadrante"] == quadrant_name].copy()
    if sub.empty:
        return

    fig = plt.figure(figsize=(14, 9))
    ax = fig.add_subplot(111)

    scatter_by_line(ax, sub, color_map)
    draw_reference_lines(ax, med_venta, med_utilidad)
    set_axes_style(ax, f"Zoom: {quadrant_name} (2025)")

    labels_df = choose_labels_zoom(df, quadrant_name)
    labels_df = assign_offsets_by_rank(labels_df)
    annotate_points(ax, labels_df)

    # Zoom con margen alrededor de los datos del cuadrante
    xmin = sub["venta"].min() * 0.75
    xmax = sub["venta"].max() * 1.35

    ymin = sub["utilidad"].min()
    ymax = sub["utilidad"].max()

    # Márgenes verticales prudentes
    if ymin > 0:
        ymin_plot = ymin * 0.75
    else:
        ymin_plot = ymin * 1.25

    if ymax > 0:
        ymax_plot = ymax * 1.35
    else:
        ymax_plot = ymax * 0.75

    # Evitar problemas si el rango es muy pequeño
    if ymin_plot == ymax_plot:
        ymin_plot = ymin_plot - 1
        ymax_plot = ymax_plot + 1

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin_plot, ymax_plot)

    quad_bbox = dict(boxstyle="round,pad=0.25", fc="white", ec="gray", alpha=0.85)
    ax.text(
        0.03, 0.95,
        f"Panel enfocado en: {quadrant_name}",
        transform=ax.transAxes,
        ha="left", va="top", fontsize=11, bbox=quad_bbox
    )

    legend1 = ax.legend(
        handles=point_handles,
        title="Línea comercial",
        loc="upper left",
        bbox_to_anchor=(1.02, 1.00),
        borderaxespad=0.0
    )
    ax.add_artist(legend1)

    ax.legend(
        handles=ref_handles,
        title="Líneas de referencia",
        loc="upper left",
        bbox_to_anchor=(1.02, 0.72),
        borderaxespad=0.0
    )

    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def export_csv(df: pd.DataFrame, output_csv: str):
    cols = [
        "linea",
        "producto_original",
        "producto",
        "venta",
        "costo",
        "utilidad",
        "margen",
        "cuadrante",
        "mediana_venta",
        "mediana_utilidad",
    ]
    df[cols].sort_values(["cuadrante", "venta"], ascending=[True, False]).to_csv(
        output_csv, index=False, encoding="utf-8"
    )
    print(f"[OK] CSV generado: {Path(output_csv).resolve()}")


def print_summary(df: pd.DataFrame):
    print("\n" + "=" * 90)
    print("RESUMEN")
    print("=" * 90)
    summary = (
        df.groupby("cuadrante")
        .agg(
            n_productos=("producto", "count"),
            ventas_totales=("venta", "sum"),
            utilidad_total=("utilidad", "sum"),
        )
        .reset_index()
        .sort_values("utilidad_total", ascending=False)
    )
    print(summary.to_string(index=False))

    for quad in ["Fuerte del portafolio", "Nicho rentable"]:
        sub = df[df["cuadrante"] == quad].copy()
        if len(sub) > 0:
            print("\n" + "-" * 90)
            print(f"{quad} | Productos")
            print("-" * 90)
            print(
                sub[["linea", "producto", "venta", "costo", "utilidad", "margen"]]
                .sort_values(["utilidad", "venta"], ascending=[False, False])
                .to_string(index=False)
            )


def main():
    OUTPUTS_MATRIZ_CSV.mkdir(parents=True, exist_ok=True)
    OUTPUTS_MATRIZ_PDF.mkdir(parents=True, exist_ok=True)
    
    data = load_json(Path(JSON_FILE))
    df = build_product_df(data)
    df = validate_df(df)
    df = classify_quadrants(df)

    color_map = color_map_for_lines(df)
    point_handles, ref_handles = legend_handles(df, color_map)

    print_summary(df)

    with PdfPages(OUTPUT_PDF) as pdf:
        make_general_page(pdf, df, color_map, point_handles, ref_handles)
        make_zoom_page(pdf, df, color_map, point_handles, ref_handles, "Fuerte del portafolio")
        make_zoom_page(pdf, df, color_map, point_handles, ref_handles, "Nicho rentable")

    print(f"[OK] PDF generado: {Path(OUTPUT_PDF).resolve()}")
    export_csv(df, OUTPUT_CSV)

    print("\n" + "=" * 90)
    print("NOTA METODOLÓGICA")
    print("=" * 90)
    print("1) El panel general da contexto completo.")
    print("2) Los paneles zoom permiten leer mejor los cuadrantes relevantes.")
    print("3) La clasificación sigue siendo descriptiva, no causal.")
    print("4) Las líneas punteadas son medianas; la sólida es utilidad cero.")


if __name__ == "__main__":
    main()