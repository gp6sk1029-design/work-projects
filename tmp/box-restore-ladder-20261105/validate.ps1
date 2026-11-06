$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
Add-Type -Path 'tmp/j-crash-diagnosis-20261029/NativeConnectionAudit.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskPath=Join-Path (Get-Location) 'tmp/box-restore-ladder-20261105/verification.json'
$taskMeta=Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResults=[ordered]@{}
foreach($taskPair in @(@($taskMeta.box_part,42),@($taskMeta.rcon_part,449),@($taskMeta.output_part,316))) {
 $taskResult=[NativeLadderCheck]::Check($taskMeta.staged,$taskPair[0])
 if($taskResult -notmatch ('TOTAL='+$taskPair[1]+' PARSE_FAIL=0 MODEL_FAIL=0')) {throw $taskResult}
 $taskResults[$taskPair[0]]=$taskResult.Trim()
}
$taskConnections=[NativeConnectionAudit]::Check($taskMeta.staged)
if($taskConnections -notmatch 'MISSING=0 PARSE_MODEL_FAIL=0') {throw $taskConnections}
$taskMeta.native_validation=[ordered]@{sections=$taskResults;connections=$taskConnections.Trim();full_application_build=$false}
[IO.File]::WriteAllText($taskPath,($taskMeta|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output ($taskResults|ConvertTo-Json -Compress)
Write-Output $taskConnections
