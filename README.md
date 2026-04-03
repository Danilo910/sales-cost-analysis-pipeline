# Sales-Cost Analysis 2025

This repository contains the modular processing and reporting system used to analyze sales, costs, margins, labels, and product documentation for for a fictitious company (the analysis was performed on a real agrochemical company, but we will not publish data from it) during the 2025 fiscal year.

The project has been refactored into reproducible pipeline-based components with a clear separation between:

- active pipeline inputs
- generated outputs
- final human-readable reports
- contextual documentation
- historical backups

---

## Project Structure

```text
.
├── archive/
│   └── back_up/                     # historical frozen copy of the old architecture
├── docs/                            # contextual material, theory, meetings, reference PDFs
│   └── theory/
├── inputs/
│   ├── raw/                         # active raw/intermediate pipeline inputs
│   └── static_company/              # company-provided static inputs
├── outputs/
│   ├── anexos_ene_jun_2025/
│   ├── matriz_ventas_2025/
│   └── productos_2025/
├── reports/
│   ├── compiled_pdf/                # final compiled reports
├── scripts/
│   └── pipelines/                   # active executable pipeline logic
├── README.md
└── requirements.txt
```

---

## Active Pipelines

### 1. `anexos_ene_jun_2025`
Processes the ANEXOS company PDF, validates extracted values against a canonical external reference, generates audit CSVs, plots, and a final compiled report.

Main runner:

```bash
bash scripts/pipelines/anexos_ene_jun_2025/run_anexos_ene_jun_2025.sh
```

Outputs:
- `outputs/anexos_ene_jun_2025/...`
- `reports/compiled_pdf/anexos/...`

---

### 2. `matriz_ventas_2025`
Builds the shared nested JSON from the company Excel file, audits the product dataset, and generates the multipanel sales-utility matrix.

Main runner:

```bash
bash scripts/pipelines/matriz_ventas_2025/run_matriz_ventas_2025.sh
```

Outputs:
- `outputs/matriz_ventas_2025/...`

---

### 3. `productos_2025`
Generates line-level product PDFs and utility/cost-vs-sales aggregate plots from the shared JSON.

Main runner:

```bash
bash scripts/pipelines/productos_2025/run_productos_2025.sh
```

Outputs:
- `outputs/productos_2025/pdf/...`


## Inputs

### Static company inputs
Located in:

```text
inputs/static_company/
```

Includes:
- company PDF documents
- Excel source files

### External inputs
Located in:

```text
inputs/external/
```

Includes:
- canonical external JSON references used for validation

### Raw/shared active inputs
Located in:

```text
inputs/raw/
```

Includes:
- extracted intermediate JSONs
- shared nested dictionaries used by multiple pipelines

---

## Reports

### Compiled final reports
Located in:

```text
reports/compiled_pdf/
```

## Contextual Documentation

Located in:

```text
docs/
```

Includes:
- theory notes

These files are not active pipeline inputs unless explicitly copied into `inputs/`.

---

## Historical Backup Policy

The folder

```text
archive/back_up/
```

contains the preserved pre-refactor architecture.

No active pipeline should depend on `archive/`.

It exists only for:
- traceability
- rollback reference
- historical inspection

---

## Environment Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Run All Pipelines

You can run the four active pipelines sequentially using a single shell script.

Suggested command:

```bash
bash run_all_pipelines.sh
```

---

## Reproducibility Notes

- Python-based pipelines are reproducible from the repository root.
- Overleaf/LaTeX report projects are external or partially external execution nodes.
- Static company inputs are intentionally separated from generated outputs.
- Historical backup material is preserved but inactive.

---

## Author

Danilo Zegarra Herrera
