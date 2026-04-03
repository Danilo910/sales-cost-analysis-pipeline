#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audit_JSON_Productos_2025.py

Audita la integridad del JSON de productos 2025 para verificar:

a) que todos los productos tengan TOTAL_VENTA y TOTAL_COSTO
b) que los nombres de producto/SKU no estén contaminados por inconsistencias
c) que utilidades negativas se detecten y se revisen
d) que el análisis posterior sea descriptivo, no causal

Salida:
- prints detallados en consola
- CSV con tabla auditada
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

from collections import defaultdict

import pandas as pd

JSON_FILE = INPUTS_RAW_SHARED / "diccionario_ventas_costos_2025.json"
OUTPUT_CSV = OUTPUTS_MATRIZ_CSV / "auditoria_productos_2025.csv"

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
    """
    Normalización simple para detectar posibles duplicados contaminados:
    - strip
    - mayúsculas
    - colapsar espacios múltiples
    """
    if name is None:
        return ""
    s = str(name).strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s


def load_json(path: Path) -> dict:
    print("=" * 80)
    print("AUDITORÍA DEL JSON DE PRODUCTOS 2025")
    print("=" * 80)
    print(f"Directorio actual           : {Path('.').resolve()}")
    print(f"Archivo JSON esperado       : {path.resolve()}")

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo JSON: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n[OK] JSON cargado correctamente.")
    print(f"Número de líneas detectadas : {len(data)}")
    print("Líneas encontradas          :", list(data.keys()))
    return data


def inspect_sample_structure(data: dict):
    print("\n" + "=" * 80)
    print("MUESTRA DE ESTRUCTURA DEL JSON")
    print("=" * 80)

    for linea, productos in data.items():
        print(f"\nLínea de muestra: {linea}")
        if not isinstance(productos, dict):
            print("  [ADVERTENCIA] Esta línea no contiene un diccionario de productos.")
            continue

        if len(productos) == 0:
            print("  [ADVERTENCIA] Esta línea no contiene productos.")
            continue

        primer_producto = next(iter(productos))
        prod_info = productos[primer_producto]

        print(f"Producto de muestra         : {primer_producto}")
        if not isinstance(prod_info, dict):
            print("  [ADVERTENCIA] El producto no contiene un diccionario interno.")
            continue

        keys = list(prod_info.keys())
        print(f"Primeras claves del producto: {keys[:15]}")
        print(f"¿Existe {KEY_TOTAL_VENTA}?   : {KEY_TOTAL_VENTA in prod_info}")
        print(f"¿Existe {KEY_TOTAL_COSTO}?   : {KEY_TOTAL_COSTO in prod_info}")
        break


def build_product_df(data: dict) -> pd.DataFrame:
    rows = []

    for linea, productos in data.items():
        if not isinstance(productos, dict):
            print(f"[ADVERTENCIA] La línea '{linea}' no es un diccionario. Se omite.")
            continue

        for producto, prod_info in productos.items():
            if not isinstance(prod_info, dict):
                print(f"[ADVERTENCIA] Producto '{producto}' en línea '{linea}' no es un dict. Se omite.")
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
                "producto_normalizado": normalize_sku_name(producto),
                "tiene_venta": tiene_venta,
                "tiene_costo": tiene_costo,
                "venta": venta,
                "costo": costo,
                "utilidad": utilidad,
                "margen": margen,
            })

    df = pd.DataFrame(rows)

    if df.empty:
        raise RuntimeError("No se pudo construir la tabla de productos. Revisa el JSON.")

    return df


