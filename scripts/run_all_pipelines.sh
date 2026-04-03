#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "============================================================"
echo "RUNNING ALL ACTIVE HYM PIPELINES"
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "============================================================"

if [[ -d ".venv" ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
    echo "[OK] Virtual environment activated."
else
    echo "[WARNING] .venv not found. Running with system Python."
fi

run_step() {
    local label="$1"
    local script_path="$2"

    echo
    echo "------------------------------------------------------------"
    echo "[RUN] $label"
    echo "SCRIPT: $script_path"
    echo "------------------------------------------------------------"

    bash "$script_path"

    echo "[OK] Completed: $label"
}

run_step "anexos_ene_jun_2025"     "scripts/pipelines/anexos_ene_jun_2025/run_anexos_ene_jun_2025.sh"

run_step "matriz_ventas_2025"     "scripts/pipelines/matriz_ventas_2025/run_matriz_ventas_2025.sh"

run_step "productos_2025"     "scripts/pipelines/productos_2025/run_productos_2025.sh"

echo
echo "============================================================"
echo "[OK] ALL ACTIVE PIPELINES COMPLETED SUCCESSFULLY"
echo "============================================================"
