#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "============================================================"
echo "PIPELINE: matriz_ventas_2025"
echo "PROJECT_ROOT: ${PROJECT_ROOT}"
echo "============================================================"

cd "${PROJECT_ROOT}"

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "[ERROR] No se encontró .venv/bin/activate en el project root."
  exit 1
fi

source .venv/bin/activate

echo "[1/3] Build nested dict (Excel -> JSON)"
python scripts/pipelines/matriz_ventas_2025/utils/build_nested_dict.py

echo "[2/3] Audit JSON productos"
python scripts/pipelines/matriz_ventas_2025/audit/Audit_JSON_Productos_2025.py

echo "[3/3] Matriz multipanel"
python scripts/pipelines/matriz_ventas_2025/plots/Matriz_Ventas_Utilidad_2025_Multipanel.py

echo "------------------------------------------------------------"
echo "[OK] Pipeline matriz_ventas_2025 completado."
echo "------------------------------------------------------------"
