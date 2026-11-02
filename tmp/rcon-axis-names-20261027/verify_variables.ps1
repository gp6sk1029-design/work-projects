# 同梱の変数表読込み処理で、名称変更前後の定義・属性と参照名を確認する。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskReportPath=Join-Path (Get-Location) 'tmp/rcon-axis-names-20261027/verification.json'
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
 $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
 if($taskSerializer) {break}
}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskBefore=@{}
$taskAfter=@{}
foreach($taskPair in @(@{path=$taskReport.source;output=$taskBefore;after=$false},@{path=$taskReport.staged;output=$taskAfter;after=$true})) {
 $taskArchive=[IO.Compression.ZipFile]::OpenRead($taskPair.path)
 try {
  foreach($taskEntryName in @($taskReport.declaration_renames.entry | Select-Object -Unique)) {
   $taskEntry=$taskArchive.GetEntry($taskEntryName)
   $taskStream=$taskEntry.Open()
   try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
   foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVariable in $taskGroup.Children) {
    $taskName=$taskVariable.Item('N')
    foreach($taskExpected in @($taskReport.declaration_renames | Where-Object {$_.entry -eq $taskEntryName})) {
     $taskExpectedName=if($taskPair.after){$taskExpected.new}else{$taskExpected.old}
     if($taskName -ne $taskExpectedName) {continue}
     $taskKey=$taskEntryName+'|'+$taskExpected.old
     if($taskPair.output.ContainsKey($taskKey)) {throw ('宣言重複 '+$taskName)}
     $taskAttrs=[ordered]@{type=$taskVariable.Item('D');group=$taskVariable.Item('G')}
     foreach($taskAttrKey in @('Const','RO','R')) {
      $taskAttr=$taskVariable.GetAttribute($taskAttrKey)
      $taskAttrs[$taskAttrKey]=if($null -eq $taskAttr){$null}else{$taskAttr.BoolValue}
     }
     $taskPair.output[$taskKey]=($taskAttrs | ConvertTo-Json -Compress)
    }
   }}}
  }
 } finally {$taskArchive.Dispose()}
}
if($taskBefore.Count -ne $taskReport.declaration_renames.Count -or $taskAfter.Count -ne $taskBefore.Count) {throw '検査件数不一致'}
foreach($taskKey in $taskBefore.Keys) {if($taskBefore[$taskKey] -ne $taskAfter[$taskKey]) {throw ('名称以外の属性変化 '+$taskKey)}}
$taskResult=[ordered]@{loader='メーカー同梱SSLightweightDataSerializer';renamed_declarations=$taskAfter.Count;names_and_type_loaded=$true;constant_readonly_retain_unchanged=$true;full_application_build_verified=$false}
$taskReport.native_variables=$taskResult
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
$taskResult | ConvertTo-Json -Depth 8
