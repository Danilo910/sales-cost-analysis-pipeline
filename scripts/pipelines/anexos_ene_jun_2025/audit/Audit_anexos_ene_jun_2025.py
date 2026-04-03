#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audit_anexos_ene_jun_2025.py

Auditoría cuantitativa del input sintético de anexos (Enero-Junio 2025).

Nueva lógica
------------
- YA NO usa datos hardcodeados dentro del script.
- Lee el JSON generado desde el XLSX:
    inputs/raw/anexos_ene_jun_2025/anexos_ene_jun_2025_extraido_desde_xlsx.json
- Conserva la lógica matemática esencial del antiguo empresa_HYM.py:
    * estructura por líneas y zonas
    * cálculo de shares
    * HHI
    * entropía de Shannon
    * número efectivo
    * ratio share margen / share facturación
    * tablas impresas en consola
    * exportación de CSV

Este script sigue siendo de tipo "audit":
- imprime resultados técnicos en consola
- exporta CSV
- opcionalmente puede mostrar gráficos si se activa el flag correspondiente

Requisitos:
    pip install numpy pandas matplotlib
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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
OUTPUTS_CSV = PROJECT_ROOT / "outputs" / "anexos_ene_jun_2025" / "csv"

INPUT_JSON = INPUTS_RAW / "anexos_ene_jun_2025_extraido_desde_xlsx.json"
OUTPUT_CSV_LINEAS = OUTPUTS_CSV / "mix_lineas_ene_jun_2025.csv"
OUTPUT_CSV_ZONAS = OUTPUTS_CSV / "ventas_zonas_ene_jun_2025.csv"

# ============================================================
# DEFINICIONES OPERATIVAS
# ============================================================
LINE_DEFINITIONS = {
    "Linea_A": {
        "descripcion": "Categoría sintética Linea_A.",
        "hipotesis_operativa": "Se usa solo para demostración del pipeline."
    },
    "Linea_B": {
        "descripcion": "Categoría sintética Linea_B.",
        "hipotesis_operativa": "Se usa solo para demostración del pipeline."
    },
    "Linea_C": {
        "descripcion": "Categoría sintética Linea_C.",
        "hipotesis_operativa": "Se usa solo para demostración del pipeline."
    },
    "Linea_D": {
        "descripcion": "Categoría sintética Linea_D.",
        "hipotesis_operativa": "Se usa solo para demostración del pipeline."
    },
}


# ============================================================
# CARGA DE DATOS
# ============================================================
def ensure_dirs() -> None:
    OUTPUTS_CSV.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el JSON de entrada: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def validate_input_schema(data: Dict[str, Any]) -> None:
    required_top = ["totales", "lineas", "zonas"]
    for key in required_top:
        if key not in data:
            raise KeyError(f"Falta la clave requerida en el JSON: '{key}'")

    if not isinstance(data["totales"], dict):
        raise TypeError("La clave 'totales' debe ser un diccionario.")
    if not isinstance(data["lineas"], list):
        raise TypeError("La clave 'lineas' debe ser una lista.")
    if not isinstance(data["zonas"], list):
        raise TypeError("La clave 'zonas' debe ser una lista.")

    for key in ["facturacion_usd", "margen_usd"]:
        if key not in data["totales"]:
            raise KeyError(f"Falta '{key}' dentro de 'totales'.")

    required_line_fields = {"linea", "facturacion_pct", "margen_pct"}
    for i, row in enumerate(data["lineas"]):
        missing = required_line_fields - set(row.keys())
        if missing:
            raise KeyError(f"Fila {i} de 'lineas' incompleta. Faltan: {sorted(missing)}")

    required_zone_fields = {"zona", "ventas_usd", "ventas_pct"}
    for i, row in enumerate(data["zonas"]):
        missing = required_zone_fields - set(row.keys())
        if missing:
            raise KeyError(f"Fila {i} de 'zonas' incompleta. Faltan: {sorted(missing)}")


