@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-DeepSAT.ps1" %*
set "DEEPSAT_EXIT=%ERRORLEVEL%"
if not "%DEEPSAT_EXIT%"=="0" echo Installation failed. See the error above and TROUBLESHOOTING.md.
pause
exit /b %DEEPSAT_EXIT%
