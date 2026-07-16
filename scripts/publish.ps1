param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Message,

    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$manifestPath = Join-Path $pluginRoot ".codex-plugin\plugin.json"
$marketplacePath = Join-Path $pluginRoot ".agents\plugins\marketplace.json"

function Resolve-CodexHome {
    if ($env:CODEX_HOME) {
        return $env:CODEX_HOME
    }
    if (Test-Path -LiteralPath "D:\CodexHome") {
        return "D:\CodexHome"
    }
    return (Join-Path $HOME ".codex")
}

function Resolve-SystemSkillScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $codexHome = Resolve-CodexHome
    $candidate = Join-Path $codexHome $RelativePath
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }
    return $null
}

Push-Location $pluginRoot
try {
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Unit tests failed."
    }

    Get-Content -Raw $manifestPath | ConvertFrom-Json | Out-Null
    Get-Content -Raw $marketplacePath | ConvertFrom-Json | Out-Null

    $cachebusterScript = Resolve-SystemSkillScript `
        "skills\.system\plugin-creator\scripts\update_plugin_cachebuster.py"
    if (-not $cachebusterScript) {
        throw "Codex plugin cachebuster helper was not found."
    }
    python $cachebusterScript $pluginRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Plugin cachebuster update failed."
    }

    $manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
    $version = $manifest.version
    if (-not $version) {
        throw "Plugin manifest does not contain a version."
    }

    $cacheRoots = @(
        (Join-Path (Resolve-CodexHome) "plugins\cache\personal\architectural-render-guard"),
        (Join-Path $HOME ".codex\plugins\cache\personal\architectural-render-guard")
    ) | Select-Object -Unique

    foreach ($cacheRoot in $cacheRoots) {
        if (-not (Test-Path -LiteralPath $cacheRoot)) {
            continue
        }
        $resolvedRoot = (Resolve-Path -LiteralPath $cacheRoot).Path
        if ($resolvedRoot -notlike "*\plugins\cache\personal\architectural-render-guard") {
            throw "Refusing unexpected cache root: $resolvedRoot"
        }

        $target = Join-Path $resolvedRoot $version
        if (-not (Test-Path -LiteralPath $target)) {
            New-Item -ItemType Directory -Path $target | Out-Null
            Get-ChildItem -LiteralPath $pluginRoot -Force |
                Where-Object { $_.Name -ne ".git" } |
                Copy-Item -Destination $target -Recurse -Force
        }
    }

    git add -A
    $pending = git status --porcelain
    if (-not $pending) {
        Write-Host "No repository changes to publish."
        exit 0
    }

    git commit -m $Message
    if ($LASTEXITCODE -ne 0) {
        throw "Git commit failed."
    }

    if (-not $SkipPush) {
        git push origin main
        if ($LASTEXITCODE -ne 0) {
            throw "Git push failed."
        }
    }

    Write-Host "Published architectural-render-guard $version"
}
finally {
    Pop-Location
}
