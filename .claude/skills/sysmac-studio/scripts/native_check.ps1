param(
 [Parameter(Mandatory=$true)][string]$Source,
 [Parameter(Mandatory=$true)][string]$Report,
 [Parameter(Mandatory=$true)][string]$HelperPath,
 [string]$InstallRoot='C:\Program Files (x86)\OMRON\Sysmac Studio'
)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$taskDll=Join-Path $InstallRoot 'Modules\Nex\NexProgramming.dll'
if(-not (Test-Path -LiteralPath $taskDll)) {throw 'Sysmac同梱DLLが見つかりません。InstallRootを確認してください'}
$taskAssembly=[Reflection.Assembly]::LoadFrom($taskDll)
for($taskAttempt=0;$taskAttempt -lt 40;$taskAttempt++) {
 try {$null=$taskAssembly.GetExportedTypes();break}
 catch {
  $taskError=$_.Exception
  while($taskError.InnerException) {$taskError=$taskError.InnerException}
  if($taskError -is [IO.FileNotFoundException] -and $taskError.FileName) {
   $taskDependency=Join-Path $InstallRoot ($taskError.FileName.Split(',')[0]+'.dll')
   if(Test-Path -LiteralPath $taskDependency) {$null=[Reflection.Assembly]::LoadFrom($taskDependency)} else {throw}
  } else {throw}
 }
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path $HelperPath -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskResult=[SysmacSkillNativeCheck]::Check([IO.Path]::GetFullPath($Source),$InstallRoot)
$taskResult['source']=[IO.Path]::GetFullPath($Source)
$taskResult['sha256']=(Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant()
$taskResult['full_application_build']=$false
$taskResult['plc_simulation']=$false
$taskResult['machine_test']=$false
$taskJson=$taskResult|ConvertTo-Json -Depth 100
[IO.File]::WriteAllText([IO.Path]::GetFullPath($Report),$taskJson,[Text.UTF8Encoding]::new($false))
if(-not $taskResult['verified']) {throw 'メーカー同梱読込み/コイル接続の検査失敗。レポートを確認してください'}
Write-Output ('読込み・モデル検査：'+$taskResult['rows']+'行、接続欠落'+$taskResult['missing_connections'])
