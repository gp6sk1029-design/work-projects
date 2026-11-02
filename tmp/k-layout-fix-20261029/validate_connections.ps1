$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -Path 'tmp/j-crash-diagnosis-20261029/NativeConnectionAudit.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskPath=Join-Path (Get-Location) 'tmp/k-layout-fix-20261029/verification.json'
$taskReport=Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResult=[NativeConnectionAudit]::Check($taskReport.staged)
if($taskResult -notmatch 'TOTAL_RUNGS=1107 COILS=1314 MISSING=0 PARSE_MODEL_FAIL=0'){throw $taskResult}
$taskReport.native_connections=[ordered]@{after_missing_connections=0;total_coils=1314;result=$taskResult}
[IO.File]::WriteAllText($taskPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output $taskResult.Trim()
