param([string]$ProjectPath='C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261026E.smc2')
# オフラインでメーカーの変数表読込みだけを呼び、定数属性の解釈を確認する。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskFormatterType=$taskNexAssembly.GetType('Omron.Cxap.Modules.NexVariable.Persisters.NexSSLightweightDataVariableFormatter')
$taskFormatter=[Runtime.Serialization.FormatterServices]::GetUninitializedObject($taskFormatterType)
$taskMethod=$taskFormatterType.GetMethod('InnerLoadFrom',[Reflection.BindingFlags]'Instance,NonPublic')
$taskArchive=[IO.Compression.ZipFile]::OpenRead($ProjectPath)
try {
    foreach($taskEntry in $taskArchive.Entries | Where-Object {$_.FullName.EndsWith('86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml') -or $_.FullName.EndsWith('f07dd06c-505c-431b-b9fc-098949805b4e.xml')}) {
        $taskStream=$taskEntry.Open()
        try {
            $taskResult=$taskMethod.Invoke($taskFormatter,[object[]]@($taskStream))
            Write-Output ($taskEntry.FullName+' RESULT '+$taskResult.GetType().FullName)
            $taskResult.GetType().GetProperties() | ForEach-Object ToString
            foreach($taskGroup in $taskResult) {
                Write-Output ('GROUP '+$taskGroup.GetType().FullName)
                $taskGroup.GetType().GetProperties() | ForEach-Object ToString
            }
        } catch {
            $taskError=$_.Exception
            while($taskError.InnerException) {$taskError=$taskError.InnerException}
            Write-Output $taskError.ToString()
        } finally {$taskStream.Dispose()}
    }
} finally {$taskArchive.Dispose()}
