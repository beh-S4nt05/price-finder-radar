@echo off
chcp 65001 >nul
echo Iniciando ICEBERG // Price Radar (Backend :8000 + Frontend :5173)...

start "ICEBERG API Server (:8000)" cmd /k "cd backend && if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) && set PYTHONPATH=. && uvicorn src.presentation.api:app --host 0.0.0.0 --port 8000 --reload"
start "ICEBERG Web UI (:5173)" cmd /k "cd frontend && npm run dev"

timeout /t 3 /nobreak >nul
start http://localhost:5173
