@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PORT=8501"
set "APPDATA_ROOT=%LOCALAPPDATA%\CRPM"
if "%LOCALAPPDATA%"=="" set "APPDATA_ROOT=%TEMP%\CRPM"
set "LOG_DIR=%APPDATA_ROOT%\logs"
set "LOG_FILE=%LOG_DIR%\streamlit.log"
set "PID_FILE=%LOG_DIR%\streamlit.pid"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    taskkill /PID %%P /F >nul 2>&1
)

if not exist "%VENV_PY%" (
    echo Local virtual environment not found at "%VENV_PY%".
    echo Create it first with:
    echo     python -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -e ".[dev]"
    pause
    exit /b 1
)

start "CRPM Streamlit" /min cmd /c ""%VENV_PY%" -m streamlit run app.py --server.port %PORT% --server.headless true --browser.gatherUsageStats false > "%LOG_FILE%" 2>&1"

timeout /t 3 /nobreak >nul

powershell -NoProfile -Command ^
  "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*streamlit run app.py*--server.port %PORT%*' } | Select-Object -First 1 -ExpandProperty ProcessId; if ($p) { Set-Content -Path '%PID_FILE%' -Value $p -Encoding ascii }"

start "" "http://localhost:%PORT%"

endlocal
