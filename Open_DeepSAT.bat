@echo off
setlocal
set "DEEPSAT_ROOT=%~dp0"
set "DEEPSAT_RUNTIME=%DEEPSAT_ROOT%.venv\Scripts\python.exe"
if exist "%DEEPSAT_ROOT%.python-path" set /p "DEEPSAT_RUNTIME=" < "%DEEPSAT_ROOT%.python-path"
if not exist "%DEEPSAT_RUNTIME%" (
    echo DeepSAT setup is required. Run Setup-DeepSAT.ps1 in PowerShell.
    if "%~1"=="" pause
    exit /b 1
)

if not "%~1"=="" goto cli
for %%P in ("%DEEPSAT_RUNTIME%") do set "DEEPSAT_GUI=%%~dpPpythonw.exe"
if not exist "%DEEPSAT_GUI%" set "DEEPSAT_GUI=%DEEPSAT_RUNTIME%"
start "DeepSAT Local" "%DEEPSAT_GUI%" "%DEEPSAT_ROOT%deepsat_app.py"
exit /b

:cli
"%DEEPSAT_RUNTIME%" "%DEEPSAT_ROOT%deepsat_local.py" %*
exit /b %errorlevel%
