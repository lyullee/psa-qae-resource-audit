param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'results\spt_pressure_consistent_manuscript_v2\SPT_PRESSURE_CONSISTENT_MANUSCRIPT.docx'
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null
$target = Join-Path $resolvedOutput 'SPT_PRESSURE_CONSISTENT_MANUSCRIPT.pdf'
$hashBefore = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open($source, $false, $true, $false)
    try {
        $document.Repaginate()
        $pageCount = $document.ComputeStatistics(2)
        $document.ExportAsFixedFormat($target, 17)
    } finally {
        $document.Close(0)
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($document)
    }
} finally {
    $word.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
$hashAfter = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if ($hashBefore -ne $hashAfter) {
    throw 'Read-only export changed source document'
}
[pscustomobject]@{
    Source = $source
    SourceSHA256 = $hashAfter
    PDF = $target
    Pages = $pageCount
}
