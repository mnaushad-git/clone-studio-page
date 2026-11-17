<#
.SYNOPSIS
    Tests SSH access to the VPS, then runs the read-only discovery script and saves its report.

.DESCRIPTION
    Windows PowerShell can't redirect a file into a command with "<", and its ">" writes UTF-16.
    This script sends vps-discovery.sh with Linux line endings and saves the report as UTF-8.
    Nothing here changes the server.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File deploy\scripts\Run-VpsDiscovery.ps1 -User tb-deploy
#>
param(
    [Parameter(Mandatory = $true)] [string] $User,
    [string] $ServerAddress = "2.25.11.35",
    [string] $KeyPath = (Join-Path $env:USERPROFILE ".ssh\terrific_bites_vps"),
    [string] $OutputPath = (Join-Path (Get-Location) "vps-report.txt"),
    [switch] $AccessCheckOnly
)

$discoveryScript = Join-Path $PSScriptRoot "vps-discovery.sh"

if (-not (Test-Path $KeyPath)) {
    Write-Error "SSH key not found: $KeyPath"
    exit 2
}
if (-not (Test-Path $discoveryScript)) {
    Write-Error "Discovery script not found: $discoveryScript"
    exit 2
}

$sshOptions = @(
    "-i", $KeyPath,
    "-o", "IdentitiesOnly=yes",
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=yes",
    "-o", "ConnectTimeout=15"
)
$target = "$User@$ServerAddress"

Write-Host "Testing SSH access to $target ..."
$identity = & ssh @sshOptions $target 'echo OK: $(whoami)@$(hostname), groups: $(id -nG)'
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "SSH access failed. Stop here and check the message above:"
    Write-Host "  Permission denied (publickey)  The key isn't installed for '$User'."
    Write-Host "  Host key verification failed   Compare the server fingerprint before going on."
    Write-Host "  Connection timed out           Check the firewall and SSH port in hPanel."
    exit 1
}
Write-Host $identity

if ($AccessCheckOnly) {
    exit 0
}

$script = (Get-Content -Raw -Path $discoveryScript) -replace "`r`n", "`n"
if ($script -match "[^\x00-\x7F]") {
    Write-Error "The discovery script must stay ASCII to survive Windows PowerShell's pipe encoding."
    exit 2
}

Write-Host "Running the read-only discovery script ..."
$previousEncoding = $OutputEncoding
$OutputEncoding = [System.Text.Encoding]::ASCII
try {
    $report = $script | & ssh @sshOptions $target "tr -d '\r' | bash -s -- --stdout"
    $code = $LASTEXITCODE
} finally {
    $OutputEncoding = $previousEncoding
}
if ($code -ne 0) {
    Write-Error "The discovery script ended with exit code $code. The report may be incomplete."
}

$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($OutputPath, [string[]]$report, $utf8)
Write-Host "Report saved: $OutputPath"
Write-Host "It lists your server's applications and domains, so skim it before sharing it."
exit $code
