@echo off
REM Real-time log from the console over 3dslink (no SD card, no photos).
REM   1. On the 3DS: open Homebrew Launcher, press Y to show the IP.
REM   2. Run:  WATCH-NETLOG.bat <3DS-IP>
set IP=%~1
if "%IP%"=="" (
  echo Usage: WATCH-NETLOG.bat ^<3DS-IP^>
  echo   1. On the 3DS open Homebrew Launcher and press Y to show the IP.
  echo   2. Run this script with that IP.
  exit /b 1
)
py -3 "%~dp0deploy-3ds.py" --ip %IP% --build debug --server | py -3 "%~dp0live-log.py" --stdin
