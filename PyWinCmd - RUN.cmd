
@echo off

@REM Atualizamos o caminho do *.cmd e do ícone, no atalho que executa o PyWincmd, se houver. 
@REM Isso é para garantir que o ícone apareça, quando instalar/mover para outras pastas
if exist "%~dp0\images\PWC3.ico" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ws = New-Object -ComObject WScript.Shell; " ^
        "$s = $ws.CreateShortcut('%~dp0\PyWinCmd - RUN.lnk'); " ^
        "$s.Arguments = 'pWc'; " ^
        "$s.TargetPath = '%~f0'; " ^
        "$s.WorkingDirectory = '%~dp0'; " ^
        "$s.IconLocation = '%~dp0\images\PWC3.ico'; " ^
        "$s.Save();"
)

cmd /c " python ".\src\pywincmd.py" "
