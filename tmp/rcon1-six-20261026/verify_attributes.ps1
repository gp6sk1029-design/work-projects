# メーカー同梱SLWD読込みで、新規の軸変数とタイマーが書込み可能な属性であることを検査する。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskReportPath=Join-Path (Get-Location) 'tmp/rcon1-six-20261026/verification.json'
$taskReport=Get-Content -LiteralPath $taskReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskSerializer=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
    $taskSerializer=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
    if($taskSerializer) {break}
}
$taskLoad=$taskSerializer.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskCounts=[ordered]@{global=0;external=0;local_timer=0}
$taskNames=[Collections.Generic.HashSet[string]]::new()
$taskArchive=[IO.Compression.ZipFile]::OpenRead($taskReport.staged)
try {
 foreach($taskEntry in $taskArchive.Entries | Where-Object {$_.FullName.EndsWith('a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml') -or $_.FullName.EndsWith('f07dd06c-505c-431b-b9fc-098949805b4e.xml')}) {
    $taskStream=$taskEntry.Open()
    try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
    foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVariable in $taskGroup.Children) {
        $taskName=$taskVariable.Item('N')
        if($taskName -notmatch '^RCON1_[2-6]_') {continue}
        foreach($taskKey in @('Const','RO')) {
            $taskAttr=$taskVariable.GetAttribute($taskKey)
            if($null -eq $taskAttr -or $taskAttr.BoolValue -ne $false) {throw ($taskName+': '+$taskKey+'が明示FALSEではありません')}
        }
        $taskG=$taskVariable.Item('G')
        if($taskG -eq 'VAR_GLOBAL') {$taskCounts.global++}
        elseif($taskG -eq 'VAR_EXTERNAL') {$taskCounts.external++}
        elseif($taskG -eq 'VAR' -and $taskName -match '_TO[NF]$') {$taskCounts.local_timer++}
        else {throw ('想定外のスコープ '+$taskName+' '+$taskG)}
        $null=$taskNames.Add($taskName)
    }}}
 }
} finally {$taskArchive.Dispose()}
if($taskCounts.global -ne 135 -or $taskCounts.external -ne 135 -or $taskCounts.local_timer -ne 10) {throw '検査数が不一致'}
$taskResult=[ordered]@{loader='メーカー同梱SSLightweightDataSerializer';counts=$taskCounts;unique_names=$taskNames.Count;all_new_const_false=$true;all_new_readonly_false=$true;full_application_build_verified=$false}
$taskReport.native_variable_attributes=$taskResult
[IO.File]::WriteAllText($taskReportPath,($taskReport | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
$taskResult | ConvertTo-Json -Depth 8
