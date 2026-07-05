#Call this script from PyWinCmd prompt. 

write-host @"
Demonstration that a state (current directory) modified by a *.PS1 script dos NOT affect 
the caller environment. Also, the VAR_X_PS variable created here will NOT be visible.
"@

write-host @"
This is NORMAL behavior for PS1 scripts (unlike CMD scripts). 
Architecturally and by design, PowerShell environments do NOT change the state of the calling 
environment, so EVEN when running this script from a standard CMD, the directory change and 
the VAR_X_PS variable set above will NEVER affect the calling script/program/CMD. 
So, the same thing will happen when running this PS1 from the PyWinCmd prompt.
"@

write-host ""
write-host "Testing a *.PS1 powershell script that interacts with the user... "
write-host ""
write-host "Executing:  Set-Location -Path '$PSScriptRoot\subdir'"
Set-Location -Path "$PSScriptRoot\subdir" # similar to "CD"
Get-ChildItem  # similar to "DIR"
write-host ""
write-host "Executing:  `$Env:VAR_X_PS = 'xxxxxxxxxx'"
$Env:VAR_X_PS = "xxxxxxxxxx"
$outstr="VAR_X_PS=" + $Env:VAR_X_PS
Write-Output $outstr

write-host ""
$void = Read-Host @"
Hit ENTER - Notice that the current directory has NOT changed. 
Then use the 'SET' command at the PywinCmd prompt and search for 'VAR_X_PS' (won't find it). 
"@
