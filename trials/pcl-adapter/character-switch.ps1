param([Parameter(Mandatory=$true)][int]$GameProcessId, [Parameter(Mandatory=$true)][string]$RuntimeDataDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $PSScriptRoot 'character-switch.cs') -ReferencedAssemblies 'System.Web.Extensions','System','System.Core'
[EldenCraftPcl.CharacterSwitch]::Run($GameProcessId, $RuntimeDataDirectory)
