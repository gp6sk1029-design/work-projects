# 同梱ローダーで３表の要素コメントを読み、表ごとの既存説明も保持されていることを確認。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskReportPath=Join-Path (Get-Location) 'tmp/st7-gap-20261028/verification.json'
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
 $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
 if($taskSerializer) {break}
}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskCount=0
$taskArchive=[IO.Compression.ZipFile]::OpenRead($taskReport.staged)
try {
 foreach($taskTable in $taskReport.comments_by_entry.PSObject.Properties) {
  $taskStream=$taskArchive.GetEntry($taskTable.Name).Open()
  try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
  foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVariable in $taskGroup.Children) {
   if($taskVariable.Item('N') -ne 'ST7_A_Dis2_M') {continue}
   if($taskVariable.Item('D') -notmatch '^ARRAY\[0\.\.99\] OF BOOL$') {throw '型が不一致'}
   $taskXml=[xml]$taskVariable.Item('EC');$taskActual=@{}
   foreach($taskElement in $taskXml.GetElementsByTagName('EC')) {
    $taskKey=$taskElement.GetAttribute('EK')
    if($taskActual.ContainsKey($taskKey)) {throw '要素コメント重複'}
    $taskActual[$taskKey]=$taskElement.GetAttribute('C')
   }
   foreach($taskExpected in $taskTable.Value.PSObject.Properties) {
    if($taskActual[$taskExpected.Name] -ne $taskExpected.Value) {throw ('要素説明が不一致 '+$taskExpected.Name)}
   }
   if($taskActual.Count -ne 24) {throw '要素件数が不一致'}
   $taskCount++
  }}}
 }
} finally {$taskArchive.Dispose()}
if($taskCount -ne 3) {throw '宣言件数が不一致'}
$taskResult=[ordered]@{loader='メーカー同梱SSLightweightDataSerializer';declarations=$taskCount;elements_per_declaration=24;all_comments_matched=$true;full_application_build_verified=$false}
$taskReport.native_comments_validation=$taskResult
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
$taskResult | ConvertTo-Json -Depth 8
