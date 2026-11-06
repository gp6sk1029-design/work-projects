# 変更ラダーと新規設定変数をメーカー同梱処理で読み取る。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskMetaPath=Join-Path (Get-Location) 'tmp/box-y-pitch-20261104/verification.json'
$taskMeta=Get-Content -LiteralPath $taskMetaPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResult=[NativeLadderCheck]::Check($taskMeta.staged,$taskMeta.target)
if($taskResult -notmatch 'TOTAL=28 PARSE_FAIL=0 MODEL_FAIL=0') {throw $taskResult}
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
 $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
 if($taskSerializer) {break}
}
if(-not $taskSerializer) {throw '変数読込み処理が見つからない'}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskVars=@()
$taskZip=[IO.Compression.ZipFile]::OpenRead($taskMeta.staged)
try {
 foreach($taskPart in @($taskMeta.localpart,$taskMeta.globalpart)) {
  $taskStream=$taskZip.GetEntry($taskPart).Open()
  try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
  foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVar in $taskGroup.Children) {
   if($taskVar.Item('N') -ne $taskMeta.pitch) {continue}
   if($taskVar.Item('D') -ne 'LREAL') {throw 'ピッチ変数の型が不一致'}
   foreach($taskKey in @('Const','RO')) {
    $taskAttribute=$taskVar.GetAttribute($taskKey)
    if($null -eq $taskAttribute -or $taskAttribute.BoolValue -ne $false) {throw ($taskKey+'がFALSEではない')}
   }
   $taskVars += [ordered]@{name=$taskVar.Item('N');type=$taskVar.Item('D');scope=$taskVar.Item('G');retain=$taskVar.Item('R');constant=$false;readonly=$false}
  }}}
 }
} finally {$taskZip.Dispose()}
if($taskVars.Count -ne 2) {throw 'グローバル/外部参照の2件と一致しない'}
if(@($taskVars | Where-Object {$_.scope -eq 'VAR_GLOBAL' -and $_.retain -eq '1'}).Count -ne 1) {throw '保持付きグローバル登録に失敗'}
$taskMeta.native_validation=[ordered]@{box_section=$taskResult.Trim();variables=$taskVars;application_build_verified=$false}
[IO.File]::WriteAllText($taskMetaPath,($taskMeta|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output $taskResult
Write-Output ($taskVars|ConvertTo-Json -Compress)
