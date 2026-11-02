param([string]$ReportPath='tmp\reorder_side_comments_20261023\verification.json')
# 同梱のラダー変換処理だけを呼び出す。Sysmac画面・PLCへは接続しない。
$ErrorActionPreference='Stop'
& ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp\inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -Path 'tmp\NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskReportPath=Join-Path (Get-Location) $ReportPath
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResults=[ordered]@{}
foreach($taskEntry in $taskReport.ladder_counts.PSObject.Properties) {
    $taskResult=[NativeLadderCheck]::Check($taskReport.staged,$taskEntry.Name)
    $taskResults[$taskEntry.Name]=$taskResult.Trim()
    if($taskResult -notmatch 'PARSE_FAIL=0 MODEL_FAIL=0') { throw ($taskEntry.Name+': '+$taskResult) }
    if($taskResult -notmatch ('TOTAL='+$taskEntry.Value+' ')) { throw '回路行数が不一致' }
    Write-Output ($taskEntry.Name.Split('/')[-1]+' '+$taskResult.Trim())
}
$taskReport.native_validation=$taskResults
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output ('検証完了：'+$taskResults.Count+'セクション')
