param([string]$ProjectPath='C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261026E.smc2')
# アプリを起動せず、メーカー同梱のSLWD構文読込みで属性の実値を調べる。
$ErrorActionPreference='Stop'
. ([ScriptBlock]::Create((Get-Content -LiteralPath 'tmp/inspect_ladder_converter.ps1' -Raw -Encoding UTF8))) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskLoaderType=$null
foreach($taskAssembly in [AppDomain]::CurrentDomain.GetAssemblies()) {
    $taskLoaderType=$taskAssembly.GetType('Omron.Cxap.DataLayer.Persistence.Serializers.LightweightData.SSLightweightDataSerializer')
    if($taskLoaderType) {break}
}
$taskLoad=$taskLoaderType.GetMethod('Load',[Reflection.BindingFlags]'Static,Public,NonPublic',$null,[type[]]@([IO.Stream]),$null)
$taskArchive=[IO.Compression.ZipFile]::OpenRead($ProjectPath)
try {
 foreach($taskEntry in $taskArchive.Entries | Where-Object {$_.FullName.EndsWith('86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml') -or $_.FullName.EndsWith('f07dd06c-505c-431b-b9fc-098949805b4e.xml')}) {
    $taskStream=$taskEntry.Open()
    try {$taskData=$taskLoad.Invoke($null,[object[]]@($taskStream))} finally {$taskStream.Dispose()}
    foreach($taskRoot in $taskData.RootElements) {foreach($taskGroup in $taskRoot.Children) {foreach($taskVariable in $taskGroup.Children) {
        $taskName=$taskVariable.Item('N')
        if($taskName -in @('ST4_A_Rev1_M','ST6_A_Rev2_M','Stm_A_Rev_Axis001_Auto','Stm_A_Rev_Axis001')) {
            Write-Output ($taskEntry.FullName+' NAME='+$taskName)
            foreach($taskKey in @('D','G','Const','RO','Com')) {
                $taskAttr=$taskVariable.GetAttribute($taskKey)
                Write-Output ($taskKey+'='+$taskVariable.Item($taskKey)+' BOOL='+$(if($taskAttr){$taskAttr.BoolValue}else{'<属性なし>'}))
            }
        }
    }}}
 }
} finally {$taskArchive.Dispose()}
