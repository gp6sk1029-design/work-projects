' FP7 Diff を「ウィンドウ非表示」で本番起動するランチャー
' タスクスケジューラ（ログオン時）から呼ばれる
Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run """" & scriptDir & "\start-production.bat""", 0, False
