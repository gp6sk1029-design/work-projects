# 同梱の変数表ローダーで、要素コメントが新しい添字へ登録されることを確認する。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskReportPath=Join-Path (Get-Location) 'tmp/st7-renumber-20261027/verification.json'
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
 $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
 if($taskSerializer) {break}
}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskLoaded=0
$taskArchive=[IO.Compression.ZipFile]::OpenRead($taskReport.staged)
try {
 foreach($taskEntryName in $taskReport.declaration_entries) {
  $taskStream=$taskArchive.GetEntry($taskEntryName).Open()
  try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
  foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVariable in $taskGroup.Children) {
   if($taskVariable.Item('N') -ne 'ST7_A_Dis2_M') {continue}
   if($taskVariable.Item('D') -notmatch '^ARRAY\[0\.\.99\] OF BOOL$') {throw '配列型が不一致'}
   $taskElements=[xml]$taskVariable.Item('EC')
   $taskActual=@{}
   foreach($taskEC in $taskElements.GetElementsByTagName('EC')) {
    $taskKey=$taskEC.GetAttribute('EK')
    if($taskActual.ContainsKey($taskKey)) {throw ('要素コメント重複 '+$taskKey)}
    $taskActual[$taskKey]=$taskEC.GetAttribute('C')
   }
   foreach($taskExpected in $taskReport.element_comments_after.PSObject.Properties) {
    $taskKey='['+$taskExpected.Name+']'
    if($taskActual[$taskKey] -ne $taskExpected.Value) {throw ('要素コメント不一致 '+$taskKey)}
   }
   if($taskActual.Count -ne @($taskReport.element_comments_after.PSObject.Properties).Count) {throw 'コメント件数不一致'}
   $taskLoaded++
  }}}
 }
} finally {$taskArchive.Dispose()}
if($taskLoaded -ne 3) {throw '宣言件数不一致'}
$taskResult=[ordered]@{loader='メーカー同梱SSLightweightDataSerializer';declarations=$taskLoaded;elements_per_declaration=@($taskReport.element_comments_after.PSObject.Properties).Count;all_element_comments_matched=$true;full_application_build_verified=$false}
$taskReport.native_comments_validation=$taskResult
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
$taskResult | ConvertTo-Json -Depth 8
