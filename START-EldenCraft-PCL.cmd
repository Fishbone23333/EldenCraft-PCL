@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0trials\pcl-adapter\start-pcl.ps1" %*
set "MA_ELDENCRAFT_EXIT=%ERRORLEVEL%"
pause
exit /b %MA_ELDENCRAFT_EXIT%
