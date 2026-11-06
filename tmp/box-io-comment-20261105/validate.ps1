$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskPath=Join-Path (Get-Location) 'tmp/box-io-comment-20261105/verification.json'
$taskMeta=Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResult=[NativeLadderCheck]::Check($taskMeta.staged,$taskMeta.part)
if($taskResult -notmatch ('TOTAL='+$taskMeta.row_count+' PARSE_FAIL=0 MODEL_FAIL=0')) {throw $taskResult}
$taskMeta.native_read=$taskResult.Trim()
[IO.File]::WriteAllText($taskPath,($taskMeta|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output $taskResult
