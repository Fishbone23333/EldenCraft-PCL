param(
    [ValidateSet('check', 'play')][string]$Mode = 'play',
    [switch]$CpuFrames,
    [switch]$GuestOnly,
    [switch]$HostOnly,
    [int]$StartupTimeoutSeconds = 600
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$adapterMode = $Mode
$adapterCpuFrames = $CpuFrames
$trialRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'paths.ps1')
$adapterPaths = Read-PclPaths
$releaseRoot = $adapterPaths.release_root
$dataRoot = $adapterPaths.data_root
$runtime = Join-Path $dataRoot 'runtime'
$instanceName = 'EldenCraft-26.3-Fabric-0.19.5'
$pclRoot = $adapterPaths.pcl_root
$minecraftRoot = Join-Path $pclRoot '.minecraft'
$instance = Join-Path $minecraftRoot "versions\$instanceName"
$game = $adapterPaths.game_path
$pclExe = Join-Path $pclRoot 'Plain Craft Launcher 2.exe'
$logs = Join-Path $dataRoot 'logs'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$lock = $null
New-Item -ItemType Directory -Force -Path $logs | Out-Null
Start-Transcript -Path (Join-Path $logs "pcl-$stamp-$PID.log") | Out-Null
try {
    # Use the verified, unchanged upstream launcher helpers for hashes, backups and me3.
    . (Join-Path $releaseRoot 'scripts\windows.ps1') -Mode check -GamePath $game -DataDirectory $dataRoot -NonInteractive
    $game = Find-EldenRing $game $null $releaseRoot
    if (-not $game) { throw 'Elden Ring not found. Set game_path in trials/pcl-adapter/local.json.' }
    $Mode = $adapterMode
    $CpuFrames = $adapterCpuFrames
    $release = Read-Release $releaseRoot
    $deps = $release.Dependencies
    Assert-FileHash $game $deps.elden_ring.sha256
    Assert-NoReShadeConflict $game $runtime
    if (-not (Test-Path -LiteralPath (Join-Path $instance '.ma-eldencraft-pcl'))) { throw 'Run pcl-adapter/install_pcl.py to install the dedicated PCL instance first.' }
    $metadata = Get-Content -LiteralPath (Join-Path $instance "$instanceName.json") -Raw | ConvertFrom-Json
    if ($metadata.clientVersion -ne '26.3' -or $metadata.javaVersion.majorVersion -ne 25 -or $metadata.mainClass -ne 'net.fabricmc.loader.impl.launch.knot.KnotClient') { throw 'Unexpected PCL Minecraft/Fabric/Java metadata.' }
    foreach ($relative in @('eldencraft_native.dll', 'eldencraft_core.dll', 'addons/EldenCraftCompositor.addon64')) {
        Assert-FileHash (Join-Path $runtime $relative) (Get-FileHash -LiteralPath (Join-Path $releaseRoot "payload/$relative") -Algorithm SHA256).Hash
    }
    $bridgeManifest = Join-Path $PSScriptRoot 'patches/manifest.json'
    if (Test-Path -LiteralPath $bridgeManifest) {
        $bridgeBuild = Get-Content -LiteralPath $bridgeManifest -Raw | ConvertFrom-Json
        if ([IO.Path]::GetFileName($bridgeBuild.file) -ne $bridgeBuild.file -or $bridgeBuild.file -notlike '*.jar') { throw 'Invalid local bridge manifest filename.' }
        Assert-FileHash (Join-Path $PSScriptRoot ('patches/' + $bridgeBuild.file)) $bridgeBuild.sha256
        Assert-FileHash (Join-Path $instance ('mods/' + $bridgeBuild.file)) $bridgeBuild.sha256
    } else {
        Assert-FileHash (Join-Path $instance 'mods/eldencraft-bridge-0.25.5.jar') (Get-FileHash -LiteralPath (Join-Path $releaseRoot 'payload/eldencraft-bridge.jar') -Algorithm SHA256).Hash
    }
    if (@(Get-ChildItem -LiteralPath (Join-Path $instance 'mods') -Filter 'eldencraft-bridge*.jar').Count -ne 1) { throw 'The PCL instance must contain exactly one EldenCraft bridge JAR.' }
    Assert-FileHash (Join-Path $instance "mods/fabric-api-$($deps.minecraft.fabric_api.version).jar") $deps.minecraft.fabric_api.sha256
    if (-not (Test-Path -LiteralPath (Join-Path $instance 'java/bin/javaw.exe'))) { throw 'Java 25 missing from PCL instance.' }
    $link = Get-Content -LiteralPath (Join-Path $instance 'config/eldencraft-campaign-link.json') -Raw | ConvertFrom-Json
    if ($link.config -ne (Join-Path $dataRoot 'campaign.json') -or $link.directory -ne (Join-Path $runtime 'data/campaign')) { throw 'PCL campaign link does not match the native runtime.' }
    $me3 = Join-Path $dataRoot 'tools/me3-0.13.0/bin/me3.exe'
    foreach ($path in @($pclExe, $me3, (Join-Path $runtime 'ReShade64.asi'), (Join-Path $runtime 'eldencraft.me3'))) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing runtime file: $path" }
    }
    foreach ($path in @((Join-Path $PSScriptRoot 'character-switch.ps1'), (Join-Path $PSScriptRoot 'character-switch.cs'))) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing F8 switch helper: $path" }
    }
    $hostProfile = Get-Content -LiteralPath (Join-Path $runtime 'eldencraft.me3') -Raw
    if ($hostProfile -notmatch '(?m)^savefile\s*=\s*"EldenCraft.sl2"\s*$' -or $hostProfile -notmatch '(?m)^start_online\s*=\s*false\s*$') { throw 'The me3 profile must use the separate EldenCraft.sl2 save and offline mode.' }
    Assert-FileHash (Join-Path $runtime 'ReShade64.asi') $deps.reshade.runtime_sha256
    if ($Mode -eq 'check') { Write-Host ('PASS: PCL instance, shared campaign, native DLLs, bridge JAR and Elden Ring executable verified. Transport: ' + $(if ($CpuFrames) { 'CPU' } else { 'GPU' })); return }
    $lock = [IO.File]::Open((Join-Path $dataRoot 'setup.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    if ($HostOnly) {
        if (Get-Process -Name eldenring,start_protected_game -ErrorAction SilentlyContinue) { throw 'Close Elden Ring before restarting the host.' }
    } else {
        Assert-GamesClosed (Join-Path $dataRoot 'minecraft') (Join-Path $dataRoot 'tools/prism-11.1.1/prismlauncher.exe')
    }
    $otherMinecraft = @(Get-CimInstance Win32_Process -Filter "Name = 'javaw.exe' OR Name = 'java.exe'" | Where-Object { $_.CommandLine -match 'KnotClient|net\.minecraft\.client\.main\.Main|org\.multimc\.EntryPoint' -and (-not $HostOnly -or $_.CommandLine.Replace('/', '\').IndexOf($instance, [StringComparison]::OrdinalIgnoreCase) -lt 0) })
    if ($otherMinecraft.Count) { throw 'Close other Minecraft clients before starting EldenCraft: the native bridge uses one shared-memory session.' }
    $pclRunning = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath -ieq $pclExe })
    if ($pclRunning.Count -and -not $HostOnly) { throw 'Close the existing PCL window first, then use START-EldenCraft-PCL.cmd so the bridge environment is inherited.' }
    $backups = Join-Path $dataRoot 'backups'
    New-VerifiedBackup (Join-Path $env:APPDATA 'EldenRing') $backups 'elden-ring' | Out-Null
    if (-not $HostOnly) {
        New-VerifiedBackup (Join-Path $instance 'saves') $backups 'minecraft-pcl' | Out-Null
        New-VerifiedBackup (Join-Path $runtime 'data/campaign') $backups 'campaign' | Out-Null
    }
    if (-not $HostOnly) {
    $pclIni = Join-Path $minecraftRoot 'PCL.ini'
    $selection = if (Test-Path -LiteralPath $pclIni) { Get-Content -LiteralPath $pclIni -Raw -Encoding UTF8 } else { '' }
    if (Test-Path -LiteralPath $pclIni) { Copy-Item -LiteralPath $pclIni -Destination (Join-Path $backups "pcl-selection-$stamp-$PID.ini") }
    if ($selection -match '(?m)^Version:.*$') { $selection = [regex]::Replace($selection, '(?m)^Version:.*$', "Version:$instanceName") }
    else { $selection += "`r`nVersion:$instanceName`r`n" }
    Write-Utf8File $pclIni $selection
    }
    $env:ELDENCRAFT_DATA_DIR = Join-Path $runtime 'data'
    $env:ELDENCRAFT_CAMPAIGN_CONFIG = $link.config
    $env:ELDENCRAFT_CAMPAIGN_DIR = $link.directory
    $env:ELDENCRAFT_EXPECTED_SHA256 = $deps.elden_ring.sha256
    $env:RESHADE_BASE_PATH_OVERRIDE = $runtime
    $env:ELDENCRAFT_MELEE_LAB = '1'
    $env:ELDENCRAFT_NATIVE_COLLIDERS = '1'
    $env:ELDENCRAFT_NATIVE_MOBS = '1'
    $env:ELDENCRAFT_GPU_TRANSPORT = if ($CpuFrames) { '0' } else { '1' }
    # The unmodified native host validates each F8 command on its game task
    # and restores character visibility, camera, input and HUD on handoff.
    $env:ELDENCRAFT_FILE_CONTROL = '1'
    $guestLog = Join-Path $instance 'logs/latest.log'
    $launchTime = if ($HostOnly) { [DateTime]::MinValue } else { [DateTime]::UtcNow }
    # PCL is the interactive launcher the user needs to see and control.
    if (-not $HostOnly) { Start-Process -FilePath $pclExe -WorkingDirectory $pclRoot -WindowStyle Normal | Out-Null }
    if (-not $HostOnly) {
        Write-Host "PCL: select $instanceName and click Launch using your usual PCL account."
        Write-Host 'Keep this launcher open. Elden Ring starts after the Minecraft bridge is ready.'
    }
    if ($GuestOnly) { return }
    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        $processes = @(Get-CimInstance Win32_Process -Filter "Name = 'javaw.exe' OR Name = 'java.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('/', '\').IndexOf($instance, [StringComparison]::OrdinalIgnoreCase) -ge 0 })
        if ($processes.Count -and (Test-Path -LiteralPath $guestLog) -and (Get-Item -LiteralPath $guestLog).LastWriteTimeUtc -ge $launchTime) {
            if (Select-String -LiteralPath $guestLog -Pattern 'EldenCraft shared-memory and GPU bridge ready' -Quiet) { $ready = $true; break }
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "PCL Minecraft bridge startup timed out. Review $guestLog, close the games and rerun." }
    $steam = Get-ItemProperty -LiteralPath 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue
    if (-not (Get-Process -Name steam -ErrorAction SilentlyContinue) -and $steam -and $steam.SteamExe) { Start-Process -FilePath $steam.SteamExe -ArgumentList '-silent' -WindowStyle Hidden | Out-Null }
    $steamDeadline = [DateTime]::UtcNow.AddSeconds(60)
    $steamReady = $false
    while ([DateTime]::UtcNow -lt $steamDeadline) {
        $steamSession = Get-ItemProperty -LiteralPath 'HKCU:\Software\Valve\Steam\ActiveProcess' -ErrorAction SilentlyContinue
        if ($steamSession -and $steamSession.PSObject.Properties['ActiveUser'] -and $steamSession.ActiveUser -ne 0 -and (Get-Process -Name steamwebhelper -ErrorAction SilentlyContinue)) { $steamReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $steamReady) { throw 'Steam is not signed in and ready. Sign in to Steam, then rerun with -HostOnly while the dedicated PCL Minecraft world stays open.' }
    # ActiveUser may be cached before the cold client is fully initialized.
    $steamProcess = Get-Process -Name steam | Select-Object -First 1
    $steamAgeSeconds = ([DateTime]::Now - $steamProcess.StartTime).TotalSeconds
    if ($steamAgeSeconds -lt 30) { Start-Sleep -Seconds ([int][Math]::Ceiling(30 - $steamAgeSeconds)) }
    $hostProcess = Start-EldenRingLoader $me3 $runtime (Join-Path $runtime 'eldencraft.me3') $game $logs $stamp
    Start-Sleep -Seconds 2
    Assert-LoaderStarted $hostProcess $logs $stamp
    $gameDeadline = [DateTime]::UtcNow.AddSeconds(20)
    $gameSeen = $false
    while ([DateTime]::UtcNow -lt $gameDeadline) {
        if (Get-Process -Name eldenring -ErrorAction SilentlyContinue) { $gameSeen = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $gameSeen) { throw 'me3 returned but Elden Ring exited before opening. See the me3 logs; no bridge connection has been verified.' }
    Start-Sleep -Seconds 8
    if (-not (Get-Process -Name eldenring -ErrorAction SilentlyContinue)) { throw 'Elden Ring exited during startup. See the me3 and native runtime logs.' }
    $runningGame = Get-Process -Name eldenring | Select-Object -First 1
    $switchScript = Join-Path $PSScriptRoot 'character-switch.ps1'
    $switchProcess = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe') `
        -ArgumentList @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $switchScript + '"'), '-GameProcessId', $runningGame.Id, '-RuntimeDataDirectory', ('"' + (Join-Path $runtime 'data') + '"')) `
        -WindowStyle Hidden -PassThru -RedirectStandardError (Join-Path $logs "pcl-switch-$stamp.stderr.log")
    Start-Sleep -Seconds 2
    if ($switchProcess.HasExited) { throw "F8 helper exited unexpectedly. See $(Join-Path $logs "pcl-switch-$stamp.stderr.log"). F6 remains the built-in fallback." }
    Write-Host 'Elden Ring is running offline with EldenCraft.sl2. Load or create a character to connect. F8 switches Steve / the native Elden Ring character during gameplay.'
} finally {
    if ($lock) { $lock.Dispose() }
    Stop-Transcript | Out-Null
}
