$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'world-profiles.ps1')
$checks = 0
function Assert-WorldCheck([bool]$Value, [string]$Message) {
    $script:checks++
    if (-not $Value) { throw $Message }
}
function Assert-WorldReject([scriptblock]$Action, [string]$Message) {
    $refused = $false
    try { & $Action | Out-Null } catch { $refused = $true }
    Assert-WorldCheck $refused $Message
}

$testRoot = Join-Path $PSScriptRoot ('.profile-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
try {
    $dataRoot = Join-Path $testRoot 'data'
    $testInstance = Join-Path $testRoot 'instance'
    $testSaves = Join-Path $testInstance 'saves'
    foreach ($folder in @('EldenCraft', 'EldenCraft - archer', 'Survival')) {
        $path = Join-Path $testSaves $folder
        New-Item -ItemType Directory -Force -Path $path | Out-Null
        [IO.File]::WriteAllText((Join-Path $path 'level.dat'), 'save sentinel')
    }
    $before = @(Get-ChildItem -LiteralPath $testSaves -Recurse -File | Get-FileHash)
    Assert-WorldCheck ((Read-WorldProfile $dataRoot) -eq 'default') 'First run keeps original world'
    Assert-WorldCheck ((ConvertTo-WorldProfile 'NEW-Character') -eq 'new-character') 'Windows profile case is stable'
    Assert-WorldCheck ((ConvertTo-WorldProfile ('a' * 40)) -eq ('a' * 40)) 'Allow maximum profile length'
    Save-WorldProfile $dataRoot 'new-character'
    Assert-WorldCheck ((Read-WorldProfile $dataRoot) -eq 'new-character') 'Selection survives next launch'
    $selectionBefore = [IO.File]::ReadAllText((Join-Path $dataRoot 'world-profile.json'))
    foreach ($invalid in @('../old', 'a/b', 'a\b', 'a:b', 'a b', '_a', ('a' * 41), "a`nb")) {
        Assert-WorldReject { Save-WorldProfile $dataRoot $invalid } "Reject unsafe profile: $invalid"
    }
    Assert-WorldCheck (([IO.File]::ReadAllText((Join-Path $dataRoot 'world-profile.json'))) -eq $selectionBefore) 'Invalid selections preserve previous setting'
    Save-WorldProfile $dataRoot 'default'
    Assert-WorldCheck ((Read-WorldProfile $dataRoot) -eq 'default') 'Original world can be selected again'

    # Exercise the real menu without opening either game.
    function Read-Host { param([string]$Prompt) return $script:answers.Dequeue() }
    $script:answers = [Collections.Generic.Queue[string]]::new()
    $script:answers.Enqueue('2')
    Assert-WorldCheck ((Select-WorldProfile $testInstance 'default') -eq 'archer') 'Existing profile is selectable'
    $script:answers.Enqueue('0')
    $script:answers.Enqueue('NEW-Character')
    Assert-WorldCheck ((Select-WorldProfile $testInstance 'default') -eq 'new-character') 'New profile is selectable'
    $script:answers.Enqueue('')
    Assert-WorldCheck ((Select-WorldProfile $testInstance 'archer') -eq 'archer') 'Enter retains current profile'
    $script:answers.Enqueue('0')
    $script:answers.Enqueue('')
    Assert-WorldReject { Select-WorldProfile $testInstance 'archer' } 'Empty new profile is rejected'
    $script:answers.Enqueue('9')
    Assert-WorldReject { Select-WorldProfile $testInstance 'archer' } 'Out-of-range menu input is rejected'

    foreach ($corrupt in @('{"profile":"../old"}', '{"profile":null}', '{"profile":false}', '{}', 'broken json')) {
        [IO.File]::WriteAllText((Join-Path $dataRoot 'world-profile.json'), $corrupt)
        Assert-WorldReject { Read-WorldProfile $dataRoot } 'Invalid settings never silently open another world'
    }
    $after = @(Get-ChildItem -LiteralPath $testSaves -Recurse -File | Get-FileHash)
    Assert-WorldCheck ($after.Count -eq $before.Count) 'World selection does not add or remove save files'
    for ($i = 0; $i -lt $before.Count; $i++) {
        Assert-WorldCheck ($after[$i].Path -eq $before[$i].Path -and $after[$i].Hash -eq $before[$i].Hash) 'World data remains unchanged'
    }
    Write-Host "World profile checks: $checks passed"
} finally {
    $resolved = [IO.Path]::GetFullPath($testRoot)
    $adapterRoot = [IO.Path]::GetFullPath($PSScriptRoot) + '\'
    if (-not $resolved.StartsWith($adapterRoot, [StringComparison]::OrdinalIgnoreCase) -or
        [IO.Path]::GetFileName($resolved) -notlike '.profile-test-*') { throw 'Unsafe profile test cleanup path' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
