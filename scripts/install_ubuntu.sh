#!/usr/bin/env bash
set -euo pipefail

# Ubuntu setup script for BioGeneticBackend
# - Creates Python venv
# - Installs Python deps (including Playwright)
# - Installs system deps for Playwright on Ubuntu
# - Downloads Chromium for Playwright
# - (Optional) Runs Alembic migrations and starts the API

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
VENV_DIR="${PROJECT_DIR}/venv"

echo "[1/7] Updating apt cache and installing base packages..."
sudo apt-get update -y
sudo apt-get install -y \
  python3 python3-venv python3-pip \
  build-essential ca-certificates curl git

echo "[2/7] Creating Python virtual environment..."
if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip wheel

echo "[3/7] Installing Python dependencies..."
python -m pip install -r "${PROJECT_DIR}/requirements.txt"

echo "[4/7] Installing Playwright OS dependencies (Ubuntu)..."
# Installs required system libraries for running browsers headless
python -m playwright install-deps || true

echo "[5/7] Downloading Playwright Chromium browser..."
python -m playwright install chromium

echo "[6/7] (Optional) Running Alembic migrations..."
if [[ "${RUN_MIGRATIONS:-1}" == "1" ]]; then
  if [[ -f "${PROJECT_DIR}/alembic.ini" ]]; then
    alembic -c "${PROJECT_DIR}/alembic.ini" upgrade head || true
  fi
fi

echo "[7/7] Done. To run the API locally:"
cat <<'EOT'

source venv/bin/activate
python main.py

# Or with Uvicorn directly (if preferred):
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# After the server is running, you can test PDF generation:
#   GET http://localhost:8000/api/informes/produccion/{produccion_id}/html
#   GET http://localhost:8000/api/informes/produccion/{produccion_id}/pdf

EOT

echo "Setup completed successfully."

