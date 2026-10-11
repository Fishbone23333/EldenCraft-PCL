$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $PSScriptRoot 'character-switch.cs') -ReferencedAssemblies 'System.Web.Extensions','System','System.Core'
function Assert-Switch([bool]$Condition, [string]$Description) {
    if (-not $Condition) { throw $Description }
    Write-Output "PASS: $Description"
}
$edge = New-Object EldenCraftPcl.SwitchEdge
Assert-Switch (-not $edge.Poll($false, $true, $false, 0)) 'F8 outside game is ignored'
Assert-Switch (-not $edge.Poll($true, $true, $false, 20)) 'Alt-tab with held F8 never toggles'
$null = $edge.Poll($true, $false, $false, 50)
Assert-Switch ($edge.Poll($true, $true, $false, 100)) 'Fresh foreground press toggles once'
Assert-Switch (-not $edge.Poll($true, $true, $false, 1000)) 'Holding F8 cannot repeatedly toggle'
$null = $edge.Poll($true, $false, $false, 1010)
Assert-Switch (-not $edge.Poll($true, $true, $true, 1020)) 'Pending acknowledgement prevents another command'
Assert-Switch (-not $edge.Poll($true, $true, $false, 1100)) 'Acknowledgement arrival cannot turn held F8 into a press'
$null = $edge.Poll($true, $false, $false, 1200)
Assert-Switch ($edge.Poll($true, $true, $false, 1500)) 'Release and press permits return to Steve'
$sequence = [EldenCraftPcl.CharacterSwitch]::NextSequence('{"seq":900000000000000000,"action":"toggle_build"}', 1)
Assert-Switch ($sequence -gt 900000000000000000) 'New helper sequence exceeds previous session command'
$folder = Join-Path $PSScriptRoot 'switch-test-temp'
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$path = Join-Path $folder 'command.json'
[EldenCraftPcl.CharacterSwitch]::Publish($path, $sequence)
[EldenCraftPcl.CharacterSwitch]::Publish($path, ($sequence + 1))
$command = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
Assert-Switch ($command.action -eq 'toggle_build' -and $command.seq -eq ($sequence + 1)) 'Atomic publication carries only supported toggle and increasing sequence'
$resolved = [IO.Path]::GetFullPath($folder)
if (-not $resolved.StartsWith([IO.Path]::GetFullPath($PSScriptRoot) + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Test path outside adapter' }
Remove-Item -LiteralPath $path
Remove-Item -LiteralPath $folder
