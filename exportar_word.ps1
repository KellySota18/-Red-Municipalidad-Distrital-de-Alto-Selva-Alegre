$ErrorActionPreference = 'Stop'

$base = 'C:\Users\Lenovo\Downloads\documentacion'
$files = @(
    @{
        Docx = Join-Path $base '01_Manual_de_Usuario.docx'
        Pdf  = Join-Path $base '01_Manual_de_Usuario.pdf'
    },
    @{
        Docx = Join-Path $base '02_Manual_de_Instalacion_y_Despliegue.docx'
        Pdf  = Join-Path $base '02_Manual_de_Instalacion_y_Despliegue.pdf'
    }
)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$word.AutomationSecurity = 3

try {
    foreach ($file in $files) {
        $doc = $word.Documents.Open($file.Docx, $false, $false, $false)
        try {
            $doc.Fields.Update() | Out-Null
            if ($doc.TablesOfContents.Count -gt 0) {
                $doc.TablesOfContents.Item(1).Update() | Out-Null
            }
            $doc.Repaginate()
            $doc.Save()
            $pages = $doc.ComputeStatistics(2)
            $tempPdf = Join-Path $env:TEMP ('opencode_' + [System.IO.Path]::GetFileName($file.Pdf))
            if (Test-Path -LiteralPath $tempPdf) {
                Remove-Item -LiteralPath $tempPdf -Force
            }
            $doc.ExportAsFixedFormat(
                $tempPdf,
                17,
                $false,
                0,
                0,
                1,
                1,
                0,
                $true,
                $true,
                1,
                $true,
                $true,
                $false
            )
            if (Test-Path -LiteralPath $file.Pdf) {
                Remove-Item -LiteralPath $file.Pdf -Force
            }
            Move-Item -LiteralPath $tempPdf -Destination $file.Pdf -Force
            Write-Output ("{0}: {1} paginas -> {2}" -f (Split-Path $file.Docx -Leaf), $pages, (Split-Path $file.Pdf -Leaf))
        }
        finally {
            $doc.Close($false)
        }
    }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
