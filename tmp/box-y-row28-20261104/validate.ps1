# メーカー同梱処理で29行の読込みと28行目STの入力接続を確認する。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskMetaPath=Join-Path (Get-Location) 'tmp/box-y-row28-20261104/verification.json'
$taskMeta=Get-Content -LiteralPath $taskMetaPath -Encoding UTF8 -Raw | ConvertFrom-Json
$taskResult=[NativeLadderCheck]::Check($taskMeta.staged,$taskMeta.target)
if($taskResult -notmatch 'TOTAL=29 PARSE_FAIL=0 MODEL_FAIL=0') {throw $taskResult}
$taskAssembly=[Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\OMRON\Sysmac Studio\Modules\Nex\NexProgramming.dll')
$taskParserType=$taskAssembly.GetType('NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToStringConverter')
$taskConverterType=$taskAssembly.GetType('NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToNormalRungConverter')
$taskParser=[Activator]::CreateInstance($taskParserType)
$taskZip=[IO.Compression.ZipFile]::OpenRead($taskMeta.staged)
try {
 $taskReader=[IO.StreamReader]::new($taskZip.GetEntry($taskMeta.target).Open(),[Text.Encoding]::UTF8,$true)
 try {$taskText=$taskReader.ReadToEnd()} finally {$taskReader.Dispose()}
} finally {$taskZip.Dispose()}
$taskLines=$taskText.Trim().Split([char]10)
$taskParseArgs=[object[]]@($taskLines[28],$null)
if(-not $taskParserType.GetMethod('TryConvertBack').Invoke($taskParser,$taskParseArgs)) {throw '28行目解析失敗'}
$taskConverter=[Activator]::CreateInstance($taskConverterType,[object[]]@($taskParseArgs[1]))
$taskOutput=[object[]]@($null)
if(-not $taskConverterType.GetMethod('TryConvert').Invoke($taskConverter,$taskOutput)) {throw '28行目変換失敗'}
$taskCount=0
$taskEdges=0
foreach($taskNode in $taskOutput[0].DiagramNodes) {
 if($taskNode.GetType().Name -ne 'InlineStructuredTextModel') {continue}
 $taskCount++
 foreach($taskPoint in $taskNode.ConnectionPoints) {if($taskPoint.IsInputConnection) {$taskEdges+=@($taskPoint.Edges).Count}}
}
if($taskCount -ne 1 -or $taskEdges -ne 1) {throw '28行目STの数または接続数が不一致'}
$taskMeta.native_validation=[ordered]@{box_section=$taskResult.Trim();row28_IST_input_edges=$taskEdges;application_build_verified=$false}
[IO.File]::WriteAllText($taskMetaPath,($taskMeta|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output $taskResult
Write-Output ('28行目ST数='+$taskCount+' 入力接続数='+$taskEdges)
