@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0trials\pcl-adapter\setup-pcl.ps1" %*
set "ELDENCRAFT_SETUP_EXIT=%ERRORLEVEL%"
pause
exit /b %ELDENCRAFT_SETUP_EXIT%
