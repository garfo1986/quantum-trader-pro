@echo off
TITLE QuantumTrader Pro - Terminal de Mercados
echo ============================================================
echo   Iniciando QuantumTrader Pro (Terminal 100%% Gratuito)
echo ============================================================
echo.

cd /d "%~dp0"

IF EXIST "..\venv\Scripts\streamlit.exe" (
    echo Usando entorno virtual detectado...
    "..\venv\Scripts\streamlit.exe" run app.py
) ELSE IF EXIST "venv\Scripts\streamlit.exe" (
    echo Usando entorno virtual local...
    "venv\Scripts\streamlit.exe" run app.py
) ELSE (
    echo Usando Python del sistema...
    streamlit run app.py
)

pause
