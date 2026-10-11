function Read-PclPaths {
    $repository = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $settingsFile = Join-Path $PSScriptRoot 'local.json'
    $settings = if (Test-Path -LiteralPath $settingsFile) {
        Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8 | ConvertFrom-Json
    } else { [pscustomobject]@{} }
    $paths = @{}
    foreach ($entry in @{
        pcl_root = 'D:\PCL'
        release_root = 'trials\EldenCraft-0.25.5'
        data_root = 'trials\EldenCraftData'
        game_path = ''
    }.GetEnumerator()) {
        $property = $settings.PSObject.Properties[$entry.Key]
        $value = if ($property -and $property.Value) { [string]$property.Value } else { $entry.Value }
        if ($value -and -not [IO.Path]::IsPathRooted($value)) { $value = Join-Path $repository $value }
        $paths[$entry.Key] = if ($value) { [IO.Path]::GetFullPath($value) } else { '' }
    }
    return $paths
}
