# 行間コメント変更後のメーカー同梱読込み検査。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskPath=Join-Path (Get-Location) 'tmp/box-comment-layout-20261105/verification.json'
$taskMeta=Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResults=[ordered]@{}
foreach($taskSection in $taskMeta.sections) {
 $taskResult=[NativeLadderCheck]::Check($taskMeta.staged,$taskSection.part)
 if($taskResult -notmatch ('TOTAL='+$taskSection.row_count+' PARSE_FAIL=0 MODEL_FAIL=0')) {throw $taskResult}
 $taskResults[$taskSection.section]=$taskResult.Trim()
}
$taskMeta|Add-Member -NotePropertyName native_read -NotePropertyValue $taskResults -Force
[IO.File]::WriteAllText($taskPath,($taskMeta|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output ($taskResults|ConvertTo-Json -Compress)
