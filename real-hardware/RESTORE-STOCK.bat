@echo off
chcp 65001 >nul 2>&1
setlocal
set "PYTHONIOENCODING=utf-8"
set "SCRIPT=C:\Users\WXP\WorkBuddy\2026-11-08-01-41-44\smg3ds\real-hardware\install-diag.py"
set "PY=C:\Users\WXP\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PY%" set "PY=C:\Users\WXP\AppData\Local\Python\bin\python.exe"
set "DRIVE=%~1"
if "%DRIVE%"=="" set "DRIVE=F:"
set "EXTRA=%~2"
echo ==========================================================
echo  SMG-3DS : restore the OFFICIAL stock 3dsx onto the SD card
echo  Target drive : %DRIVE%
echo ==========================================================
echo.
if exist "%PY%" (
    "%PY%" "%SCRIPT%" %DRIVE% --restore %EXTRA%
) else (
    py -3 "%SCRIPT%" %DRIVE% --restore %EXTRA%
)
echo.
echo Script exit code: %ERRORLEVEL%
echo.
if not "%SMG_NOPAUSE%"=="1" pause
