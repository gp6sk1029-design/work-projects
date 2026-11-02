# メーカー同梱処理で全ラダー・接続・追加変数属性を読み取り検査する。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
Add-Type -Path 'tmp/j-crash-diagnosis-20261029/NativeConnectionAudit.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskPath=Join-Path (Get-Location) 'tmp/rcon2-five-20261030/verification.json'
$taskReport=Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResults=[ordered]@{}
foreach($taskEntry in $taskReport.ladder_counts.PSObject.Properties) {
 $taskResult=[NativeLadderCheck]::Check($taskReport.staged,$taskEntry.Name)
 if($taskResult -notmatch 'PARSE_FAIL=0 MODEL_FAIL=0') {throw ($taskEntry.Name+': '+$taskResult)}
 if($taskResult -notmatch ('TOTAL='+$taskEntry.Value+' ')) {throw '行数不一致'}
 $taskResults[$taskEntry.Name]=$taskResult.Trim()
}
$taskConnections=[NativeConnectionAudit]::Check($taskReport.staged)
if($taskConnections -notmatch 'MISSING=0 PARSE_MODEL_FAIL=0') {throw $taskConnections}
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
 $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
 if($taskSerializer) {break}
}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskCounts=[ordered]@{global=0;external=0;local_timer=0}
$taskZip=[IO.Compression.ZipFile]::OpenRead($taskReport.staged)
try {
 foreach($taskEntry in $taskZip.Entries | Where-Object {$_.FullName.EndsWith('a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml') -or $_.FullName.EndsWith('f07dd06c-505c-431b-b9fc-098949805b4e.xml')}) {
  $taskStream=$taskEntry.Open()
  try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
  foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVar in $taskGroup.Children) {
   $taskName=$taskVar.Item('N')
   if($taskName -notmatch '^RCON2_[1-5]_') {continue}
   foreach($taskKey in @('Const','RO')) {
    $taskAttr=$taskVar.GetAttribute($taskKey)
    if($null -eq $taskAttr -or $taskAttr.BoolValue -ne $false) {throw ($taskName+': '+$taskKey+'がFALSEではありません')}
   }
   switch($taskVar.Item('G')) {
    'VAR_GLOBAL' {$taskCounts.global++}
    'VAR_EXTERNAL' {$taskCounts.external++}
    'VAR' {if($taskName -notmatch '_TO[NF]$') {throw '未知のローカル'}; $taskCounts.local_timer++}
    default {throw '未知の変数区分'}
   }
  }}}
 }
} finally {$taskZip.Dispose()}
if($taskCounts.global -ne 130 -or $taskCounts.external -ne 130 -or $taskCounts.local_timer -ne 10) {throw ($taskCounts|ConvertTo-Json)}
$taskReport.native_validation=$taskResults
$taskReport.native_connections=[ordered]@{missing=0;result=$taskConnections.Trim()}
$taskReport.native_variables=[ordered]@{counts=$taskCounts;all_const_false=$true;all_readonly_false=$true;application_build_verified=$false}
[IO.File]::WriteAllText($taskPath,($taskReport|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output ('全'+$taskResults.Count+'セクションの読込・モデル変換失敗0')
Write-Output $taskConnections
Write-Output ($taskCounts|ConvertTo-Json)
