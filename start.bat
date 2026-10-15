
@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo      CertiMail - Certificate Distribution Dashboard
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 goto no_python

where npm >nul 2>&1
if errorlevel 1 goto no_node

if not exist ".venv\Scripts\python.exe" goto create_venv
goto install_backend

:create_venv
echo [SETUP] Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 goto venv_failed

:install_backend
echo [SETUP] Checking backend dependencies...
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto backend_failed

if not exist "frontend\package.json" goto frontend_missing
if exist "frontend\node_modules" goto launch_servers

echo [SETUP] Installing frontend dependencies...
pushd frontend
call npm install
if errorlevel 1 goto frontend_install_failed
popd

:launch_servers
echo.
echo [LAUNCH] Starting FastAPI backend...
start "CertiMail Backend" /D "%~dp0" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [LAUNCH] Starting React frontend...
start "CertiMail Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo.
echo Frontend: http://localhost:5173
echo Backend:  http://127.0.0.1:8000/docs
echo.
timeout /t 3 >nul
start "" "http://localhost:5173"
echo Keep the backend and frontend windows open.
pause
exit /b 0

:no_python
echo [ERROR] Python was not found in PATH.
echo Install Python 3.10 or newer and reopen Command Prompt.
pause
exit /b 1

:no_node
echo [ERROR] Node.js/npm was not found in PATH.
echo Install Node.js 18 or newer and reopen Command Prompt.
pause
exit /b 1

:venv_failed
echo [ERROR] Could not create the Python virtual environment.
pause
exit /b 1

:backend_failed
echo [ERROR] Backend dependency installation failed.
pause
exit /b 1

:frontend_missing
echo [ERROR] frontend\package.json was not found.
pause
exit /b 1

:frontend_install_failed
popd
echo [ERROR] Frontend dependency installation failed.
pause
exit /b 1
