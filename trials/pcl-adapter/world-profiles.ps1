# A profile selects a separate vanilla world; no save folders or pairing tags are modified.
function ConvertTo-WorldProfile {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return 'default' }
    $worldKey = $Value.Trim().ToLowerInvariant()
    if ($worldKey -cnotmatch '^[a-z0-9][a-z0-9_-]{0,39}\z') {
        throw 'World profile must use 1-40 letters (a-z), digits, - or _, and start with a letter or digit.'
    }
    return $worldKey
}

function Read-WorldProfile {
    param([string]$DataRoot)
    $settingsFile = Join-Path $DataRoot 'world-profile.json'
    if (-not (Test-Path -LiteralPath $settingsFile)) { return 'default' }
    $settings = Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $settings -or -not $settings.PSObject.Properties['profile'] -or
        $settings.profile -isnot [string] -or [string]::IsNullOrWhiteSpace($settings.profile)) {
        throw "Invalid world selection: $settingsFile"
    }
    return ConvertTo-WorldProfile $settings.profile
}

function Save-WorldProfile {
    param([string]$DataRoot, [string]$Value)
    $worldKey = ConvertTo-WorldProfile $Value
    New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null
    $settingsFile = Join-Path $DataRoot 'world-profile.json'
    $temporary = $settingsFile + '.tmp'
    $json = @{ profile = $worldKey } | ConvertTo-Json
    [IO.File]::WriteAllText($temporary, $json, (New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $temporary -Destination $settingsFile -Force
}

function Select-WorldProfile {
    param([string]$Instance, [string]$Current)
    $profiles = @('default')
    $saves = Join-Path $Instance 'saves'
    if (Test-Path -LiteralPath $saves) {
        $profiles += @(Get-ChildItem -LiteralPath $saves -Directory |
            Where-Object { $_.Name -cmatch '^EldenCraft - [a-z0-9][a-z0-9_-]{0,39}\z' } |
            ForEach-Object { $_.Name.Substring('EldenCraft - '.Length) } |
            Where-Object { $_ -ne 'default' } | Sort-Object -Unique)
    }
    Write-Host '请选择与法环角色对应的 MC 世界。'
    Write-Host '旧世界的物品和进度会保留；法环角色仍需在法环菜单中选择。'
    Write-Host "当前编号：$Current（default 是原来的世界）"
    for ($i = 0; $i -lt $profiles.Count; $i++) {
        Write-Host (('{0}. {1}' -f ($i + 1), $profiles[$i]))
    }
    Write-Host '0. 输入新的世界编号（例如 new-character）'
    $choice = Read-Host '输入序号，直接回车保留当前编号'
    if ([string]::IsNullOrWhiteSpace($choice)) { return $Current }
    if ($choice -eq '0') {
        $name = Read-Host '世界编号：1-40 个英文字母、数字、- 或 _，以字母或数字开头'
        if ([string]::IsNullOrWhiteSpace($name)) { throw 'A new profile name is required.' }
        return ConvertTo-WorldProfile $name
    }
    $index = 0
    if (-not [int]::TryParse($choice, [ref]$index) -or $index -lt 1 -or $index -gt $profiles.Count) {
        throw 'Invalid world selection. Run SELECT-EldenCraft-WORLD.cmd again.'
    }
    return $profiles[$index - 1]
}
