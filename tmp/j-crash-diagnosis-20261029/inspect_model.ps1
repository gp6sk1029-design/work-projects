# 元ファイルは変更せず、メーカー変換後モデルの参照と接続を読み取る。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskPrevious=Get-Content -LiteralPath 'tmp/section-organize-20261028/verification.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$taskPath=$taskPrevious.destination
$taskArchive=[IO.Compression.ZipFile]::OpenRead($taskPath)
try {
 $taskEntry=$taskArchive.Entries | Where-Object {$_.FullName.EndsWith('78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4.xml')}
 $taskReader=[IO.StreamReader]::new($taskEntry.Open(),[Text.Encoding]::UTF8,$true)
 try {$taskLines=$taskReader.ReadToEnd() -split '\r?\n' | Where-Object {$_.Trim()}} finally {$taskReader.Dispose()}
 $taskStrings=$taskNexAssembly.GetType('NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToStringConverter')
 $taskNormal=$taskNexAssembly.GetType('NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToNormalRungConverter')
 $taskParser=[Activator]::CreateInstance($taskStrings)
 $taskArgs=[object[]]@([string]$taskLines[11],$null)
 $null=$taskStrings.GetMethod('TryConvertBack').Invoke($taskParser,$taskArgs)
 $taskConverter=[Activator]::CreateInstance($taskNormal,[object[]]@($taskArgs[1]))
 $taskOutput=[object[]]@($null)
 $taskOK=$taskNormal.GetMethod('TryConvert').Invoke($taskConverter,$taskOutput)
 $taskModel=$taskOutput[0]
 Write-Output ('MODEL '+$taskModel.GetType().FullName+' OK='+$taskOK)
 $taskNodes=$taskModel.GetType().GetProperties() | Where-Object {$_.Name -eq 'DiagramNodes'}
 foreach($taskProp in $taskNodes) {
  foreach($taskNode in $taskProp.GetValue($taskModel,$null)) {
   if($taskNode.GetType().Name -ne 'Coil') {continue}
   Write-Output ('COIL_SUMMARY '+[string]$taskNode+' POINTS='+$taskNode.ConnectionPoints.Count+' '+(@($taskNode.ConnectionPoints | ForEach-Object {([string]$_.IsInputConnection)+':'+$_.Edges.Count}) -join ','))
   continue
   Write-Output ('NODE '+$taskNode.GetType().FullName+' '+[string]$taskNode)
   foreach($taskP in $taskNode.GetType().GetProperties()) {
    try {$taskV=$taskP.GetValue($taskNode,$null);Write-Output (' '+$taskP.Name+' '+$taskP.PropertyType.FullName+' '+[string]$taskV)}catch{}
   }
   foreach($taskCP in $taskNode.ConnectionPoints) {
    Write-Output (' CP '+$taskCP.GetType().FullName)
    foreach($taskP in $taskCP.GetType().GetProperties()) {
     try {$taskV=$taskP.GetValue($taskCP,$null);Write-Output ('  '+$taskP.Name+' '+$taskP.PropertyType.Name+' '+[string]$taskV)}catch{}
    }
    foreach($taskEdge in $taskCP.Edges) {
     Write-Output (' EDGE '+$taskEdge.GetType().FullName)
     foreach($taskP in $taskEdge.GetType().GetProperties()) {
      try {$taskV=$taskP.GetValue($taskEdge,$null);Write-Output ('  '+$taskP.Name+' '+$taskP.PropertyType.Name+' '+[string]$taskV)}catch{}
     }
    }
   }
   if([string]$taskNode -match 'HMI_Message_Request\[101\]') {break}
  }
 }
} finally {$taskArchive.Dispose()}
