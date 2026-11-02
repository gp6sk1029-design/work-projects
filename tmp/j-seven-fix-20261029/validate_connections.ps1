# プロジェクトを開かず、コイルの出口接続を修正前後で確認する。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -Path 'tmp/j-crash-diagnosis-20261029/NativeConnectionAudit.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskPath=Join-Path (Get-Location) 'tmp/j-seven-fix-20261029/verification.json'
$taskReport=Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskBefore=[NativeConnectionAudit]::Check($taskReport.source)
$taskAfter=[NativeConnectionAudit]::Check($taskReport.staged)
if($taskBefore -notmatch 'COILS=1314 MISSING=7 PARSE_MODEL_FAIL=0'){throw ('修正前の状態が診断と違います：'+$taskBefore)}
if($taskAfter -notmatch 'TOTAL_RUNGS=1100 COILS=1314 MISSING=0 PARSE_MODEL_FAIL=0'){throw ('接続検査不合格：'+$taskAfter)}
$taskReport.native_connections=[ordered]@{
 before_missing_connections=7
 after_missing_connections=0
 fixed_coils_connected=7
 total_coils=1314
 before=$taskBefore
 after=$taskAfter
}
[IO.File]::WriteAllText($taskPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output $taskAfter.Trim()
