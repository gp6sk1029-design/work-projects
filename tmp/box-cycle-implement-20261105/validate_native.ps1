# メーカー同梱処理で読込み・結線・追加変数属性を検査する。全体ビルドではない。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
Add-Type -Path 'tmp/j-crash-diagnosis-20261029/NativeConnectionAudit.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskDir=Join-Path (Get-Location) 'tmp/box-cycle-implement-20261105'
$taskMeta=Get-Content -LiteralPath (Join-Path $taskDir 'verification.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResults=[ordered]@{}
foreach($taskPair in @(@($taskMeta.box_part,45),@($taskMeta.sf_part,32),@($taskMeta.rcon_part,457))) {
 $taskResult=[NativeLadderCheck]::Check($taskMeta.staged,$taskPair[0])
 if($taskResult -notmatch ('TOTAL='+$taskPair[1]+' PARSE_FAIL=0 MODEL_FAIL=0')) {throw $taskResult}
 $taskResults[$taskPair[0]]=$taskResult.Trim()
}
$taskConnections=[NativeConnectionAudit]::Check($taskMeta.staged)
if($taskConnections -notmatch 'MISSING=0 PARSE_MODEL_FAIL=0') {throw $taskConnections}
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
 $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
 if($taskSerializer) {break}
}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskVars=[ordered]@{}
$taskZip=[IO.Compression.ZipFile]::OpenRead($taskMeta.staged)
try {
 $taskEntry=$taskZip.GetEntry($taskMeta.scope_part)
 $taskStream=$taskEntry.Open()
 try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
 foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVar in $taskGroup.Children) {
  $taskName=$taskVar.Item('N')
  if($taskName -notin $taskMeta.new_variable_names) {continue}
  foreach($taskKey in @('Const','RO','R')) {
   $taskAttr=$taskVar.GetAttribute($taskKey)
   if($null -eq $taskAttr -or $taskAttr.BoolValue -ne $false) {throw ($taskName+': '+$taskKey+'がFALSEではありません')}
  }
  if($taskVar.Item('D') -ne 'BOOL' -or $taskVar.Item('G') -ne 'VAR') {throw ('変数区分不一致：'+$taskName)}
  $taskVars[$taskName]='BOOL・非保持・書込み可'
 }}}
} finally {$taskZip.Dispose()}
if($taskVars.Count -ne 2) {throw '追加変数数不一致'}
$taskReport=[ordered]@{sections=$taskResults;connections=$taskConnections.Trim();new_variables=$taskVars;full_application_build=$false;plc_simulation=$false;machine_test=$false}
[IO.File]::WriteAllText((Join-Path $taskDir 'native.json'),($taskReport|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output ($taskReport|ConvertTo-Json -Depth 100 -Compress)
