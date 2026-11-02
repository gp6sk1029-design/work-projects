# メーカー同梱の読込み処理で、追加BOOLが可変であることを検証する。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskReportPath=Join-Path (Get-Location) 'tmp/rcon-simple-20261026/verification.json'
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
 $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
 if($taskSerializer) {break}
}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskCounts=[ordered]@{global=0;external=0}
$taskArchive=[IO.Compression.ZipFile]::OpenRead($taskReport.staged)
try {
 foreach($taskEntry in $taskArchive.Entries | Where-Object {$_.FullName.EndsWith('.xml')}) {
  $taskStream=$taskEntry.Open()
  try {$taskReader=[IO.StreamReader]::new($taskStream);$taskText=$taskReader.ReadToEnd()} finally {$taskReader.Dispose()}
  if(-not $taskText.StartsWith('[SLWD')) {continue}
  $taskMemory=[IO.MemoryStream]::new([Text.Encoding]::UTF8.GetBytes($taskText))
  try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskMemory))} finally {$taskMemory.Dispose()}
  foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVariable in $taskGroup.Children) {
   $taskName=$taskVariable.Item('N')
   if($taskName -notmatch '^RCON1_[1-6]_MoveDone$') {continue}
   if($taskVariable.Item('D') -ne 'BOOL') {throw ('BOOLでない '+$taskName)}
   foreach($taskKey in @('Const','RO')) {
    $taskAttr=$taskVariable.GetAttribute($taskKey)
    if($null -eq $taskAttr -or $taskAttr.BoolValue -ne $false) {throw ($taskName+': '+$taskKey+'がFALSEでない')}
   }
   $taskG=$taskVariable.Item('G')
   if($taskG -eq 'VAR_GLOBAL') {$taskCounts.global++}
   elseif($taskG -eq 'VAR_EXTERNAL') {$taskCounts.external++}
   else {throw ('スコープ不一致 '+$taskName)}
  }}}
 }
} finally {$taskArchive.Dispose()}
if($taskCounts.global -ne 6 -or $taskCounts.external -ne 7) {throw '検査件数不一致'}
$taskResult=[ordered]@{loader='メーカー同梱SSLightweightDataSerializer';counts=$taskCounts;all_new_const_false=$true;all_new_readonly_false=$true;full_application_build_verified=$false}
$taskReport.native_variable_attributes=$taskResult
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
$taskResult | ConvertTo-Json -Depth 8
