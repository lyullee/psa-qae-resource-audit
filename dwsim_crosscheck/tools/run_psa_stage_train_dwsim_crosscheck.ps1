param(
    [Parameter(Mandatory = $true)][string]$DwsimDirectory,
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$InputDeck,
    [Parameter(Mandatory = $true)][string]$ResultsCsv,
    [Parameter(Mandatory = $true)][string]$StreamsCsv,
    [Parameter(Mandatory = $true)][string]$SavedCaseDirectory,
    [Parameter(Mandatory = $false)][string]$FileStorageAssembly = ''
)

$ErrorActionPreference = 'Stop'
$DwsimDirectory = (Resolve-Path -LiteralPath $DwsimDirectory).Path
$Source = (Resolve-Path -LiteralPath $Source).Path
$InputDeck = (Resolve-Path -LiteralPath $InputDeck).Path
$ResultsCsv = [IO.Path]::GetFullPath($ResultsCsv)
$StreamsCsv = [IO.Path]::GetFullPath($StreamsCsv)
$SavedCaseDirectory = [IO.Path]::GetFullPath($SavedCaseDirectory)
Set-Location -LiteralPath $DwsimDirectory

$toolDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceCode = Get-Content -Raw -LiteralPath (Join-Path $toolDirectory 'DwsimPsaStageTrainCrosscheck.cs')
$references = @(
    (Join-Path $DwsimDirectory 'CapeOpen.dll'),
    (Join-Path $DwsimDirectory 'DWSIM.Interfaces.dll'),
    (Join-Path $DwsimDirectory 'DWSIM.SharedClasses.dll'),
    (Join-Path $DwsimDirectory 'DWSIM.Thermodynamics.dll'),
    (Join-Path $DwsimDirectory 'DWSIM.UnitOperations.dll'),
    (Join-Path $DwsimDirectory 'DWSIM.Automation.dll')
)
foreach ($reference in $references) {
    [Reflection.Assembly]::LoadFrom($reference) | Out-Null
}
$supportAssemblies = @(
    (Join-Path $DwsimDirectory 'Eto.dll'),
    (Join-Path $DwsimDirectory 'LiteDB.dll'),
    (Join-Path $DwsimDirectory 'System.Runtime.dll'),
    (Join-Path $DwsimDirectory 'System.IO.dll'),
    (Join-Path $DwsimDirectory 'netstandard.dll')
)
foreach ($supportAssembly in $supportAssemblies) {
    if (Test-Path -LiteralPath $supportAssembly) {
        [Reflection.Assembly]::LoadFrom($supportAssembly) | Out-Null
    }
}
if (-not [string]::IsNullOrWhiteSpace($FileStorageAssembly)) {
    $FileStorageAssembly = (Resolve-Path -LiteralPath $FileStorageAssembly).Path
    $loadedFileStorage = [Reflection.Assembly]::LoadFrom($FileStorageAssembly)
    if ($loadedFileStorage.GetName().Name -ne 'DWSIM.FileStorage' -or $loadedFileStorage.GetName().Version.ToString() -ne '8.7.1.0') {
        throw "Unexpected DWSIM.FileStorage identity: $($loadedFileStorage.FullName)"
    }
}
$thermoCs = Join-Path $DwsimDirectory 'ThermoCS\ThermoCS.dll'
if (Test-Path -LiteralPath $thermoCs) {
    [Reflection.Assembly]::LoadFrom($thermoCs) | Out-Null
}
Add-Type -TypeDefinition $sourceCode -ReferencedAssemblies $references -Language CSharp

[DwsimPsaStageTrainCrosscheck]::Run(
    $Source,
    $InputDeck,
    $ResultsCsv,
    $StreamsCsv,
    $SavedCaseDirectory
)
