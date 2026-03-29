@echo off
setlocal

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

echo [INFO] Installing project and dev dependencies...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
call ".venv\Scripts\python.exe" -m pip install -e .[dev]

if not exist "config\hosts.yaml" (
    echo [INFO] Creating config\hosts.yaml from example...
    copy /Y "config\hosts.yaml.example" "config\hosts.yaml" >nul
)

echo [INFO] Verifying import...
call ".venv\Scripts\python.exe" -c "from core.server import get_server; print(type(get_server()).__name__)"

echo [DONE] SAPladdin environment ready.
endlocal
