# メーカー同梱処理によるオフライン読込み検査。Sysmac画面・PLCは操作しない。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskReportPath=Join-Path (Get-Location) 'tmp/error-station-20261028/verification.json'
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskResults=[ordered]@{}
foreach($taskEntry in $taskReport.ladder_counts.PSObject.Properties) {
    $taskResult=[NativeLadderCheck]::Check($taskReport.staged,$taskEntry.Name)
    if($taskResult -notmatch 'PARSE_FAIL=0 MODEL_FAIL=0') {throw ($taskEntry.Name+': '+$taskResult)}
    if($taskResult -notmatch ('TOTAL='+$taskEntry.Value+' ')) {throw '回路行数不一致'}
    $taskResults[$taskEntry.Name]=$taskResult.Trim()
}
$taskReport.native_validation=$taskResults
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
    $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
    if($taskSerializer) {break}
}
if(!$taskSerializer) {throw '変数読込みクラスなし'}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskFound=@{}
$taskArchive=[IO.Compression.ZipFile]::OpenRead($taskReport.staged)
try {
    foreach($taskEntryName in @($taskReport.new_declarations.entry | Select-Object -Unique)) {
        $taskStream=$taskArchive.GetEntry($taskEntryName).Open()
        try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
        foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVariable in $taskGroup.Children) {
            $taskName=$taskVariable.Item('N')
            $taskExpected=@($taskReport.new_declarations | Where-Object {$_.entry -eq $taskEntryName -and $_.name -eq $taskName})
            if(!$taskExpected.Count) {continue}
            if($taskExpected.Count -ne 1) {throw ('検証リスト重複 '+$taskName)}
            $taskKey=$taskEntryName+'|'+$taskName
            if($taskFound.ContainsKey($taskKey)) {throw ('変数宣言重複 '+$taskName)}
            if($taskVariable.Item('D').ToUpperInvariant() -ne $taskExpected[0].type.ToUpperInvariant()) {throw ('型不一致 '+$taskName)}
            foreach($taskAttrKey in @('Const','RO')) {
                $taskAttr=$taskVariable.GetAttribute($taskAttrKey)
                if($null -eq $taskAttr -or $taskAttr.BoolValue) {throw ('定数/読取専用属性不正 '+$taskName+' '+$taskAttrKey)}
            }
            if($taskVariable.Item('AT')) {throw ('意図しない割付 '+$taskName)}
            $taskFound[$taskKey]=$taskVariable.Item('D')
        }}}
    }
} finally {$taskArchive.Dispose()}
if($taskFound.Count -ne $taskReport.new_declarations.Count) {throw '新規変数検査件数不一致'}
$taskReport.native_variables=[ordered]@{
    loader='メーカー同梱SSLightweightDataSerializer'
    new_declarations=$taskFound.Count
    constant_and_readonly_false=$true
    full_application_build_verified=$false
}
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output ('全'+$taskResults.Count+'セクション：解析・モデル変換失敗0、新規宣言'+$taskFound.Count+'件：型・定数・読取専用を確認')
