# メーカー同梱処理で箱詰め回路と追加STの接続を検査する。実機・画面操作なし。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -Path 'tmp/NativeLadderCheck.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
Add-Type -Path 'tmp/j-crash-diagnosis-20261029/NativeConnectionAudit.cs' -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')
$taskMetaPath=Join-Path (Get-Location) 'tmp/box-x-st-20261104/verification.json'
$taskMeta=Get-Content -LiteralPath $taskMetaPath -Encoding UTF8 -Raw | ConvertFrom-Json
$taskResult=[NativeLadderCheck]::Check($taskMeta.staged,$taskMeta.target)
if($taskResult -notmatch 'TOTAL=28 PARSE_FAIL=0 MODEL_FAIL=0') {throw $taskResult}
$taskConnections=[NativeConnectionAudit]::Check($taskMeta.staged)
if($taskConnections -notmatch 'MISSING=0 PARSE_MODEL_FAIL=0') {throw $taskConnections}

$taskAssembly=[Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\OMRON\Sysmac Studio\Modules\Nex\NexProgramming.dll')
$taskParserType=$taskAssembly.GetType('NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToStringConverter')
$taskConverterType=$taskAssembly.GetType('NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToNormalRungConverter')
$taskParser=[Activator]::CreateInstance($taskParserType)
$taskZip=[IO.Compression.ZipFile]::OpenRead($taskMeta.staged)
try {
 $taskEntry=$taskZip.GetEntry($taskMeta.target)
 $taskReader=[IO.StreamReader]::new($taskEntry.Open(),[Text.Encoding]::UTF8,$true)
 try {$taskText=$taskReader.ReadToEnd()} finally {$taskReader.Dispose()}
} finally {$taskZip.Dispose()}
$taskLines=$taskText.Trim().Split([char]10)
$taskParseArgs=[object[]]@($taskLines[27],$null)
if(-not $taskParserType.GetMethod('TryConvertBack').Invoke($taskParser,$taskParseArgs)) {throw '27行目解析失敗'}
$taskConverter=[Activator]::CreateInstance($taskConverterType,[object[]]@($taskParseArgs[1]))
$taskOutput=[object[]]@($null)
if(-not $taskConverterType.GetMethod('TryConvert').Invoke($taskConverter,$taskOutput)) {throw '27行目変換失敗'}
$taskNodes=@()
foreach($taskNode in $taskOutput[0].DiagramNodes) {
 $taskInputEdges=0
 foreach($taskPoint in $taskNode.ConnectionPoints) {if($taskPoint.IsInputConnection) {$taskInputEdges+=@($taskPoint.Edges).Count}}
 $taskNodes+= [ordered]@{type=$taskNode.GetType().Name;input_edges=$taskInputEdges}
}
$taskMeta.native_validation=[ordered]@{box_section=$taskResult.Trim();connections=$taskConnections.Trim();row27_nodes=$taskNodes;application_build_verified=$false}
[IO.File]::WriteAllText($taskMetaPath,($taskMeta|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output $taskResult
Write-Output $taskConnections
Write-Output ($taskNodes|ConvertTo-Json -Compress)
