# MHP3rd DLC English Localizer v1.0.0 — complete Windows x64 release builder.
# Run ONLY this command from the extracted source folder:
#   .\Build_Windows_EXE.ps1
# It builds both EXEs and automatically creates the seven-file END-USER ZIP.
# No previous build, old release ZIP, or separate packaging command is required.
# Build tools remain in .build-venv/; temporary binaries under .build/. Neither is shipped.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = $PSScriptRoot
$Version = '1.0.0'
$BuildRoot = Join-Path $Root '.build'
$Venv = Join-Path $Root '.build-venv' # reuse the previously installed private build environment when present
$Python = Join-Path $Venv 'Scripts\python.exe'
$BinaryDir = Join-Path $BuildRoot 'compiled-exes'
$ReleaseDir = Join-Path $Root 'Release'

function Require-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required builder input is missing: $Path"
    }
    return (Resolve-Path -LiteralPath $Path).Path
}
function Run-Checked([string]$Executable, [string[]]$Arguments, [string]$Failure) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Failure (exit code $LASTEXITCODE)" }
}

Set-Location -LiteralPath $Root
Write-Host 'MHP3rd DLC English Localizer v1.0.0 — FINAL WINDOWS BUILDER'
Write-Host 'Building both standalone executables and a clean end-user ZIP.'
Write-Host ''

$Catalog = Require-File (Join-Path $Root 'catalog.json')
$MainEntry = Require-File (Join-Path $Root 'MHP3rd_Localizer.pyw')
$RestoreEntry = Require-File (Join-Path $Root 'MHP3rd_Recovery.py')
$MainVersion = Require-File (Join-Path $Root 'WindowsVersion_localizer.txt')
$RestoreVersion = Require-File (Join-Path $Root 'WindowsVersion_recovery.txt')
$Requirements = Require-File (Join-Path $Root 'requirements-build.txt')
$Packager = Require-File (Join-Path $Root 'release_packager.py')
$ExpectedHash = (Get-Content -LiteralPath (Require-File (Join-Path $Root 'CATALOG_SHA256.expected')) -Raw).Trim().ToUpperInvariant()
$ActualHash = (Get-FileHash -LiteralPath $Catalog -Algorithm SHA256).Hash.ToUpperInvariant()
if ($ExpectedHash -ne $ActualHash) {
    throw 'Translation catalog does not match frozen v1.0.0 baseline. No build was started.'
}
foreach ($Filename in @('END_USER_README.md', 'RECOVERY_MANUAL.md', 'LICENSE_GPLv3.txt',
                        'THIRD_PARTY_TRANSLATION_RIGHTS.md', 'RELEASE_NOTES_v1.0.0.md')) {
    $null = Require-File (Join-Path $Root $Filename)
}

New-Item -ItemType Directory -Force -Path $BuildRoot, $ReleaseDir | Out-Null
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    Write-Host '[1/4] Creating isolated Python 3.15 build environment...'
    & py -3.15 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create private Python build environment.' }
}
$CheckPython = 'import sys; assert sys.version_info[:3] == (3,15,2), "Python 3.15.2 is required"; assert sys.maxsize > 2**32, "64-bit Python is required"'
Run-Checked $Python @('-c', $CheckPython) 'Python version check failed'

Write-Host '[1/4] Checking isolated build dependencies...'
Run-Checked $Python @('-m','pip','install','--disable-pip-version-check','--only-binary=:all:', '-r',$Requirements) 'Dependency setup failed'
Run-Checked $Python @('-m','pip','check') 'Build dependencies are inconsistent'
Run-Checked $Python @('-c','import cryptography,PyInstaller; assert cryptography.__version__=="50.0.2"; assert PyInstaller.__version__=="6.22.3"') 'Pinned build dependency mismatch'

# Absolute entrypoint/catalog paths prevent the old build-spec/catalog.json issue.
$Common = @('--noconfirm', '--clean', '--noupx',
            '--workpath', (Join-Path $BuildRoot 'work'),
            '--specpath', (Join-Path $BuildRoot 'spec'),
            '--distpath', $BinaryDir,
            '--paths', $Root)
$BundledCatalog = "$Catalog;."
Write-Host '[2/4] Building standalone localizer...'
Run-Checked $Python (@('-m','PyInstaller') + $Common + @('--onefile','--windowed',
    '--name','MHP3rd_DLC_Localizer','--version-file',$MainVersion,
    '--add-data',$BundledCatalog,$MainEntry)) 'Localizer EXE build failed'

Write-Host '[3/4] Building standalone recovery utility...'
Run-Checked $Python (@('-m','PyInstaller') + $Common + @('--onefile','--console',
    '--name','MHP3rd_Recovery','--version-file',$RestoreVersion,
    $RestoreEntry)) 'Recovery EXE build failed'

foreach ($Name in @('MHP3rd_DLC_Localizer.exe', 'MHP3rd_Recovery.exe')) {
    $Exe = Require-File (Join-Path $BinaryDir $Name)
    $FileVersion = (Get-Item -LiteralPath $Exe).VersionInfo.FileVersion
    if ($FileVersion -ne '1.0.0.0') {
        throw "Incorrect version for $Name`: $FileVersion (expected 1.0.0.0)"
    }
}

Write-Host '[4/4] Packaging only end-user files...'
Run-Checked $Python @($Packager, '--source-root',$Root,
    '--exe-dir',$BinaryDir,'--output-dir',$ReleaseDir) 'End-user package creation failed'

$Zip = Join-Path $ReleaseDir 'MHP3rd_DLC_Localizer_v1.0.0_Windows_x64.zip'
$Checksum = "$Zip.sha256"
if (-not (Test-Path -LiteralPath $Zip -PathType Leaf) -or
    -not (Test-Path -LiteralPath $Checksum -PathType Leaf)) {
    throw 'Release package/checksum missing after packaging.'
}
Write-Host ''
Write-Host 'SUCCESS — final end-user release is ready:' -ForegroundColor Green
Write-Host "  $Zip"
Write-Host "  $Checksum"
Write-Host 'The ZIP has exactly 7 end-user files. No build files are inside.'
Write-Host 'The source and build intermediates stay in their own folders.'
Write-Host 'Review translation redistribution rights before publishing publicly.'
