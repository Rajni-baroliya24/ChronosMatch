@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install
:usepython
python -m venv .venv
if errorlevel 1 goto failed
:install
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Open http://127.0.0.1:5000 in your browser.
echo Keep this terminal open. Press Ctrl+C to stop.
echo.
.venv\Scripts\python.exe app.py
if errorlevel 1 goto failed
goto end
:failed
echo.
echo Setup or startup failed. Read the error above and README.md.
pause
:end
endlocal
