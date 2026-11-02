# 変更した宣言のコメントを、メーカー同梱ローダーで読み直して照合する。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskReportPath=Join-Path (Get-Location) 'tmp/io-station-20261028/verification.json'
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
 $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
 if($taskSerializer) {break}
}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskArchive=[IO.Compression.ZipFile]::OpenRead($taskReport.staged)
$taskCount=0;$taskElements=0
try {
 foreach($taskEntryName in @($taskReport.declaration_changes.entry | Select-Object -Unique)) {
  $taskExpectedByName=@{}
  foreach($taskExpected in @($taskReport.declaration_changes | Where-Object {$_.entry -eq $taskEntryName})) {
   $taskExpectedByName[$taskExpected.name]=$taskExpected
  }
  $taskStream=$taskArchive.GetEntry($taskEntryName).Open()
  try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
  $taskFound=@{}
  foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVariable in $taskGroup.Children) {
   $taskName=$taskVariable.Item('N')
   if(-not $taskExpectedByName.ContainsKey($taskName)) {continue}
   if($taskFound.ContainsKey($taskName)) {throw ('Duplicate '+$taskName)}
   $taskExpected=$taskExpectedByName[$taskName]
   if($taskVariable.Item('D') -ne $taskExpected.type) {throw ('Type mismatch '+$taskName)}
   if($null -ne $taskExpected.new_comment -and $taskVariable.Item('Com') -ne $taskExpected.new_comment) {throw ('Comment mismatch '+$taskName)}
   $taskEC=$taskVariable.Item('EC')
   if($taskEC) {
    $taskXml=[xml]$taskEC
    $taskElements+=$taskXml.GetElementsByTagName('EC').Count
   }
   $taskFound[$taskName]=$true;$taskCount++
  }}}
  if($taskFound.Count -ne $taskExpectedByName.Count) {throw 'Declaration count mismatch'}
 }
} finally {$taskArchive.Dispose()}
if($taskCount -ne $taskReport.declaration_changes.Count) {throw 'Total count mismatch'}
$taskReport.native_comments=[ordered]@{loader='SSLightweightDataSerializer';declarations=$taskCount;array_elements_loaded=$taskElements;all_changed_comments_matched=$true;full_application_build_verified=$false}
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
$taskReport.native_comments | ConvertTo-Json