def report_basic_counts(df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("RESUMEN GENERAL DE PRODUCTOS")
    print("=" * 80)

    print(f"Total de registros de producto                : {len(df)}")
    print(f"Productos con TOTAL_VENTA                     : {int(df['tiene_venta'].sum())}")
    print(f"Productos con TOTAL_COSTO                     : {int(df['tiene_costo'].sum())}")
    print(f"Productos con ambos (venta y costo)           : {int((df['tiene_venta'] & df['tiene_costo']).sum())}")
    print(f"Productos sin TOTAL_VENTA                     : {int((~df['tiene_venta']).sum())}")
    print(f"Productos sin TOTAL_COSTO                     : {int((~df['tiene_costo']).sum())}")
    print(f"Productos con datos completos para utilidad   : {int(df['utilidad'].notna().sum())}")


def report_missing_values(df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("CHEQUEO A) PRODUCTOS CON FALTANTES")
    print("=" * 80)

    missing_venta = df[~df["tiene_venta"]].copy()
    missing_costo = df[~df["tiene_costo"]].copy()
    missing_any = df[(~df["tiene_venta"]) | (~df["tiene_costo"])].copy()

    print(f"Cantidad sin TOTAL_VENTA  : {len(missing_venta)}")
    print(f"Cantidad sin TOTAL_COSTO  : {len(missing_costo)}")
    print(f"Cantidad con algún faltante: {len(missing_any)}")

    if len(missing_any) == 0:
        print("[OK] Todos los productos tienen TOTAL_VENTA y TOTAL_COSTO.")
    else:
        print("\n[ADVERTENCIA] Hay productos incompletos. Primeros casos:")
        cols = ["linea", "producto_original", "tiene_venta", "tiene_costo", "venta", "costo"]
        print(missing_any[cols].head(20).to_string(index=False))


def report_by_line(df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("RESUMEN POR LÍNEA")
    print("=" * 80)

    grouped = df.groupby("linea").agg(
        n_productos=("producto_original", "count"),
        con_venta=("tiene_venta", "sum"),
        con_costo=("tiene_costo", "sum"),
        venta_total=("venta", "sum"),
        costo_total=("costo", "sum"),
    ).reset_index()

    grouped["con_ambos"] = df.groupby("linea").apply(
        lambda x: int((x["tiene_venta"] & x["tiene_costo"]).sum())
    ).values
    grouped["utilidad_total"] = grouped["venta_total"] - grouped["costo_total"]

    print(grouped.to_string(index=False))


def report_sku_inconsistencies(df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("CHEQUEO B) POSIBLES INCONSISTENCIAS EN NOMBRES DE SKU")
    print("=" * 80)

    # 1. nombres con espacios raros
    weird_spaces = df[
        (df["producto_original"].str.startswith(" ", na=False)) |
        (df["producto_original"].str.endswith(" ", na=False)) |
        (df["producto_original"].str.contains(r"\s{2,}", regex=True, na=False))
    ].copy()

    print(f"Productos con espacios sospechosos: {len(weird_spaces)}")
    if len(weird_spaces) > 0:
        print(weird_spaces[["linea", "producto_original"]].drop_duplicates().head(20).to_string(index=False))

    # 2. posibles duplicados normalizados
    dup_norm = (
        df.groupby("producto_normalizado")["producto_original"]
        .nunique()
        .reset_index(name="n_variantes")
    )
    dup_norm = dup_norm[dup_norm["n_variantes"] > 1].copy()

    print(f"\nNormalizados con más de una variante original: {len(dup_norm)}")

    if len(dup_norm) == 0:
        print("[OK] No se detectaron variantes obvias del mismo SKU por formato.")
    else:
        print("[ADVERTENCIA] Posibles nombres contaminados por formato:")
        for _, row in dup_norm.iterrows():
            norm = row["producto_normalizado"]
            variants = sorted(df.loc[df["producto_normalizado"] == norm, "producto_original"].unique())
            print(f"\nSKU normalizado: {norm}")
            for v in variants:
                print(f"   - {repr(v)}")

    # 3. mismo producto normalizado en varias líneas
    multi_line = (
        df.groupby("producto_normalizado")["linea"]
        .nunique()
        .reset_index(name="n_lineas")
    )
    multi_line = multi_line[multi_line["n_lineas"] > 1].copy()

    print(f"\nSKUs normalizados presentes en más de una línea: {len(multi_line)}")
    if len(multi_line) > 0:
        print("Esto no es necesariamente error, pero conviene revisar si son comparables o duplicados.")
        for _, row in multi_line.head(20).iterrows():
            norm = row["producto_normalizado"]
            lineas = sorted(df.loc[df["producto_normalizado"] == norm, "linea"].unique())
            originals = sorted(df.loc[df["producto_normalizado"] == norm, "producto_original"].unique())
            print(f"\nSKU normalizado: {norm}")
            print(f"  Líneas       : {lineas}")
            print(f"  Variantes    : {originals}")


def report_negative_profit(df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("CHEQUEO C) UTILIDADES NEGATIVAS O SOSPECHOSAS")
    print("=" * 80)

    valid = df[df["utilidad"].notna()].copy()

    negative = valid[valid["utilidad"] < 0].copy()
    zero_profit = valid[valid["utilidad"] == 0].copy()
    zero_sales_positive_cost = valid[(valid["venta"] == 0) & (valid["costo"] > 0)].copy()
    zero_cost_positive_sales = valid[(valid["costo"] == 0) & (valid["venta"] > 0)].copy()

    print(f"Productos con utilidad negativa           : {len(negative)}")
    print(f"Productos con utilidad exactamente cero   : {len(zero_profit)}")
    print(f"Productos con venta=0 y costo>0           : {len(zero_sales_positive_cost)}")
    print(f"Productos con costo=0 y venta>0           : {len(zero_cost_positive_sales)}")

    if len(negative) == 0:
        print("[OK] No se detectaron utilidades negativas.")
    else:
        print("\n[ADVERTENCIA] Revisar si estos casos son reales o errores de carga:")
        cols = ["linea", "producto_original", "venta", "costo", "utilidad", "margen"]
        print(negative[cols].sort_values("utilidad").head(30).to_string(index=False))

    if len(zero_sales_positive_cost) > 0:
        print("\n[ADVERTENCIA] Casos con venta=0 y costo>0:")
        print(zero_sales_positive_cost[["linea", "producto_original", "venta", "costo", "utilidad"]]
              .head(20).to_string(index=False))

    if len(zero_cost_positive_sales) > 0:
        print("\n[ADVERTENCIA] Casos con costo=0 y venta>0:")
        print(zero_cost_positive_sales[["linea", "producto_original", "venta", "costo", "utilidad"]]
              .head(20).to_string(index=False))


def report_descriptive_scope(df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("CHEQUEO D) ALCANCE DEL ANÁLISIS")
    print("=" * 80)

    print("Este dataset permite análisis DESCRIPTIVO por producto usando:")
    print("  - venta")
    print("  - costo")
    print("  - utilidad = venta - costo")
    print("  - margen = utilidad / venta")
    print("\nPero NO permite inferir causalidad sobre por qué un producto vende más.")
    print("No hay aquí variables de:")
    print("  - inventario")
    print("  - reposición")
    print("  - rotación real")
    print("  - quiebres de stock por fecha")
    print("  - cobranza por SKU")
    print("  - demanda observada por tienda")
    print("\nConclusión metodológica:")
    print("  Cualquier matriz posterior será descriptiva del desempeño observado, no causal.")


def report_top_products(df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("TOP PRODUCTOS PARA INSPECCIÓN RÁPIDA")
    print("=" * 80)

    valid = df[df["utilidad"].notna()].copy()

    print("\nTop 15 por ventas:")
    print(valid[["linea", "producto_original", "venta", "costo", "utilidad"]]
          .sort_values("venta", ascending=False)
          .head(15)
          .to_string(index=False))

    print("\nTop 15 por utilidad:")
    print(valid[["linea", "producto_original", "venta", "costo", "utilidad"]]
          .sort_values("utilidad", ascending=False)
          .head(15)
          .to_string(index=False))

    print("\nBottom 15 por utilidad:")
    print(valid[["linea", "producto_original", "venta", "costo", "utilidad"]]
          .sort_values("utilidad", ascending=True)
          .head(15)
          .to_string(index=False))


def export_csv(df: pd.DataFrame, output_csv: str):
    df.to_csv(output_csv, index=False, encoding="utf-8")
    print("\n" + "=" * 80)
    print("EXPORTACIÓN")
    print("=" * 80)
    print(f"[OK] CSV auditado generado: {Path(output_csv).resolve()}")


def main():
    OUTPUTS_MATRIZ_CSV.mkdir(parents=True, exist_ok=True)
    data = load_json(Path(JSON_FILE))
    inspect_sample_structure(data)

    df = build_product_df(data)

    report_basic_counts(df)
    report_missing_values(df)
    report_by_line(df)
    report_sku_inconsistencies(df)
    report_negative_profit(df)
    report_descriptive_scope(df)
    report_top_products(df)
    export_csv(df, OUTPUT_CSV)

    print("\n" + "=" * 80)
    print("FIN DE LA AUDITORÍA")
    print("=" * 80)
    print("Siguiente paso razonable:")
    print("1) revisar faltantes")
    print("2) revisar variantes de nombre sospechosas")
    print("3) revisar utilidades negativas")
    print("4) recién luego construir la matriz ventas-utilidad")


if __name__ == "__main__":
    main()