' PLC Craft AI を「ウィンドウ非表示」で本番起動するランチャー
' タスクスケジューラ（ログオン時）から呼ばれる
Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
' 第2引数 0 = ウィンドウ非表示, False = 完了を待たない
WshShell.Run """" & scriptDir & "\start-production.bat""", 0, False
