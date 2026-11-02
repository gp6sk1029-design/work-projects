$ErrorActionPreference = 'Stop'
$dir = $PSScriptRoot
$target = Get-ChildItem -LiteralPath $dir -Filter '*_循環参照修正.xlsx' | Select-Object -First 1
$copy = Join-Path $dir 'native_verification.xlsx'
Copy-Item -LiteralPath $target.FullName -Destination $copy
$excel = $null
$book = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.EnableEvents = $false
    $excel.AutomationSecurity = 3
    $book = $excel.Workbooks.Open($copy,0,$false)
    $excel.CalculateFullRebuild()
    $cycles = @()
    foreach ($sheet in $book.Worksheets) {
        $sheet.Activate()
        $circle = $excel.CircularReference
        if ($null -ne $circle) { $cycles += ($sheet.Name + '!' + $circle.Address()) }
    }
    if ($cycles.Count -ne 0) { throw ('循環参照が残存: ' + ($cycles -join ',')) }
    $inputCell = $book.Worksheets.Item('PLC・軸').Range('B2')
    $original = $inputCell.Value2
    $inputCell.Value2 = '循環参照修正_再計算検証'
    $excel.CalculateFullRebuild()
    if ($book.Worksheets.Item('IO').Range('B2').Value2 -ne '循環参照修正_再計算検証') { throw '参照の再計算に失敗' }
    $inputCell.Value2 = $original
    $excel.CalculateFullRebuild()
    $book.Save()
    $book.Close($false)
    $book = $excel.Workbooks.Open($copy,0,$true)
    $excel.CalculateFullRebuild()
    foreach ($sheet in $book.Worksheets) {
        $sheet.Activate()
        if ($null -ne $excel.CircularReference) { throw '再オープン後に循環参照を検出' }
    }
    Write-Output 'Excel検証成功: 全4シート循環参照なし、入力変更の再計算成功、保存後の再オープン成功'
} finally {
    if ($null -ne $book) { $book.Close($false) }
    if ($null -ne $excel) { $excel.Quit(); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
