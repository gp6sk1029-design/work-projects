$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
Add-Type -Path 'tmp/j-crash-diagnosis-20261029/NativeConnectionAudit.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskPath=Join-Path (Get-Location) 'tmp/box-improve-20261105/verification.json'
$taskMeta=Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskBox=[NativeLadderCheck]::Check($taskMeta.staged,$taskMeta.box_part)
$taskRcon=[NativeLadderCheck]::Check($taskMeta.staged,$taskMeta.rcon_part)
$taskOutput=[NativeLadderCheck]::Check($taskMeta.staged,$taskMeta.output_part)
if($taskBox -notmatch 'TOTAL=43 PARSE_FAIL=0 MODEL_FAIL=0' -or $taskRcon -notmatch 'TOTAL=453 PARSE_FAIL=0 MODEL_FAIL=0') {throw ($taskBox+$taskRcon)}
if($taskOutput -notmatch 'TOTAL=316 PARSE_FAIL=0 MODEL_FAIL=0') {throw $taskOutput}
$taskConnections=[NativeConnectionAudit]::Check($taskMeta.staged)
if($taskConnections -notmatch 'MISSING=0 PARSE_MODEL_FAIL=0') {throw $taskConnections}
$taskMeta.native_validation=[ordered]@{box=$taskBox.Trim();rcon=$taskRcon.Trim();output=$taskOutput.Trim();connections=$taskConnections.Trim();full_application_build=$false}
[IO.File]::WriteAllText($taskPath,($taskMeta|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output $taskBox
Write-Output $taskRcon
Write-Output $taskConnections
