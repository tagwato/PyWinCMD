@echo off
@REM Call this script from PyWinCmd prompt. 
echo Demonstration of a script that interacts with the user.
echo Also demonstrates that a state (current directory) modified by a *.cmd script affects
echo the caller environment. And the VAR_X variable created here will be visible.
echo.
echo Executing 'Set VAR_X=xxxxxxxx'
set VAR_X=xxxxxxxx
echo VAR_X=%VAR_X%%
echo Executing:  'CD %~dp0\subdir'
CD %~dp0\subdir
dir
echo.
set /P void="Hit ENTER - Notice how the current directory changed. Then use the 'SET' command and search for 'VAR_X' "
set ERRORLEVEL=1
