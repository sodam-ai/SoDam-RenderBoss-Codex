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

function Publish-GitHubSnapshot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommitMessage
    )

    $remoteUrl = git remote get-url origin
    if ($LASTEXITCODE -ne 0 -or -not $remoteUrl) {
        throw "Git remote 'origin' is not configured."
    }
    if ($remoteUrl -notmatch "github\.com[/:](?<owner>[^/]+)/(?<repo>[^/]+?)(?:\.git)?$") {
        throw "Origin is not a supported GitHub repository URL: $remoteUrl"
    }
    $owner = $matches.owner
    $repo = $matches.repo

    $credentialLines = @("protocol=https", "host=github.com", "") |
        git credential fill
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read GitHub credentials."
    }
    $credential = @{}
    foreach ($line in $credentialLines) {
        if ($line -match "^([^=]+)=(.*)$") {
            $credential[$matches[1]] = $matches[2]
        }
    }
    if (-not $credential.password) {
        throw "GitHub credentials do not contain a token."
    }

    $headers = @{
        Authorization = "Bearer $($credential.password)"
        Accept = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent" = "architectural-render-guard-publisher"
    }
    $apiRoot = "https://api.github.com/repos/$owner/$repo"

    $treeEntries = @()
    $trackedFiles = git ls-files
    if ($LASTEXITCODE -ne 0 -or -not $trackedFiles) {
        throw "No tracked files were found."
    }
    foreach ($relativePath in $trackedFiles) {
        $filePath = Join-Path $pluginRoot $relativePath
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
            continue
        }
        $blobBody = @{
            content = [Convert]::ToBase64String(
                [System.IO.File]::ReadAllBytes($filePath)
            )
            encoding = "base64"
        } | ConvertTo-Json
        $blob = Invoke-RestMethod `
            -Uri "$apiRoot/git/blobs" `
            -Headers $headers `
            -Method Post `
            -Body $blobBody `
            -ContentType "application/json"
        $treeEntries += @{
            path = $relativePath.Replace("\", "/")
            mode = "100644"
            type = "blob"
            sha = $blob.sha
        }
    }

    $treeBody = @{ tree = $treeEntries } | ConvertTo-Json -Depth 6
    $tree = Invoke-RestMethod `
        -Uri "$apiRoot/git/trees" `
        -Headers $headers `
        -Method Post `
        -Body $treeBody `
        -ContentType "application/json"

    $parentSha = $null
    try {
        $remoteRef = Invoke-RestMethod `
            -Uri "$apiRoot/git/ref/heads/main" `
            -Headers $headers `
            -Method Get
        $parentSha = $remoteRef.object.sha
    }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -ne 404) {
            throw
        }
    }

    $commitData = @{
        message = $CommitMessage
        tree = $tree.sha
    }
    if ($parentSha) {
        $commitData.parents = @($parentSha)
    }
    $commit = Invoke-RestMethod `
        -Uri "$apiRoot/git/commits" `
        -Headers $headers `
        -Method Post `
        -Body ($commitData | ConvertTo-Json -Depth 4) `
        -ContentType "application/json"

    if ($parentSha) {
        $refBody = @{ sha = $commit.sha; force = $false } | ConvertTo-Json
        Invoke-RestMethod `
            -Uri "$apiRoot/git/refs/heads/main" `
            -Headers $headers `
            -Method Patch `
            -Body $refBody `
            -ContentType "application/json" | Out-Null
    }
    else {
        $refBody = @{ ref = "refs/heads/main"; sha = $commit.sha } |
            ConvertTo-Json
        Invoke-RestMethod `
            -Uri "$apiRoot/git/refs" `
            -Headers $headers `
            -Method Post `
            -Body $refBody `
            -ContentType "application/json" | Out-Null
    }

    Write-Host "Published through GitHub API: https://github.com/$owner/$repo"
}

Push-Location $pluginRoot
try {
    $branch = (git branch --show-current).Trim()
    $remoteUrl = (git remote get-url origin).Trim()
    if (-not $branch -or $branch -in @("main", "master")) {
        throw "Publish from a non-default working branch, then open a PR."
    }
    if ($remoteUrl -notmatch '^https://github\.com/sodam-ai/_SoDam-RenderBoss(?:\.git)?$') {
        throw "Refusing to publish to an unexpected origin: $remoteUrl"
    }
    if (Test-Path -LiteralPath (Join-Path $pluginRoot "CHECKPOINT.md")) {
        throw "Review or move CHECKPOINT.md before publishing; it must not be committed."
    }
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
        git push origin "HEAD:refs/heads/$branch"
        if ($LASTEXITCODE -ne 0) {
            throw "Git push failed. Resolve the error and retry; no API fallback is used."
        }
    }

    Write-Host "Published architectural-render-guard $version"
}
finally {
    Pop-Location
}
