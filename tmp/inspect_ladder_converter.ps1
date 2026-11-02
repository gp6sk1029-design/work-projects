# Sysmacの同梱DLLを読み、公開変換APIの形だけを確認する。
$taskOmronBase='C:\Program Files (x86)\OMRON\Sysmac Studio'
$taskNexAssembly=[Reflection.Assembly]::LoadFrom((Join-Path $taskOmronBase 'Modules\Nex\NexProgramming.dll'))
for($taskAttempt=0;$taskAttempt -lt 40;$taskAttempt++) {
    try { $taskNexTypes=$taskNexAssembly.GetExportedTypes(); break }
    catch {
        $taskError=$_.Exception
        while($taskError.InnerException) { $taskError=$taskError.InnerException }
        if($taskError -is [IO.FileNotFoundException] -and $taskError.FileName) {
            $taskDependency=Join-Path $taskOmronBase ($taskError.FileName.Split(',')[0]+'.dll')
            if(Test-Path -LiteralPath $taskDependency) { $null=[Reflection.Assembly]::LoadFrom($taskDependency) }
            else { throw }
        } else { throw }
    }
}
foreach($taskType in $taskNexTypes | Where-Object FullName -match 'CompactRungToNormalRungConverter$|NormalRungToCompactRungConverter$|CompactRungToStringConverter$|Model.CompactRung$|CompactLadderPersister$|CompactLadderPersistResult$') {
    $taskType.FullName
    $taskType.GetConstructors() | ForEach-Object ToString
    $taskType.GetMethods() | Where-Object DeclaringType -eq $taskType | ForEach-Object ToString
    $taskType.GetProperties() | ForEach-Object ToString
}
