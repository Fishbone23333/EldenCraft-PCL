param([string]$PythonCommand = 'python')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'paths.ps1')
$paths = Read-PclPaths
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $repo 'scripts/windows.ps1') -Mode check -NonInteractive
$releaseRoot = $paths.release_root
$dataRoot = $paths.data_root
$game = Find-EldenRing $paths.game_path $null $repo
if (-not $game) { throw 'Elden Ring not found. Set game_path in trials/pcl-adapter/local.json.' }
if (-not (Test-Path -LiteralPath (Join-Path $paths.pcl_root 'Plain Craft Launcher 2.exe'))) {
    throw 'Set pcl_root in trials/pcl-adapter/local.json to the folder containing Plain Craft Launcher 2.exe.'
}
& $PythonCommand -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12 or later is required"'
if ($LASTEXITCODE) { throw 'Python 3.12 or later is required. Use -PythonCommand to specify its executable.' }
Assert-GamesClosed (Join-Path $paths.pcl_root '.minecraft') (Join-Path $dataRoot 'tools/prism-11.1.1/prismlauncher.exe')
if (Get-Process javaw,eldenring -ErrorAction SilentlyContinue) { throw 'Close Minecraft and Elden Ring before setup.' }
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
$lock = [IO.File]::Open((Join-Path $dataRoot 'setup.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
try {
    $cache = Join-Path $dataRoot 'downloads'
    if (-not (Test-Path -LiteralPath (Join-Path $releaseRoot 'release-manifest.json'))) {
        $archive = Get-VerifiedDownload $cache 'EldenCraft-0.25.5-windows-x64.zip' `
            'https://github.com/SocketByte/EldenCraft/releases/download/v0.25.5/EldenCraft-0.25.5-windows-x64.zip' `
            '2cedbfe5c93482a0e98505f8db6f130158169eff626e5c1101bd2633e5c758b9'
        if ((Test-Path -LiteralPath $releaseRoot) -and @(Get-ChildItem -LiteralPath $releaseRoot -Force).Count) {
            throw 'Release folder exists but has no manifest. Use an empty release_root or the official extracted release.'
        }
        Expand-Archive -LiteralPath $archive -DestinationPath $releaseRoot
    }
    $release = Read-Release $releaseRoot
    $deps = $release.Dependencies
    Assert-FileHash $game $deps.elden_ring.sha256
    $runtime = Join-Path $dataRoot 'runtime'
    Assert-NoReShadeConflict $game $runtime
    $backups = Join-Path $dataRoot 'backups'
    New-VerifiedBackup (Join-Path $env:APPDATA 'EldenRing') $backups 'elden-ring' | Out-Null
    New-VerifiedBackup (Join-Path $runtime 'data/campaign') $backups 'campaign' | Out-Null
    $tools = Join-Path $dataRoot 'tools'
    foreach ($name in @('java', 'me3')) {
        $dependency = $deps.$name
        $archive = Get-VerifiedDownload $cache "$name-$($dependency.version).zip" $dependency.url $dependency.sha256
        $destination = Join-Path $tools "$name-$($dependency.version)"
        Expand-VerifiedArchive $archive $destination $dependency.sha256 $dependency.executable | Out-Null
    }
    $installer = Get-VerifiedDownload $cache "ReShade-$($deps.reshade.version)-Addon.exe" $deps.reshade.url $deps.reshade.sha256
    $reshade = Expand-ReShadeRuntime $installer (Join-Path $tools "reshade-$($deps.reshade.version)") $deps.reshade.sha256 $deps.reshade.runtime_sha256
    Set-NativeRuntime $release $runtime $reshade
    Update-CampaignRules (Join-Path $releaseRoot 'config/campaign.json') (Join-Path $dataRoot 'campaign.json') $release.Version
    $paths.game_path = $game
    Write-Utf8File (Join-Path $PSScriptRoot 'local.json') ($paths | ConvertTo-Json)
    & $PythonCommand (Join-Path $PSScriptRoot 'install_pcl.py')
    if ($LASTEXITCODE) { throw 'PCL installation failed. Correct the error and rerun setup.' }
    Write-Host 'Setup complete. Run START-EldenCraft-PCL.cmd, then click Launch in PCL.'
} finally { $lock.Dispose() }
