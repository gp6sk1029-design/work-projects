$ErrorActionPreference='Stop'
$source='\\nas-ime5\生産技術部\2.見積 決裁願\見積\1_見積依頼書\2026\@【見積依頼書】_原紙.xls'
$converted=Join-Path $PSScriptRoot 'template.xlsx'
$excel=New-Object -ComObject Excel.Application
$excel.Visible=$false
$excel.DisplayAlerts=$false
$excel.AutomationSecurity=3
$book=$null
try {
    $book=$excel.Workbooks.Open($source,0,$true)
    $details=foreach($sheet in $book.Worksheets){
        $cells=foreach($cell in $sheet.UsedRange.Cells){if($null -ne $cell.Value2){[pscustomobject]@{Address=$cell.Address($false,$false);Value=$cell.Value2;Merge=$cell.MergeArea.Address($false,$false)}}}
        [pscustomobject]@{Sheet=$sheet.Name;Used=$sheet.UsedRange.Address($false,$false);PrintArea=$sheet.PageSetup.PrintArea;Cells=@($cells)}
    }
    $details | ConvertTo-Json -Depth 6
    if(Test-Path -LiteralPath $converted){throw '中間ファイルが既に存在します。'}
    $book.SaveAs($converted,51)
} finally {
    if($null -ne $book){$book.Close($false)}
    $excel.Quit()
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel)
}
