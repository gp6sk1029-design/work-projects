$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -Path 'tmp/j-crash-diagnosis-20261029/NativeConnectionAudit.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskPrevious=Get-Content -LiteralPath 'tmp/section-organize-20261028/verification.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$taskG=Get-Content -LiteralPath 'tmp/error-station-20261028/verification.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResults=[ordered]@{}
foreach($taskFile in @($taskG.destination,$taskPrevious.source,$taskPrevious.destination)) {
 $taskResult=[NativeConnectionAudit]::Check($taskFile)
 $taskResults[$taskFile]=$taskResult
 Write-Output ([IO.Path]::GetFileName($taskFile))
 Write-Output $taskResult
}
[IO.File]::WriteAllText((Join-Path (Get-Location) 'tmp/j-crash-diagnosis-20261029/connection_results.json'),($taskResults | ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
