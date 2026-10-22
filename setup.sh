#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo "  ICEBERG // Price Radar — Setup Completo (Linux/macOS/WSL)"
echo "=========================================================="

echo "[1/4] Criando ambiente virtual Python em backend/.venv..."
python3 -m venv backend/.venv
source backend/.venv/bin/activate

echo "[2/4] Instalando dependências Python e motor Playwright Chromium..."
pip install --upgrade pip -q
pip install -r backend/requirements.txt
playwright install chromium

echo "[3/4] Executando testes unitários da Arquitetura DDD/SOLID..."
PYTHONPATH=backend pytest backend/tests -v

echo "[4/4] Instalando dependências Frontend (React + TypeScript + Tailwind)..."
cd frontend
npm install
cd ..

echo ""
echo "✅ Inicialização concluída com sucesso!"
echo "👉 Para iniciar Backend + Frontend juntos, execute:"
echo "   ./start.sh"
