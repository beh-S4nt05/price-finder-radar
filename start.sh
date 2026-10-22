#!/usr/bin/env bash
set -euo pipefail

cleanup() {
  echo ""
  echo "Encerrando servidores ICEBERG..."
  kill "${API_PID:-}" "${WEB_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [ -d "backend/.venv" ]; then
  source backend/.venv/bin/activate
fi

echo "🚀 Iniciando Backend FastAPI em http://localhost:8000 (Docs: /docs)..."
PYTHONPATH=backend uvicorn src.presentation.api:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo "❄️  Iniciando Frontend React + Tailwind em http://localhost:5173 ..."
(cd frontend && npm run dev) &
WEB_PID=$!

wait
