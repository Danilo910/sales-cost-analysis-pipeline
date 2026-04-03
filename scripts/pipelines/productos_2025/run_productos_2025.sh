#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "============================================================"
echo "PIPELINE: productos_2025"
echo "PROJECT_ROOT: ${PROJECT_ROOT}"
echo "============================================================"

cd "${PROJECT_ROOT}"

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "[ERROR] No se encontró .venv/bin/activate en el project root."
  exit 1
fi

source .venv/bin/activate

echo "[1/3] Build nested dict (Excel -> JSON compartido)"
python scripts/pipelines/productos_2025/utils/build_nested_dict.py

echo "[2/3] Plots por línea / productos"
python scripts/pipelines/productos_2025/plots/Plots_Products.py

echo "[3/3] Plots agregados por línea"
python scripts/pipelines/productos_2025/plots/Plots_Utilities_2025.py

echo "------------------------------------------------------------"
echo "[OK] Pipeline productos_2025 completado."
echo "------------------------------------------------------------"
