# メーカー付属処理で対象42行の保存構造を読み取る。アプリ・実機操作なし。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskPath=Join-Path (Get-Location) 'tmp/box-normalize42-20261105/verification.json'
$taskMeta=Get-Content -LiteralPath $taskPath -Encoding UTF8 -Raw | ConvertFrom-Json
$taskResult=[NativeLadderCheck]::Check($taskMeta.staged,$taskMeta.target)
if($taskResult -notmatch 'TOTAL=42 PARSE_FAIL=0 MODEL_FAIL=0') {throw $taskResult}
$taskMeta.native_validation=[ordered]@{box_section=$taskResult.Trim();application_build_verified=$false}
[IO.File]::WriteAllText($taskPath,($taskMeta|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output $taskResult