def build_dataframes_from_json(data: Dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    total_facturacion_usd = int(data["totales"]["facturacion_usd"])
    total_margen_usd = int(data["totales"]["margen_usd"])

    df_lines = pd.DataFrame(data["lineas"]).copy()
    df_zones = pd.DataFrame(data["zonas"]).copy()

    expected_line_order = ["Linea_A", "Linea_B", "Linea_C", "Linea_D"]
    found_lines = df_lines["linea"].tolist()
    if sorted(found_lines) != sorted(expected_line_order):
        raise ValueError(
            f"Líneas inesperadas en JSON. Esperado: {expected_line_order}. "
            f"Encontrado: {found_lines}"
        )

    return df_lines, df_zones, total_facturacion_usd, total_margen_usd


# ============================================================
# FUNCIONES MATEMÁTICAS
# ============================================================
def hhi(shares: np.ndarray) -> float:
    s = np.array(shares, dtype=float)
    s = s[np.isfinite(s) & (s > 0)]
    if s.size == 0:
        return float("nan")
    s = s / s.sum()
    return float(np.sum(s ** 2))


def shannon_entropy(shares: np.ndarray) -> float:
    s = np.array(shares, dtype=float)
    s = s[np.isfinite(s) & (s > 0)]
    if s.size == 0:
        return float("nan")
    s = s / s.sum()
    return float(-np.sum(s * np.log(s)))


def effective_number(hhi_value: float) -> float:
    if not np.isfinite(hhi_value) or hhi_value <= 0:
        return float("nan")
    return 1.0 / hhi_value


# ============================================================
# CONSTRUCCIÓN DE INDICADORES
# ============================================================
def build_indicators(
    df_lines: pd.DataFrame,
    df_zones: pd.DataFrame,
    total_facturacion_usd: int,
    total_margen_usd: int,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    dfL = df_lines.copy()
    dfL["share_facturacion"] = dfL["facturacion_pct"] / 100.0
    dfL["share_margen"] = dfL["margen_pct"] / 100.0

    dfL["facturacion_usd_aprox"] = dfL["share_facturacion"] * total_facturacion_usd
    dfL["margen_usd_aprox"] = dfL["share_margen"] * total_margen_usd

    hhi_fact = hhi(dfL["share_facturacion"].to_numpy())
    ent_fact = shannon_entropy(dfL["share_facturacion"].to_numpy())
    out["lineas_hhi_facturacion"] = hhi_fact
    out["lineas_entropia_facturacion"] = ent_fact
    out["lineas_numero_efectivo_facturacion"] = effective_number(hhi_fact)

    hhi_m = hhi(dfL["share_margen"].to_numpy())
    ent_m = shannon_entropy(dfL["share_margen"].to_numpy())
    out["lineas_hhi_margen"] = hhi_m
    out["lineas_entropia_margen"] = ent_m
    out["lineas_numero_efectivo_margen"] = effective_number(hhi_m)

    dfL["ratio_share_margen_sobre_fact"] = (
        dfL["share_margen"] / dfL["share_facturacion"]
    )

    dfZ = df_zones.copy()
    dfZ["share_ventas"] = dfZ["ventas_pct"] / 100.0

    hhi_z = hhi(dfZ["share_ventas"].to_numpy())
    ent_z = shannon_entropy(dfZ["share_ventas"].to_numpy())
    out["zonas_hhi_ventas"] = hhi_z
    out["zonas_entropia_ventas"] = ent_z
    out["zonas_numero_efectivo_ventas"] = effective_number(hhi_z)

    out["df_lineas"] = dfL.sort_values("facturacion_pct", ascending=False).reset_index(drop=True)
    out["df_zonas"] = dfZ.sort_values("ventas_usd", ascending=False).reset_index(drop=True)

    return out


# ============================================================
# VALIDACIONES DE CONSISTENCIA
# ============================================================
def print_basic_validations(
    df_lines: pd.DataFrame,
    df_zones: pd.DataFrame,
    total_facturacion_usd: int,
    total_margen_usd: int,
) -> None:
    print("\n--- Validaciones básicas de consistencia ---")
    print(f"Suma facturacion_pct líneas: {df_lines['facturacion_pct'].sum():.1f}")
    print(f"Suma margen_pct líneas     : {df_lines['margen_pct'].sum():.1f}")
    print(f"Suma ventas_pct zonas      : {df_zones['ventas_pct'].sum():.1f}")
    print(f"Suma ventas_usd zonas      : {int(df_zones['ventas_usd'].sum())}")
    print(f"Total facturación anexo    : {total_facturacion_usd}")
    print(f"Total margen anexo         : {total_margen_usd}")

    if not np.isclose(df_lines["facturacion_pct"].sum(), 100.0, atol=0.2):
        print("[ADVERTENCIA] facturacion_pct de líneas no suma ~100.")
    if not np.isclose(df_lines["margen_pct"].sum(), 100.0, atol=0.2):
        print("[ADVERTENCIA] margen_pct de líneas no suma ~100.")
    if not np.isclose(df_zones["ventas_pct"].sum(), 99.9, atol=0.2) and not np.isclose(
        df_zones["ventas_pct"].sum(), 100.0, atol=0.2
    ):
        print("[ADVERTENCIA] ventas_pct de zonas no suma ~100.")
    sum_zonas_usd = int(df_zones["ventas_usd"].sum())
    sum_zonas_pct = df_zones["ventas_pct"].sum()

    print(f"Suma ventas_usd zonas      : {sum_zonas_usd}")
    print(f"Total facturación anexo    : {total_facturacion_usd}")

    if not np.isclose(sum_zonas_pct, 100.0, atol=0.2) and not np.isclose(sum_zonas_pct, 99.9, atol=0.2):
        print("[ADVERTENCIA] ventas_pct de zonas no suma ~100.")

    # Validación interna del cuadro de zonas:
    implied_total_from_zones = []
    for _, row in df_zones.iterrows():
        if row["ventas_pct"] > 0:
            implied_total_from_zones.append(row["ventas_usd"] / (row["ventas_pct"] / 100.0))

    if implied_total_from_zones:
        mean_implied_total = np.mean(implied_total_from_zones)
        print(f"Total implícito del cuadro de zonas (aprox.): {mean_implied_total:.0f}")

    if abs(sum_zonas_usd - total_facturacion_usd) > 1:
        print("[NOTA] El cuadro de zonas parece usar una base total distinta al total de facturación del cuadro por líneas.")


# ============================================================
# IMPRESIÓN Y EXPORTACIÓN
# ============================================================
def print_line_definitions() -> None:
    print("Definiciones operativas de líneas (EDITABLES):\n")
    for k, v in LINE_DEFINITIONS.items():
        print(f"- {k}: {v['descripcion']}")
        print(f"  Hipótesis/interpretación: {v['hipotesis_operativa']}\n")


def print_results(res: Dict[str, Any]) -> None:
    dfL = res["df_lineas"]
    dfZ = res["df_zonas"]

    print("Tabla por LÍNEA (con shares y montos aproximados):\n")
    print(dfL.to_string(index=False))

    print("\nTabla por ZONA:\n")
    print(dfZ.to_string(index=False))

    print("\n--- Métricas de concentración/diversificación ---")
    print(f"HHI (líneas, facturación): {res['lineas_hhi_facturacion']:.4f}")
    print(f"N_eff (líneas, facturación) = 1/HHI: {res['lineas_numero_efectivo_facturacion']:.2f}")
    print(f"Entropía (líneas, facturación): {res['lineas_entropia_facturacion']:.4f}\n")

    print(f"HHI (líneas, margen): {res['lineas_hhi_margen']:.4f}")
    print(f"N_eff (líneas, margen) = 1/HHI: {res['lineas_numero_efectivo_margen']:.2f}")
    print(f"Entropía (líneas, margen): {res['lineas_entropia_margen']:.4f}\n")

    print(f"HHI (zonas, ventas): {res['zonas_hhi_ventas']:.4f}")
    print(f"N_eff (zonas, ventas) = 1/HHI: {res['zonas_numero_efectivo_ventas']:.2f}")
    print(f"Entropía (zonas, ventas): {res['zonas_entropia_ventas']:.4f}")

    print("\n--- Interpretación matemática (sin cuentos) ---")
    print("* HHI cercano a 1 implica concentración fuerte; cercano a 1/N implica reparto uniforme.")
    print("* N_eff = 1/HHI se interpreta como cuántas categorías equivalentes tendrías si fueran iguales.")
    print("* Entropía mayor implica mayor diversidad de shares.\n")

    print("Indicador ratio_share_margen_sobre_fact (por línea):")
    print("- > 1: la línea aporta proporcionalmente más margen que facturación.")
    print("- < 1: aporta proporcionalmente menos margen que facturación.\n")
    print(dfL[["linea", "ratio_share_margen_sobre_fact"]].to_string(index=False))


def export_csvs(dfL: pd.DataFrame, dfZ: pd.DataFrame) -> None:
    dfL.to_csv(OUTPUT_CSV_LINEAS, index=False, encoding="utf-8")
    dfZ.to_csv(OUTPUT_CSV_ZONAS, index=False, encoding="utf-8")

    print("\nCSV exportados:")
    print(f"- {OUTPUT_CSV_LINEAS.resolve()}")
    print(f"- {OUTPUT_CSV_ZONAS.resolve()}")


# ============================================================
# GRÁFICOS OPCIONALES
# ============================================================
def plot_bars(df: pd.DataFrame, xcol: str, ycol: str, title: str, ylabel: str, rotate_x: bool = False) -> None:
    plt.figure()
    plt.bar(df[xcol], df[ycol])
    plt.title(title)
    plt.xlabel(xcol)
    plt.ylabel(ylabel)
    if rotate_x:
        plt.xticks(rotation=30, ha="right")
    plt.grid(True, axis="y")
    plt.tight_layout()
    plt.show()


def maybe_plot(res: Dict[str, Any], enable_plots: bool = False) -> None:
    if not enable_plots:
        return

    dfL = res["df_lineas"]
    dfZ = res["df_zonas"]

    plot_bars(
        dfL, "linea", "facturacion_pct",
        "Mix por línea (% facturación) Ene-Jun 2025", "% facturación", rotate_x=False
    )
    plot_bars(
        dfL, "linea", "margen_pct",
        "Mix por línea (% margen, según anexo) Ene-Jun 2025", "% margen", rotate_x=False
    )
    plot_bars(
        dfZ, "zona", "ventas_usd",
        "Ventas por zona (US$) Ene-Jun 2025", "Ventas (US$)", rotate_x=True
    )
    plot_bars(
        dfZ, "zona", "ventas_pct",
        "Ventas por zona (% total) Ene-Jun 2025", "% ventas", rotate_x=True
    )


# ============================================================
# MAIN
# ============================================================
def main(enable_plots: bool = False) -> None:
    ensure_dirs()

    print("\n==============================")
    print("AUDITORÍA ANEXOS Ene-Jun 2025")
    print("==============================\n")

    print(f"JSON de entrada: {INPUT_JSON.resolve()}\n")

    data = load_json(INPUT_JSON)
    validate_input_schema(data)

    df_lines, df_zones, total_facturacion_usd, total_margen_usd = build_dataframes_from_json(data)

    print_line_definitions()
    print_basic_validations(df_lines, df_zones, total_facturacion_usd, total_margen_usd)

    res = build_indicators(
        df_lines=df_lines,
        df_zones=df_zones,
        total_facturacion_usd=total_facturacion_usd,
        total_margen_usd=total_margen_usd,
    )

    print()
    print_results(res)
    export_csvs(res["df_lineas"], res["df_zonas"])
    maybe_plot(res, enable_plots=enable_plots)


if __name__ == "__main__":
    main(enable_plots=False)