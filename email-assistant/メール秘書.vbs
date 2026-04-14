Dim objShell, strDir, strScript
Set objShell = CreateObject("WScript.Shell")
strDir    = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
strScript = strDir & "メール秘書.pyw"
objShell.Run "python """ & strScript & """", 0, False
Set objShell = Nothing
