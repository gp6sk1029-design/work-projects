$scriptPath = 'C:\Users\SEIGI-N13\my-ai-company\.claude\worktrees\peaceful-knuth\plc-debugger\start-silent.bat'
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ("/c `"" + $scriptPath + "`"")
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 0) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
Register-ScheduledTask -TaskName 'PLC Craft AI' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
Write-Host 'Done'
