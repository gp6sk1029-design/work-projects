# メーカー同梱の読込み・変換処理で検証する。実機接続・転送は行わない。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskReportPath=Join-Path (Get-Location) 'tmp/tray-rename-20261028/verification.json'
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResults=[ordered]@{}
foreach($taskEntry in $taskReport.ladder_counts.PSObject.Properties) {
 $taskResult=[NativeLadderCheck]::Check($taskReport.staged,$taskEntry.Name)
 if($taskResult -notmatch 'PARSE_FAIL=0 MODEL_FAIL=0') {throw $taskResult}
 $taskResults[$taskEntry.Name]=$taskResult.Trim()
}
$taskReport.native_validation=$taskResults
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
 $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
 if($taskSerializer) {break}
}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskBefore=@{};$taskAfter=@{}
foreach($taskPair in @(@{path=$taskReport.source;output=$taskBefore;after=$false},@{path=$taskReport.staged;output=$taskAfter;after=$true})) {
 $taskArchive=[IO.Compression.ZipFile]::OpenRead($taskPair.path)
 try {
  foreach($taskEntryName in @($taskReport.declaration_renames.entry | Select-Object -Unique)) {
   $taskStream=$taskArchive.GetEntry($taskEntryName).Open()
   try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
   foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVariable in $taskGroup.Children) {
    $taskName=$taskVariable.Item('N')
    foreach($taskExpected in @($taskReport.declaration_renames | Where-Object {$_.entry -eq $taskEntryName})) {
     $taskExpectedName=if($taskPair.after){$taskExpected.new}else{$taskExpected.old}
     if($taskName -ne $taskExpectedName) {continue}
     $taskKey=$taskEntryName+'|'+$taskExpected.old
     if($taskPair.output.ContainsKey($taskKey)) {throw ('宣言重複 '+$taskName)}
     $taskAttrs=[ordered]@{type=$taskVariable.Item('D');group=$taskVariable.Item('G');address=$taskVariable.Item('AT')}
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
$taskReport.native_variables=[ordered]@{loader='メーカー同梱SSLightweightDataSerializer';declarations=$taskAfter.Count;type_constant_readonly_retain_address_preserved=$true;full_application_build_verified=$false}
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output ('ラダー '+$taskResults.Count+' セクション：解析・モデル変換失敗0、宣言 '+$taskAfter.Count+' 件：型・保持・定数・読取専用・割付保持')
