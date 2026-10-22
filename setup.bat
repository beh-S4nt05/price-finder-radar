@echo off
chcp 65001 >nul
echo ==========================================================
echo   ICEBERG // Price Radar - Setup Completo (Windows)
echo ==========================================================

echo [1/4] Criando ambiente virtual Python em backend\.venv...
python -m venv backend\.venv
call backend\.venv\Scripts\activate.bat

echo [2/4] Instalando pacotes Python e navegador Playwright Chromium...
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
playwright install chromium

echo [3/4] Validando testes unitarios DDD / SOLID...
set PYTHONPATH=backend
pytest backend\tests -v

echo [4/4] Instalando dependencias Frontend (React + TS + Tailwind)...
cd frontend
call npm install
cd ..

echo.
echo ==========================================================
echo   Setup concluido com sucesso!
echo   Execute start.bat para subir Backend + Frontend juntos.
echo ==========================================================
pause
