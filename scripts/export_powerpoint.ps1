param(
    [Parameter(Mandatory=$true)][string]$InputPath,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
# Never connect to or close a user's existing PowerPoint session.
if (Get-Process -Name POWERPNT -ErrorAction SilentlyContinue) {
    throw 'PowerPoint is already open. Use LibreOffice, or close PowerPoint yourself before retrying.'
}
$sourcePath = (Resolve-Path -LiteralPath $InputPath).Path
$targetPath = [System.IO.Path]::GetFullPath($OutputPath)
if ([System.IO.Path]::GetExtension($sourcePath) -ne '.pptx' -or [System.IO.Path]::GetExtension($targetPath) -ne '.pdf') {
    throw 'Expected a .pptx input and a separate .pdf output.'
}
$pptApp = $null
$deck = $null
$owned = $false
try {
    $pptApp = New-Object -ComObject PowerPoint.Application
    if ($pptApp.Presentations.Count -ne 0) { throw 'An existing presentation session was found; export stopped.' }
    $owned = $true
    # ReadOnly=true, Untitled=false, WithWindow=false.
    $deck = $pptApp.Presentations.Open($sourcePath, -1, 0, 0)
    $deck.SaveAs($targetPath, 32)
    if (-not (Test-Path -LiteralPath $targetPath)) { throw 'PowerPoint did not create the PDF.' }
} finally {
    if ($null -ne $deck) {
        $deck.Close()
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($deck)
    }
    if ($null -ne $pptApp) {
        if ($owned -and $pptApp.Presentations.Count -eq 0) { $pptApp.Quit() }
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($pptApp)
    }
}
