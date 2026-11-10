@echo off
REM Attach the devkitARM GDB to the real console (Rosalina GDB stub).
REM   1. On the 3DS: Rosalina menu (L+Down+Select) -> Debugger options ->
REM      Enable debugger -> Force-debug next application at launch.
REM      Note the IP (top-right) and the port (break-on-start = 4003).
REM   2. Launch SMG-3DS from HBL/SD (screen goes black, waiting).
REM   3. Run:  GDB-3DS.cmd <3DS-IP> [PORT=4003]
set IP=%~1
if "%IP%"=="" (
  echo Usage: GDB-3DS.cmd ^<3DS-IP^> [PORT=4003]
  exit /b 1
)
set PORT=%~2
if "%PORT%"=="" set PORT=4003
set GDB=%DEVKITPRO%\devkitARM\bin\arm-none-eabi-gdb.exe
if not exist "%GDB%" (
  echo arm-none-eabi-gdb not found at %GDB%
  echo Set DEVKITPRO, or install devkitARM.
  exit /b 1
)
echo Attaching to %IP%:%PORT% with optional/SMG-3DS-debug.elf ...
"%GDB%" -ex "set sysroot" -ex "target remote %IP%:%PORT%" "%~dp0optional\SMG-3DS-debug.elf"
