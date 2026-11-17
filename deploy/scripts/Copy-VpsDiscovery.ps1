<#
.SYNOPSIS
    Copies a single command to the clipboard that runs vps-discovery.sh in the hPanel browser terminal.

.DESCRIPTION
    The command carries the script compressed and encoded, so it is one paste with no repository
    access on the VPS. It unpacks to a private temporary file, refuses to run if the checksum
    differs (for example after a truncated paste), runs it, and removes that temporary file.
    Nothing here connects to the server.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File deploy\scripts\Copy-VpsDiscovery.ps1
#>
param([string] $OutFile)

$scriptPath = Join-Path $PSScriptRoot "vps-discovery.sh"
$text = (Get-Content -Raw -Path $scriptPath) -replace "`r`n", "`n"
if ($text -match "[^\x00-\x7F]") {
    Write-Error "vps-discovery.sh must stay ASCII."
    exit 2
}

$bytes = [System.Text.Encoding]::ASCII.GetBytes($text)
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$hash = ($sha256.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""

$buffer = New-Object System.IO.MemoryStream
$gzip = New-Object System.IO.Compression.GZipStream($buffer, [System.IO.Compression.CompressionLevel]::Optimal, $true)
$gzip.Write($bytes, 0, $bytes.Length)
$gzip.Close()
$encoded = [Convert]::ToBase64String($buffer.ToArray())

$command = 'f=$(mktemp); echo ''{0}'' | base64 -d | gunzip >"$f" && echo "{1}  $f" | sha256sum -c --quiet && bash "$f"; rm -f "$f"; unset f' -f $encoded, $hash

if ($OutFile) {
    [System.IO.File]::WriteAllText($OutFile, $command + "`n", (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Command saved: $OutFile"
} else {
    Set-Clipboard -Value $command
    Write-Host "Copied to the clipboard ($($command.Length) characters). Paste it into the hPanel browser terminal."
}
Write-Host "Script SHA-256: $hash"
