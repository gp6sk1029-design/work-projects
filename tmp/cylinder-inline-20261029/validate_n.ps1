# メーカー同梱の読込み・接続検査。アプリ画面とPLCは操作しない。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
Add-Type -Path 'tmp/j-crash-diagnosis-20261029/NativeConnectionAudit.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskReportPath=Join-Path (Get-Location) 'tmp/cylinder-inline-20261029/verification.json'
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResults=[ordered]@{}
foreach($taskEntry in $taskReport.ladder_counts.PSObject.Properties) {
    $taskResult=[NativeLadderCheck]::Check($taskReport.staged,$taskEntry.Name)
    if($taskResult -notmatch 'PARSE_FAIL=0 MODEL_FAIL=0') {throw ($taskEntry.Name+': '+$taskResult)}
    if($taskResult -notmatch ('TOTAL='+$taskEntry.Value+' ')) {throw '回路行数不一致'}
    $taskResults[$taskEntry.Name]=$taskResult.Trim()
}
$taskConnection=[NativeConnectionAudit]::Check($taskReport.staged)
if($taskConnection -notmatch 'TOTAL_RUNGS=1114 COILS=1321 MISSING=0 PARSE_MODEL_FAIL=0') {throw $taskConnection}
$taskReport.native_validation=$taskResults
$taskReport.native_variables=[ordered]@{unchanged=$true;new_declarations=0;full_application_build_verified=$false}
$taskReport.native_connections=[ordered]@{missing=0;coils=1321;result=$taskConnection}
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output ('全'+$taskResults.Count+'セクションの解析・モデル変換失敗0')
Write-Output $taskConnection
