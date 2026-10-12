[CmdletBinding()]
param(
    [string]$Repository = 'Anrixa/anrixa-audit',
    [ValidateSet('public', 'private')]
    [string]$Visibility = 'public'
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE"
    }
}

$Root = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$ExpectedPyProject = Join-Path $Root 'pyproject.toml'
$ExpectedPackage = Join-Path $Root 'src\anrixa_audit'

if (-not (Test-Path -LiteralPath $ExpectedPyProject -PathType Leaf)) {
    throw "PROJECT_ROOT_GATE=FAIL missing=$ExpectedPyProject"
}
if (-not (Test-Path -LiteralPath $ExpectedPackage -PathType Container)) {
    throw "PROJECT_ROOT_GATE=FAIL missing=$ExpectedPackage"
}

Set-Location $Root
Write-Host "PROJECT_ROOT=$Root"
Write-Host 'PROJECT_ROOT_GATE=PASS'

$Git = (Get-Command git -ErrorAction Stop).Source
$GhCommand = Get-Command gh -ErrorAction SilentlyContinue
if ($GhCommand) {
    $Gh = $GhCommand.Source
}
else {
    $KnownGh = 'C:\dev\tools\gh\2.101.0\bin\gh.exe'
    if (Test-Path -LiteralPath $KnownGh -PathType Leaf) {
        $Gh = $KnownGh
    }
    else {
        throw 'GitHub CLI (gh.exe) was not found.'
    }
}

Invoke-Native -FilePath $Gh -Arguments @('auth', 'status')

$GitDir = Join-Path $Root '.git'
if (-not (Test-Path -LiteralPath $GitDir -PathType Container)) {
    Invoke-Native -FilePath $Git -Arguments @('init', '-b', 'main')
}

$Branch = (& $Git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Could not determine current branch.'
}
if ($Branch -ne 'main') {
    throw "BRANCH_GATE=FAIL actual=$Branch expected=main"
}
Write-Host 'BRANCH_GATE=PASS'

$Remotes = @(& $Git remote)
if ($LASTEXITCODE -ne 0) {
    throw 'Could not list Git remotes.'
}

if ($Remotes -contains 'origin') {
    $TrackedRemote = (& $Git remote get-url origin).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not read origin URL.'
    }
    Write-Host "ORIGIN=$TrackedRemote"
}

Invoke-Native -FilePath $Git -Arguments @('add', '--all')

$Status = @(& $Git status --porcelain)
if ($LASTEXITCODE -ne 0) {
    throw 'git status failed.'
}

if ($Status.Count -gt 0) {
    Write-Host 'STAGED_CHANGE_GATE=PASS'
    Invoke-Native -FilePath $Git -Arguments @(
        'commit',
        '-m',
        'Initial release: anrixa-audit 0.1.0'
    )
}
else {
    Write-Host 'STAGED_CHANGE_GATE=NO_CHANGES'
}

# HEAD is only queried after the commit/no-change decision.
# If there are no changes in an empty repository, this is a real failure.
$HeadFile = Join-Path $GitDir 'HEAD'
if (-not (Test-Path -LiteralPath $HeadFile -PathType Leaf)) {
    throw 'HEAD_FILE_GATE=FAIL'
}

# Use git log only after a commit is expected to exist.
$Head = (& $Git log -1 --format='%H').Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Head)) {
    throw 'HEAD_COMMIT_GATE=FAIL'
}
Write-Host "LOCAL_HEAD=$Head"
Write-Host 'HEAD_COMMIT_GATE=PASS'

# Query repo existence without letting an expected 404/nonzero become a PS terminating error.
$OldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $Gh repo view $Repository '--json' 'nameWithOwner' *> $null
$RepoViewExit = $LASTEXITCODE
$ErrorActionPreference = $OldEap
$RepoExists = ($RepoViewExit -eq 0)

$ExpectedUrl = "https://github.com/$Repository.git"

if (-not $RepoExists) {
    Write-Host "REMOTE_REPOSITORY=CREATE $Repository"
    $Description = 'Deterministic audit gates, SHA-256 evidence, and file manifests for controlled Python workflows.'
    Invoke-Native -FilePath $Gh -Arguments @(
        'repo', 'create', $Repository,
        "--$Visibility",
        '--description', $Description,
        '--source', $Root,
        '--remote', 'origin',
        '--push'
    )
}
else {
    Write-Host "REMOTE_REPOSITORY=EXISTS $Repository"

    $Remotes = @(& $Git remote)
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not list Git remotes after repository check.'
    }

    if ($Remotes -notcontains 'origin') {
        Invoke-Native -FilePath $Git -Arguments @('remote', 'add', 'origin', $ExpectedUrl)
    }
    else {
        $CurrentOrigin = (& $Git remote get-url origin).Trim()
        if ($LASTEXITCODE -ne 0) {
            throw 'Could not read existing origin URL.'
        }
        if ($CurrentOrigin -ne $ExpectedUrl) {
            throw "ORIGIN_GATE=FAIL actual=$CurrentOrigin expected=$ExpectedUrl"
        }
    }

    Invoke-Native -FilePath $Git -Arguments @('push', '-u', 'origin', 'main')
}

$FinalHead = (& $Git log -1 --format='%H').Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($FinalHead)) {
    throw 'FINAL_HEAD_GATE=FAIL'
}

Write-Host "REPOSITORY=$Repository"
Write-Host "HEAD=$FinalHead"
Write-Host 'GITHUB_BOOTSTRAP_GATE=PASS'
