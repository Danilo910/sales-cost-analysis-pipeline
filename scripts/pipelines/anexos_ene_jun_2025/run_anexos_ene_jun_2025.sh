#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "============================================================"
echo "PIPELINE: anexos_ene_jun_2025"
echo "PROJECT_ROOT: ${PROJECT_ROOT}"
echo "============================================================"

cd "${PROJECT_ROOT}"

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "[ERROR] No se encontró .venv/bin/activate en el project root."
  exit 1
fi

source .venv/bin/activate

echo "[1/3] Extract + validate PDF -> JSON"
python scripts/pipelines/anexos_ene_jun_2025/utils/extract_validate_anexos_xlsx_to_json.py

echo "[2/3] Audit"
python scripts/pipelines/anexos_ene_jun_2025/audit/Audit_anexos_ene_jun_2025.py

echo "[3/3] Report"
python scripts/pipelines/anexos_ene_jun_2025/reports/analisis_anexos_ene_jun_2025.py

echo "------------------------------------------------------------"
echo "[OK] Pipeline anexos_ene_jun_2025 completado."
echo "------------------------------------------------------------"
