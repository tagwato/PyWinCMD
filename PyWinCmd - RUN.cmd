
@echo off
setlocal enabledelayedexpansion
@REM Use SCRIPTDIR throughout the code, instead of ~dp0, because if ~dp0 used AFTER a CD, then bad things happen 
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_NAME_WITH_PATH=%~f0"

@REM Ensures it is running in the location where this script is located
cd /D "%SCRIPT_DIR%" 

@REM Update the *.cmd path and the icon path in the shortcut that launches PyWincmd, if it exists.
@REM This ensures the icon is displayed correctly if the installation folder has been moved.
set "ICON_PATH=%SCRIPT_DIR%\images\PWC_128x128.ico"
if exist "%ICON_PATH%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ws = New-Object -ComObject WScript.Shell; " ^
        "$s = $ws.CreateShortcut('%SCRIPT_DIR%\PyWinCMD - RUN.lnk'); " ^
        "$s.Arguments = '' "; ^
        "$s.TargetPath = '%SCRIPT_NAME_WITH_PATH%'; " ^
        "$s.WorkingDirectory = '%SCRIPT_DIR%'; " ^
        "$s.IconLocation = '%ICON_PATH%'; " ^
        "$s.Save();"
) 

cmd /c " python "%SCRIPT_DIR%\src\pywincmd.py" "
